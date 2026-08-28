"""
Observing a tracked comparable: fetch, extract, record.

The whole point of this module is that EVERY outcome becomes a row. A failed
fetch is a fact about the market -- "this competitor has been unreadable for
two weeks" is information, and it is also the evidence-based worklist of which
adapter to write next.
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from shared.config import settings
from shared.models.intel import ComparableObservation, TrackedComparable

from app.services import adapters, extract, fetcher
from app.services.extract import jsonld
from app.services.money import is_plausible

logger = logging.getLogger(__name__)

# Five failures in a row deactivates the comparable, so a dead URL stops
# consuming its host's politeness budget forever.
MAX_CONSECUTIVE_FAILURES = 5

SUCCESS_STATUSES = {fetcher.OK}


def url_hash(url: str) -> str:
    return hashlib.sha256(fetcher.normalise_url(url).encode("utf-8")).hexdigest()


def host_of(url: str) -> str:
    return adapters.normalise_host(urlparse(url).hostname or "")


def observe(db: Session, comparable: TrackedComparable, *, respect_budget: bool = True):
    """
    Look once, and record what happened either way.

    Returns the observation. Never raises for an ordinary failure -- a
    competitor's site being down is not an error in our system, and treating it
    as one would surface a stack trace where a sentence belongs.
    """
    observation = ComparableObservation(comparable_id=comparable.id, status=fetcher.HTTP_ERROR)

    try:
        result = fetcher.fetch(comparable.url, respect_budget=respect_budget)
    except fetcher.FetchRefused as refused:
        observation.status = refused.status
        observation.evidence = refused.detail[:480] or None
        return _record(db, comparable, observation)

    observation.http_status = result.http_status
    if result.status != fetcher.OK:
        observation.status = result.status
        observation.evidence = (result.detail or "")[:480] or None
        return _record(db, comparable, observation)

    observation.content_hash = hashlib.sha256(result.body.encode("utf-8")).hexdigest()

    adapter = adapters.for_host(host_of(comparable.url))
    found = extract.run_ladder(result.body, adapter)

    if found is None:
        observation.status = (
            fetcher.JS_REQUIRED
            if extract.looks_javascript_rendered(result.body, False)
            else fetcher.NO_PRICE_FOUND
        )
        return _record(db, comparable, observation)

    history = [
        row[0] for row in db.query(ComparableObservation.price)
        .filter(
            ComparableObservation.comparable_id == comparable.id,
            ComparableObservation.price.isnot(None),
        )
        .order_by(ComparableObservation.observed_at.desc())
        .limit(5).all()
    ]
    # The magnitude check is what catches a site redesign silently repointing a
    # selector at the wrong element -- the failure mode most likely to survive
    # every other guard, because the new number is well-formed and in range.
    if not is_plausible(found.price, history):
        observation.status = fetcher.IMPLAUSIBLE
        observation.price = found.price
        observation.extractor_tier = found.tier
        observation.confidence = found.confidence
        observation.evidence = found.evidence[:480]
        return _record(db, comparable, observation)

    low, high = jsonld.price_range(result.body)
    observation.status = fetcher.OK
    observation.price = found.price
    observation.currency = (found.currency or "VND")[:3]
    observation.extractor_tier = found.tier
    observation.confidence = found.confidence
    observation.evidence = (
        f"{found.evidence} [{'+'.join(found.tiers_matched)}]"
        + (f" {found.flag}" if found.flag else "")
    )[:480]
    observation.title_seen = (found.title or None)
    observation.availability = found.availability
    if low is not None and high is not None and high != low:
        observation.price_min, observation.price_max = low, high
        observation.is_range = True
    return _record(db, comparable, observation)


def _record(db: Session, comparable: TrackedComparable, observation: ComparableObservation):
    """
    TELEMETRY class: a failed write must not fail the seller's request.

    Unlike price_history this describes the outside world and is already
    approximate, so it degrades to an unsaved object rather than raising.
    """
    comparable.last_fetched_at = datetime.now(timezone.utc)
    comparable.last_status = observation.status
    if observation.status in SUCCESS_STATUSES:
        comparable.consecutive_failures = 0
    else:
        comparable.consecutive_failures = (comparable.consecutive_failures or 0) + 1
        if comparable.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            comparable.is_active = False

    try:
        db.add(observation)
        db.commit()
        db.refresh(observation)
    except Exception:
        logger.warning("Could not persist observation", exc_info=True)
        db.rollback()
    return observation


def latest_observation(db: Session, comparable_id: int) -> Optional[ComparableObservation]:
    return (
        db.query(ComparableObservation)
        .filter(ComparableObservation.comparable_id == comparable_id)
        .order_by(ComparableObservation.observed_at.desc(),
                  ComparableObservation.id.desc())
        .first()
    )


def trusted_prices(db: Session, product_id: int):
    """
    External prices good enough to join the market statistics.

    Deliberately strict: high confidence AND recent AND a successful read. A
    tier-5 guess or a three-week-old reading can be shown to the seller with a
    caveat, but it must not move a median that the seller might act on.
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=settings.INTEL_OBSERVATION_STALE_HOURS
    )
    rows = (
        db.query(ComparableObservation, TrackedComparable)
        .join(TrackedComparable, TrackedComparable.id == ComparableObservation.comparable_id)
        .filter(
            TrackedComparable.product_id == product_id,
            TrackedComparable.is_active.is_(True),
            ComparableObservation.status == fetcher.OK,
            ComparableObservation.price.isnot(None),
            ComparableObservation.confidence >= settings.INTEL_MIN_TRUSTED_CONFIDENCE,
            ComparableObservation.observed_at >= cutoff,
        )
        .order_by(ComparableObservation.observed_at.desc())
        .all()
    )

    # One price per comparable -- the most recent. Without this a URL fetched
    # ten times would carry ten times the weight of one fetched once.
    seen, out = set(), []
    for observation, comparable in rows:
        if comparable.id in seen:
            continue
        seen.add(comparable.id)
        out.append(observation)
    return out


