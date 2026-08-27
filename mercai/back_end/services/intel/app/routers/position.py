"""
Price position endpoints.

Read-only. This router never writes to `products` -- it reports on the
catalogue, and anything a seller decides to change goes through the existing
PUT /api/v1/products/{id}, so that service's validation, ownership checks,
cache invalidation and price ledger all keep working untouched.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from shared.cache import cache
from shared.config import settings
from shared.database import get_db
from shared.models.ai import FEATURE_PRICE_INTEL
from shared.models.product import Category, Product
from shared.models.user import User, UserRole
from shared.security import get_current_user

from app.schemas.position import PricePositionResponse
from app.services import benchmarks as benchmark_service
from app.services import position as position_service
from app.services.guardrails import feature_enabled

logger = logging.getLogger(__name__)
router = APIRouter()


def _require_enabled(current_user: User) -> None:
    # 404 rather than 403: a disabled feature should not advertise its
    # existence. Matches the convention the retired listing router set.
    if not feature_enabled(FEATURE_PRICE_INTEL, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _cache_key(product_id: int) -> str:
    return f"mercai:intel:position:{product_id}"


@router.get("/products/{product_id}/price-position", response_model=PricePositionResponse)
def get_price_position(
    product_id: int,
    background: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Where this listing sits against comparable listings.

    Seller-scoped: a seller may only ask about their own products. That is not
    only an authorisation rule -- the answer is framed for the person who sets
    the price, and the same numbers shown to a competitor would be a different
    feature with different consequences.
    """
    _require_enabled(current_user)

    if current_user.role not in (UserRole.SELLER, UserRole.DUAL):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can view price position",
        )

    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this product",
        )

    # The market moves whenever any seller edits a price, so this is cached
    # briefly rather than not at all. No quota is consumed: phase 1 makes no
    # outbound request, so there is no cost to control.
    cached = cache.get(_cache_key(product_id))
    if cached is not None:
        return PricePositionResponse(**cached)

    payload = position_service.compute_position(db, product)
    cache.set(_cache_key(product_id), payload, ttl=settings.CACHE_TTL_INTEL_POSITION)

    # Serve what we have, then re-sample in the background if it has aged out.
    # Sampling takes three paced requests to a third-party site; making a
    # seller wait for that would be the wrong trade, and there is still no
    # scheduler to do it out of band (section 9). BackgroundTasks follows the
    # precedent already set by search logging in the product service.
    _schedule_benchmark_refresh(background, db, product)
    return PricePositionResponse(**payload)


def _schedule_benchmark_refresh(background: BackgroundTasks, db: Session, product) -> None:
    if product.category_id is None:
        return
    category = db.query(Category).filter(Category.id == product.category_id).first()
    if category is None:
        return
    existing = benchmark_service.for_category(db, category.name)
    if existing is not None and not benchmark_service.is_stale(existing):
        return
    if not any(e.get("mercai_category") == category.name
               for e in benchmark_service.config()):
        return
    background.add_task(_refresh_benchmark_task, category.name)


def _refresh_benchmark_task(category_name: str) -> None:
    """Own session: the request's session is closed by the time this runs."""
    from shared.database import SessionLocal

    session = SessionLocal()
    try:
        benchmark_service.refresh_for_category(session, category_name)
    except Exception:
        logger.warning("Background benchmark refresh failed", exc_info=True)
    finally:
        session.close()
