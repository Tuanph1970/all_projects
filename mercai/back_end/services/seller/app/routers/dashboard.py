from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, and_, or_, extract, case
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime, timedelta, date
from decimal import Decimal
import os
import shutil
import uuid
import subprocess
import json

from shared.database import get_db
from shared.security import get_current_user
from shared.models.user import User, UserRole
from shared.models.product import Product, Category, ProductVideo, PriceHistory
from shared.models.order import Order, OrderItem
from shared.models.review import Review

from app.services.video_service import video_service

router = APIRouter()

@router.get("/dashboard/overview")
def get_seller_dashboard_overview(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get seller dashboard overview with key metrics"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can access dashboard")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Product statistics
    total_products = db.query(Product).filter(
        Product.seller_id == current_user.id,
        Product.is_active == True
    ).count()

    in_stock_products = db.query(Product).filter(
        Product.seller_id == current_user.id,
        Product.is_active == True,
        Product.quantity_available > 0
    ).count()

    featured_products = db.query(Product).filter(
        Product.seller_id == current_user.id,
        Product.is_active == True,
        Product.is_featured == True
    ).count()

    # Sales statistics
    sales_data = db.query(
        func.count(OrderItem.id).label('total_orders'),
        func.sum(OrderItem.quantity).label('total_quantity_sold'),
        func.sum(OrderItem.total_price).label('total_revenue')
    ).join(Product).filter(
        Product.seller_id == current_user.id,
        OrderItem.created_at >= cutoff_date
    ).first()

    # Previous period comparison
    previous_cutoff = cutoff_date - timedelta(days=days)
    previous_sales = db.query(
        func.count(OrderItem.id).label('prev_orders'),
        func.sum(OrderItem.total_price).label('prev_revenue')
    ).join(Product).filter(
        Product.seller_id == current_user.id,
        OrderItem.created_at >= previous_cutoff,
        OrderItem.created_at < cutoff_date
    ).first()

    # Calculate growth rates
    current_orders = sales_data.total_orders or 0
    current_revenue = float(sales_data.total_revenue or 0)
    prev_orders = previous_sales.prev_orders or 0
    prev_revenue = float(previous_sales.prev_revenue or 0)

    order_growth = ((current_orders - prev_orders) / max(prev_orders, 1)) * 100
    revenue_growth = ((current_revenue - prev_revenue) / max(prev_revenue, 1)) * 100

    # Review statistics
    review_stats = db.query(
        func.count(Review.id).label('total_reviews'),
        func.avg(Review.rating).label('avg_rating')
    ).join(Product).filter(
        Product.seller_id == current_user.id
    ).first()

    recent_reviews_count = db.query(
        func.count(Review.id)
    ).join(Product).filter(
        Product.seller_id == current_user.id,
        Review.created_at >= cutoff_date
    ).scalar() or 0

    total_views = 0

    return {
        "period_days": days,
        "products": {
            "total": total_products,
            "in_stock": in_stock_products,
            "out_of_stock": total_products - in_stock_products,
            "featured": featured_products,
            "stock_ratio": (in_stock_products / max(total_products, 1)) * 100
        },
        "sales": {
            "total_orders": current_orders,
            "total_quantity_sold": sales_data.total_quantity_sold or 0,
            "total_revenue": current_revenue,
            "avg_order_value": current_revenue / max(current_orders, 1),
            "growth": {
                "orders": round(order_growth, 2),
                "revenue": round(revenue_growth, 2)
            }
        },
        "engagement": {
            "total_views": total_views,
            "total_reviews": review_stats.total_reviews or 0,
            "recent_reviews": recent_reviews_count,
            "avg_rating": float(review_stats.avg_rating or 0),
            "conversion_rate": (current_orders / max(total_views, 1)) * 100
        }
    }

