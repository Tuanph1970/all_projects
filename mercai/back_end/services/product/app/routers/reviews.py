from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.sql import func
from typing import List

from shared.database import get_db
from shared.security import get_current_user
from shared.models.user import User
from shared.models.review import Review
from shared.models.order import Order
from shared.models.product import Product

from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate

router = APIRouter()

@router.post("/", response_model=ReviewResponse)
def create_review(
    review: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new review for a product"""
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
    """Get all reviews for a specific product"""
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    reviews = db.query(Review).filter(
        Review.product_id == product_id,
        Review.is_approved == True
    ).order_by(desc(Review.created_at)).offset(skip).limit(limit).all()
    return reviews

@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(
    review_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific review by ID"""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review

@router.put("/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: int,
    review_update: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a review - reviewers can edit their review, sellers can respond"""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Check if user is the reviewer or the seller (for seller response)
    if review.reviewer_id != current_user.id and review.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this review")

    # If seller is responding
    if review.seller_id == current_user.id and review_update.seller_response:
        review.seller_response = review_update.seller_response
        review.seller_response_at = func.now()

    # If reviewer is updating
    elif review.reviewer_id == current_user.id:
        for field, value in review_update.dict(exclude_unset=True, exclude={"seller_response"}).items():
            setattr(review, field, value)

    db.commit()
    db.refresh(review)
    return review

@router.delete("/{review_id}")
def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a review (reviewer only)"""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.reviewer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this review")

    db.delete(review)
    db.commit()

    return {"message": "Review deleted successfully"}

@router.post("/{review_id}/helpful")
def mark_review_helpful(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a review as helpful"""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.is_helpful_count is None:
        review.is_helpful_count = 1
    else:
        review.is_helpful_count += 1
    db.commit()
    return {"message": "Review marked as helpful", "helpful_count": review.is_helpful_count}

@router.get("/seller/{seller_id}", response_model=List[ReviewResponse])
def get_seller_reviews(
    seller_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get all reviews for a specific seller"""
    reviews = db.query(Review).filter(
        Review.seller_id == seller_id,
        Review.is_approved == True
    ).order_by(desc(Review.created_at)).offset(skip).limit(limit).all()
    return reviews

@router.get("/user/{user_id}", response_model=List[ReviewResponse])
def get_user_reviews(
    user_id: int,
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get all reviews written by a specific user"""
    # Users can only view their own reviews
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    reviews = db.query(Review).filter(
        Review.reviewer_id == user_id
    ).order_by(desc(Review.created_at)).offset(skip).limit(limit).all()
    return reviews

@router.get("/stats/product/{product_id}")
def get_product_review_stats(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Get review statistics for a product"""
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    from sqlalchemy import func

    stats = db.query(
        func.count(Review.id).label('total_reviews'),
        func.avg(Review.rating).label('avg_rating'),
        func.sum(Review.is_helpful_count).label('total_helpful')
    ).filter(
        Review.product_id == product_id,
        Review.is_approved == True
    ).first()

    # Rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        count = db.query(func.count(Review.id)).filter(
            Review.product_id == product_id,
            Review.rating == i,
            Review.is_approved == True
        ).scalar()
        rating_distribution[i] = count

    return {
        "product_id": product_id,
        "total_reviews": stats.total_reviews or 0,
        "average_rating": round(float(stats.avg_rating or 0), 1),
        "total_helpful_votes": stats.total_helpful or 0,
        "rating_distribution": rating_distribution
    }
