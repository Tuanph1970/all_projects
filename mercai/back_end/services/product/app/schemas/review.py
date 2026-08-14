from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReviewBase(BaseModel):
    rating: int  # 1-5
    title: Optional[str] = None
    comment: Optional[str] = None
    image_urls: Optional[str] = None  # JSON array

class ReviewCreate(ReviewBase):
    product_id: int
    order_id: int

class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    title: Optional[str] = None
    comment: Optional[str] = None
    image_urls: Optional[str] = None
    seller_response: Optional[str] = None

class ReviewResponse(ReviewBase):
    id: int
    product_id: int
    reviewer_id: int
    seller_id: int
    order_id: int
    is_verified_purchase: bool
    is_approved: bool
    is_helpful_count: Optional[int] = 0
    seller_response: Optional[str] = None
    seller_response_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
