from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func, case, extract, text, literal
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import calendar

from shared.database import get_db
from shared.security import get_current_user
from shared.models.user import User, UserRole
from shared.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from shared.models.product import Product, Category
from shared.models.review import Review

router = APIRouter()

@router.get("/analytics/dashboard", response_model=dict)
def get_analytics_dashboard(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive analytics dashboard for seller"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access analytics"
        )

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Revenue analytics
    revenue_stats = db.query(
        func.sum(Order.total_amount).label('total_revenue'),
        func.avg(Order.total_amount).label('avg_order_value'),
        func.count(Order.id).label('total_orders'),
        func.sum(case(
            (Order.created_at >= datetime.utcnow() - timedelta(days=7), Order.total_amount),
            else_=0
        )).label('revenue_last_7_days'),
        func.sum(case(
            (Order.created_at >= datetime.utcnow() - timedelta(days=30), Order.total_amount),
            else_=0
        )).label('revenue_last_30_days')
    ).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.created_at >= cutoff_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING])
        )
    ).first()

    # Customer analytics
    customer_stats = db.query(
        func.count(func.distinct(Order.customer_id)).label('unique_customers'),
        func.count(case(
            (Order.created_at >= datetime.utcnow() - timedelta(days=30), Order.customer_id),
            else_=None
        )).label('orders_last_30_days')
    ).filter(
        and_(Order.seller_id == current_user.id, Order.created_at >= cutoff_date)
    ).first()

    # Product performance
    product_stats = db.query(
        func.count(func.distinct(Product.id)).label('total_products'),
        func.count(case(
            (Product.quantity_available > 0, Product.id),
            else_=None
        )).label('products_in_stock'),
        func.count(case(
            (Product.quantity_available == 0, Product.id),
            else_=None
        )).label('products_out_of_stock')
    ).filter(Product.seller_id == current_user.id).first()

    # Review analytics
    review_stats = db.query(
        func.count(Review.id).label('total_reviews'),
        func.avg(Review.rating).label('avg_rating'),
        func.count(case(
            (Review.created_at >= datetime.utcnow() - timedelta(days=30), Review.id),
            else_=None
        )).label('reviews_last_30_days')
    ).join(Product).filter(Product.seller_id == current_user.id).first()

    return {
        "period_days": days,
        "revenue": {
            "total": float(revenue_stats.total_revenue) if revenue_stats.total_revenue else 0,
            "average_order_value": float(revenue_stats.avg_order_value) if revenue_stats.avg_order_value else 0,
            "total_orders": revenue_stats.total_orders or 0,
            "last_7_days": float(revenue_stats.revenue_last_7_days) if revenue_stats.revenue_last_7_days else 0,
            "last_30_days": float(revenue_stats.revenue_last_30_days) if revenue_stats.revenue_last_30_days else 0
        },
        "customers": {
            "unique_customers": customer_stats.unique_customers or 0,
            "orders_last_30_days": customer_stats.orders_last_30_days or 0,
            "avg_orders_per_customer": round(
                (customer_stats.orders_last_30_days or 0) / max(customer_stats.unique_customers or 1, 1), 2
            )
        },
        "products": {
            "total_products": product_stats.total_products or 0,
            "in_stock": product_stats.products_in_stock or 0,
            "out_of_stock": product_stats.products_out_of_stock or 0,
            "stock_ratio": round(
                (product_stats.products_in_stock or 0) / max(product_stats.total_products or 1, 1) * 100, 1
            )
        },
        "reviews": {
            "total_reviews": review_stats.total_reviews or 0,
            "average_rating": round(float(review_stats.avg_rating or 0), 2),
            "recent_reviews": review_stats.reviews_last_30_days or 0
        }
    }

@router.get("/analytics/revenue-trends", response_model=dict)
def get_revenue_trends(
    days: int = Query(90, ge=7, le=365),
    granularity: str = Query("day", regex="^(day|week|month)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get revenue trends over time"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access analytics"
        )

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    if granularity == "day":
        time_group = func.date(Order.created_at)
        date_format = "%Y-%m-%d"
    elif granularity == "week":
        time_group = func.concat(
            func.year(Order.created_at),
            '-W',
            func.lpad(func.week(Order.created_at), 2, '0')
        )
        date_format = "%Y-W%U"
    else:
        time_group = func.concat(
            func.year(Order.created_at),
            '-',
            func.lpad(func.month(Order.created_at), 2, '0')
        )
        date_format = "%Y-%m"

    trends = db.query(
        time_group.label('period'),
        func.sum(Order.total_amount).label('revenue'),
        func.count(Order.id).label('orders'),
        func.sum(OrderItem.quantity).label('items_sold')
    ).join(OrderItem).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.created_at >= cutoff_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING])
        )
    ).group_by(time_group).order_by(time_group).all()

    return {
        "period_days": days,
        "granularity": granularity,
        "trends": [
            {
                "period": trend.period,
                "revenue": float(trend.revenue),
                "orders": trend.orders,
                "items_sold": trend.items_sold,
                "avg_order_value": float(trend.revenue) / trend.orders if trend.orders > 0 else 0
            }
            for trend in trends
        ]
    }

