from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ProductImageCreate(BaseModel):
    image_url: str
    alt_text: Optional[str] = None
    is_primary: bool = False
    order_index: int = 0

class ProductImageResponse(BaseModel):
    id: int
    image_url: str
    alt_text: Optional[str] = None
    is_primary: bool
    order_index: int

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    description: str
    price: Decimal
    quantity_available: int
    dimensions: Optional[str] = None
    weight: Optional[Decimal] = None
    material: Optional[str] = None
    color: Optional[str] = None
    technique: Optional[str] = None
    minimum_order_quantity: int = 1
    tags: Optional[str] = None
    category_id: int

class ProductCreate(ProductBase):
    images: Optional[List[ProductImageCreate]] = []

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    quantity_available: Optional[int] = None
    dimensions: Optional[str] = None
    weight: Optional[Decimal] = None
    material: Optional[str] = None
    color: Optional[str] = None
    technique: Optional[str] = None
    minimum_order_quantity: Optional[int] = None
    tags: Optional[str] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None

class ProductResponse(BaseModel):
    id: int
    name: str
    description: str
    price: Decimal
    quantity_available: int
    dimensions: Optional[str] = None
    weight: Optional[Decimal] = None
    material: Optional[str] = None
    color: Optional[str] = None
    technique: Optional[str] = None
    minimum_order_quantity: Optional[int] = 1
    tags: Optional[str] = None
    category_id: int
    seller_id: int
    sku: Optional[str] = None
    is_active: bool
    is_featured: bool
    created_at: datetime
    images: List[ProductImageResponse] = []

    class Config:
        from_attributes = True
