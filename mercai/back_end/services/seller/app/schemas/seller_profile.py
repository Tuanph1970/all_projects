from pydantic import BaseModel, validator, HttpUrl
from typing import Optional, Dict, List, Any
from datetime import datetime

class BusinessHours(BaseModel):
    open: Optional[str] = None  # "HH:MM" format
    close: Optional[str] = None  # "HH:MM" format
    closed: bool = False

class BrandColors(BaseModel):
    primary: Optional[str] = None
    secondary: Optional[str] = None
    accent: Optional[str] = None
    background: Optional[str] = None
    text: Optional[str] = None

class SocialMediaLinks(BaseModel):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None
    tiktok: Optional[str] = None

class ComponentSettings(BaseModel):
    product_cards: Optional[Dict[str, Any]] = None
    buttons: Optional[Dict[str, Any]] = None
    navigation: Optional[Dict[str, Any]] = None
    footer: Optional[Dict[str, Any]] = None

class SellerProfileBase(BaseModel):
    store_name: Optional[str] = None
    store_description: Optional[str] = None
    store_tagline: Optional[str] = None

    business_phone: Optional[str] = None
    business_email: Optional[str] = None
    website_url: Optional[str] = None

    business_address_line1: Optional[str] = None
    business_address_line2: Optional[str] = None
    business_city: Optional[str] = None
    business_state: Optional[str] = None
    business_postal_code: Optional[str] = None
    business_country: Optional[str] = None

    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    brand_colors: Optional[BrandColors] = None

    social_media_links: Optional[SocialMediaLinks] = None

    business_type: Optional[str] = None
    tax_id: Optional[str] = None
    business_license: Optional[str] = None

    display_contact_info: bool = True
    display_business_hours: bool = True
    allow_custom_orders: bool = False
    minimum_order_amount: int = 0

    business_hours: Optional[Dict[str, BusinessHours]] = None

    shipping_policy: Optional[str] = None
    return_policy: Optional[str] = None
    processing_time: Optional[str] = None

    about_us: Optional[str] = None
    specialties: Optional[List[str]] = None
    certifications: Optional[List[str]] = None

    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    keywords: Optional[List[str]] = None

class SellerProfileCreate(SellerProfileBase):
    pass

class SellerProfileUpdate(SellerProfileBase):
    pass

class SellerProfileResponse(SellerProfileBase):
    id: int
    user_id: int
    is_verified: bool
    is_featured: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class StoreThemeBase(BaseModel):
    theme_name: str
    is_active: bool = False

    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None

    font_family: Optional[str] = None
    heading_font: Optional[str] = None
    body_font: Optional[str] = None

    layout_style: Optional[str] = None
    header_style: Optional[str] = None
    footer_style: Optional[str] = None

    custom_css: Optional[str] = None
    component_settings: Optional[ComponentSettings] = None

class StoreThemeCreate(StoreThemeBase):
    pass

class StoreThemeUpdate(StoreThemeBase):
    theme_name: Optional[str] = None

class StoreThemeResponse(StoreThemeBase):
    id: int
    seller_profile_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SellerStoreResponse(BaseModel):
    profile: SellerProfileResponse
    active_theme: Optional[StoreThemeResponse] = None
    available_themes: List[StoreThemeResponse] = []

class PublicStoreResponse(BaseModel):
    """Public-facing store information for customers"""
    store_name: Optional[str] = None
    store_description: Optional[str] = None
    store_tagline: Optional[str] = None

    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    brand_colors: Optional[BrandColors] = None

    contact_info: Optional[Dict[str, Any]] = None
    business_hours: Optional[Dict[str, BusinessHours]] = None

    social_media_links: Optional[SocialMediaLinks] = None

    allow_custom_orders: bool = False
    minimum_order_amount: int = 0

    shipping_policy: Optional[str] = None
    return_policy: Optional[str] = None
    processing_time: Optional[str] = None

    about_us: Optional[str] = None
    specialties: Optional[List[str]] = None
    certifications: Optional[List[str]] = None

    is_verified: bool = False
    is_featured: bool = False

    active_theme: Optional[StoreThemeResponse] = None

class StoreAnalytics(BaseModel):
    total_products: int
    total_orders: int
    total_revenue: float
    avg_rating: float
    total_reviews: int
    conversion_rate: float

class StoreStats(BaseModel):
    profile_completion: float
    store_views: int
    store_followers: int
    recent_activity: List[Dict[str, Any]]

class BusinessVerificationRequest(BaseModel):
    business_name: str
    business_type: str
    tax_id: str
    business_license: Optional[str] = None
    business_address: str
    business_phone: str
    business_email: str
    supporting_documents: Optional[List[str]] = None

class StoreCustomization(BaseModel):
    """Request model for store customization"""
    profile_updates: Optional[SellerProfileUpdate] = None
    theme_updates: Optional[StoreThemeUpdate] = None
    new_theme: Optional[StoreThemeCreate] = None
    activate_theme_id: Optional[int] = None