@router.get("/analytics/category-performance", response_model=dict)
def get_category_performance(
    days: int = Query(90, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance analytics by product category"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access analytics"
        )

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    category_performance = db.query(
        Category.id.label('category_id'),
        Category.name.label('category_name'),
        func.count(func.distinct(Product.id)).label('product_count')
    ).join(Product, Category.id == Product.category_id).filter(
        Product.seller_id == current_user.id
    ).group_by(Category.id, Category.name).all()

    categories_with_stats = []
    for cat in category_performance:
        order_stats = db.query(
            func.sum(OrderItem.quantity).label('total_quantity_sold'),
            func.sum(OrderItem.total_price).label('total_revenue'),
            func.count(func.distinct(Order.id)).label('total_orders')
        ).join(Product, OrderItem.product_id == Product.id).join(Order, OrderItem.order_id == Order.id).filter(
            Product.category_id == cat.category_id,
            Product.seller_id == current_user.id,
            Order.created_at >= cutoff_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING])
        ).first()

        review_stats = db.query(
            func.avg(Review.rating).label('avg_rating'),
            func.count(Review.id).label('review_count')
        ).join(Product, Review.product_id == Product.id).filter(
            Product.category_id == cat.category_id,
            Product.seller_id == current_user.id
        ).first()

        categories_with_stats.append({
            'category_id': cat.category_id,
            'category_name': cat.category_name,
            'product_count': cat.product_count,
            'total_quantity_sold': order_stats.total_quantity_sold or 0,
            'total_revenue': order_stats.total_revenue or 0,
            'total_orders': order_stats.total_orders or 0,
            'avg_rating': review_stats.avg_rating or 0,
            'review_count': review_stats.review_count or 0
        })

    categories_sorted = sorted(categories_with_stats, key=lambda x: x['total_revenue'], reverse=True)

    return {
        "period_days": days,
        "categories": [
            {
                "category_id": cat['category_id'],
                "category_name": cat['category_name'],
                "product_count": cat['product_count'],
                "total_quantity_sold": cat['total_quantity_sold'],
                "total_revenue": float(cat['total_revenue']),
                "total_orders": cat['total_orders'],
                "avg_rating": round(float(cat['avg_rating']), 2),
                "review_count": cat['review_count'],
                "avg_revenue_per_product": round(
                    float(cat['total_revenue']) / max(cat['product_count'], 1), 2
                )
            }
            for cat in categories_sorted
        ]
    }

@router.get("/analytics/customer-demographics", response_model=dict)
def get_customer_demographics(
    days: int = Query(90, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get customer demographics and behavior analytics"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access analytics"
        )

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    customer_segments = db.query(
        case(
            (func.count(Order.id) == 1, 'One-time'),
            (func.count(Order.id).between(2, 5), 'Regular'),
            (func.count(Order.id) > 5, 'Loyal'),
            else_='Unknown'
        ).label('segment'),
        func.count(func.distinct(Order.customer_id)).label('customer_count'),
        func.avg(Order.total_amount).label('avg_order_value'),
        func.sum(Order.total_amount).label('total_revenue')
    ).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.created_at >= cutoff_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING])
        )
    ).group_by(Order.customer_id).subquery()

    segments_summary = db.query(
        customer_segments.c.segment,
        func.sum(customer_segments.c.customer_count).label('total_customers'),
        func.avg(customer_segments.c.avg_order_value).label('avg_order_value'),
        func.sum(customer_segments.c.total_revenue).label('segment_revenue')
    ).group_by(customer_segments.c.segment).all()

    geographic_dist = db.query(
        Order.shipping_state.label('state'),
        func.count(func.distinct(Order.customer_id)).label('customer_count'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_revenue')
    ).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.created_at >= cutoff_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING])
        )
    ).group_by(Order.shipping_state).order_by(desc('order_count')).limit(10).all()

    order_patterns = db.query(
        func.hour(Order.created_at).label('hour'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue')
    ).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.created_at >= cutoff_date
        )
    ).group_by(func.hour(Order.created_at)).order_by('hour').all()

    return {
        "period_days": days,
        "customer_segments": [
            {
                "segment": seg.segment,
                "customer_count": int(seg.total_customers or 0),
                "avg_order_value": round(float(seg.avg_order_value or 0), 2),
                "total_revenue": float(seg.segment_revenue or 0),
                "percentage": round(
                    (seg.total_customers or 0) / sum(s.total_customers or 0 for s in segments_summary) * 100, 1
                ) if sum(s.total_customers or 0 for s in segments_summary) > 0 else 0
            }
            for seg in segments_summary
        ],
        "geographic_distribution": [
            {
                "state": geo.state,
                "customer_count": geo.customer_count,
                "order_count": geo.order_count,
                "total_revenue": float(geo.total_revenue),
                "avg_order_value": round(float(geo.total_revenue) / geo.order_count, 2) if geo.order_count > 0 else 0
            }
            for geo in geographic_dist
        ],
        "order_patterns_by_hour": [
            {
                "hour": pattern.hour,
                "order_count": pattern.order_count,
                "revenue": float(pattern.revenue),
                "percentage": round(
                    pattern.order_count / sum(p.order_count for p in order_patterns) * 100, 1
                ) if sum(p.order_count for p in order_patterns) > 0 else 0
            }
            for pattern in order_patterns
        ]
    }

