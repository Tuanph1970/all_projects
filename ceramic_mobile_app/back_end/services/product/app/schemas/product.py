from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class SellerInfo(BaseModel):
    """Seller information embedded in product response"""
    id: int
    name: str
    shop_name: Optional[str] = None
    rating: Optional[float] = None
    reviewCount: int = 0

    class Config:
        from_attributes = True


class SellerCategoryInfo(BaseModel):
    """Seller category information embedded in product response"""
    id: int
    name: str
    full_path_name: Optional[str] = None

    class Config:
        from_attributes = True


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


class ProductVideoResponse(BaseModel):
    id: int
    video_url: str
    thumbnail_url: Optional[str] = None
    alt_text: Optional[str] = None
    duration_seconds: Optional[Decimal] = None
    file_size_mb: Optional[Decimal] = None
    resolution: Optional[str] = None
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
    category_id: Optional[int] = None
    seller_category_id: Optional[int] = None

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
    seller_category_id: Optional[int] = None
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
    category_id: Optional[int] = None
    seller_category_id: Optional[int] = None
    seller_category: Optional[SellerCategoryInfo] = None
    seller_id: int
    sku: Optional[str] = None
    is_active: bool
    is_featured: bool
    created_at: datetime
    images: List[ProductImageResponse] = []
    videos: List[ProductVideoResponse] = []
    seller: Optional[SellerInfo] = None

    class Config:
        from_attributes = True
