"""
Listing optimizer endpoints.

This router deliberately has NO write path into `products`. Suggestions are
proposals; the client applies accepted fields through the existing
PUT /api/v1/products/{id}, so that service's validation, ownership checks,
cache invalidation and price ledger all keep working untouched.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session, joinedload

from shared.database import get_db
from shared.cache import cache
from shared.config import settings
from shared.models.ai import (
    AiSuggestion, FEATURE_LISTING_OPTIMIZER, STATUS_PROPOSED,
    STATUS_ACCEPTED, STATUS_PARTIALLY_ACCEPTED, STATUS_REJECTED,
)
from shared.models.product import Product
from shared.models.user import User, UserRole
from shared.security import get_current_user

from app.prompts.listing import PROMPT_VERSION
from app.schemas.listing import (
    ListingSuggestRequest, ListingSuggestResponse, ResolveRequest, ResolveResponse,
)
from app.services import listing_optimizer
from app.services.guardrails import (
    check_quota, consume_quota, feature_enabled, input_hash,
)
from app.services.ollama_client import (
    OllamaBusy, OllamaError, OllamaUnavailable, ollama_client,
)

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_RESOLUTIONS = {STATUS_ACCEPTED, STATUS_PARTIALLY_ACCEPTED, STATUS_REJECTED}


def _require_seller(current_user: User) -> None:
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(status_code=403, detail="Only sellers can use listing suggestions")


def _require_enabled(current_user: User) -> None:
    # 404 rather than 403: a disabled feature should not advertise its existence.
    if not feature_enabled(FEATURE_LISTING_OPTIMIZER, current_user.id):
        raise HTTPException(status_code=404, detail="Not found")


def _cache_key(digest: str) -> str:
    return f"mercai:ai:listing:{digest}"


@router.post("/listing/suggest", response_model=ListingSuggestResponse)
def suggest_listing(
    payload: ListingSuggestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_enabled(current_user)
    _require_seller(current_user)

    if (payload.product_id is None) == (payload.draft is None):
        raise HTTPException(
            status_code=422,
            detail="Provide exactly one of 'product_id' or 'draft'",
        )

    if payload.product_id is not None:
        product = (
            db.query(Product)
            .options(joinedload(Product.images))
            .filter(Product.id == payload.product_id)
            .first()
        )
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        if product.seller_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized for this product")
    else:
        # Unsaved listing from the create form. No ownership check is needed --
        # the content came from this seller in this request, and nothing is read
        # from or written to the catalogue.
        product = listing_optimizer.DraftProduct(payload.draft, current_user.id)

    digest = input_hash(
        {
            "name": product.name, "description": product.description,
            "tags": product.tags, "material": product.material,
            "color": product.color, "technique": product.technique,
            "dimensions": product.dimensions, "fields": payload.fields,
        },
        PROMPT_VERSION,
        settings.OLLAMA_MODEL,
    )

    # Cache hit: no model call, so no quota is consumed.
    cached_result = cache.get(_cache_key(digest))
    if cached_result is not None:
        record = _store(db, current_user.id, product.id, digest, cached_result, cached=True)
        return ListingSuggestResponse(
            suggestion_id=record.id, product_id=product.id,
            model=settings.OLLAMA_MODEL, prompt_version=PROMPT_VERSION,
            cached=True, latency_ms=cached_result.get("latency_ms"),
            suggestions=cached_result.get("suggestions", {}),
            image_report=cached_result.get("image_report", {}),
        )

    allowed, retry_after = check_quota(FEATURE_LISTING_OPTIMIZER, current_user.id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Suggestion limit reached. Try again later.",
            headers={"Retry-After": str(retry_after or 3600)},
        )

    try:
        result = listing_optimizer.generate_suggestion(db, product, payload.fields)
    except OllamaBusy:
        raise HTTPException(
            status_code=429,
            detail="The assistant is busy right now. Please try again in a moment.",
            headers={"Retry-After": "15"},
        )
    except (OllamaUnavailable, OllamaError) as exc:
        logger.warning("Listing suggestion failed for product %s: %s", product.id or "draft", exc)
        _store_failure(db, current_user.id, product.id, digest, str(exc))
        raise HTTPException(
            status_code=503,
            detail="The assistant is unavailable right now. Your listing is unaffected.",
        )

    consume_quota(FEATURE_LISTING_OPTIMIZER, current_user.id)
    cache.set(_cache_key(digest), result, ttl=settings.CACHE_TTL_AI_SUGGESTION)

    record = _store(db, current_user.id, product.id, digest, result, cached=False)
    return ListingSuggestResponse(
        suggestion_id=record.id, product_id=product.id,
        model=settings.OLLAMA_MODEL, prompt_version=PROMPT_VERSION,
        cached=False, latency_ms=result.get("latency_ms"),
        suggestions=result.get("suggestions", {}),
        image_report=result.get("image_report", {}),
    )


def _store(db: Session, seller_id: int, product_id: int, digest: str,
           result: dict, cached: bool) -> AiSuggestion:
    """
    Persist the proposal. TELEMETRY class: a failed write must never stop the
    seller seeing their suggestion, so this degrades to an unsaved record
    rather than raising.
    """
    record = AiSuggestion(
        seller_id=seller_id,
        feature=FEATURE_LISTING_OPTIMIZER,
        entity_type="product" if product_id else "draft",
        entity_id=product_id,
        input_hash=digest,
        suggestion={
            "suggestions": result.get("suggestions", {}),
            "image_report": result.get("image_report", {}),
            "cached": cached,
        },
        status=STATUS_PROPOSED,
        model=settings.OLLAMA_MODEL,
        prompt_version=PROMPT_VERSION,
        latency_ms=result.get("latency_ms"),
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception:
        logger.warning("Could not persist ai_suggestion", exc_info=True)
        db.rollback()
        record.id = 0
    return record


def _store_failure(db: Session, seller_id: int, product_id: int,
                   digest: str, error: str) -> None:
    try:
        db.add(AiSuggestion(
            seller_id=seller_id, feature=FEATURE_LISTING_OPTIMIZER,
            entity_type="product", entity_id=product_id, input_hash=digest,
            suggestion={}, status=STATUS_REJECTED,
            model=settings.OLLAMA_MODEL, prompt_version=PROMPT_VERSION,
            error=error[:255],
        ))
        db.commit()
    except Exception:
        logger.warning("Could not persist ai_suggestion failure", exc_info=True)
        db.rollback()


@router.post("/listing/suggestions/{suggestion_id}/resolve", response_model=ResolveResponse)
def resolve_suggestion(
    suggestion_id: int,
    payload: ResolveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Record what the seller did. LEDGER class -- acceptance is the metric the
    rollout is judged on, so unlike the proposal write this one is allowed to
    fail the request.
    """
    _require_enabled(current_user)

    if payload.status not in VALID_RESOLUTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {sorted(VALID_RESOLUTIONS)}",
        )

    record = (
        db.query(AiSuggestion)
        .filter(
            AiSuggestion.id == suggestion_id,
            AiSuggestion.feature == FEATURE_LISTING_OPTIMIZER,
        )
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if record.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this suggestion")

    record.status = payload.status
    record.accepted_fields = payload.accepted_fields or None
    record.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)

    return ResolveResponse(
        suggestion_id=record.id,
        status=record.status,
        resolved_at=record.resolved_at.isoformat() if record.resolved_at else None,
    )
