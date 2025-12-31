from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.user import User
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.schemas.cart import (
    CartResponse, CartItemResponse, AddToCartRequest, 
    CartItemUpdate, CartSummary
)

router = APIRouter(prefix="/cart", tags=["cart"])

def calculate_cart_summary(cart_items: List[CartItem]) -> CartSummary:
    """Calculate cart totals and summary"""
    subtotal = sum(item.total_price for item in cart_items)
    
    # Simple tax calculation (you can make this more sophisticated)
    tax_rate = Decimal('0.08')  # 8% tax
    tax_amount = subtotal * tax_rate
    
    # Simple shipping calculation
    shipping_amount = Decimal('10.00') if subtotal < 100 else Decimal('0.00')
    
    total_amount = subtotal + tax_amount + shipping_amount
    item_count = sum(item.quantity for item in cart_items)
    
    return CartSummary(
        subtotal=subtotal,
        tax_amount=tax_amount,
        shipping_amount=shipping_amount,
        total_amount=total_amount,
        item_count=item_count
    )

def get_or_create_cart(db: Session, user_id: int) -> Cart:
    """Get existing cart or create new one for user"""
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart

@router.get("/", response_model=CartResponse)
def get_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's cart"""
    cart = get_or_create_cart(db, current_user.id)
    
    # Load cart with items and product details
    cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
    
    # Build response with product details
    items_response = []
    for item in cart_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        item_response = CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            created_at=item.created_at,
            updated_at=item.updated_at,
            product_name=product.name if product else "Unknown Product",
            product_description=product.description if product else None,
            product_image_url=product.images[0].image_url if product and product.images else None,
            product_category=product.category.name if product and product.category else None
        )
        items_response.append(item_response)
    
    summary = calculate_cart_summary(cart_items)
    
    return CartResponse(
        id=cart.id,
        user_id=cart.user_id,
        items=items_response,
        summary=summary,
        created_at=cart.created_at,
        updated_at=cart.updated_at
    )

@router.post("/add", response_model=dict)
def add_to_cart(
    request: AddToCartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add item to cart"""
    # Check if product exists and is available
    product = db.query(Product).filter(
        Product.id == request.product_id,
        Product.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or not available"
        )
    
    # Check if requested quantity is available
    if product.quantity_available < request.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {product.quantity_available} items available"
        )
    
    # Get or create cart
    cart = get_or_create_cart(db, current_user.id)
    
    # Check if item already exists in cart
    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == request.product_id
    ).first()
    
    if existing_item:
        # Update existing item
        new_quantity = existing_item.quantity + request.quantity
        if product.quantity_available < new_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot add {request.quantity} more items. Only {product.quantity_available - existing_item.quantity} more available"
            )
        
        existing_item.quantity = new_quantity
        existing_item.total_price = existing_item.unit_price * new_quantity
        db.commit()
        
        return {"message": "Cart updated successfully", "item_id": existing_item.id}
    else:
        # Create new cart item
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=request.product_id,
            quantity=request.quantity,
            unit_price=product.price,
            total_price=product.price * request.quantity
        )
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)
        
        return {"message": "Item added to cart successfully", "item_id": cart_item.id}

@router.put("/items/{item_id}", response_model=dict)
def update_cart_item(
    item_id: int,
    request: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update cart item quantity"""
    # Get user's cart
    cart = get_or_create_cart(db, current_user.id)
    
    # Find cart item
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    ).first()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    # Check product availability
    product = db.query(Product).filter(Product.id == cart_item.product_id).first()
    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or not available"
        )
    
    if product.quantity_available < request.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {product.quantity_available} items available"
        )
    
    # Update cart item
    cart_item.quantity = request.quantity
    cart_item.total_price = cart_item.unit_price * request.quantity
    db.commit()
    
    return {"message": "Cart item updated successfully"}

@router.delete("/items/{item_id}", response_model=dict)
def remove_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove item from cart"""
    # Get user's cart
    cart = get_or_create_cart(db, current_user.id)
    
    # Find and delete cart item
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    ).first()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    db.delete(cart_item)
    db.commit()
    
    return {"message": "Item removed from cart successfully"}

@router.delete("/clear", response_model=dict)
def clear_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all items from cart"""
    cart = get_or_create_cart(db, current_user.id)
    
    # Delete all cart items
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    
    return {"message": "Cart cleared successfully"}

@router.get("/count", response_model=dict)
def get_cart_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get total item count in cart"""
    cart = get_or_create_cart(db, current_user.id)
    
    total_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).count()
    total_quantity = sum(
        item.quantity for item in 
        db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
    )
    
    return {
        "item_count": total_items,
        "total_quantity": total_quantity
    }