from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, func, and_, or_
from typing import List, Optional
from decimal import Decimal
import uuid
import logging

from shared.database import get_db
from shared.cache import cache, CacheKeys, CacheInvalidation
from shared.config import settings
from shared.security import get_current_user, get_optional_current_user
from shared.models.user import User, UserRole
from shared.models.product import Product, Category, ProductImage
from shared.models.review import Review

from app.schemas.product import (
    ProductCreate, ProductResponse, ProductUpdate,
    CategoryCreate, CategoryResponse
)
from app.services.image_service import image_service
from app.services.product_analytics import product_analytics

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
    cache_key = CacheKeys.categories()
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug("Cache HIT: categories")
        return cached_data[skip:skip+limit]

    categories = db.query(Category).filter(Category.is_active == True).all()
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

    for img_data in product.images:
        img_data_dict = img_data.dict()
        img_data_dict["product_id"] = db_product.id
        db_image = ProductImage(**img_data_dict)
        db.add(db_image)

    db.commit()
    db.refresh(db_product)

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
    cache_key = CacheKeys.featured_products(category_id)
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug("Cache HIT: featured products")
        return cached_data[:limit]

    query = db.query(Product).filter(
        Product.is_featured == True,
        Product.is_active == True,
        Product.quantity_available > 0
    )

    if category_id:
        query = query.filter(Product.category_id == category_id)

    products = query.order_by(desc(Product.created_at)).limit(20).all()

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

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    recent_reviews = db.query(
        Review.product_id,
        func.count(Review.id).label('recent_review_count')
    ).filter(
        Review.created_at >= cutoff_date
    ).group_by(Review.product_id).subquery()

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

    related_query = db.query(Product).filter(
        Product.id != product_id,
        Product.category_id == product.category_id,
        Product.is_active == True
    )

    if product.tags:
        product_tags = [tag.strip().lower() for tag in product.tags.split(',')]
        tag_conditions = [Product.tags.ilike(f"%{tag}%") for tag in product_tags]

        related_with_tags = related_query.filter(or_(*tag_conditions)).limit(limit).all()

        if len(related_with_tags) >= limit:
            return related_with_tags

        remaining = limit - len(related_with_tags)
        category_products = related_query.filter(
            ~Product.id.in_([p.id for p in related_with_tags])
        ).limit(remaining).all()

        return related_with_tags + category_products

    return related_query.limit(limit).all()

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

    CacheInvalidation.invalidate_product(product_id)

    return {"message": "Product deleted successfully"}

# Home featured products
@router.get("/home/featured", response_model=dict)
def get_home_featured_products(db: Session = Depends(get_db)):
    """Get featured products for home screen with different sections"""
    cache_key = CacheKeys.home_featured()
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug("Cache HIT: home featured")
        return cached_data

    latest_featured = db.query(Product).filter(
        Product.is_featured == True,
        Product.is_active == True,
        Product.quantity_available > 0
    ).order_by(desc(Product.created_at)).limit(6).all()

    popular_products = db.query(Product).outerjoin(Review).filter(
        Product.is_active == True,
        Product.quantity_available > 0
    ).group_by(Product.id).order_by(
        desc(func.count(Review.id))
    ).limit(6).all()

    newest_products = db.query(Product).filter(
        Product.is_active == True,
        Product.quantity_available > 0
    ).order_by(desc(Product.created_at)).limit(6).all()

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

    featured_list = [ProductResponse.from_orm(p).model_dump() for p in latest_featured]
    popular_list = [ProductResponse.from_orm(p).model_dump() for p in popular_products]
    newest_list = [ProductResponse.from_orm(p).model_dump() for p in newest_products]

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

    cache.set(cache_key, result, ttl=settings.CACHE_TTL_HOME)

    return result

@router.get("/categories/tree", response_model=List[dict])
def get_category_tree(db: Session = Depends(get_db)):
    """Get hierarchical category structure for navigation"""
    cache_key = CacheKeys.category_tree()
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug("Cache HIT: category tree")
        return cached_data

    parent_categories = db.query(Category).filter(
        Category.parent_id.is_(None),
        Category.is_active == True
    ).all()

    result = []
    for parent in parent_categories:
        children = db.query(Category).filter(
            Category.parent_id == parent.id,
            Category.is_active == True
        ).all()

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

    cache.set(cache_key, result, ttl=settings.CACHE_TTL_CATEGORIES)

    return result

@router.get("/stats/catalog", response_model=dict)
def get_catalog_stats(db: Session = Depends(get_db)):
    """Get catalog statistics for dashboard"""
    cache_key = CacheKeys.catalog_stats()
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug("Cache HIT: catalog stats")
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

    cache.set(cache_key, result, ttl=settings.CACHE_TTL_PRODUCTS)

    return result

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

    if category_id:
        query = query.filter(Product.category_id == category_id)

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

    if tags:
        tag_list = [tag.strip() for tag in tags.split(',')]
        tag_conditions = [Product.tags.ilike(f"%{tag}%") for tag in tag_list]
        query = query.filter(or_(*tag_conditions))

    if seller_id:
        query = query.filter(Product.seller_id == seller_id)

    if is_featured is not None:
        query = query.filter(Product.is_featured == is_featured)

    if in_stock:
        query = query.filter(Product.quantity_available > 0)

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
    elif sort_by != "relevance":
        if sort_order == "desc":
            query = query.order_by(desc(getattr(Product, sort_by)))
        else:
            query = query.order_by(asc(getattr(Product, sort_by)))

    total = query.count()
    products = query.offset(skip).limit(limit).all()

    return {
        "products": products,
        "total": total,
        "page": (skip // limit) + 1,
        "pages": (total + limit - 1) // limit,
        "has_more": skip + limit < total
    }

# Image Management Endpoints
@router.get("/{product_id}/images", response_model=dict)
def get_product_images(product_id: int, db: Session = Depends(get_db)):
    """Get all images for a product with optimization"""
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
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    image = image_service.save_product_image(
        db, product_id, image_url, alt_text, is_primary, order_index
    )

    return {"message": "Image added successfully", "image_id": image.id}

@router.delete("/{product_id}/images/{image_id}")
def delete_product_image(
    product_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete product image"""
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

# Analytics Endpoints
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

@router.get("/recommendations/{user_id}", response_model=List[ProductResponse])
def get_user_recommendations(
    user_id: int,
    limit: int = Query(10, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized recommendations for a user"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return product_analytics.get_personalized_recommendations(
        db, user_id=user_id, limit=limit
    )
