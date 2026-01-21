# Order Fulfillment Router for Seller Service
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func, text
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from shared.database import get_db
from shared.security import get_current_user
from shared.models.user import User, UserRole
from shared.models.order import Order, OrderItem, OrderStatus, PaymentStatus, OrderStatusHistory
from shared.models.product import Product

from app.schemas.order_fulfillment import (
    OrderUpdate, ShippingInfo, ReturnRequest, RefundRequest
)

router = APIRouter()


@router.get("/orders", response_model=dict)
def get_seller_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    order_status: Optional[OrderStatus] = None,
    payment_status: Optional[PaymentStatus] = None,
    search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|total_amount|status)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of seller's orders with filtering and sorting"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access order management"
        )

    # Base query
    query = db.query(Order).filter(Order.seller_id == current_user.id)

    # Apply filters
    if order_status:
        query = query.filter(Order.status == order_status)

    if payment_status:
        query = query.filter(Order.payment_status == payment_status)

    if search:
        query = query.filter(
            or_(
                Order.order_number.ilike(f"%{search}%"),
                Order.customer_notes.ilike(f"%{search}%"),
                Order.tracking_number.ilike(f"%{search}%")
            )
        )

    if date_from:
        query = query.filter(Order.created_at >= date_from)

    if date_to:
        query = query.filter(Order.created_at <= date_to)

    # Sorting
    order_column = getattr(Order, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(order_column))
    else:
        query = query.order_by(order_column)

    # Pagination
    total_items = query.count()
    total_pages = (total_items + per_page - 1) // per_page
    offset = (page - 1) * per_page

    orders = query.options(
        joinedload(Order.customer),
        joinedload(Order.items).joinedload(OrderItem.product)
    ).offset(offset).limit(per_page).all()

    return {
        "orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "status": order.status.value,
                "payment_status": order.payment_status.value,
                "total_amount": float(order.total_amount),
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
                "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
                "tracking_number": order.tracking_number,
                "shipping_carrier": order.shipping_carrier,
                "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
                "customer": {
                    "id": order.customer.id,
                    "email": order.customer.email,
                    "first_name": order.customer.first_name,
                    "last_name": order.customer.last_name
                },
                "items": [
                    {
                        "id": item.id,
                        "product_id": item.product_id,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "unit_price": float(item.unit_price),
                        "total_price": float(item.total_price)
                    }
                    for item in order.items
                ],
                "shipping_address": {
                    "line1": order.shipping_address_line1,
                    "line2": order.shipping_address_line2,
                    "city": order.shipping_city,
                    "state": order.shipping_state,
                    "postal_code": order.shipping_postal_code,
                    "country": order.shipping_country
                }
            }
            for order in orders
        ],
        "pagination": {
            "current_page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        "filters_applied": {
            "status": order_status.value if order_status else None,
            "payment_status": payment_status.value if payment_status else None,
            "search": search,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
    }


@router.get("/orders/{order_id}", response_model=dict)
def get_order_details(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific order"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access order details"
        )

    order = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.items).joinedload(OrderItem.product)
    ).filter(
        and_(Order.id == order_id, Order.seller_id == current_user.id)
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status.value,
        "payment_status": order.payment_status.value,
        "subtotal": float(order.subtotal),
        "tax_amount": float(order.tax_amount),
        "shipping_amount": float(order.shipping_amount),
        "total_amount": float(order.total_amount),
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "tracking_number": order.tracking_number,
        "shipping_carrier": order.shipping_carrier,
        "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
        "customer_notes": order.customer_notes,
        "seller_notes": order.seller_notes,
        "customer": {
            "id": order.customer.id,
            "email": order.customer.email,
            "first_name": order.customer.first_name,
            "last_name": order.customer.last_name,
            "phone": getattr(order.customer, 'phone', None)
        },
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "product_description": item.product_description,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total_price": float(item.total_price),
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "sku": item.product.sku,
                    "current_price": float(item.product.price),
                    "quantity_available": item.product.quantity_available
                } if item.product else None
            }
            for item in order.items
        ],
        "shipping_address": {
            "line1": order.shipping_address_line1,
            "line2": order.shipping_address_line2,
            "city": order.shipping_city,
            "state": order.shipping_state,
            "postal_code": order.shipping_postal_code,
            "country": order.shipping_country
        }
    }


