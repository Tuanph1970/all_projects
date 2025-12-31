from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.user import User
from app.models.review import Review
from app.models.order import Order
from app.models.product import Product
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate

router = APIRouter()

@router.post("/", response_model=ReviewResponse)
def create_review(
    review: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify order exists and belongs to current user
    order = db.query(Order).filter(Order.id == review.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only review your own orders")
    
    # Get product and seller info
    product = db.query(Product).filter(Product.id == review.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if review already exists
    existing_review = db.query(Review).filter(
        Review.product_id == review.product_id,
        Review.reviewer_id == current_user.id,
        Review.order_id == review.order_id
    ).first()
    
    if existing_review:
        raise HTTPException(status_code=400, detail="Review already exists for this product and order")
    
    db_review = Review(
        **review.dict(),
        reviewer_id=current_user.id,
        seller_id=product.seller_id,
        is_verified_purchase=True
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

@router.get("/product/{product_id}", response_model=List[ReviewResponse])
def read_product_reviews(
    product_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    from sqlalchemy import desc

    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    reviews = db.query(Review).filter(
        Review.product_id == product_id,
        Review.is_approved == True
    ).order_by(desc(Review.created_at)).offset(skip).limit(limit).all()
    return reviews

@router.put("/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: int,
    review_update: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Check if user is the reviewer or the seller (for seller response)
    if review.reviewer_id != current_user.id and review.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this review")
    
    # If seller is responding
    if review.seller_id == current_user.id and review_update.seller_response:
        review.seller_response = review_update.seller_response
        from sqlalchemy.sql import func
        review.seller_response_at = func.now()
    
    # If reviewer is updating
    elif review.reviewer_id == current_user.id:
        for field, value in review_update.dict(exclude_unset=True, exclude={"seller_response"}).items():
            setattr(review, field, value)
    
    db.commit()
    db.refresh(review)
    return review

@router.post("/{review_id}/helpful")
def mark_review_helpful(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Handle None value for is_helpful_count
    if review.is_helpful_count is None:
        review.is_helpful_count = 1
    else:
        review.is_helpful_count += 1
    db.commit()
    return {"message": "Review marked as helpful"}