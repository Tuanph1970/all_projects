from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, func, and_, or_
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.cache import cache, CacheKeys, CacheInvalidation
from app.core.config import settings
from app.routers.auth import get_current_user, get_optional_current_user
from app.models.user import User, UserRole
from app.models.product import (
    Product, Category, ProductImage, Brand,
    ProductVariant, PriceHistory, ProductTag,
    ProductTagAssociation, ProductAttribute, ProductSpecification
)
from app.models.review import Review
from app.schemas.product import (
    ProductCreate, ProductResponse, ProductUpdate,
    CategoryCreate, CategoryResponse, CategoryDetailResponse,
    BrandCreate, BrandResponse,
    ProductVariantCreate, ProductVariantResponse, ProductVariantUpdate,
    PriceHistoryResponse,
    ProductTagResponse,
    ProductAttributeResponse, ProductAttributeCreate,
    ProductSpecificationResponse, ProductSpecificationCreate,
    ProductAvailabilityResponse, ProductCompareResponse
)
from app.services.image_service import image_service
from app.services.product_analytics import product_analytics
import uuid
import random
import logging
import re

logger = logging.getLogger(__name__)

router = APIRouter()

# Categories
@router.post("/categories", response_model=CategoryResponse)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    db_category = Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.get("/categories", response_model=List[CategoryResponse])
def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Try cache first
    cache_key = CacheKeys.categories()
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache HIT: categories")
        return cached_data[skip:skip+limit]

    # Query database
    categories = db.query(Category).filter(Category.is_active == True).all()

    # Cache all categories
    categories_data = [CategoryResponse.from_orm(c).model_dump() for c in categories]
    cache.set(cache_key, categories_data, ttl=settings.CACHE_TTL_CATEGORIES)

    return categories_data[skip:skip+limit]

