from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class CartItemBase(BaseModel):
    product_id: int
    quantity: int

    @validator('quantity')
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError('Quantity must be at least 1')
        return v

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: int

    @validator('quantity')
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError('Quantity must be at least 1')
        return v

class CartItemResponse(CartItemBase):
    id: int
    unit_price: Decimal
    total_price: Decimal
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Product details
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_image_url: Optional[str] = None
    product_category: Optional[str] = None

    class Config:
        from_attributes = True

class CartSummary(BaseModel):
    subtotal: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    item_count: int

class CartResponse(BaseModel):
    id: int
    user_id: int
    items: List[CartItemResponse] = []
    summary: CartSummary
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AddToCartRequest(BaseModel):
    product_id: int
    quantity: int = 1

    @validator('quantity')
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError('Quantity must be at least 1')
        return v