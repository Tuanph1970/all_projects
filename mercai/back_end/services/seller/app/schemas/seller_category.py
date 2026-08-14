"""
Pydantic schemas for Seller Category Management API
Supports tree structure with max 4 levels depth
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, ForwardRef
from datetime import datetime


# Forward reference for recursive tree structure
SellerCategoryTreeNodeRef = ForwardRef('SellerCategoryTreeNode')


class SellerCategoryBase(BaseModel):
    """Base schema with common category fields"""
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    slug: Optional[str] = Field(None, max_length=120, description="URL-friendly name")
    description: Optional[str] = Field(None, description="Category description")
    icon_url: Optional[str] = Field(None, max_length=500, description="Icon image URL")
    image_url: Optional[str] = Field(None, max_length=500, description="Category image URL")
    is_active: bool = Field(True, description="Whether category is active")
    display_order: int = Field(0, ge=0, description="Display order for sorting")


class SellerCategoryCreate(SellerCategoryBase):
    """Schema for creating a new seller category"""
    parent_id: Optional[int] = Field(None, description="Parent category ID (null for root categories)")

    @validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Category name cannot be empty')
        return v.strip()


class SellerCategoryUpdate(BaseModel):
    """Schema for updating an existing seller category"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, max_length=120)
    description: Optional[str] = None
    icon_url: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    display_order: Optional[int] = Field(None, ge=0)
    parent_id: Optional[int] = None  # Allows moving category to different parent

    @validator('name')
    def name_not_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Category name cannot be empty')
        return v.strip() if v else v


class SellerCategoryResponse(SellerCategoryBase):
    """Response schema for a single category (without nested children)"""
    id: int
    seller_id: int
    parent_id: Optional[int] = None
    level: int
    path: Optional[str] = None
    product_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SellerCategoryBrief(BaseModel):
    """Brief category info for lists and references"""
    id: int
    name: str
    slug: Optional[str] = None
    level: int
    is_active: bool
    product_count: int = 0

    class Config:
        from_attributes = True


class SellerCategoryTreeNode(SellerCategoryResponse):
    """Category node with nested children for tree structure"""
    children: List['SellerCategoryTreeNode'] = []
    full_path_name: Optional[str] = None  # "Parent > Child > Grandchild"

    class Config:
        from_attributes = True


# Update forward reference
SellerCategoryTreeNode.model_rebuild()


class SellerCategoryListResponse(BaseModel):
    """Response for paginated category list"""
    items: List[SellerCategoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SellerCategoryTreeResponse(BaseModel):
    """Response for full category tree"""
    categories: List[SellerCategoryTreeNode]
    total_count: int
    max_level: int = 4


class CategoryReorderItem(BaseModel):
    """Single item in reorder request"""
    id: int = Field(..., description="Category ID")
    display_order: int = Field(..., ge=0, description="New display order")
    parent_id: Optional[int] = Field(None, description="New parent ID (optional, for moving)")


class CategoryReorderRequest(BaseModel):
    """Request to reorder multiple categories"""
    items: List[CategoryReorderItem] = Field(..., min_items=1, description="Categories to reorder")


class CategoryMoveRequest(BaseModel):
    """Request to move a category to a new parent"""
    new_parent_id: Optional[int] = Field(None, description="New parent ID (null for root)")


class CategoryBulkActionRequest(BaseModel):
    """Request for bulk actions on categories"""
    category_ids: List[int] = Field(..., min_items=1, description="Category IDs to act on")
    action: str = Field(..., description="Action: activate, deactivate, delete")


class CategoryBulkActionResponse(BaseModel):
    """Response for bulk actions"""
    success: bool
    affected_count: int
    message: str
    failed_ids: List[int] = []


class CategoryPathResponse(BaseModel):
    """Response with category breadcrumb path"""
    path: List[SellerCategoryBrief]
    current: SellerCategoryResponse


class CategoryStatsResponse(BaseModel):
    """Statistics about seller's categories"""
    total_categories: int
    active_categories: int
    root_categories: int
    max_depth_used: int
    categories_by_level: dict  # {1: count, 2: count, 3: count, 4: count}
