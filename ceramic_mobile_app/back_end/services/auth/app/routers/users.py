"""
Users Router - User profile and address management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from shared.database import get_db
from shared.security import verify_password, get_password_hash
from shared.models.user import User
from shared.models.address import ShippingAddress
from app.routers.auth import get_current_active_user, get_current_verified_user
from app.schemas.user import UserResponse, UserUpdate, PasswordChange
from app.schemas.address import (
    ShippingAddressCreate,
    ShippingAddressUpdate,
    ShippingAddressResponse
)

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all users (paginated)"""
    users = db.query(User).filter(User.is_active == True).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/me/profile", response_model=UserResponse)
def get_user_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return current_user


@router.put("/me/profile", response_model=UserResponse)
def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    # Update only provided fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/change-password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Change current user password"""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.delete("/me/account")
def deactivate_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deactivate current user account"""
    current_user.is_active = False
    db.commit()
    return {"message": "Account deactivated successfully"}


# Address Management Endpoints

@router.get("/me/addresses", response_model=List[ShippingAddressResponse])
def get_user_addresses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all addresses for current user"""
    addresses = db.query(ShippingAddress).filter(
        ShippingAddress.user_id == current_user.id,
        ShippingAddress.is_active == True
    ).order_by(ShippingAddress.is_default.desc(), ShippingAddress.created_at.desc()).all()
    return addresses


@router.post("/me/addresses", response_model=ShippingAddressResponse)
def create_user_address(
    address: ShippingAddressCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create new address for current user"""
    # Check if user already has 5 addresses (limit)
    address_count = db.query(ShippingAddress).filter(
        ShippingAddress.user_id == current_user.id,
        ShippingAddress.is_active == True
    ).count()

    if address_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 5 addresses allowed per user"
        )

    # If this is set as default, unset other default addresses
    if address.is_default:
        db.query(ShippingAddress).filter(
            ShippingAddress.user_id == current_user.id
        ).update({"is_default": False})

    # If this is the first address, make it default
    if address_count == 0:
        address.is_default = True

    db_address = ShippingAddress(
        user_id=current_user.id,
        **address.dict()
    )
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address


@router.get("/me/addresses/{address_id}", response_model=ShippingAddressResponse)
def get_user_address(
    address_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific address by ID"""
    address = db.query(ShippingAddress).filter(
        ShippingAddress.id == address_id,
        ShippingAddress.user_id == current_user.id,
        ShippingAddress.is_active == True
    ).first()

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    return address


@router.put("/me/addresses/{address_id}", response_model=ShippingAddressResponse)
def update_user_address(
    address_id: int,
    address_update: ShippingAddressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update existing address"""
    address = db.query(ShippingAddress).filter(
        ShippingAddress.id == address_id,
        ShippingAddress.user_id == current_user.id,
        ShippingAddress.is_active == True
    ).first()

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    # Update fields
    update_data = address_update.dict(exclude_unset=True)

    # Handle default address logic
    if update_data.get("is_default") == True:
        # Unset other default addresses
        db.query(ShippingAddress).filter(
            ShippingAddress.user_id == current_user.id,
            ShippingAddress.id != address_id
        ).update({"is_default": False})

    for field, value in update_data.items():
        setattr(address, field, value)

    db.commit()
    db.refresh(address)
    return address


@router.post("/me/addresses/{address_id}/set-default")
def set_default_address(
    address_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Set address as default"""
    address = db.query(ShippingAddress).filter(
        ShippingAddress.id == address_id,
        ShippingAddress.user_id == current_user.id,
        ShippingAddress.is_active == True
    ).first()

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    # Unset all default addresses for user
    db.query(ShippingAddress).filter(
        ShippingAddress.user_id == current_user.id
    ).update({"is_default": False})

    # Set this address as default
    address.is_default = True
    db.commit()

    return {"message": "Default address updated successfully"}


@router.delete("/me/addresses/{address_id}")
def delete_user_address(
    address_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete address (soft delete)"""
    address = db.query(ShippingAddress).filter(
        ShippingAddress.id == address_id,
        ShippingAddress.user_id == current_user.id,
        ShippingAddress.is_active == True
    ).first()

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    # Don't allow deletion of the last address if it's default
    address_count = db.query(ShippingAddress).filter(
        ShippingAddress.user_id == current_user.id,
        ShippingAddress.is_active == True
    ).count()

    if address.is_default and address_count > 1:
        # Set another address as default
        next_address = db.query(ShippingAddress).filter(
            ShippingAddress.user_id == current_user.id,
            ShippingAddress.id != address_id,
            ShippingAddress.is_active == True
        ).first()
        if next_address:
            next_address.is_default = True

    # Soft delete
    address.is_active = False
    db.commit()

    return {"message": "Address deleted successfully"}