@router.patch("/orders/{order_id}/status", response_model=dict)
def update_order_status(
    order_id: int,
    status_update: OrderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update order status and related information"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can update order status"
        )

    order = db.query(Order).filter(
        and_(Order.id == order_id, Order.seller_id == current_user.id)
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Validate status transitions
    valid_transitions = {
        OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
        OrderStatus.CONFIRMED: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
        OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
        OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
        OrderStatus.DELIVERED: [OrderStatus.REFUNDED],
        OrderStatus.CANCELLED: [],
        OrderStatus.REFUNDED: []
    }

    if status_update.status and status_update.status not in valid_transitions[order.status]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {order.status.value} to {status_update.status.value}"
        )

    # Capture old status for history
    old_status = order.status

    # Update fields
    update_data = status_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(order, field, value)

    # Set timestamps based on status changes
    if status_update.status:
        if status_update.status == OrderStatus.SHIPPED:
            order.shipped_at = datetime.utcnow()
        elif status_update.status == OrderStatus.DELIVERED:
            order.delivered_at = datetime.utcnow()

    order.updated_at = datetime.utcnow()

    # Record status change in history
    if status_update.status and status_update.status != old_status:
        history_entry = OrderStatusHistory(
            order_id=order.id,
            old_status=old_status,
            new_status=status_update.status,
            changed_by_id=current_user.id,
            changed_by_role=current_user.role.value,
            notes=status_update.seller_notes if hasattr(status_update, 'seller_notes') else None
        )
        db.add(history_entry)

    try:
        db.commit()
        db.refresh(order)

        return {
            "message": "Order status updated successfully",
            "order_id": order.id,
            "new_status": order.status.value,
            "updated_at": order.updated_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order status"
        )


@router.get("/orders/stats/overview", response_model=dict)
def get_order_stats_overview(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get seller's order statistics overview"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access order statistics"
        )

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Overall stats
    total_orders = db.query(Order).filter(
        and_(Order.seller_id == current_user.id, Order.created_at >= cutoff_date)
    ).count()

    # Status breakdown
    status_stats = db.query(
        Order.status,
        func.count(Order.id).label('count'),
        func.sum(Order.total_amount).label('total_value')
    ).filter(
        and_(Order.seller_id == current_user.id, Order.created_at >= cutoff_date)
    ).group_by(Order.status).all()

    # Revenue stats
    revenue_stats = db.query(
        func.sum(Order.total_amount).label('total_revenue'),
        func.avg(Order.total_amount).label('avg_order_value')
    ).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.created_at >= cutoff_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING])
        )
    ).first()

    # Pending actions (orders needing attention)
    pending_actions = {
        "pending_confirmation": db.query(Order).filter(
            and_(Order.seller_id == current_user.id, Order.status == OrderStatus.PENDING)
        ).count(),
        "ready_to_ship": db.query(Order).filter(
            and_(Order.seller_id == current_user.id, Order.status == OrderStatus.PROCESSING)
        ).count(),
        "shipped_orders": db.query(Order).filter(
            and_(Order.seller_id == current_user.id, Order.status == OrderStatus.SHIPPED)
        ).count()
    }

    return {
        "period_days": days,
        "total_orders": total_orders,
        "revenue": {
            "total": float(revenue_stats.total_revenue) if revenue_stats.total_revenue else 0,
            "average_order_value": float(revenue_stats.avg_order_value) if revenue_stats.avg_order_value else 0
        },
        "status_breakdown": {
            stat.status.value: {
                "count": stat.count,
                "total_value": float(stat.total_value) if stat.total_value else 0
            }
            for stat in status_stats
        },
        "pending_actions": pending_actions
    }


@router.post("/orders/{order_id}/ship", response_model=dict)
def ship_order(
    order_id: int,
    shipping_info: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark order as shipped with tracking information"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can ship orders"
        )

    order = db.query(Order).filter(
        and_(Order.id == order_id, Order.seller_id == current_user.id)
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status != OrderStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be in processing status to ship"
        )

    # Capture old status for history
    old_status = order.status

    # Update order with shipping information
    order.status = OrderStatus.SHIPPED
    order.tracking_number = shipping_info.get("tracking_number")
    order.shipping_carrier = shipping_info.get("carrier")
    order.estimated_delivery = shipping_info.get("estimated_delivery")
    order.shipped_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()

    # Add seller notes if provided
    if shipping_info.get("notes"):
        order.seller_notes = shipping_info.get("notes")

    # Record status change in history
    history_entry = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status=OrderStatus.SHIPPED,
        changed_by_id=current_user.id,
        changed_by_role=current_user.role.value,
        notes=f"Shipped with tracking: {order.tracking_number}" if order.tracking_number else "Shipped"
    )
    db.add(history_entry)

    try:
        db.commit()
        db.refresh(order)

        return {
            "message": "Order shipped successfully",
            "order_id": order.id,
            "tracking_number": order.tracking_number,
            "carrier": order.shipping_carrier,
            "shipped_at": order.shipped_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ship order"
        )


