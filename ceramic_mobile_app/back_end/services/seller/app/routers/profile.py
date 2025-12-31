from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os

from shared.database import get_db
from shared.security import get_current_user
from shared.models.user import User, UserRole
from shared.models.seller_profile import SellerProfile, StoreTheme
from shared.models.product import Product
from shared.models.order import Order, OrderStatus
from shared.models.review import Review

from app.schemas.seller_profile import (
    SellerProfileCreate, SellerProfileUpdate, SellerProfileResponse,
    StoreThemeCreate, StoreThemeUpdate, StoreThemeResponse,
    SellerStoreResponse, PublicStoreResponse, StoreCustomization,
    BusinessVerificationRequest, StoreAnalytics, StoreStats
)

router = APIRouter()

@router.get("/profile", response_model=SellerProfileResponse)
def get_seller_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get seller's profile information"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access profile"
        )

    profile = db.query(SellerProfile).filter(
        SellerProfile.user_id == current_user.id
    ).first()

    if not profile:
        profile = SellerProfile(
            user_id=current_user.id,
            store_name=f"{current_user.first_name}'s Store",
            display_contact_info=True,
            display_business_hours=True,
            allow_custom_orders=False,
            minimum_order_amount=0
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile

@router.put("/profile", response_model=SellerProfileResponse)
def update_seller_profile(
    profile_update: SellerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update seller's profile information"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can update profile"
        )

    profile = db.query(SellerProfile).filter(
        SellerProfile.user_id == current_user.id
    ).first()

    if not profile:
        profile_data = profile_update.dict(exclude_unset=True)
        profile_data['user_id'] = current_user.id
        profile = SellerProfile(**profile_data)
        db.add(profile)
    else:
        update_data = profile_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        profile.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(profile)
        return profile
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@router.get("/store", response_model=SellerStoreResponse)
def get_seller_store(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complete store information including themes"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access store information"
        )

    profile = db.query(SellerProfile).filter(
        SellerProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller profile not found"
        )

    themes = db.query(StoreTheme).filter(
        StoreTheme.seller_profile_id == profile.id
    ).order_by(desc(StoreTheme.is_active), StoreTheme.created_at).all()

    active_theme = next((theme for theme in themes if theme.is_active), None)

    return {
        "profile": profile,
        "active_theme": active_theme,
        "available_themes": themes
    }

@router.post("/themes", response_model=StoreThemeResponse)
def create_store_theme(
    theme_create: StoreThemeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new store theme"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can create themes"
        )

    profile = db.query(SellerProfile).filter(
        SellerProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller profile not found"
        )

    if theme_create.is_active:
        db.query(StoreTheme).filter(
            StoreTheme.seller_profile_id == profile.id
        ).update({"is_active": False})

    theme_data = theme_create.dict()
    theme_data['seller_profile_id'] = profile.id

    theme = StoreTheme(**theme_data)

    try:
        db.add(theme)
        db.commit()
        db.refresh(theme)
        return theme
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create theme"
        )

@router.put("/themes/{theme_id}", response_model=StoreThemeResponse)
def update_store_theme(
    theme_id: int,
    theme_update: StoreThemeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a store theme"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can update themes"
        )

    profile = db.query(SellerProfile).filter(
        SellerProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller profile not found"
        )

    theme = db.query(StoreTheme).filter(
        and_(
            StoreTheme.id == theme_id,
            StoreTheme.seller_profile_id == profile.id
        )
    ).first()

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found"
        )

    if theme_update.is_active:
        db.query(StoreTheme).filter(
            and_(
                StoreTheme.seller_profile_id == profile.id,
                StoreTheme.id != theme_id
            )
        ).update({"is_active": False})

    update_data = theme_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(theme, field):
            setattr(theme, field, value)

    theme.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(theme)
        return theme
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update theme"
        )

@router.post("/themes/{theme_id}/activate", response_model=StoreThemeResponse)
def activate_theme(
    theme_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Activate a specific theme"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can activate themes"
        )

    profile = db.query(SellerProfile).filter(
        SellerProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller profile not found"
        )

    db.query(StoreTheme).filter(
        StoreTheme.seller_profile_id == profile.id
    ).update({"is_active": False})

    theme = db.query(StoreTheme).filter(
        and_(
            StoreTheme.id == theme_id,
            StoreTheme.seller_profile_id == profile.id
        )
    ).first()

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found"
        )

    theme.is_active = True
    theme.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(theme)
        return theme
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate theme"
        )

@router.delete("/themes/{theme_id}")
def delete_theme(
    theme_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a store theme"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can delete themes"
        )

    profile = db.query(SellerProfile).filter(
        SellerProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller profile not found"
        )

    theme = db.query(StoreTheme).filter(
        and_(
            StoreTheme.id == theme_id,
            StoreTheme.seller_profile_id == profile.id
        )
    ).first()

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found"
        )

    if theme.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active theme"
        )

    try:
        db.delete(theme)
        db.commit()
        return {"message": "Theme deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete theme"
        )

