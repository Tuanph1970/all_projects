from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.cart import Cart, CartItem
from app.schemas.order import OrderCreate, OrderResponse, OrderUpdate
from app.schemas.address import ShippingAddressCreate
import uuid

router = APIRouter()

@router.post("/", response_model=OrderResponse)
def create_order(
    order: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate products and calculate totals
    subtotal = Decimal('0.00')
    seller_id = None
    
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        if product.quantity_available < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for product {product.name}")
        
        if seller_id is None:
            seller_id = product.seller_id
        elif seller_id != product.seller_id:
            raise HTTPException(status_code=400, detail="All items must be from the same seller")
        
        subtotal += product.price * item.quantity
    
    # Create order
    order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    shipping_amount = Decimal('10.00')  # Fixed shipping for now
    tax_amount = subtotal * Decimal('0.08')  # 8% tax
    total_amount = subtotal + tax_amount + shipping_amount
    
    db_order = Order(
        order_number=order_number,
        customer_id=current_user.id,
        seller_id=seller_id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        shipping_amount=shipping_amount,
        total_amount=total_amount,
        **order.dict(exclude={"items"})
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Create order items
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        total_price = product.price * item.quantity
        
        db_item = OrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=product.price,
            total_price=total_price,
            product_name=product.name,
            product_description=product.description
        )
        db.add(db_item)
        
        # Update product quantity
        product.quantity_available -= item.quantity
    
    db.commit()
    db.refresh(db_order)
    return db_order

@router.get("/", response_model=List[OrderResponse])
def read_orders(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "customer":
        orders = db.query(Order).filter(Order.customer_id == current_user.id).offset(skip).limit(limit).all()
    elif current_user.role in ["seller", "dual"]:
        orders = db.query(Order).filter(Order.seller_id == current_user.id).offset(skip).limit(limit).all()
    else:
        orders = []
    
    return orders

@router.get("/{order_id}", response_model=OrderResponse)
def read_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.customer_id != current_user.id and order.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    
    return order

@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    order_update: OrderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Only seller can update orders
    if order.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the seller can update order status")
    
    for field, value in order_update.dict(exclude_unset=True).items():
        setattr(order, field, value)
    
    db.commit()
    db.refresh(order)
    return order

@router.post("/checkout", response_model=OrderResponse)
def checkout_from_cart(
    shipping_address: ShippingAddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create order from cart items"""
    # Get user's cart
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # Get cart items
    cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Group items by seller (for now, we'll handle single seller orders)
    sellers = set()
    subtotal = Decimal('0.00')
    
    for cart_item in cart_items:
        product = db.query(Product).filter(Product.id == cart_item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {cart_item.product_id} not found")
        
        if not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product {product.name} is no longer available")
        
        if product.quantity_available < cart_item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for product {product.name}")
        
        sellers.add(product.seller_id)
        subtotal += cart_item.total_price
    
    # For now, we only support single seller checkout
    if len(sellers) > 1:
        raise HTTPException(status_code=400, detail="Cart contains items from multiple sellers. Please checkout separately.")
    
    seller_id = list(sellers)[0]
    
    # Calculate totals
    order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    tax_amount = subtotal * Decimal('0.08')  # 8% tax
    shipping_amount = Decimal('10.00') if subtotal < 100 else Decimal('0.00')  # Free shipping over $100
    total_amount = subtotal + tax_amount + shipping_amount
    
    # Create order
    db_order = Order(
        order_number=order_number,
        customer_id=current_user.id,
        seller_id=seller_id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        shipping_amount=shipping_amount,
        total_amount=total_amount,
        shipping_address_line1=shipping_address.address_line1,
        shipping_address_line2=shipping_address.address_line2,
        shipping_city=shipping_address.city,
        shipping_state=shipping_address.state,
        shipping_postal_code=shipping_address.postal_code,
        shipping_country=shipping_address.country,
        customer_notes=getattr(shipping_address, 'notes', None)
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Create order items from cart items
    for cart_item in cart_items:
        product = db.query(Product).filter(Product.id == cart_item.product_id).first()
        
        db_item = OrderItem(
            order_id=db_order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            total_price=cart_item.total_price,
            product_name=product.name,
            product_description=product.description
        )
        db.add(db_item)
        
        # Update product quantity
        product.quantity_available -= cart_item.quantity
    
    # Clear cart after successful order
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    
    db.commit()
    db.refresh(db_order)
    return db_order