@router.get("/analytics/performance-metrics", response_model=dict)
def get_performance_metrics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed performance metrics and KPIs"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access analytics"
        )

    cutoff_date = datetime.utcnow() - timedelta(days=days)
    previous_period_cutoff = cutoff_date - timedelta(days=days)

    current_metrics = db.query(
        func.count(Order.id).label('total_orders'),
        func.sum(Order.total_amount).label('total_revenue'),
        func.avg(Order.total_amount).label('avg_order_value'),
        func.count(func.distinct(Order.customer_id)).label('unique_customers')
    ).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.created_at >= cutoff_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING])
        )
    ).first()

    avg_fulfillment = db.query(
        func.avg(func.timestampdiff(text('DAY'), Order.created_at, Order.shipped_at))
    ).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.created_at >= cutoff_date,
            Order.shipped_at.isnot(None),
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED])
        )
    ).scalar() or 0

    previous_metrics = db.query(
        func.count(Order.id).label('total_orders'),
        func.sum(Order.total_amount).label('total_revenue'),
        func.avg(Order.total_amount).label('avg_order_value'),
        func.count(func.distinct(Order.customer_id)).label('unique_customers')
    ).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.created_at >= previous_period_cutoff,
            Order.created_at < cutoff_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING])
        )
    ).first()

    product_views_total = 0

    return_metrics = db.query(
        func.count(case(
            (Order.status == OrderStatus.REFUNDED, Order.id),
            else_=None
        )).label('refunded_orders'),
        func.count(case(
            (Order.status == OrderStatus.CANCELLED, Order.id),
            else_=None
        )).label('cancelled_orders')
    ).filter(
        and_(Order.seller_id == current_user.id, Order.created_at >= cutoff_date)
    ).first()

    def calculate_growth_rate(current, previous):
        if not previous or previous == 0:
            return 0
        return round(((current - previous) / previous) * 100, 2)

    return {
        "period_days": days,
        "current_period": {
            "total_orders": current_metrics.total_orders or 0,
            "total_revenue": float(current_metrics.total_revenue or 0),
            "avg_order_value": round(float(current_metrics.avg_order_value or 0), 2),
            "unique_customers": current_metrics.unique_customers or 0,
            "avg_fulfillment_days": round(float(avg_fulfillment or 0), 1)
        },
        "growth_rates": {
            "orders_growth": calculate_growth_rate(
                current_metrics.total_orders or 0,
                previous_metrics.total_orders or 0
            ),
            "revenue_growth": calculate_growth_rate(
                float(current_metrics.total_revenue or 0),
                float(previous_metrics.total_revenue or 0)
            ),
            "customer_growth": calculate_growth_rate(
                current_metrics.unique_customers or 0,
                previous_metrics.unique_customers or 0
            )
        },
        "efficiency_metrics": {
            "conversion_rate": round(
                (current_metrics.total_orders or 0) / max(product_views_total or 1, 1) * 100, 2
            ) if product_views_total else 0,
            "refund_rate": round(
                (return_metrics.refunded_orders or 0) / max(current_metrics.total_orders or 1, 1) * 100, 2
            ),
            "cancellation_rate": round(
                (return_metrics.cancelled_orders or 0) / max(current_metrics.total_orders or 1, 1) * 100, 2
            ),
            "customer_lifetime_value": round(
                float(current_metrics.total_revenue or 0) / max(current_metrics.unique_customers or 1, 1), 2
            )
        }
    }

