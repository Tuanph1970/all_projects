"""
Seller-supplied comparable listings.

Adding a URL fetches it ONCE, synchronously, and returns the result. A URL that
cannot be read must fail now, with a reason the seller can act on -- not
silently produce a row that never yields a price and quietly rots.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from shared.config import settings
from shared.database import get_db
from shared.models.ai import FEATURE_PRICE_INTEL
from shared.models.intel import ComparableObservation, TrackedComparable
from shared.models.product import Product
from shared.models.user import User, UserRole
from shared.security import get_current_user

from app.schemas.comparable import (
    AddComparableRequest, ComparableListResponse, ComparableOut, ObservationOut,
)
from app.services import adapters, comparables as service, demand, fetcher
from app.services.guardrails import check_quota, consume_quota, feature_enabled

logger = logging.getLogger(__name__)
router = APIRouter()


def _guard(current_user: User) -> None:
    if not feature_enabled(FEATURE_PRICE_INTEL, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if current_user.role not in (UserRole.SELLER, UserRole.DUAL):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can manage comparables",
        )


def _own_product(db: Session, product_id: int, current_user: User) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this product",
        )
    return product


def _observation_out(observation) -> ObservationOut:
    if observation is None:
        return None
    stale = False
    if observation.observed_at:
        cutoff = datetime.now(timezone.utc) - timedelta(
            hours=settings.INTEL_OBSERVATION_STALE_HOURS
        )
        observed = observation.observed_at
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        stale = observed < cutoff

    trusted = (
        observation.status == fetcher.OK
        and observation.price is not None
        and (observation.confidence or 0) >= settings.INTEL_MIN_TRUSTED_CONFIDENCE
        and not stale
    )
    return ObservationOut(
        observed_at=observation.observed_at.isoformat() if observation.observed_at else None,
        status=observation.status,
        message=fetcher.MESSAGES.get(observation.status, "We couldn't read this page."),
        price=float(observation.price) if observation.price is not None else None,
        price_min=float(observation.price_min) if observation.price_min is not None else None,
        price_max=float(observation.price_max) if observation.price_max is not None else None,
        is_range=bool(observation.is_range),
        currency=observation.currency,
        availability=observation.availability,
        confidence=observation.confidence,
        extractor_tier=observation.extractor_tier,
        trusted=trusted,
        stale=stale,
    )


def _comparable_out(db: Session, comparable: TrackedComparable) -> ComparableOut:
    return ComparableOut(
        id=comparable.id,
        product_id=comparable.product_id,
        url=comparable.url,
        source_host=comparable.source_host,
        label=comparable.label,
        is_active=comparable.is_active,
        consecutive_failures=comparable.consecutive_failures or 0,
        last_fetched_at=(
            comparable.last_fetched_at.isoformat() if comparable.last_fetched_at else None
        ),
        latest=_observation_out(service.latest_observation(db, comparable.id)),
    )


@router.post("/comparables", response_model=ComparableOut, status_code=201)
def add_comparable(
    payload: AddComparableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _guard(current_user)
    _own_product(db, payload.product_id, current_user)

    # Validate before writing anything: an unsupported host or a private
    # address should never leave a row behind.
    try:
        host, _ = fetcher.check_url(payload.url)
    except fetcher.FetchRefused as refused:
        # A host we don't support is the one refusal that is also a request.
        # No comparable row is created -- one we can never fetch is worse than
        # none -- but the demand is counted, because "which adapter next?" is
        # otherwise answered by guessing. Only HOST_NOT_ALLOWED: a private
        # address is a mistake or an attack, never a source worth adding.
        if refused.status == fetcher.HOST_NOT_ALLOWED:
            demand.record_rejection(db, seller_id=current_user.id, url=payload.url)
        raise HTTPException(status_code=422, detail=refused.detail or
                            fetcher.MESSAGES.get(refused.status, "That URL can't be used"))

    digest = service.url_hash(payload.url)
    existing = (
        db.query(TrackedComparable)
        .filter(
            TrackedComparable.product_id == payload.product_id,
            TrackedComparable.url_hash == digest,
        )
        .first()
    )
    if existing is not None:
        # Re-adding a URL the seller previously removed should revive it rather
        # than 409 -- they are asking for the same outcome either way.
        if not existing.is_active:
            existing.is_active = True
            existing.consecutive_failures = 0
            db.commit()
        return _comparable_out(db, existing)

    allowed, retry_after = check_quota(FEATURE_PRICE_INTEL, current_user.id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="You've added a lot of comparables recently. Try again later.",
            headers={"Retry-After": str(retry_after or 3600)},
        )

    comparable = TrackedComparable(
        seller_id=current_user.id,
        product_id=payload.product_id,
        url=fetcher.normalise_url(payload.url),
        url_hash=digest,
        source_host=host,
        label=payload.label,
        is_active=True,
    )
    db.add(comparable)
    db.commit()
    db.refresh(comparable)

    consume_quota(FEATURE_PRICE_INTEL, current_user.id)
    # Fetch once now, so the seller learns immediately whether we can read it.
    # The politeness budget is bypassed for this single first read: refusing to
    # look at a URL the seller just typed would be baffling, and it is one
    # request, gated by their own quota.
    service.observe(db, comparable, respect_budget=False)
    return _comparable_out(db, comparable)


@router.get("/comparables", response_model=ComparableListResponse)
def list_comparables(
    product_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _guard(current_user)
    _own_product(db, product_id, current_user)

    rows = (
        db.query(TrackedComparable)
        .filter(TrackedComparable.product_id == product_id)
        .order_by(TrackedComparable.created_at.asc())
        .all()
    )
    return ComparableListResponse(
        product_id=product_id,
        comparables=[_comparable_out(db, row) for row in rows],
        supported_hosts=adapters.allowed_hosts(),
    )


@router.delete("/comparables/{comparable_id}", status_code=204)
def remove_comparable(
    comparable_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft delete. Observations are kept -- they are a record of the market."""
    _guard(current_user)
    comparable = db.query(TrackedComparable).filter(
        TrackedComparable.id == comparable_id
    ).first()
    if comparable is None:
        raise HTTPException(status_code=404, detail="Comparable not found")
    if comparable.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this comparable")

    comparable.is_active = False
    db.commit()
    return None


@router.post("/comparables/{comparable_id}/refresh", response_model=ComparableOut)
def refresh_comparable(
    comparable_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _guard(current_user)
    comparable = db.query(TrackedComparable).filter(
        TrackedComparable.id == comparable_id
    ).first()
    if comparable is None:
        raise HTTPException(status_code=404, detail="Comparable not found")
    if comparable.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this comparable")

    allowed, retry_after = check_quota(FEATURE_PRICE_INTEL, current_user.id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="You've refreshed a lot recently. Try again later.",
            headers={"Retry-After": str(retry_after or 3600)},
        )

    observation = service.observe(db, comparable)
    consume_quota(FEATURE_PRICE_INTEL, current_user.id)

    # The per-host budget refusing is a normal outcome, not a failure: it means
    # someone checked this site seconds ago. Say so rather than pretending the
    # site was unreachable.
    if observation is not None and observation.status == fetcher.RATE_LIMITED:
        raise HTTPException(
            status_code=429,
            detail=fetcher.MESSAGES[fetcher.RATE_LIMITED],
            headers={"Retry-After": str(settings.INTEL_HOST_INTERVAL_SECONDS)},
        )
    return _comparable_out(db, comparable)