def observation_series(db: Session, product_id: int, limit_per_comparable: int = 30):
    """
    Each tracked comparable's readings over time, for the trend panel.

    Returned as discrete POINTS, deliberately. The seller's own line comes from
    a ledger and is continuous -- every change is recorded. These come from
    irregular, seller-triggered fetches, so there is no record of what happened
    between two of them. Drawing a smooth curve through four scattered readings
    would imply a continuity we do not have, and that is the kind of chart a
    real pricing decision gets made on. `stale` is carried per point so the
    client can grey out anything old rather than presenting it as current.
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=settings.INTEL_OBSERVATION_STALE_HOURS
    )

    comparables = (
        db.query(TrackedComparable)
        .filter(TrackedComparable.product_id == product_id)
        .order_by(TrackedComparable.created_at.asc())
        .all()
    )

    series = []
    for comparable in comparables:
        rows = (
            db.query(ComparableObservation)
            .filter(
                ComparableObservation.comparable_id == comparable.id,
                ComparableObservation.price.isnot(None),
            )
            .order_by(ComparableObservation.observed_at.asc())
            .limit(limit_per_comparable)
            .all()
        )
        if not rows:
            continue

        points = []
        for row in rows:
            observed = row.observed_at
            if observed is not None and observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            points.append({
                "at": observed.isoformat() if observed else None,
                "price": float(row.price),
                "confidence": row.confidence,
                # Below the trusted bar this reading is shown with a caveat and
                # never counted, so the client must be able to tell them apart.
                "trusted": (row.confidence or 0) >= settings.INTEL_MIN_TRUSTED_CONFIDENCE,
                "stale": bool(observed and observed < cutoff),
            })

        series.append({
            "comparable_id": comparable.id,
            "source_host": comparable.source_host,
            "label": comparable.label,
            "is_active": comparable.is_active,
            "points": points,
        })
    return series