@router.get("/analytics/top-products", response_model=dict)
def get_top_performing_products(
    days: int = Query(30, ge=1, le=365),
    metric: str = Query("revenue", regex="^(revenue|orders|quantity|rating)$"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get top performing products by various metrics"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access analytics"
        )

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    base_query = db.query(
        Product.id.label('product_id'),
        Product.name.label('product_name'),
        Product.price.label('current_price'),
        Product.quantity_available.label('stock'),
        func.sum(OrderItem.quantity).label('total_quantity_sold'),
        func.sum(OrderItem.total_price).label('total_revenue'),
        func.count(func.distinct(Order.id)).label('total_orders'),
        func.avg(Review.rating).label('avg_rating'),
        func.count(Review.id).label('review_count')
    ).select_from(Product
    ).join(OrderItem, OrderItem.product_id == Product.id
    ).join(Order, OrderItem.order_id == Order.id
    ).outerjoin(Review, Review.product_id == Product.id
    ).filter(
        and_(
            Product.seller_id == current_user.id,
            Order.created_at >= cutoff_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING])
        )
    ).group_by(Product.id, Product.name, Product.price, Product.quantity_available)

    if metric == "revenue":
        ordered_query = base_query.order_by(desc('total_revenue'))
    elif metric == "orders":
        ordered_query = base_query.order_by(desc('total_orders'))
    elif metric == "quantity":
        ordered_query = base_query.order_by(desc('total_quantity_sold'))
    else:
        ordered_query = base_query.order_by(desc('avg_rating'))

    top_products = ordered_query.limit(limit).all()

    return {
        "period_days": days,
        "metric": metric,
        "products": [
            {
                "product_id": product.product_id,
                "product_name": product.product_name,
                "current_price": float(product.current_price),
                "stock": product.stock,
                "total_quantity_sold": product.total_quantity_sold or 0,
                "total_revenue": float(product.total_revenue or 0),
                "total_orders": product.total_orders or 0,
                "avg_rating": round(float(product.avg_rating or 0), 2),
                "review_count": product.review_count or 0,
                "total_views": 0,
                "conversion_rate": 0
            }
            for product in top_products
        ]
    }

@router.get("/analytics/comparison", response_model=dict)
def get_comparison_analytics(
    period1_days: int = Query(30, ge=1, le=365),
    period2_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compare performance between two time periods"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access analytics"
        )

    period1_start = datetime.utcnow() - timedelta(days=period1_days)
    period1_end = datetime.utcnow()

    period2_start = period1_start - timedelta(days=period2_days)
    period2_end = period1_start

    def get_period_stats(start_date, end_date):
        return db.query(
            func.count(Order.id).label('total_orders'),
            func.sum(Order.total_amount).label('total_revenue'),
            func.avg(Order.total_amount).label('avg_order_value'),
            func.count(func.distinct(Order.customer_id)).label('unique_customers'),
            func.sum(OrderItem.quantity).label('items_sold')
        ).join(OrderItem).filter(
            and_(
                Order.seller_id == current_user.id,
                Order.created_at >= start_date,
                Order.created_at < end_date,
                Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING])
            )
        ).first()

    period1_stats = get_period_stats(period1_start, period1_end)
    period2_stats = get_period_stats(period2_start, period2_end)

    def calculate_change(current, previous):
        if not previous or previous == 0:
            return {"absolute": current, "percentage": 0}
        return {
            "absolute": current - previous,
            "percentage": round(((current - previous) / previous) * 100, 2)
        }

    return {
        "period1": {
            "days": period1_days,
            "start_date": period1_start.isoformat(),
            "end_date": period1_end.isoformat(),
            "stats": {
                "total_orders": period1_stats.total_orders or 0,
                "total_revenue": float(period1_stats.total_revenue or 0),
                "avg_order_value": round(float(period1_stats.avg_order_value or 0), 2),
                "unique_customers": period1_stats.unique_customers or 0,
                "items_sold": period1_stats.items_sold or 0
            }
        },
        "period2": {
            "days": period2_days,
            "start_date": period2_start.isoformat(),
            "end_date": period2_end.isoformat(),
            "stats": {
                "total_orders": period2_stats.total_orders or 0,
                "total_revenue": float(period2_stats.total_revenue or 0),
                "avg_order_value": round(float(period2_stats.avg_order_value or 0), 2),
                "unique_customers": period2_stats.unique_customers or 0,
                "items_sold": period2_stats.items_sold or 0
            }
        },
        "changes": {
            "orders": calculate_change(
                period1_stats.total_orders or 0,
                period2_stats.total_orders or 0
            ),
            "revenue": calculate_change(
                float(period1_stats.total_revenue or 0),
                float(period2_stats.total_revenue or 0)
            ),
            "avg_order_value": calculate_change(
                float(period1_stats.avg_order_value or 0),
                float(period2_stats.avg_order_value or 0)
            ),
            "customers": calculate_change(
                period1_stats.unique_customers or 0,
                period2_stats.unique_customers or 0
            ),
            "items_sold": calculate_change(
                period1_stats.items_sold or 0,
                period2_stats.items_sold or 0
            )
        }
    }