@router.post("/orders/bulk/update-status", response_model=dict)
def bulk_update_order_status(
    updates: List[dict],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk update order statuses"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can update order statuses"
        )

    if len(updates) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update more than 50 orders at once"
        )

    updated_orders = []
    errors = []

    for update in updates:
        try:
            order_id = update.get("order_id")
            new_status = OrderStatus(update.get("status"))

            order = db.query(Order).filter(
                and_(Order.id == order_id, Order.seller_id == current_user.id)
            ).first()

            if not order:
                errors.append(f"Order {order_id} not found")
                continue

            # Validate transition (simplified for bulk operations)
            if new_status in [OrderStatus.CANCELLED, OrderStatus.REFUNDED]:
                pass
            elif order.status == OrderStatus.PENDING and new_status == OrderStatus.CONFIRMED:
                pass
            elif order.status == OrderStatus.CONFIRMED and new_status == OrderStatus.PROCESSING:
                pass
            else:
                errors.append(f"Invalid status transition for order {order_id}")
                continue

            order.status = new_status
            order.updated_at = datetime.utcnow()

            updated_orders.append({
                "order_id": order.id,
                "new_status": order.status.value
            })

        except Exception as e:
            errors.append(f"Error updating order {update.get('order_id', 'unknown')}: {str(e)}")

    try:
        db.commit()

        return {
            "message": f"Bulk update completed. {len(updated_orders)} orders updated.",
            "updated_orders": updated_orders,
            "errors": errors
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete bulk update"
        )


@router.post("/orders/{order_id}/return", response_model=dict)
def process_return_request(
    order_id: int,
    return_request: ReturnRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process a return request for an order"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can process returns"
        )

    order = db.query(Order).options(
        joinedload(Order.items)
    ).filter(
        and_(Order.id == order_id, Order.seller_id == current_user.id)
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status not in [OrderStatus.DELIVERED, OrderStatus.SHIPPED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Returns can only be processed for delivered or shipped orders"
        )

    # Calculate refund amount if not provided
    refund_amount = return_request.refund_amount
    if not refund_amount:
        refund_amount = Decimal('0')
        for return_item in return_request.items:
            item_id = return_item.get("item_id")
            return_qty = return_item.get("quantity", 0)

            order_item = next((item for item in order.items if item.id == item_id), None)
            if order_item and return_qty <= order_item.quantity:
                item_refund = (order_item.unit_price * return_qty)
                refund_amount += item_refund

    # Update order status and add notes
    if order.status == OrderStatus.DELIVERED:
        order.status = OrderStatus.REFUNDED

    order.seller_notes = f"Return processed: {return_request.reason}. " + (order.seller_notes or "")
    order.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(order)

        return {
            "message": "Return request processed successfully",
            "order_id": order.id,
            "refund_amount": float(refund_amount),
            "return_items": return_request.items,
            "status": order.status.value
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process return request"
        )


@router.post("/orders/{order_id}/refund", response_model=dict)
def process_refund(
    order_id: int,
    refund_request: RefundRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process a refund for an order"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can process refunds"
        )

    order = db.query(Order).filter(
        and_(Order.id == order_id, Order.seller_id == current_user.id)
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.payment_status == PaymentStatus.REFUNDED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order has already been refunded"
        )

    if refund_request.amount > order.total_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund amount cannot exceed order total"
        )

    # Update order status
    order.payment_status = PaymentStatus.REFUNDED
    order.status = OrderStatus.REFUNDED
    order.seller_notes = f"Refund processed: {refund_request.reason}. Amount: ${refund_request.amount}. " + (order.seller_notes or "")
    order.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(order)

        return {
            "message": "Refund processed successfully",
            "order_id": order.id,
            "refund_amount": float(refund_request.amount),
            "reason": refund_request.reason,
            "status": order.status.value,
            "payment_status": order.payment_status.value
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process refund"
        )


@router.get("/orders/returns/pending", response_model=dict)
def get_pending_returns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get orders that may need return processing"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can view return requests"
        )

    delivered_orders = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.items)
    ).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.status == OrderStatus.DELIVERED,
            Order.delivered_at >= datetime.utcnow() - timedelta(days=30)
        )
    ).order_by(desc(Order.delivered_at)).limit(20).all()

    return {
        "message": "Delivered orders eligible for returns (last 30 days)",
        "orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "total_amount": float(order.total_amount),
                "delivered_at": order.delivered_at.isoformat(),
                "customer": {
                    "id": order.customer.id,
                    "name": f"{order.customer.first_name} {order.customer.last_name}",
                    "email": order.customer.email
                },
                "items_count": len(order.items),
                "days_since_delivery": (datetime.utcnow() - order.delivered_at).days
            }
            for order in delivered_orders
        ]
    }


