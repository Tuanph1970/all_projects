"""
Deterministic image quality checks for a seller's listing.

This is the one piece of the old ai-service that survived the removal of the
model, and it survived precisely because it never needed one: every finding is
a measurement taken with Pillow, so it cannot hallucinate. It lost its caller
when the listing optimizer was deleted; this router gives it one back.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from shared.config import settings
from shared.database import get_db
from shared.models.ai import FEATURE_PRICE_INTEL
from shared.models.product import Product
from shared.models.user import User, UserRole
from shared.security import get_current_user

from app.services.guardrails import feature_enabled
from app.services.image_report import build_image_report

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/products/{product_id}/image-report")
def get_image_report(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    What is measurably wrong with this listing's photos.

    Findings are advisory and nothing is written -- the seller decides what to
    reshoot.
    """
    if not feature_enabled(FEATURE_PRICE_INTEL, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if current_user.role not in (UserRole.SELLER, UserRole.DUAL):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can view image reports",
        )

    product = (
        db.query(Product)
        .options(joinedload(Product.images))
        .filter(Product.id == product_id)
        .first()
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this product",
        )

    return {"product_id": product.id, **build_image_report(list(product.images or []))}
