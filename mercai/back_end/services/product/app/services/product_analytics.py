"""
Product analytics and recommendation service
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case
from shared.models.product import Product, Category
from shared.models.review import Review
from shared.models.order import Order, OrderItem
from shared.models.user import User

class ProductAnalyticsService:
    """Service for product analytics and recommendations"""

    def __init__(self):
        self.cache_duration = 3600  # 1 hour cache
        self._cache = {}

    def get_product_performance_metrics(
        self,
        db: Session,
        product_id: int,
        days: int = 30
    ) -> Dict:
        """Get comprehensive performance metrics for a product"""

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {}

        sales_data = db.query(
            func.count(OrderItem.id).label('total_orders'),
            func.sum(OrderItem.quantity).label('total_quantity_sold'),
            func.sum(OrderItem.total_price).label('total_revenue')
        ).filter(
            OrderItem.product_id == product_id,
            OrderItem.created_at >= cutoff_date
        ).first()

        review_data = db.query(
            func.count(Review.id).label('total_reviews'),
            func.avg(Review.rating).label('avg_rating'),
            func.sum(case((Review.created_at >= cutoff_date, 1), else_=0)).label('recent_reviews')
        ).filter(Review.product_id == product_id).first()

        view_count = 0

        conversion_rate = 0
        if view_count > 0:
            conversion_rate = (sales_data.total_orders or 0) / view_count * 100

        return {
            "product_id": product_id,
            "period_days": days,
            "sales": {
                "total_orders": sales_data.total_orders or 0,
                "total_quantity_sold": sales_data.total_quantity_sold or 0,
                "total_revenue": float(sales_data.total_revenue or 0),
                "avg_order_value": float(sales_data.total_revenue or 0) / max(sales_data.total_orders or 1, 1)
            },
            "engagement": {
                "total_views": view_count,
                "total_reviews": review_data.total_reviews or 0,
                "recent_reviews": review_data.recent_reviews or 0,
                "avg_rating": float(review_data.avg_rating or 0),
                "conversion_rate": conversion_rate
            },
            "inventory": {
                "current_stock": product.quantity_available,
                "stock_status": "in_stock" if product.quantity_available > 0 else "out_of_stock"
            }
        }

    def get_trending_products(
        self,
        db: Session,
        category_id: Optional[int] = None,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict]:
        """Get trending products based on recent activity"""

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = db.query(Product).filter(
            Product.is_active == True,
            Product.quantity_available > 0
        )

        if category_id:
            query = query.filter(Product.category_id == category_id)

        products = query.all()
        trending_scores = []

        for product in products:
            recent_reviews = db.query(func.count(Review.id)).filter(
                Review.product_id == product.id,
                Review.created_at >= cutoff_date
            ).scalar() or 0

            recent_orders_raw = db.query(func.sum(OrderItem.quantity)).filter(
                OrderItem.product_id == product.id,
                OrderItem.created_at >= cutoff_date
            ).scalar()
            recent_orders = float(recent_orders_raw) if recent_orders_raw else 0.0

            review_weight = 2.0
            order_weight = 3.0
            recency_weight = 1.0

            days_since_creation = (datetime.utcnow() - product.created_at).days
            recency_factor = max(0, 30 - days_since_creation) / 30

            trending_score = (
                float(recent_reviews) * review_weight +
                recent_orders * order_weight +
                recency_factor * recency_weight
            )

            trending_scores.append({
                "product": product,
                "trending_score": trending_score,
                "recent_activity": {
                    "reviews": recent_reviews,
                    "orders": recent_orders
                }
            })

        trending_scores.sort(key=lambda x: x["trending_score"], reverse=True)
        return trending_scores[:limit]

    def get_personalized_recommendations(
        self,
        db: Session,
        user_id: int,
        limit: int = 10
    ) -> List[Product]:
        """Get personalized product recommendations for a user"""

        user_orders = db.query(OrderItem).join(Order).filter(
            Order.customer_id == user_id
        ).all()

        if not user_orders:
            return self.get_popular_products(db, limit=limit)

        purchased_categories = set()
        purchased_materials = set()
        purchased_techniques = set()
        price_range = []

        for order_item in user_orders:
            product = db.query(Product).filter(Product.id == order_item.product_id).first()
            if product:
                purchased_categories.add(product.category_id)
                if product.material:
                    purchased_materials.add(product.material)
                if product.technique:
                    purchased_techniques.add(product.technique)
                price_range.append(float(product.price))

        if price_range:
            avg_price = sum(price_range) / len(price_range)
            price_tolerance = avg_price * 0.5
            min_price = max(0, avg_price - price_tolerance)
            max_price = avg_price + price_tolerance
        else:
            min_price = max_price = None

        query = db.query(Product).filter(
            Product.is_active == True,
            Product.quantity_available > 0,
            ~Product.id.in_([item.product_id for item in user_orders])
        )

        preference_conditions = []

        if purchased_categories:
            preference_conditions.append(
                Product.category_id.in_(purchased_categories)
            )

        if purchased_materials:
            material_conditions = [
                Product.material.ilike(f"%{material}%")
                for material in purchased_materials
            ]
            preference_conditions.append(or_(*material_conditions))

        if purchased_techniques:
            technique_conditions = [
                Product.technique.ilike(f"%{technique}%")
                for technique in purchased_techniques
            ]
            preference_conditions.append(or_(*technique_conditions))

        if min_price and max_price:
            preference_conditions.append(
                Product.price.between(min_price, max_price)
            )

        if preference_conditions:
            query = query.filter(or_(*preference_conditions))

        recommended_products = query.outerjoin(Review).group_by(Product.id).order_by(
            desc(func.avg(Review.rating)),
            desc(Product.created_at)
        ).limit(limit).all()

        if len(recommended_products) < limit:
            remaining = limit - len(recommended_products)
            popular = self.get_popular_products(
                db,
                limit=remaining,
                exclude_ids=[p.id for p in recommended_products]
            )
            recommended_products.extend(popular)

        return recommended_products[:limit]

    def get_popular_products(
        self,
        db: Session,
        category_id: Optional[int] = None,
        days: int = 30,
        limit: int = 10,
        exclude_ids: List[int] = None
    ) -> List[Product]:
        """Get popular products based on orders and reviews"""

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = db.query(Product).filter(
            Product.is_active == True,
            Product.quantity_available > 0
        )

        if category_id:
            query = query.filter(Product.category_id == category_id)

        if exclude_ids:
            query = query.filter(~Product.id.in_(exclude_ids))

        popular_products = query.outerjoin(OrderItem).outerjoin(Review).group_by(Product.id).order_by(
            desc(func.count(OrderItem.id) + func.count(Review.id)),
            desc(func.avg(Review.rating)),
            desc(Product.created_at)
        ).limit(limit).all()

        return popular_products

    def get_category_insights(
        self,
        db: Session,
        category_id: int,
        days: int = 30
    ) -> Dict:
        """Get insights for a specific category"""

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            return {}

        products_in_category = db.query(Product).filter(
            Product.category_id == category_id,
            Product.is_active == True
        ).all()

        total_products = len(products_in_category)
        in_stock_products = len([p for p in products_in_category if p.quantity_available > 0])

        if products_in_category:
            prices = [float(p.price) for p in products_in_category]
            price_stats = {
                "min": min(prices),
                "max": max(prices),
                "avg": sum(prices) / len(prices),
                "median": sorted(prices)[len(prices) // 2]
            }
        else:
            price_stats = {"min": 0, "max": 0, "avg": 0, "median": 0}

        category_sales = db.query(
            func.count(OrderItem.id).label('total_orders'),
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.sum(OrderItem.total_price).label('total_revenue')
        ).join(Product).filter(
            Product.category_id == category_id,
            OrderItem.created_at >= cutoff_date
        ).first()

        category_reviews = db.query(
            func.count(Review.id).label('total_reviews'),
            func.avg(Review.rating).label('avg_rating')
        ).join(Product).filter(
            Product.category_id == category_id
        ).first()

        top_products = self.get_popular_products(
            db,
            category_id=category_id,
            days=days,
            limit=5
        )

        return {
            "category": {
                "id": category.id,
                "name": category.name,
                "description": category.description
            },
            "metrics": {
                "total_products": total_products,
                "in_stock_products": in_stock_products,
                "out_of_stock_products": total_products - in_stock_products
            },
            "price_stats": price_stats,
            "performance": {
                "total_orders": category_sales.total_orders or 0,
                "total_quantity_sold": category_sales.total_quantity or 0,
                "total_revenue": float(category_sales.total_revenue or 0),
                "total_reviews": category_reviews.total_reviews or 0,
                "avg_rating": float(category_reviews.avg_rating or 0)
            },
            "top_products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": float(p.price),
                    "stock": p.quantity_available
                }
                for p in top_products
            ]
        }

    def get_search_analytics(
        self,
        db: Session,
        days: int = 30
    ) -> Dict:
        """Get search and discovery analytics"""

        popular_categories = db.query(
            Category.id,
            Category.name,
            func.count(Product.id).label('product_count')
        ).join(Product).filter(
            Product.is_active == True
        ).group_by(Category.id, Category.name).order_by(
            desc(func.count(Product.id))
        ).limit(10).all()

        popular_materials = db.query(
            Product.material,
            func.count(Product.id).label('count')
        ).filter(
            Product.is_active == True,
            Product.material.isnot(None)
        ).group_by(Product.material).order_by(desc(func.count(Product.id))).limit(10).all()

        return {
            "popular_categories": [
                {
                    "id": cat.id,
                    "name": cat.name,
                    "product_count": cat.product_count
                }
                for cat in popular_categories
            ],
            "popular_materials": [
                {
                    "material": mat.material,
                    "product_count": mat.count
                }
                for mat in popular_materials if mat.material
            ]
        }

# Global instance
product_analytics = ProductAnalyticsService()