# Products
@router.post("/", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can create products")
    
    product_data = product.dict(exclude={"images"})
    product_data["seller_id"] = current_user.id
    product_data["sku"] = str(uuid.uuid4())[:8].upper()
    
    db_product = Product(**product_data)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    # Add images
    for img_data in product.images:
        img_data_dict = img_data.dict()
        img_data_dict["product_id"] = db_product.id
        db_image = ProductImage(**img_data_dict)
        db.add(db_image)
    
    db.commit()
    db.refresh(db_product)

    # Invalidate relevant caches
    CacheInvalidation.invalidate_all_products()

    return db_product

@router.get("/", response_model=List[ProductResponse])
def read_products(
    skip: int = 0,
    limit: int = 20,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = Query("created_at", regex="^(created_at|price|name)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.is_active == True)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if search:
        query = query.filter(
            Product.name.contains(search) | 
            Product.description.contains(search) |
            Product.tags.contains(search)
        )
    
    if min_price:
        query = query.filter(Product.price >= min_price)
    
    if max_price:
        query = query.filter(Product.price <= max_price)
    
    # Sorting
    if sort_order == "desc":
        query = query.order_by(desc(getattr(Product, sort_by)))
    else:
        query = query.order_by(asc(getattr(Product, sort_by)))
    
    products = query.offset(skip).limit(limit).all()
    return products

@router.get("/featured", response_model=List[ProductResponse])
def get_featured_products(
    limit: int = Query(10, le=20),
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get featured products with optional category filter"""
    # Try cache first
    cache_key = CacheKeys.featured_products(category_id)
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache HIT: featured products")
        return cached_data[:limit]

    query = db.query(Product).filter(
        Product.is_featured == True,
        Product.is_active == True,
        Product.quantity_available > 0
    )

    if category_id:
        query = query.filter(Product.category_id == category_id)

    # Order by created_at desc to show newest featured products first
    products = query.order_by(desc(Product.created_at)).limit(20).all()

    # Cache results
    products_data = [ProductResponse.from_orm(p).model_dump() for p in products]
    cache.set(cache_key, products_data, ttl=settings.CACHE_TTL_FEATURED)

    return products_data[:limit]

@router.get("/trending", response_model=List[ProductResponse])
def get_trending_products(
    limit: int = Query(10, le=20),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get trending products based on recent activity"""
    from datetime import datetime, timedelta

    # Calculate trending based on recent reviews and orders
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Subquery for recent review counts
    recent_reviews = db.query(
        Review.product_id,
        func.count(Review.id).label('recent_review_count')
    ).filter(
        Review.created_at >= cutoff_date
    ).group_by(Review.product_id).subquery()

    # Get products with recent activity
    trending_query = db.query(Product).outerjoin(
        recent_reviews, Product.id == recent_reviews.c.product_id
    ).filter(
        Product.is_active == True,
        Product.quantity_available > 0
    ).order_by(
        desc(func.coalesce(recent_reviews.c.recent_review_count, 0)),
        desc(Product.created_at)
    )

    products = trending_query.limit(limit).all()
    return products

@router.get("/{product_id}", response_model=ProductResponse)
def read_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).options(
        joinedload(Product.seller),
        joinedload(Product.category),
        joinedload(Product.images),
        joinedload(Product.reviews)
    ).filter(Product.id == product_id, Product.is_active == True).first()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/{product_id}/related", response_model=List[ProductResponse])
def get_related_products(
    product_id: int, 
    limit: int = Query(10, le=20),
    db: Session = Depends(get_db)
):
    """Get related products based on category and tags"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get products from the same category
    related_query = db.query(Product).filter(
        Product.id != product_id,
        Product.category_id == product.category_id,
        Product.is_active == True
    )
    
    # If product has tags, prioritize products with similar tags
    if product.tags:
        product_tags = [tag.strip().lower() for tag in product.tags.split(',')]
        tag_conditions = [Product.tags.ilike(f"%{tag}%") for tag in product_tags]
        
        # First try to get products with matching tags
        related_with_tags = related_query.filter(or_(*tag_conditions)).limit(limit).all()
        
        if len(related_with_tags) >= limit:
            return related_with_tags
        
        # If not enough with tags, fill with category products
        remaining = limit - len(related_with_tags)
        category_products = related_query.filter(
            ~Product.id.in_([p.id for p in related_with_tags])
        ).limit(remaining).all()
        
        return related_with_tags + category_products
    
    # Just return products from same category
    return related_query.limit(limit).all()

@router.get("/categories/{category_id}/products", response_model=List[ProductResponse])
def get_products_by_category(
    category_id: int,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = Query("created_at", regex="^(created_at|price|name|rating)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Get products by category with enhanced filtering"""
    query = db.query(Product).filter(
        Product.category_id == category_id,
        Product.is_active == True
    )
    
    if min_price:
        query = query.filter(Product.price >= min_price)
    
    if max_price:
        query = query.filter(Product.price <= max_price)
    
    # Enhanced sorting including rating
    if sort_by == "rating":
        # Sort by average rating
        query = query.outerjoin(Review).group_by(Product.id)
        if sort_order == "desc":
            query = query.order_by(desc(func.avg(Review.rating)))
        else:
            query = query.order_by(asc(func.avg(Review.rating)))
    else:
        if sort_order == "desc":
            query = query.order_by(desc(getattr(Product, sort_by)))
        else:
            query = query.order_by(asc(getattr(Product, sort_by)))
    
    products = query.offset(skip).limit(limit).all()
    return products

@router.get("/search/advanced")
def advanced_search(
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    material: Optional[str] = None,
    color: Optional[str] = None,
    technique: Optional[str] = None,
    tags: Optional[str] = None,
    seller_id: Optional[int] = None,
    is_featured: Optional[bool] = None,
    in_stock: Optional[bool] = None,
    sort_by: str = Query("relevance", regex="^(relevance|created_at|price|name|rating|popular)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Advanced search with multiple filters"""
    query = db.query(Product).filter(Product.is_active == True)
    
    # Text search
    if q:
        search_terms = q.split()
        search_conditions = []
        for term in search_terms:
            search_conditions.append(
                or_(
                    Product.name.ilike(f"%{term}%"),
                    Product.description.ilike(f"%{term}%"),
                    Product.tags.ilike(f"%{term}%"),
                    Product.material.ilike(f"%{term}%"),
                    Product.technique.ilike(f"%{term}%")
                )
            )
        if search_conditions:
            query = query.filter(and_(*search_conditions))
    
    # Category filter
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    # Price range
    if min_price:
        query = query.filter(Product.price >= min_price)
    if max_price:
        query = query.filter(Product.price <= max_price)
    
    # Product attributes
    if material:
        query = query.filter(Product.material.ilike(f"%{material}%"))
    if color:
        query = query.filter(Product.color.ilike(f"%{color}%"))
    if technique:
        query = query.filter(Product.technique.ilike(f"%{technique}%"))
    
    # Tags filter
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',')]
        tag_conditions = [Product.tags.ilike(f"%{tag}%") for tag in tag_list]
        query = query.filter(or_(*tag_conditions))
    
    # Seller filter
    if seller_id:
        query = query.filter(Product.seller_id == seller_id)
    
    # Featured filter
    if is_featured is not None:
        query = query.filter(Product.is_featured == is_featured)
    
    # Stock filter
    if in_stock:
        query = query.filter(Product.quantity_available > 0)
    
    # Sorting
    if sort_by == "relevance" and q:
        # Simple relevance scoring based on term matches
        pass  # Keep default order for now
    elif sort_by == "rating":
        query = query.outerjoin(Review).group_by(Product.id)
        if sort_order == "desc":
            query = query.order_by(desc(func.avg(Review.rating)))
        else:
            query = query.order_by(asc(func.avg(Review.rating)))
    elif sort_by == "popular":
        # Sort by review count as popularity indicator
        query = query.outerjoin(Review).group_by(Product.id)
        if sort_order == "desc":
            query = query.order_by(desc(func.count(Review.id)))
        else:
            query = query.order_by(asc(func.count(Review.id)))
    else:
        if sort_order == "desc":
            query = query.order_by(desc(getattr(Product, sort_by)))
        else:
            query = query.order_by(asc(getattr(Product, sort_by)))
    
    # Get total count for pagination
    total = query.count()
    products = query.offset(skip).limit(limit).all()
    
    return {
        "products": products,
        "total": total,
        "page": (skip // limit) + 1,
        "pages": (total + limit - 1) // limit,
        "has_more": skip + limit < total
    }

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this product")
    
    for field, value in product_update.dict(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    # Invalidate caches for this product
    CacheInvalidation.invalidate_product(product_id)

    return product

@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this product")

    product.is_active = False
    db.commit()

    # Invalidate caches for this product
    CacheInvalidation.invalidate_product(product_id)

    return {"message": "Product deleted successfully"}

# Additional endpoints for Week 4 & 5 features

@router.get("/home/featured", response_model=dict)
def get_home_featured_products(
    db: Session = Depends(get_db)
):
    """Get featured products for home screen with different sections"""
    # Try cache first - this is a heavy endpoint
    cache_key = CacheKeys.home_featured()
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache HIT: home featured")
        return cached_data

    # Get latest featured products
    latest_featured = db.query(Product).filter(
        Product.is_featured == True,
        Product.is_active == True,
        Product.quantity_available > 0
    ).order_by(desc(Product.created_at)).limit(6).all()
    
    # Get popular products (based on review count)
    popular_products = db.query(Product).outerjoin(Review).filter(
        Product.is_active == True,
        Product.quantity_available > 0
    ).group_by(Product.id).order_by(
        desc(func.count(Review.id))
    ).limit(6).all()
    
    # Get newest products
    newest_products = db.query(Product).filter(
        Product.is_active == True,
        Product.quantity_available > 0
    ).order_by(desc(Product.created_at)).limit(6).all()
    
    # Get products by top categories
    top_categories = db.query(Category).filter(Category.is_active == True).limit(5).all()
    categories_with_products = []
    
    for category in top_categories:
        category_products = db.query(Product).filter(
            Product.category_id == category.id,
            Product.is_active == True,
            Product.quantity_available > 0
        ).order_by(desc(Product.created_at)).limit(4).all()
        
        if category_products:
            categories_with_products.append({
                "category": category,
                "products": category_products
            })
    
    # Convert Product models to dictionaries
    featured_list = [ProductResponse.from_orm(p).model_dump() for p in latest_featured]
    popular_list = [ProductResponse.from_orm(p).model_dump() for p in popular_products]
    newest_list = [ProductResponse.from_orm(p).model_dump() for p in newest_products]

    # Convert categories with products
    categories_data = []
    for cat_item in categories_with_products:
        categories_data.append({
            "category": CategoryResponse.from_orm(cat_item["category"]).model_dump(),
            "products": [ProductResponse.from_orm(p).model_dump() for p in cat_item["products"]]
        })

    result = {
        "featured": featured_list,
        "popular": popular_list,
        "newest": newest_list,
        "categories": categories_data,
        "banner": {
            "title": "Discover Unique Ceramics",
            "subtitle": "Handcrafted pieces from talented artisans",
            "featured_product": ProductResponse.from_orm(latest_featured[0]).model_dump() if latest_featured else None
        }
    }

    # Cache the result
    cache.set(cache_key, result, ttl=settings.CACHE_TTL_HOME)

    return result

@router.get("/categories/tree", response_model=List[dict])
def get_category_tree(db: Session = Depends(get_db)):
    """Get hierarchical category structure for navigation"""
    # Try cache first
    cache_key = CacheKeys.category_tree()
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache HIT: category tree")
        return cached_data

    # Get parent categories (those without parent_id)
    parent_categories = db.query(Category).filter(
        Category.parent_id.is_(None),
        Category.is_active == True
    ).all()
    
    result = []
    for parent in parent_categories:
        # Get children categories
        children = db.query(Category).filter(
            Category.parent_id == parent.id,
            Category.is_active == True
        ).all()
        
        # Get product count for parent category (including children)
        child_ids = [child.id for child in children] + [parent.id]
        product_count = db.query(Product).filter(
            Product.category_id.in_(child_ids),
            Product.is_active == True
        ).count()
        
        category_data = {
            "id": parent.id,
            "name": parent.name,
            "description": parent.description,
            "product_count": product_count,
            "children": []
        }
        
        for child in children:
            child_product_count = db.query(Product).filter(
                Product.category_id == child.id,
                Product.is_active == True
            ).count()
            
            category_data["children"].append({
                "id": child.id,
                "name": child.name,
                "description": child.description,
                "product_count": child_product_count
            })

        result.append(category_data)

    # Cache the result
    cache.set(cache_key, result, ttl=settings.CACHE_TTL_CATEGORIES)

    return result

@router.get("/stats/catalog", response_model=dict)
def get_catalog_stats(db: Session = Depends(get_db)):
    """Get catalog statistics for dashboard"""
    # Try cache first
    cache_key = CacheKeys.catalog_stats()
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache HIT: catalog stats")
        return cached_data

    total_products = db.query(Product).filter(Product.is_active == True).count()
    total_categories = db.query(Category).filter(Category.is_active == True).count()
    featured_products = db.query(Product).filter(
        Product.is_featured == True,
        Product.is_active == True
    ).count()
    out_of_stock = db.query(Product).filter(
        Product.is_active == True,
        Product.quantity_available == 0
    ).count()
    
    # Price statistics
    price_stats = db.query(
        func.min(Product.price).label('min_price'),
        func.max(Product.price).label('max_price'),
        func.avg(Product.price).label('avg_price')
    ).filter(Product.is_active == True).first()
    
    result = {
        "total_products": total_products,
        "total_categories": total_categories,
        "featured_products": featured_products,
        "out_of_stock": out_of_stock,
        "in_stock": total_products - out_of_stock,
        "price_range": {
            "min": float(price_stats.min_price or 0),
            "max": float(price_stats.max_price or 0),
            "average": float(price_stats.avg_price or 0)
        }
    }

    # Cache the result
    cache.set(cache_key, result, ttl=settings.CACHE_TTL_PRODUCTS)

    return result

@router.get("/search/suggestions")
def get_search_suggestions(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, le=20),
    db: Session = Depends(get_db)
):
    """Get search suggestions for autocomplete"""
    
    # Search in product names
    product_suggestions = db.query(Product.name).filter(
        Product.name.ilike(f"%{q}%"),
        Product.is_active == True
    ).distinct().limit(limit//2).all()
    
    # Search in categories
    category_suggestions = db.query(Category.name).filter(
        Category.name.ilike(f"%{q}%"),
        Category.is_active == True
    ).distinct().limit(limit//2).all()
    
    # Search in tags
    tag_suggestions = db.query(Product.tags).filter(
        Product.tags.ilike(f"%{q}%"),
        Product.is_active == True,
        Product.tags.isnot(None)
    ).distinct().limit(limit//3).all()
    
    # Process tag suggestions to extract individual tags
    processed_tags = []
    for tag_row in tag_suggestions:
        if tag_row.tags:
            tags = [tag.strip() for tag in tag_row.tags.split(',')]
            for tag in tags:
                if q.lower() in tag.lower() and tag not in processed_tags:
                    processed_tags.append(tag)
    
    suggestions = {
        "products": [p.name for p in product_suggestions],
        "categories": [c.name for c in category_suggestions],
        "tags": processed_tags[:limit//3]
    }
    
    return suggestions

@router.get("/filters/options")
def get_filter_options(
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get available filter options for advanced search"""
    
    query = db.query(Product).filter(Product.is_active == True)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    # Get unique materials
    materials = db.query(Product.material).filter(
        Product.material.isnot(None),
        Product.is_active == True
    )
    if category_id:
        materials = materials.filter(Product.category_id == category_id)
    materials = materials.distinct().all()
    
    # Get unique colors
    colors = db.query(Product.color).filter(
        Product.color.isnot(None),
        Product.is_active == True
    )
    if category_id:
        colors = colors.filter(Product.category_id == category_id)
    colors = colors.distinct().all()
    
    # Get unique techniques
    techniques = db.query(Product.technique).filter(
        Product.technique.isnot(None),
        Product.is_active == True
    )
    if category_id:
        techniques = techniques.filter(Product.category_id == category_id)
    techniques = techniques.distinct().all()
    
    # Get price range
    price_range = query.with_entities(
        func.min(Product.price).label('min_price'),
        func.max(Product.price).label('max_price')
    ).first()
    
    # Get popular tags
    tag_products = query.filter(Product.tags.isnot(None)).all()
    all_tags = []
    for product in tag_products:
        if product.tags:
            tags = [tag.strip() for tag in product.tags.split(',')]
            all_tags.extend(tags)
    
    # Count tag frequency and get top tags
    from collections import Counter
    tag_counts = Counter(all_tags)
    popular_tags = [tag for tag, count in tag_counts.most_common(20)]
    
    return {
        "materials": [m.material for m in materials if m.material],
        "colors": [c.color for c in colors if c.color],
        "techniques": [t.technique for t in techniques if t.technique],
        "tags": popular_tags,
        "price_range": {
            "min": float(price_range.min_price or 0),
            "max": float(price_range.max_price or 0)
        }
    }

@router.post("/{product_id}/view")
def track_product_view(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Track product view for analytics (optional user)"""
    
    # Verify product exists
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Here you could implement view tracking logic
    # For now, just return success
    return {"message": "View tracked", "product_id": product_id}

@router.get("/{product_id}/similar", response_model=List[ProductResponse])
def get_similar_products(
    product_id: int,
    limit: int = Query(8, le=20),
    db: Session = Depends(get_db)
):
    """Get similar products using enhanced similarity algorithm"""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Base query for similar products
    similar_query = db.query(Product).filter(
        Product.id != product_id,
        Product.is_active == True,
        Product.quantity_available > 0
    )
    
    # Priority 1: Same category and similar price range (±50%)
    price_min = product.price * Decimal('0.5')
    price_max = product.price * Decimal('1.5')
    
    category_similar = similar_query.filter(
        Product.category_id == product.category_id,
        Product.price.between(price_min, price_max)
    ).limit(limit//2).all()
    
    # Priority 2: Similar material or technique
    attribute_similar = []
    if len(category_similar) < limit:
        remaining = limit - len(category_similar)
        
        conditions = []
        if product.material:
            conditions.append(Product.material == product.material)
        if product.technique:
            conditions.append(Product.technique == product.technique)
        if product.color:
            conditions.append(Product.color == product.color)
        
        if conditions:
            attribute_similar = similar_query.filter(
                or_(*conditions),
                ~Product.id.in_([p.id for p in category_similar])
            ).limit(remaining).all()
    
    # Priority 3: Same category (if still need more)
    category_fallback = []
    total_found = len(category_similar) + len(attribute_similar)
    if total_found < limit:
        remaining = limit - total_found
        
        category_fallback = similar_query.filter(
            Product.category_id == product.category_id,
            ~Product.id.in_([p.id for p in category_similar + attribute_similar])
        ).limit(remaining).all()
    
    # Combine and return
    all_similar = category_similar + attribute_similar + category_fallback
    return all_similar[:limit]

# Image Management Endpoints

@router.get("/{product_id}/images", response_model=dict)
def get_product_images(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Get all images for a product with optimization"""
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    images = image_service.get_product_images(db, product_id)
    optimized_images = image_service.optimize_image_loading(images)
    
    return optimized_images

@router.post("/{product_id}/images", response_model=dict)
def add_product_image(
    product_id: int,
    image_url: str,
    alt_text: Optional[str] = None,
    is_primary: bool = False,
    order_index: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add image to product"""
    # Verify product exists and user owns it
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Add image
    image = image_service.save_product_image(
        db, product_id, image_url, alt_text, is_primary, order_index
    )
    
    return {"message": "Image added successfully", "image_id": image.id}

@router.put("/{product_id}/images/{image_id}/primary")
def set_primary_image(
    product_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set image as primary for product"""
    # Verify product exists and user owns it
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = image_service.set_primary_image(db, product_id, image_id)
    
    if success:
        return {"message": "Primary image updated successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to update primary image")

@router.put("/{product_id}/images/reorder")
def reorder_product_images(
    product_id: int,
    image_order: List[int],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reorder product images"""
    # Verify product exists and user owns it
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = image_service.reorder_product_images(db, product_id, image_order)
    
    if success:
        return {"message": "Images reordered successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to reorder images")

@router.delete("/{product_id}/images/{image_id}")
def delete_product_image(
    product_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete product image"""
    # Verify product exists and user owns it
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = image_service.delete_product_image(db, product_id, image_id)
    
    if success:
        return {"message": "Image deleted successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to delete image")

# Enhanced Pagination Endpoints

@router.get("/catalog/paginated", response_model=dict)
def get_paginated_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    material: Optional[str] = None,
    color: Optional[str] = None,
    technique: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|price|name|rating|popular)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    in_stock: bool = True,
    db: Session = Depends(get_db)
):
    """Get paginated products with comprehensive filtering - optimized for infinite scroll"""
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Base query
    query = db.query(Product).filter(Product.is_active == True)
    
    # Apply filters
    if in_stock:
        query = query.filter(Product.quantity_available > 0)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if search:
        search_terms = search.split()
        search_conditions = []
        for term in search_terms:
            search_conditions.append(
                or_(
                    Product.name.ilike(f"%{term}%"),
                    Product.description.ilike(f"%{term}%"),
                    Product.tags.ilike(f"%{term}%")
                )
            )
        if search_conditions:
            query = query.filter(and_(*search_conditions))
    
    if min_price:
        query = query.filter(Product.price >= min_price)
    
    if max_price:
        query = query.filter(Product.price <= max_price)
    
    if material:
        query = query.filter(Product.material.ilike(f"%{material}%"))
    
    if color:
        query = query.filter(Product.color.ilike(f"%{color}%"))
    
    if technique:
        query = query.filter(Product.technique.ilike(f"%{technique}%"))
    
    # Get total count before applying sorting with joins
    total_items = query.count()

    # Apply sorting
    if sort_by == "rating":
        query = query.outerjoin(Review).group_by(Product.id)
        if sort_order == "desc":
            query = query.order_by(desc(func.avg(Review.rating)))
        else:
            query = query.order_by(asc(func.avg(Review.rating)))
    elif sort_by == "popular":
        query = query.outerjoin(Review).group_by(Product.id)
        if sort_order == "desc":
            query = query.order_by(desc(func.count(Review.id)))
        else:
            query = query.order_by(asc(func.count(Review.id)))
    else:
        if sort_order == "desc":
            query = query.order_by(desc(getattr(Product, sort_by)))
        else:
            query = query.order_by(asc(getattr(Product, sort_by)))
    
    # Get paginated results
    products = query.offset(offset).limit(per_page).all()

    # Calculate pagination info
    total_pages = (total_items + per_page - 1) // per_page
    has_next = page < total_pages
    has_prev = page > 1

    # Convert to ProductResponse models for proper serialization
    products_response = [ProductResponse.from_orm(p) for p in products]

    return {
        "products": products_response,
        "pagination": {
            "current_page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
            "next_page": page + 1 if has_next else None,
            "prev_page": page - 1 if has_prev else None
        },
        "filters_applied": {
            "category_id": category_id,
            "search": search,
            "price_range": {"min": min_price, "max": max_price},
            "material": material,
            "color": color,
            "technique": technique,
            "in_stock": in_stock
        }
    }

@router.get("/categories/{category_id}/showcase", response_model=dict)
def get_category_showcase(
    category_id: int,
    db: Session = Depends(get_db)
):
    """Get category showcase with featured products and subcategories"""
    
    # Get category
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.is_active == True
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get subcategories
    subcategories = db.query(Category).filter(
        Category.parent_id == category_id,
        Category.is_active == True
    ).all()
    
    # Get featured products in this category
    featured_products = db.query(Product).filter(
        Product.category_id == category_id,
        Product.is_featured == True,
        Product.is_active == True,
        Product.quantity_available > 0
    ).order_by(desc(Product.created_at)).limit(8).all()
    
    # Get newest products in this category
    newest_products = db.query(Product).filter(
        Product.category_id == category_id,
        Product.is_active == True,
        Product.quantity_available > 0
    ).order_by(desc(Product.created_at)).limit(8).all()
    
    # Get popular products (by review count)
    popular_products = db.query(Product).outerjoin(Review).filter(
        Product.category_id == category_id,
        Product.is_active == True,
        Product.quantity_available > 0
    ).group_by(Product.id).order_by(
        desc(func.count(Review.id))
    ).limit(8).all()
    
    # Get price range for category
    price_stats = db.query(
        func.min(Product.price).label('min_price'),
        func.max(Product.price).label('max_price'),
        func.avg(Product.price).label('avg_price'),
        func.count(Product.id).label('product_count')
    ).filter(
        Product.category_id == category_id,
        Product.is_active == True
    ).first()
    
    return {
        "category": {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "product_count": price_stats.product_count or 0
        },
        "subcategories": [
            {
                "id": sub.id,
                "name": sub.name,
                "description": sub.description,
                "product_count": db.query(Product).filter(
                    Product.category_id == sub.id,
                    Product.is_active == True
                ).count()
            }
            for sub in subcategories
        ],
        "featured_products": featured_products,
        "newest_products": newest_products,
        "popular_products": popular_products,
        "price_stats": {
            "min": float(price_stats.min_price or 0),
            "max": float(price_stats.max_price or 0),
            "average": float(price_stats.avg_price or 0)
        }
    }

# Analytics and Recommendation Endpoints

@router.get("/analytics/trending", response_model=List[dict])
def get_trending_analytics(
    category_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, le=20),
    db: Session = Depends(get_db)
):
    """Get trending products with analytics data"""
    trending_data = product_analytics.get_trending_products(
        db, category_id=category_id, days=days, limit=limit
    )

    return [
        {
            "product": ProductResponse.from_orm(item["product"]).model_dump(),
            "trending_score": item["trending_score"],
            "recent_activity": item["recent_activity"]
        }
        for item in trending_data
    ]

@router.get("/analytics/popular", response_model=List[ProductResponse])
def get_popular_products_analytics(
    category_id: Optional[int] = None,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(10, le=20),
    db: Session = Depends(get_db)
):
    """Get popular products based on sales and reviews"""
    return product_analytics.get_popular_products(
        db, category_id=category_id, days=days, limit=limit
    )

@router.get("/recommendations/{user_id}", response_model=List[ProductResponse])
def get_user_recommendations(
    user_id: int,
    limit: int = Query(10, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized recommendations for a user"""
    # Users can only get their own recommendations
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return product_analytics.get_personalized_recommendations(
        db, user_id=user_id, limit=limit
    )

@router.get("/analytics/categories/{category_id}", response_model=dict)
def get_category_analytics(
    category_id: int,
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get comprehensive analytics for a category"""
    return product_analytics.get_category_insights(
        db, category_id=category_id, days=days
    )

@router.get("/analytics/search", response_model=dict)
def get_search_analytics(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get search and discovery analytics"""
    return product_analytics.get_search_analytics(db, days=days)

@router.get("/{product_id}/analytics", response_model=dict)
def get_product_analytics(
    product_id: int,
    days: int = Query(30, ge=1, le=90),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics for a specific product (detailed for owners, public for others)"""
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if user is the seller (full analytics) or public user (basic analytics)
    is_owner = current_user and product.seller_id == current_user.id

    if is_owner:
        # Full detailed analytics for product owner
        return product_analytics.get_product_performance_metrics(
            db, product_id=product_id, days=days
        )
    else:
        # Public analytics (basic stats) for non-owners
        return {
            "product_id": product_id,
            "views": "Public analytics available for product owners only",
            "rating": db.query(func.avg(Review.rating)).filter(Review.product_id == product_id).scalar() or 0,
            "review_count": db.query(func.count(Review.id)).filter(Review.product_id == product_id).scalar() or 0
        }

# Bulk Operations for Product Management

@router.post("/bulk/update-featured")
def bulk_update_featured(
    product_ids: List[int],
    is_featured: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk update featured status for products"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can update products")
    
    # Verify all products belong to the user
    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.seller_id == current_user.id
    ).all()
    
    if len(products) != len(product_ids):
        raise HTTPException(status_code=404, detail="Some products not found or not owned")
    
    # Update featured status
    updated_count = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.seller_id == current_user.id
    ).update({"is_featured": is_featured}, synchronize_session=False)
    
    db.commit()
    
    return {
        "message": f"Updated {updated_count} products",
        "is_featured": is_featured,
        "product_ids": product_ids
    }

@router.post("/bulk/update-stock")
def bulk_update_stock(
    updates: List[dict],  # [{"product_id": 1, "quantity": 10}, ...]
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk update stock quantities"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can update products")
    
    product_ids = [update["product_id"] for update in updates]
    
    # Verify all products belong to the user
    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.seller_id == current_user.id
    ).all()
    
    if len(products) != len(product_ids):
        raise HTTPException(status_code=404, detail="Some products not found or not owned")
    
    # Update stock quantities
    updated_count = 0
    for update in updates:
        result = db.query(Product).filter(
            Product.id == update["product_id"],
            Product.seller_id == current_user.id
        ).update({"quantity_available": update["quantity"]})
        
        if result:
            updated_count += 1
    
    db.commit()

    return {
        "message": f"Updated stock for {updated_count} products",
        "updates": updates
    }


# ============================================
# SECTION A.1: Missing Frontend Endpoints
# ============================================

def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a product name"""
    slug = name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    return slug


# A.1.1 - Get Product by Slug
@router.get("/slug/{slug}", response_model=ProductResponse)
def get_product_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get product by SEO-friendly slug"""
    product = db.query(Product).options(
        joinedload(Product.seller),
        joinedload(Product.category),
        joinedload(Product.images),
        joinedload(Product.reviews)
    ).filter(
        Product.slug == slug,
        Product.is_active == True
    ).first()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


# A.1.2 - Get Category by ID
@router.get("/categories/{category_id}", response_model=CategoryDetailResponse)
def get_category_by_id(
    category_id: int,
    db: Session = Depends(get_db)
):
    """Get single category by ID with product count and children"""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.is_active == True
    ).first()

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    # Get product count for this category
    product_count = db.query(Product).filter(
        Product.category_id == category_id,
        Product.is_active == True
    ).count()

    # Get child categories
    children = db.query(Category).filter(
        Category.parent_id == category_id,
        Category.is_active == True
    ).all()

    children_with_counts = []
    for child in children:
        child_product_count = db.query(Product).filter(
            Product.category_id == child.id,
            Product.is_active == True
        ).count()
        children_with_counts.append({
            **CategoryResponse.from_orm(child).model_dump(),
            "product_count": child_product_count,
            "children": []
        })

    return {
        **CategoryResponse.from_orm(category).model_dump(),
        "product_count": product_count,
        "children": children_with_counts
    }


# A.1.3 - Get New Products
@router.get("/new", response_model=List[ProductResponse])
def get_new_products(
    limit: int = Query(10, le=50),
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get newest products sorted by creation date"""
    query = db.query(Product).filter(
        Product.is_active == True,
        Product.quantity_available > 0
    )

    if category_id:
        query = query.filter(Product.category_id == category_id)

    products = query.order_by(desc(Product.created_at)).limit(limit).all()

    return products


# A.1.4 - Get Discounted Products
@router.get("/discounted", response_model=List[ProductResponse])
def get_discounted_products(
    limit: int = Query(10, le=50),
    min_discount: Optional[float] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get products currently on sale/discount"""
    query = db.query(Product).filter(
        Product.is_active == True,
        Product.quantity_available > 0,
        Product.discount_percentage.isnot(None),
        Product.discount_percentage > 0
    )

    if min_discount:
        query = query.filter(Product.discount_percentage >= min_discount)

    if category_id:
        query = query.filter(Product.category_id == category_id)

    # Order by discount percentage (highest first)
    products = query.order_by(desc(Product.discount_percentage)).limit(limit).all()

    return products


# A.1.5 - Get Product Variants (HIGH PRIORITY)
@router.get("/{product_id}/variants", response_model=List[ProductVariantResponse])
def get_product_variants(
    product_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db)
):
    """Get all variants for a product"""
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    query = db.query(ProductVariant).filter(ProductVariant.product_id == product_id)

    if not include_inactive:
        query = query.filter(ProductVariant.is_active == True)

    variants = query.order_by(
        desc(ProductVariant.is_default),
        asc(ProductVariant.name)
    ).all()

    return variants


# A.1.6 - Check Product Availability
@router.get("/{product_id}/availability", response_model=ProductAvailabilityResponse)
def check_product_availability(
    product_id: int,
    variant_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Check real-time availability of a product or variant"""
    LOW_STOCK_THRESHOLD = 5

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_active == True
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if product has variants
    variants = db.query(ProductVariant).filter(
        ProductVariant.product_id == product_id,
        ProductVariant.is_active == True
    ).all()

    has_variants = len(variants) > 0

    if variant_id:
        # Check specific variant availability
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id,
            ProductVariant.is_active == True
        ).first()

        if not variant:
            raise HTTPException(status_code=404, detail="Variant not found")

        return ProductAvailabilityResponse(
            product_id=product_id,
            is_available=variant.quantity_available > 0,
            quantity_available=variant.quantity_available,
            has_variants=True,
            is_low_stock=variant.quantity_available <= LOW_STOCK_THRESHOLD and variant.quantity_available > 0
        )

    if has_variants:
        # Calculate total availability across all variants
        total_quantity = sum(v.quantity_available for v in variants)
        variants_availability = [
            {
                "variant_id": v.id,
                "name": v.name,
                "is_available": v.quantity_available > 0,
                "quantity_available": v.quantity_available,
                "is_low_stock": v.quantity_available <= LOW_STOCK_THRESHOLD and v.quantity_available > 0
            }
            for v in variants
        ]

        return ProductAvailabilityResponse(
            product_id=product_id,
            is_available=total_quantity > 0,
            quantity_available=total_quantity,
            has_variants=True,
            variants_availability=variants_availability,
            is_low_stock=total_quantity <= LOW_STOCK_THRESHOLD and total_quantity > 0
        )

    # No variants - check base product availability
    return ProductAvailabilityResponse(
        product_id=product_id,
        is_available=product.quantity_available > 0,
        quantity_available=product.quantity_available,
        has_variants=False,
        is_low_stock=product.quantity_available <= LOW_STOCK_THRESHOLD and product.quantity_available > 0
    )


# A.1.7 - Get Price History
@router.get("/{product_id}/price-history", response_model=List[PriceHistoryResponse])
def get_price_history(
    product_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get price change history for a product"""
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    price_history = db.query(PriceHistory).filter(
        PriceHistory.product_id == product_id,
        PriceHistory.created_at >= cutoff_date
    ).order_by(desc(PriceHistory.created_at)).all()

    return price_history


# A.1.8 - Get Product Specifications
@router.get("/{product_id}/specifications", response_model=dict)
def get_product_specifications(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed specifications for a product"""
    # Verify product exists
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_active == True
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get specifications from dedicated table
    specifications = db.query(ProductSpecification).filter(
        ProductSpecification.product_id == product_id
    ).order_by(
        ProductSpecification.group_name,
        ProductSpecification.display_order
    ).all()

    # Group specifications by group_name
    grouped_specs = {}
    for spec in specifications:
        group = spec.group_name or "General"
        if group not in grouped_specs:
            grouped_specs[group] = []
        grouped_specs[group].append({
            "name": spec.spec_name,
            "value": spec.spec_value
        })

    # Also include basic product attributes as specifications
    basic_specs = {
        "Physical": []
    }

    if product.dimensions:
        basic_specs["Physical"].append({"name": "Dimensions", "value": product.dimensions})
    if product.weight:
        basic_specs["Physical"].append({"name": "Weight", "value": f"{product.weight} kg"})
    if product.material:
        basic_specs["Physical"].append({"name": "Material", "value": product.material})
    if product.color:
        basic_specs["Physical"].append({"name": "Color", "value": product.color})
    if product.technique:
        basic_specs["Physical"].append({"name": "Technique", "value": product.technique})

    # Merge basic specs with custom specs
    for group, specs in basic_specs.items():
        if specs:
            if group not in grouped_specs:
                grouped_specs[group] = []
            grouped_specs[group] = specs + grouped_specs.get(group, [])

    return {
        "product_id": product_id,
        "specifications": grouped_specs,
        "total_specs": sum(len(specs) for specs in grouped_specs.values())
    }


# A.1.9 - Compare Products
@router.get("/compare")
def compare_products(
    ids: str = Query(..., description="Comma-separated product IDs"),
    db: Session = Depends(get_db)
):
    """Compare multiple products side by side"""
    try:
        product_ids = [int(id.strip()) for id in ids.split(',')]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product IDs format")

    if len(product_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 products required for comparison")

    if len(product_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 products can be compared")

    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.is_active == True
    ).all()

    if len(products) != len(product_ids):
        raise HTTPException(status_code=404, detail="Some products not found")

    # Define comparison attributes
    comparison_attributes = [
        "price", "material", "color", "technique",
        "dimensions", "weight", "quantity_available"
    ]

    # Build comparison data
    comparison_data = {}
    for attr in comparison_attributes:
        comparison_data[attr] = {}
        for product in products:
            value = getattr(product, attr, None)
            comparison_data[attr][product.id] = str(value) if value is not None else "N/A"

    # Get category names
    comparison_data["category"] = {}
    for product in products:
        category = db.query(Category).filter(Category.id == product.category_id).first()
        comparison_data["category"][product.id] = category.name if category else "N/A"

    # Get average ratings
    comparison_data["average_rating"] = {}
    for product in products:
        avg_rating = db.query(func.avg(Review.rating)).filter(
            Review.product_id == product.id
        ).scalar()
        comparison_data["average_rating"][product.id] = round(float(avg_rating), 1) if avg_rating else "N/A"

    return {
        "products": [ProductResponse.from_orm(p) for p in products],
        "comparison_attributes": comparison_attributes + ["category", "average_rating"],
        "comparison_data": comparison_data
    }


# A.1.10 - Get Brands
@router.get("/brands", response_model=List[BrandResponse])
def get_brands(
    skip: int = 0,
    limit: int = Query(100, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all brands"""
    query = db.query(Brand).filter(Brand.is_active == True)

    if search:
        query = query.filter(Brand.name.ilike(f"%{search}%"))

    brands = query.order_by(asc(Brand.name)).offset(skip).limit(limit).all()

    return brands


@router.post("/brands", response_model=BrandResponse)
def create_brand(
    brand: BrandCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new brand (sellers only)"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can create brands")

    # Generate slug if not provided
    slug = brand.slug or generate_slug(brand.name)

    # Check if brand name or slug already exists
    existing = db.query(Brand).filter(
        or_(Brand.name == brand.name, Brand.slug == slug)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Brand name or slug already exists")

    db_brand = Brand(
        name=brand.name,
        slug=slug,
        description=brand.description,
        logo_url=brand.logo_url,
        website=brand.website
    )
    db.add(db_brand)
    db.commit()
    db.refresh(db_brand)

    return db_brand


@router.get("/brands/{brand_id}", response_model=BrandResponse)
def get_brand_by_id(
    brand_id: int,
    db: Session = Depends(get_db)
):
    """Get a single brand by ID"""
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.is_active == True
    ).first()

    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    return brand


# A.1.11 - Get Product Tags
@router.get("/{product_id}/tags", response_model=List[ProductTagResponse])
def get_product_tags(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Get tags associated with a product"""
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get tags from association table
    tag_associations = db.query(ProductTagAssociation).filter(
        ProductTagAssociation.product_id == product_id
    ).all()

    tag_ids = [assoc.tag_id for assoc in tag_associations]

    tags = db.query(ProductTag).filter(ProductTag.id.in_(tag_ids)).all() if tag_ids else []

    # Also parse legacy comma-separated tags from product
    legacy_tags = []
    if product.tags:
        for tag_name in product.tags.split(','):
            tag_name = tag_name.strip()
            if tag_name:
                # Check if tag already exists in proper tags
                existing = next((t for t in tags if t.name.lower() == tag_name.lower()), None)
                if not existing:
                    legacy_tags.append({
                        "id": 0,  # Legacy tags don't have IDs
                        "name": tag_name,
                        "slug": generate_slug(tag_name),
                        "description": None,
                        "created_at": product.created_at
                    })

    # Combine proper tags with legacy tags
    result = [ProductTagResponse.from_orm(t) for t in tags]
    result.extend([ProductTagResponse(**lt) for lt in legacy_tags])

    return result


# A.1.12 - Get Product Attributes
@router.get("/{product_id}/attributes", response_model=List[ProductAttributeResponse])
def get_product_attributes(
    product_id: int,
    visible_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get custom attributes for a product"""
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    query = db.query(ProductAttribute).filter(
        ProductAttribute.product_id == product_id
    )

    if visible_only:
        query = query.filter(ProductAttribute.is_visible == True)

    attributes = query.order_by(ProductAttribute.display_order).all()

    return attributes


# ============================================
# Variant Management Endpoints
# ============================================

@router.post("/{product_id}/variants", response_model=ProductVariantResponse)
def create_product_variant(
    product_id: int,
    variant: ProductVariantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new variant for a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Generate SKU if not provided
    sku = variant.sku or f"{product.sku or 'P'}-V-{uuid.uuid4().hex[:6].upper()}"

    # Check if SKU already exists
    existing = db.query(ProductVariant).filter(ProductVariant.sku == sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")

    # If this is set as default, unset other defaults
    if variant.is_default:
        db.query(ProductVariant).filter(
            ProductVariant.product_id == product_id
        ).update({"is_default": False})

    db_variant = ProductVariant(
        product_id=product_id,
        sku=sku,
        name=variant.name,
        size=variant.size,
        color=variant.color,
        material=variant.material,
        weight=variant.weight,
        dimensions=variant.dimensions,
        price=variant.price,
        price_adjustment=variant.price_adjustment,
        quantity_available=variant.quantity_available,
        is_default=variant.is_default,
        image_url=variant.image_url
    )
    db.add(db_variant)
    db.commit()
    db.refresh(db_variant)

    return db_variant


@router.put("/{product_id}/variants/{variant_id}", response_model=ProductVariantResponse)
def update_product_variant(
    product_id: int,
    variant_id: int,
    variant_update: ProductVariantUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a product variant"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id,
        ProductVariant.product_id == product_id
    ).first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    # If setting as default, unset other defaults
    if variant_update.is_default:
        db.query(ProductVariant).filter(
            ProductVariant.product_id == product_id,
            ProductVariant.id != variant_id
        ).update({"is_default": False})

    # Update variant fields
    for field, value in variant_update.model_dump(exclude_unset=True).items():
        setattr(variant, field, value)

    db.commit()
    db.refresh(variant)

    return variant


@router.delete("/{product_id}/variants/{variant_id}")
def delete_product_variant(
    product_id: int,
    variant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a product variant"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id,
        ProductVariant.product_id == product_id
    ).first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    # Soft delete
    variant.is_active = False
    db.commit()

    return {"message": "Variant deleted successfully"}


# ============================================
# Attribute & Specification Management
# ============================================

@router.post("/{product_id}/attributes", response_model=ProductAttributeResponse)
def create_product_attribute(
    product_id: int,
    attribute: ProductAttributeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a custom attribute to a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db_attribute = ProductAttribute(
        product_id=product_id,
        name=attribute.name,
        value=attribute.value,
        unit=attribute.unit,
        display_order=attribute.display_order,
        is_visible=attribute.is_visible
    )
    db.add(db_attribute)
    db.commit()
    db.refresh(db_attribute)

    return db_attribute


@router.post("/{product_id}/specifications", response_model=ProductSpecificationResponse)
def create_product_specification(
    product_id: int,
    spec: ProductSpecificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a specification to a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db_spec = ProductSpecification(
        product_id=product_id,
        group_name=spec.group_name,
        spec_name=spec.spec_name,
        spec_value=spec.spec_value,
        display_order=spec.display_order
    )
    db.add(db_spec)
    db.commit()
    db.refresh(db_spec)

    return db_spec