from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from shared.database import Base

class SellerProfile(Base):
    __tablename__ = "seller_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Store Information
    store_name = Column(String(255), nullable=True)
    store_description = Column(Text, nullable=True)
    store_tagline = Column(String(500), nullable=True)
    
    # Contact Information
    business_phone = Column(String(20), nullable=True)
    business_email = Column(String(255), nullable=True)
    website_url = Column(String(500), nullable=True)
    
    # Address Information
    business_address_line1 = Column(String(255), nullable=True)
    business_address_line2 = Column(String(255), nullable=True)
    business_city = Column(String(100), nullable=True)
    business_state = Column(String(100), nullable=True)
    business_postal_code = Column(String(20), nullable=True)
    business_country = Column(String(100), nullable=True)
    
    # Branding
    logo_url = Column(String(500), nullable=True)
    banner_url = Column(String(500), nullable=True)
    brand_colors = Column(JSON, nullable=True)  # {"primary": "#hex", "secondary": "#hex", "accent": "#hex"}
    
    # Social Media
    social_media_links = Column(JSON, nullable=True)  # {"facebook": "url", "instagram": "url", etc.}
    
    # Business Information
    business_type = Column(String(100), nullable=True)  # "individual", "business", "corporation"
    tax_id = Column(String(50), nullable=True)
    business_license = Column(String(100), nullable=True)
    
    # Settings
    display_contact_info = Column(Boolean, default=True)
    display_business_hours = Column(Boolean, default=True)
    allow_custom_orders = Column(Boolean, default=False)
    minimum_order_amount = Column(Integer, default=0)  # in cents
    
    # Business Hours (JSON format)
    business_hours = Column(JSON, nullable=True)
    # Example: {
    #   "monday": {"open": "09:00", "close": "17:00", "closed": false},
    #   "tuesday": {"open": "09:00", "close": "17:00", "closed": false},
    #   ...
    # }
    
    # Shipping Information
    shipping_policy = Column(Text, nullable=True)
    return_policy = Column(Text, nullable=True)
    processing_time = Column(String(100), nullable=True)  # "1-2 business days"
    
    # Additional Information
    about_us = Column(Text, nullable=True)
    specialties = Column(JSON, nullable=True)  # Array of specialty tags
    certifications = Column(JSON, nullable=True)  # Array of certifications
    
    # SEO
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # Array of SEO keywords
    
    # Status
    is_verified = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="seller_profile")

class StoreTheme(Base):
    __tablename__ = "store_themes"

    id = Column(Integer, primary_key=True, index=True)
    seller_profile_id = Column(Integer, ForeignKey("seller_profiles.id"), nullable=False, index=True)
    
    # Theme Information
    theme_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=False)
    
    # Color Scheme
    primary_color = Column(String(7), nullable=True)  # Hex color
    secondary_color = Column(String(7), nullable=True)
    accent_color = Column(String(7), nullable=True)
    background_color = Column(String(7), nullable=True)
    text_color = Column(String(7), nullable=True)
    
    # Typography
    font_family = Column(String(100), nullable=True)
    heading_font = Column(String(100), nullable=True)
    body_font = Column(String(100), nullable=True)
    
    # Layout Settings
    layout_style = Column(String(50), nullable=True)  # "grid", "list", "masonry"
    header_style = Column(String(50), nullable=True)  # "minimal", "full", "centered"
    footer_style = Column(String(50), nullable=True)
    
    # Custom CSS
    custom_css = Column(Text, nullable=True)
    
    # Component Settings
    component_settings = Column(JSON, nullable=True)
    # Example: {
    #   "product_cards": {"border_radius": "8px", "shadow": "medium"},
    #   "buttons": {"style": "rounded", "size": "medium"},
    #   ...
    # }
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    seller_profile = relationship("SellerProfile", backref="themes")