@router.get("/dashboard/sales-chart")
def get_sales_chart_data(
    days: int = Query(30, ge=7, le=365),
    granularity: str = Query("day", regex="^(day|week|month)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get sales data for charts"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can access dashboard")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    if granularity == "day":
        date_group = func.date(OrderItem.created_at)
    elif granularity == "week":
        date_group = func.date_trunc('week', OrderItem.created_at)
    else:
        date_group = func.date_trunc('month', OrderItem.created_at)

    sales_data = db.query(
        date_group.label('date'),
        func.count(OrderItem.id).label('orders'),
        func.sum(OrderItem.quantity).label('quantity'),
        func.sum(OrderItem.total_price).label('revenue')
    ).join(Product).filter(
        Product.seller_id == current_user.id,
        OrderItem.created_at >= cutoff_date
    ).group_by(date_group).order_by(date_group).all()

    return {
        "period_days": days,
        "granularity": granularity,
        "data": [
            {
                "date": data.date.isoformat() if data.date else None,
                "orders": data.orders or 0,
                "quantity": data.quantity or 0,
                "revenue": float(data.revenue or 0)
            }
            for data in sales_data
        ]
    }

@router.get("/dashboard/top-products")
def get_top_performing_products(
    days: int = Query(30, ge=1, le=365),
    metric: str = Query("revenue", regex="^(revenue|orders|quantity|rating)$"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get top performing products by different metrics"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can access dashboard")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    if metric == "revenue":
        product_data = db.query(
            Product,
            func.sum(OrderItem.total_price).label('total_revenue'),
            func.count(OrderItem.id).label('order_count'),
            func.sum(OrderItem.quantity).label('quantity_sold')
        ).outerjoin(OrderItem).filter(
            Product.seller_id == current_user.id,
            Product.is_active == True,
            or_(OrderItem.created_at >= cutoff_date, OrderItem.created_at.is_(None))
        ).group_by(Product.id).order_by(
            desc(func.sum(OrderItem.total_price))
        ).limit(limit).all()

    elif metric == "orders":
        product_data = db.query(
            Product,
            func.count(OrderItem.id).label('order_count'),
            func.sum(OrderItem.total_price).label('total_revenue'),
            func.sum(OrderItem.quantity).label('quantity_sold')
        ).outerjoin(OrderItem).filter(
            Product.seller_id == current_user.id,
            Product.is_active == True,
            or_(OrderItem.created_at >= cutoff_date, OrderItem.created_at.is_(None))
        ).group_by(Product.id).order_by(
            desc(func.count(OrderItem.id))
        ).limit(limit).all()

    elif metric == "quantity":
        product_data = db.query(
            Product,
            func.sum(OrderItem.quantity).label('quantity_sold'),
            func.count(OrderItem.id).label('order_count'),
            func.sum(OrderItem.total_price).label('total_revenue')
        ).outerjoin(OrderItem).filter(
            Product.seller_id == current_user.id,
            Product.is_active == True,
            or_(OrderItem.created_at >= cutoff_date, OrderItem.created_at.is_(None))
        ).group_by(Product.id).order_by(
            desc(func.sum(OrderItem.quantity))
        ).limit(limit).all()

    else:  # rating
        product_data = db.query(
            Product,
            func.avg(Review.rating).label('avg_rating'),
            func.count(Review.id).label('review_count')
        ).outerjoin(Review).filter(
            Product.seller_id == current_user.id,
            Product.is_active == True
        ).group_by(Product.id).having(
            func.count(Review.id) > 0
        ).order_by(
            desc(func.avg(Review.rating))
        ).limit(limit).all()

    results = []
    for data in product_data:
        product = data[0]
        result_item = {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "stock": product.quantity_available,
            "is_featured": product.is_featured,
            "created_at": product.created_at
        }

        if metric in ["revenue", "orders", "quantity"]:
            result_item.update({
                "total_revenue": float(data.total_revenue or 0),
                "order_count": data.order_count or 0,
                "quantity_sold": data.quantity_sold or 0
            })
        else:
            result_item.update({
                "avg_rating": float(data.avg_rating or 0),
                "review_count": data.review_count or 0
            })

        results.append(result_item)

    return {
        "period_days": days,
        "metric": metric,
        "products": results
    }

@router.get("/dashboard/category-performance")
def get_category_performance(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance breakdown by product categories"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can access dashboard")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    category_data = db.query(
        Category.id,
        Category.name,
        func.count(Product.id.distinct()).label('product_count'),
        func.count(OrderItem.id).label('total_orders'),
        func.sum(OrderItem.quantity).label('quantity_sold'),
        func.sum(OrderItem.total_price).label('total_revenue'),
        func.avg(Review.rating).label('avg_rating'),
        func.count(Review.id.distinct()).label('review_count')
    ).outerjoin(Product, Category.id == Product.category_id).outerjoin(
        OrderItem, and_(
            Product.id == OrderItem.product_id,
            OrderItem.created_at >= cutoff_date
        )
    ).outerjoin(Review, Product.id == Review.product_id).filter(
        Product.seller_id == current_user.id,
        Product.is_active == True
    ).group_by(Category.id, Category.name).all()

    categories = []
    for data in category_data:
        categories.append({
            "category_id": data.id,
            "category_name": data.name,
            "product_count": data.product_count or 0,
            "total_orders": data.total_orders or 0,
            "quantity_sold": data.quantity_sold or 0,
            "total_revenue": float(data.total_revenue or 0),
            "avg_rating": float(data.avg_rating or 0),
            "review_count": data.review_count or 0,
            "avg_revenue_per_product": float(data.total_revenue or 0) / max(data.product_count or 1, 1)
        })

    categories.sort(key=lambda x: x["total_revenue"], reverse=True)

    return {
        "period_days": days,
        "categories": categories
    }

@router.get("/dashboard/recent-orders")
def get_recent_orders(
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, regex="^(pending|confirmed|shipped|delivered|cancelled)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent orders for seller's products"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can access dashboard")

    query = db.query(Order).join(OrderItem).join(Product).filter(
        Product.seller_id == current_user.id
    )

    if status:
        query = query.filter(Order.status == status)

    orders = query.distinct().order_by(desc(Order.created_at)).limit(limit).all()

    order_list = []
    for order in orders:
        seller_items = db.query(OrderItem).join(Product).filter(
            OrderItem.order_id == order.id,
            Product.seller_id == current_user.id
        ).all()

        if seller_items:
            order_list.append({
                "id": order.id,
                "status": order.status,
                "total_amount": float(order.total_amount),
                "created_at": order.created_at,
                "updated_at": order.updated_at,
                "customer": {
                    "id": order.customer.id,
                    "email": order.customer.email,
                    "first_name": getattr(order.customer, 'first_name', ''),
                    "last_name": getattr(order.customer, 'last_name', '')
                },
                "items": [
                    {
                        "id": item.id,
                        "product_id": item.product_id,
                        "product_name": item.product.name,
                        "quantity": item.quantity,
                        "unit_price": float(item.unit_price),
                        "total_price": float(item.total_price)
                    }
                    for item in seller_items
                ],
                "seller_total": sum(float(item.total_price) for item in seller_items)
            })

    return {
        "orders": order_list,
        "status_filter": status
    }

@router.get("/dashboard/inventory-alerts")
def get_inventory_alerts(
    low_stock_threshold: int = Query(5, ge=0, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get inventory alerts for low stock and out of stock products"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can access dashboard")

    out_of_stock = db.query(Product).filter(
        Product.seller_id == current_user.id,
        Product.is_active == True,
        Product.quantity_available == 0
    ).all()

    low_stock = db.query(Product).filter(
        Product.seller_id == current_user.id,
        Product.is_active == True,
        Product.quantity_available > 0,
        Product.quantity_available <= low_stock_threshold
    ).all()

    return {
        "alerts": {
            "out_of_stock": {
                "count": len(out_of_stock),
                "products": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "price": float(p.price),
                        "quantity_available": p.quantity_available,
                        "is_featured": p.is_featured
                    }
                    for p in out_of_stock
                ]
            },
            "low_stock": {
                "count": len(low_stock),
                "threshold": low_stock_threshold,
                "products": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "price": float(p.price),
                        "quantity_available": p.quantity_available,
                        "is_featured": p.is_featured
                    }
                    for p in low_stock
                ]
            }
        }
    }

@router.get("/products/management")
def get_products_for_management(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = Query(None, regex="^(active|inactive|all)$"),
    stock_status: Optional[str] = Query(None, regex="^(in_stock|low_stock|out_of_stock|all)$"),
    sort_by: str = Query("created_at", regex="^(created_at|name|price|quantity_available|status)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    low_stock_threshold: int = Query(5, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get products for management interface with enhanced filtering"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can access product management")

    query = db.query(Product).filter(Product.seller_id == current_user.id)

    if status == "active":
        query = query.filter(Product.is_active == True)
    elif status == "inactive":
        query = query.filter(Product.is_active == False)

    if stock_status == "in_stock":
        query = query.filter(Product.quantity_available > low_stock_threshold)
    elif stock_status == "low_stock":
        query = query.filter(
            Product.quantity_available > 0,
            Product.quantity_available <= low_stock_threshold
        )
    elif stock_status == "out_of_stock":
        query = query.filter(Product.quantity_available == 0)

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
                    Product.sku.ilike(f"%{term}%"),
                    Product.tags.ilike(f"%{term}%")
                )
            )
        if search_conditions:
            query = query.filter(and_(*search_conditions))

    if sort_order == "desc":
        query = query.order_by(desc(getattr(Product, sort_by)))
    else:
        query = query.order_by(getattr(Product, sort_by))

    total_items = query.count()
    offset = (page - 1) * per_page
    products = query.offset(offset).limit(per_page).all()

    product_list = []
    for product in products:
        sales_data = db.query(
            func.count(OrderItem.id).label('total_orders'),
            func.sum(OrderItem.quantity).label('quantity_sold'),
            func.sum(OrderItem.total_price).label('revenue')
        ).filter(OrderItem.product_id == product.id).first()

        review_summary = db.query(
            func.count(Review.id).label('review_count'),
            func.avg(Review.rating).label('avg_rating')
        ).filter(Review.product_id == product.id).first()

        if product.quantity_available == 0:
            stock_status_value = "out_of_stock"
        elif product.quantity_available <= low_stock_threshold:
            stock_status_value = "low_stock"
        else:
            stock_status_value = "in_stock"

        product_list.append({
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "price": float(product.price),
            "quantity_available": product.quantity_available,
            "is_active": product.is_active,
            "is_featured": product.is_featured,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "category": {
                "id": product.category.id,
                "name": product.category.name
            } if product.category else None,
            "seller_category_id": product.seller_category_id,
            "seller_category": {
                "id": product.seller_category.id,
                "name": product.seller_category.name
            } if product.seller_category else None,
            "stock_status": stock_status_value,
            "sales": {
                "total_orders": sales_data.total_orders or 0,
                "quantity_sold": sales_data.quantity_sold or 0,
                "revenue": float(sales_data.revenue or 0)
            },
            "reviews": {
                "count": review_summary.review_count or 0,
                "avg_rating": float(review_summary.avg_rating or 0)
            }
        })

    return {
        "products": product_list,
        "pagination": {
            "current_page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": (total_items + per_page - 1) // per_page,
            "has_next": page * per_page < total_items,
            "has_prev": page > 1
        },
        "filters_applied": {
            "search": search,
            "category_id": category_id,
            "status": status,
            "stock_status": stock_status,
            "low_stock_threshold": low_stock_threshold
        }
    }

class BulkStatusUpdateRequest(BaseModel):
    product_ids: List[int]
    is_active: bool

@router.post("/bulk-operations/update-status")
def bulk_update_product_status(
    request: BulkStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk update product active status"""
    product_ids = request.product_ids
    is_active = request.is_active
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can update products")

    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.seller_id == current_user.id
    ).all()

    if len(products) != len(product_ids):
        raise HTTPException(status_code=404, detail="Some products not found or not owned")

    updated_count = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.seller_id == current_user.id
    ).update({"is_active": is_active}, synchronize_session=False)

    db.commit()

    return {
        "message": f"Updated {updated_count} products",
        "is_active": is_active,
        "product_ids": product_ids
    }

@router.post("/bulk-operations/update-prices")
def bulk_update_product_prices(
    updates: List[Dict],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk update product prices"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can update products")

    product_ids = [update["product_id"] for update in updates]

    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.seller_id == current_user.id
    ).all()

    if len(products) != len(product_ids):
        raise HTTPException(status_code=404, detail="Some products not found or not owned")

    # Reuse the products already loaded for the ownership check above.
    # The previous Query.update() never loaded them, so the old price was not
    # in memory and could not be recorded -- hence the ORM assignment here.
    products_by_id = {product.id: product for product in products}

    updated_count = 0
    for update in updates:
        product = products_by_id.get(update["product_id"])
        if product is None:
            continue

        old_price = product.price
        new_price = Decimal(str(update["price"]))
        if new_price == old_price:
            continue

        product.price = new_price
        # Same transaction as the change: a failed ledger write must roll the
        # price change back rather than let the two diverge.
        db.add(PriceHistory(
            product_id=product.id,
            old_price=old_price,
            new_price=new_price,
            change_reason="bulk_update",
            changed_by=current_user.id,
        ))
        updated_count += 1

    db.commit()

    return {
        "message": f"Updated prices for {updated_count} products",
        "updates": updates
    }

@router.delete("/products/{product_id}")
def delete_seller_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete (deactivate) a seller's product"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can delete products")

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.seller_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    db.commit()

    return {"message": "Product deleted successfully", "product_id": product_id}


@router.get("/dashboard/product-analytics/{product_id}")
def get_product_dashboard_analytics(
    product_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed analytics for a specific product"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can access dashboard")

    # Verify product belongs to seller
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.seller_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Sales statistics
    sales_stats = db.query(
        func.count(OrderItem.id).label('total_orders'),
        func.sum(OrderItem.quantity).label('total_quantity_sold'),
        func.sum(OrderItem.total_price).label('total_revenue')
    ).filter(
        OrderItem.product_id == product_id,
        OrderItem.created_at >= cutoff_date
    ).first()

    # Daily sales trend
    daily_sales = db.query(
        func.date(OrderItem.created_at).label('date'),
        func.count(OrderItem.id).label('orders'),
        func.sum(OrderItem.quantity).label('quantity'),
        func.sum(OrderItem.total_price).label('revenue')
    ).filter(
        OrderItem.product_id == product_id,
        OrderItem.created_at >= cutoff_date
    ).group_by(func.date(OrderItem.created_at)).order_by(func.date(OrderItem.created_at)).all()

    # Review statistics
    review_stats = db.query(
        func.count(Review.id).label('total_reviews'),
        func.avg(Review.rating).label('avg_rating')
    ).filter(Review.product_id == product_id).first()

    # Recent reviews
    recent_reviews = db.query(Review).filter(
        Review.product_id == product_id
    ).order_by(desc(Review.created_at)).limit(5).all()

    return {
        "product_id": product_id,
        "product_name": product.name,
        "period_days": days,
        "sales": {
            "total_orders": sales_stats.total_orders or 0,
            "total_quantity_sold": sales_stats.total_quantity_sold or 0,
            "total_revenue": float(sales_stats.total_revenue or 0),
            "avg_order_value": float(sales_stats.total_revenue or 0) / max(sales_stats.total_orders or 1, 1)
        },
        "daily_sales": [
            {
                "date": sale.date.isoformat() if sale.date else None,
                "orders": sale.orders or 0,
                "quantity": sale.quantity or 0,
                "revenue": float(sale.revenue or 0)
            }
            for sale in daily_sales
        ],
        "reviews": {
            "total_reviews": review_stats.total_reviews or 0,
            "avg_rating": float(review_stats.avg_rating or 0)
        },
        "recent_reviews": [
            {
                "id": review.id,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at.isoformat() if review.created_at else None
            }
            for review in recent_reviews
        ],
        "product_info": {
            "price": float(product.price),
            "quantity_available": product.quantity_available,
            "is_active": product.is_active,
            "is_featured": product.is_featured
        }
    }


@router.post("/upload-image")
async def upload_product_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload image for product use"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can upload images")

    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )

    # Validate file size (max 10MB)
    file_data = await file.read()
    max_size = 10 * 1024 * 1024  # 10MB
    if len(file_data) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB"
        )

    try:
        # Create upload directory if it doesn't exist
        upload_dir = "uploads/products"
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)

        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(file_data)

        # Return file URL
        file_url = f"/static/{upload_dir}/{unique_filename}"

        return {
            "message": "Image uploaded successfully",
            "url": file_url,
            "filename": unique_filename,
            "original_name": file.filename,
            "size": len(file_data),
            "content_type": file.content_type
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload image: {str(e)}"
        )


@router.post("/upload-video")
async def upload_product_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload video for product use (max 60 seconds, 50MB)"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can upload videos")

    # Read file data
    file_data = await file.read()

    # Validate video file
    if not video_service.validate_video_file(file_data, file.filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid video file. Allowed formats: MP4, MOV, AVI, MKV. Max size: 50MB"
        )

    try:
        # Create upload directory if it doesn't exist
        upload_dir = "uploads/products"
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        filename = video_service.generate_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)

        # Save video file
        with open(file_path, "wb") as buffer:
            buffer.write(file_data)

        # Validate duration
        if not video_service.validate_duration(file_path):
            # Clean up the file
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail=f"Video exceeds maximum duration of {video_service.max_duration} seconds"
            )

        # Validate resolution
        if not video_service.validate_resolution(file_path):
            # Clean up the file
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail=f"Video resolution too low. Minimum required: 480p"
            )

        # Generate thumbnail
        thumbnail_path = video_service.generate_thumbnail(file_path)
        thumbnail_url = None
        if thumbnail_path:
            thumbnail_url = f"/static/{thumbnail_path}"

        # Get video metadata
        metadata = video_service.get_video_metadata(file_path)

        # Create file URL
        video_url = f"/static/{upload_dir}/{filename}"

        return {
            "message": "Video uploaded successfully",
            "url": video_url,
            "thumbnail_url": thumbnail_url,
            "filename": filename,
            "original_name": file.filename,
            "duration": metadata['duration'],
            "resolution": f"{metadata['width']}x{metadata['height']}",
            "file_size_mb": metadata['file_size_mb']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload video: {str(e)}"
        )
