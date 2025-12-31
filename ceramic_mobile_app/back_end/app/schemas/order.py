from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.models.order import OrderStatus, PaymentStatus

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemResponse(OrderItemBase):
    id: int
    unit_price: Decimal
    total_price: Decimal
    product_name: str
    product_description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    shipping_address_line1: str
    shipping_address_line2: Optional[str] = None
    shipping_city: str
    shipping_state: str
    shipping_postal_code: str
    shipping_country: str
    customer_notes: Optional[str] = None

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    tracking_number: Optional[str] = None
    shipping_carrier: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    seller_notes: Optional[str] = None

class OrderResponse(OrderBase):
    id: int
    order_number: str
    customer_id: int
    seller_id: int
    status: OrderStatus
    payment_status: PaymentStatus
    subtotal: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    tracking_number: Optional[str] = None
    shipping_carrier: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    seller_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True

# New schemas for order fulfillment

class ShippingInfo(BaseModel):
    tracking_number: str
    carrier: str
    estimated_delivery: Optional[datetime] = None
    notes: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    notes: Optional[str] = None
    
    @validator('status')
    def validate_status_transition(cls, v):
        # This will be validated in the API endpoint with current status
        return v

class BulkOrderStatusUpdate(BaseModel):
    order_id: int
    status: OrderStatus
    notes: Optional[str] = None

class OrderListFilter(BaseModel):
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    search: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"

class OrderStatsResponse(BaseModel):
    period_days: int
    total_orders: int
    revenue: Dict[str, float]
    status_breakdown: Dict[str, Dict[str, Any]]
    pending_actions: Dict[str, int]

class CustomerInfo(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None

class ProductSnapshot(BaseModel):
    id: int
    name: str
    sku: str
    current_price: Decimal
    quantity_available: int
    image_url: Optional[str] = None

class OrderItemWithProduct(OrderItemResponse):
    product: Optional[ProductSnapshot] = None

class ShippingAddress(BaseModel):
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str

class DetailedOrderResponse(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    subtotal: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    created_at: datetime
    updated_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    tracking_number: Optional[str] = None
    shipping_carrier: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    customer_notes: Optional[str] = None
    seller_notes: Optional[str] = None
    customer: CustomerInfo
    items: List[OrderItemWithProduct]
    shipping_address: ShippingAddress

class OrderListResponse(BaseModel):
    orders: List[Dict[str, Any]]
    pagination: Dict[str, Any]
    filters_applied: Dict[str, Any]

class ReturnRequest(BaseModel):
    order_id: int
    items: List[Dict[str, Any]]  # item_id, quantity, reason
    reason: str
    description: Optional[str] = None
    refund_amount: Optional[Decimal] = None

class RefundRequest(BaseModel):
    order_id: int
    amount: Decimal
    reason: str
    description: Optional[str] = None