@router.get("/orders/analytics/fulfillment", response_model=dict)
def get_fulfillment_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get order fulfillment analytics for seller"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can view fulfillment analytics"
        )

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Processing time analytics (MySQL compatible)
    avg_processing_days = db.query(
        func.avg(func.timestampdiff(text('DAY'), Order.created_at, Order.shipped_at))
    ).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.created_at >= cutoff_date,
            Order.shipped_at.isnot(None)
        )
    ).scalar() or 0

    avg_shipping_days = db.query(
        func.avg(func.timestampdiff(text('DAY'), Order.shipped_at, Order.delivered_at))
    ).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.created_at >= cutoff_date,
            Order.shipped_at.isnot(None),
            Order.delivered_at.isnot(None)
        )
    ).scalar() or 0

    # Return and refund rates
    total_delivered = db.query(Order).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.status == OrderStatus.DELIVERED,
            Order.created_at >= cutoff_date
        )
    ).count()

    total_refunded = db.query(Order).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.status == OrderStatus.REFUNDED,
            Order.created_at >= cutoff_date
        )
    ).count()

    # Fulfillment performance
    on_time_deliveries = db.query(Order).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.status == OrderStatus.DELIVERED,
            Order.created_at >= cutoff_date,
            Order.delivered_at <= Order.estimated_delivery
        )
    ).count() if db.query(Order).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.estimated_delivery.isnot(None)
        )
    ).count() > 0 else 0

    total_with_estimates = db.query(Order).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.status == OrderStatus.DELIVERED,
            Order.created_at >= cutoff_date,
            Order.estimated_delivery.isnot(None)
        )
    ).count()

    return {
        "period_days": days,
        "processing_metrics": {
            "avg_processing_days": float(avg_processing_days),
            "avg_shipping_days": float(avg_shipping_days)
        },
        "quality_metrics": {
            "total_delivered": total_delivered,
            "total_refunded": total_refunded,
            "refund_rate": round(total_refunded / total_delivered * 100, 2) if total_delivered > 0 else 0,
            "on_time_delivery_rate": round(on_time_deliveries / total_with_estimates * 100, 2) if total_with_estimates > 0 else 0
        },
        "fulfillment_health": {
            "orders_needing_attention": db.query(Order).filter(
                and_(
                    Order.seller_id == current_user.id,
                    Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING])
                )
            ).count(),
            "overdue_shipments": db.query(Order).filter(
                and_(
                    Order.seller_id == current_user.id,
                    Order.status == OrderStatus.PROCESSING,
                    Order.created_at <= datetime.utcnow() - timedelta(days=2)
                )
            ).count()
        }
    }


@router.patch("/orders/{order_id}/tracking", response_model=dict)
def update_order_tracking(
    order_id: int,
    tracking_info: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update tracking information for a shipped order"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can update tracking information"
        )

    order = db.query(Order).filter(
        and_(Order.id == order_id, Order.seller_id == current_user.id)
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status not in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tracking can only be updated for shipped or delivered orders"
        )

    # Update tracking fields
    if "tracking_number" in tracking_info:
        order.tracking_number = tracking_info["tracking_number"]
    if "carrier" in tracking_info:
        order.shipping_carrier = tracking_info["carrier"]
    if "estimated_delivery" in tracking_info:
        order.estimated_delivery = tracking_info["estimated_delivery"]

    order.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(order)

        return {
            "message": "Tracking information updated successfully",
            "order_id": order.id,
            "tracking_number": order.tracking_number,
            "carrier": order.shipping_carrier,
            "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
            "updated_at": order.updated_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tracking information"
        )


@router.get("/orders/{order_id}/status-history", response_model=dict)
def get_order_status_history(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the status change history for an order"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can view order status history"
        )

    order = db.query(Order).filter(
        and_(Order.id == order_id, Order.seller_id == current_user.id)
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Get status history
    history = db.query(OrderStatusHistory).filter(
        OrderStatusHistory.order_id == order_id
    ).order_by(OrderStatusHistory.changed_at.asc()).all()

    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "current_status": order.status.value,
        "history": [
            {
                "id": h.id,
                "old_status": h.old_status.value if h.old_status else None,
                "new_status": h.new_status.value,
                "changed_by_role": h.changed_by_role,
                "notes": h.notes,
                "changed_at": h.changed_at.isoformat()
            }
            for h in history
        ],
        "timestamps": {
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None
        }
    }


def _record_status_change(
    db: Session,
    order: Order,
    old_status: OrderStatus,
    new_status: OrderStatus,
    changed_by: User,
    notes: str = None
):
    """Helper function to record a status change in the history table"""
    history_entry = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status=new_status,
        changed_by_id=changed_by.id if changed_by else None,
        changed_by_role=changed_by.role.value if changed_by else "system",
        notes=notes
    )
    db.add(history_entry)
    return history_entry
