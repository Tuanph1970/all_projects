from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ============================================
# Seller Info Schema (for product responses)
# ============================================

class SellerInfo(BaseModel):
    """Seller information embedded in product response"""
    id: int
    name: str
    shop_name: Optional[str] = None
    rating: Optional[float] = None
    reviewCount: int = 0

    class Config:
        from_attributes = True


# ============================================
# Brand Schemas
# ============================================

class BrandBase(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None


class BrandCreate(BrandBase):
    pass


class BrandResponse(BrandBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Category Schemas
# ============================================

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


class CategoryDetailResponse(CategoryResponse):
    """Extended category response with product count"""
    product_count: Optional[int] = 0
    children: List["CategoryDetailResponse"] = []


# ============================================
# Product Variant Schemas
# ============================================

class ProductVariantBase(BaseModel):
    name: str
    sku: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[str] = None
    price: Decimal
    price_adjustment: Optional[Decimal] = 0
    quantity_available: int = 0
    is_default: bool = False
    image_url: Optional[str] = None


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantUpdate(BaseModel):
    name: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[str] = None
    price: Optional[Decimal] = None
    price_adjustment: Optional[Decimal] = None
    quantity_available: Optional[int] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    image_url: Optional[str] = None


class ProductVariantResponse(ProductVariantBase):
    id: int
    product_id: int
    sku: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Price History Schemas
# ============================================

class PriceHistoryBase(BaseModel):
    old_price: Decimal
    new_price: Decimal
    change_reason: Optional[str] = None


class PriceHistoryCreate(PriceHistoryBase):
    product_id: int
    variant_id: Optional[int] = None
    changed_by: Optional[int] = None


class PriceHistoryResponse(PriceHistoryBase):
    id: int
    product_id: int
    variant_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Product Tag Schemas
# ============================================

class ProductTagBase(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None


class ProductTagCreate(ProductTagBase):
    pass


class ProductTagResponse(ProductTagBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Product Attribute Schemas
# ============================================

class ProductAttributeBase(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None
    display_order: int = 0
    is_visible: bool = True


class ProductAttributeCreate(ProductAttributeBase):
    pass


class ProductAttributeResponse(ProductAttributeBase):
    id: int
    product_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Product Specification Schemas
# ============================================

class ProductSpecificationBase(BaseModel):
    group_name: Optional[str] = None
    spec_name: str
    spec_value: str
    display_order: int = 0


class ProductSpecificationCreate(ProductSpecificationBase):
    pass


class ProductSpecificationResponse(ProductSpecificationBase):
    id: int
    product_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Product Availability Schema
# ============================================

class ProductAvailabilityResponse(BaseModel):
    product_id: int
    is_available: bool
    quantity_available: int
    has_variants: bool = False
    variants_availability: Optional[List[dict]] = None
    low_stock_threshold: int = 5
    is_low_stock: bool = False
    estimated_restock_date: Optional[datetime] = None

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
    brand_id: Optional[int] = None


class ProductCreate(ProductBase):
    slug: Optional[str] = None
    original_price: Optional[Decimal] = None
    discount_percentage: Optional[Decimal] = None
    images: Optional[List[ProductImageCreate]] = []
    variants: Optional[List[ProductVariantCreate]] = []
    attributes: Optional[List[ProductAttributeCreate]] = []
    specifications: Optional[List[ProductSpecificationCreate]] = []


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    discount_percentage: Optional[Decimal] = None
    quantity_available: Optional[int] = None
    dimensions: Optional[str] = None
    weight: Optional[Decimal] = None
    material: Optional[str] = None
    color: Optional[str] = None
    technique: Optional[str] = None
    minimum_order_quantity: Optional[int] = None
    tags: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    slug: Optional[str] = None
    description: str
    price: Decimal
    original_price: Optional[Decimal] = None
    discount_percentage: Optional[Decimal] = None
    quantity_available: int
    dimensions: Optional[str] = None
    weight: Optional[Decimal] = None
    material: Optional[str] = None
    color: Optional[str] = None
    technique: Optional[str] = None
    minimum_order_quantity: Optional[int] = 1
    tags: Optional[str] = None
    category_id: int
    brand_id: Optional[int] = None
    seller_id: int
    sku: Optional[str] = None
    is_active: bool
    is_featured: bool
    created_at: datetime
    images: List[ProductImageResponse] = []
    seller: Optional[SellerInfo] = None

    class Config:
        from_attributes = True


class ProductCompareResponse(BaseModel):
    """Response for product comparison"""
    products: List[ProductResponse]
    comparison_attributes: List[str]
    comparison_data: dict