# Order Fulfillment Schemas for Seller Service
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from shared.models.order import OrderStatus, PaymentStatus


class OrderUpdate(BaseModel):
    """Schema for updating order status and related fields"""
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    tracking_number: Optional[str] = None
    shipping_carrier: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    seller_notes: Optional[str] = None


class ShippingInfo(BaseModel):
    """Schema for shipping information when marking order as shipped"""
    tracking_number: str
    carrier: str
    estimated_delivery: Optional[datetime] = None
    notes: Optional[str] = None


class ReturnRequest(BaseModel):
    """Schema for processing return requests"""
    order_id: int
    items: List[Dict[str, Any]]  # item_id or product_id, quantity, reason
    reason: str
    description: Optional[str] = None
    refund_amount: Optional[Decimal] = None


class RefundRequest(BaseModel):
    """Schema for processing refunds"""
    order_id: int
    amount: Decimal
    reason: str
    description: Optional[str] = None