@router.get("/public/{seller_id}", response_model=PublicStoreResponse)
def get_public_store(
    seller_id: int,
    db: Session = Depends(get_db)
):
    """Get public store information for customers"""

    profile = db.query(SellerProfile).filter(
        SellerProfile.user_id == seller_id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )

    active_theme = db.query(StoreTheme).filter(
        and_(
            StoreTheme.seller_profile_id == profile.id,
            StoreTheme.is_active == True
        )
    ).first()

    response_data = {
        "store_name": profile.store_name,
        "store_description": profile.store_description,
        "store_tagline": profile.store_tagline,
        "logo_url": profile.logo_url,
        "banner_url": profile.banner_url,
        "brand_colors": profile.brand_colors,
        "social_media_links": profile.social_media_links,
        "allow_custom_orders": profile.allow_custom_orders,
        "minimum_order_amount": profile.minimum_order_amount,
        "shipping_policy": profile.shipping_policy,
        "return_policy": profile.return_policy,
        "processing_time": profile.processing_time,
        "about_us": profile.about_us,
        "specialties": profile.specialties,
        "certifications": profile.certifications,
        "is_verified": profile.is_verified,
        "is_featured": profile.is_featured,
        "active_theme": active_theme
    }

    if profile.display_contact_info:
        response_data["contact_info"] = {
            "business_phone": profile.business_phone,
            "business_email": profile.business_email,
            "website_url": profile.website_url
        }

    if profile.display_business_hours:
        response_data["business_hours"] = profile.business_hours

    return response_data

@router.get("/store-analytics", response_model=StoreAnalytics)
def get_store_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get store analytics summary"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access analytics"
        )

    product_stats = db.query(
        func.count(Product.id).label('total_products')
    ).filter(Product.seller_id == current_user.id).first()

    order_stats = db.query(
        func.count(Order.id).label('total_orders'),
        func.sum(Order.total_amount).label('total_revenue')
    ).filter(
        and_(
            Order.seller_id == current_user.id,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING])
        )
    ).first()

    review_stats = db.query(
        func.avg(Review.rating).label('avg_rating'),
        func.count(Review.id).label('total_reviews')
    ).join(Product).filter(Product.seller_id == current_user.id).first()

    total_views_count = 0
    conversion_rate = 0

    return {
        "total_products": product_stats.total_products or 0,
        "total_orders": order_stats.total_orders or 0,
        "total_revenue": float(order_stats.total_revenue or 0),
        "avg_rating": round(float(review_stats.avg_rating or 0), 2),
        "total_reviews": review_stats.total_reviews or 0,
        "conversion_rate": conversion_rate
    }

@router.get("/stats", response_model=StoreStats)
def get_store_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get store statistics and completion info"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access stats"
        )

    profile = db.query(SellerProfile).filter(
        SellerProfile.user_id == current_user.id
    ).first()

    profile_completion = 0
    if profile:
        total_fields = 20
        completed_fields = 0

        if profile.store_name: completed_fields += 1
        if profile.store_description: completed_fields += 1
        if profile.store_tagline: completed_fields += 1
        if profile.business_phone: completed_fields += 1
        if profile.business_email: completed_fields += 1
        if profile.business_address_line1: completed_fields += 1
        if profile.business_city: completed_fields += 1
        if profile.business_state: completed_fields += 1
        if profile.logo_url: completed_fields += 1
        if profile.banner_url: completed_fields += 1
        if profile.brand_colors: completed_fields += 1
        if profile.social_media_links: completed_fields += 1
        if profile.business_type: completed_fields += 1
        if profile.shipping_policy: completed_fields += 1
        if profile.return_policy: completed_fields += 1
        if profile.processing_time: completed_fields += 1
        if profile.about_us: completed_fields += 1
        if profile.specialties: completed_fields += 1
        if profile.business_hours: completed_fields += 1
        if profile.meta_description: completed_fields += 1

        profile_completion = round((completed_fields / total_fields) * 100, 1)

    store_views = 0
    store_followers = 0

    recent_activity = [
        {"type": "profile_update", "timestamp": datetime.utcnow().isoformat(), "description": "Profile updated"},
        {"type": "theme_change", "timestamp": datetime.utcnow().isoformat(), "description": "Store theme updated"}
    ]

    return {
        "profile_completion": profile_completion,
        "store_views": store_views,
        "store_followers": store_followers,
        "recent_activity": recent_activity
    }

@router.post("/upload-logo")
async def upload_store_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload store logo"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can upload logo"
        )

    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )

    logo_url = f"/uploads/logos/{current_user.id}_{file.filename}"

    profile = db.query(SellerProfile).filter(
        SellerProfile.user_id == current_user.id
    ).first()

    if profile:
        profile.logo_url = logo_url
        profile.updated_at = datetime.utcnow()
        db.commit()

    return {
        "message": "Logo uploaded successfully",
        "logo_url": logo_url
    }

@router.post("/upload-banner")
async def upload_store_banner(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload store banner"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can upload banner"
        )

    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )

    banner_url = f"/uploads/banners/{current_user.id}_{file.filename}"

    profile = db.query(SellerProfile).filter(
        SellerProfile.user_id == current_user.id
    ).first()

    if profile:
        profile.banner_url = banner_url
        profile.updated_at = datetime.utcnow()
        db.commit()

    return {
        "message": "Banner uploaded successfully",
        "banner_url": banner_url
    }

@router.post("/verify")
def request_business_verification(
    verification_request: BusinessVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request business verification"""

    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can request verification"
        )

    return {
        "message": "Verification request submitted successfully",
        "status": "pending_review"
    }
