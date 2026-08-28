"""
Undercut alerts, evaluated when a seller opens their price screen.

WHY EVERY CONDITION IS STRICT

An alert tells a seller a competitor has moved under them, and a seller may act
on it by changing a real price. The cost of a false one is therefore not a
wasted notification -- it is a price cut made on a misreading. Each condition
below removes one specific way that happens:

  confidence >= 90     keeps out tier-5 guesses and unconfigured state walks,
                       which are displayed but never trusted (section 4)
  age <= 48h           a price from last week is not news about today
  >= 5% below          smaller gaps are noise, or rounding, or a different
                       bundle size
  two consecutive      ONE low reading is a flash sale, a voucher price, or a
                       misparse that the magnitude check let through. Two in
                       the same direction is a move.

The last one is the one that matters most and is the easiest to drop by
accident, because it is the only condition that cannot be evaluated from a
single row.

There is still no scheduler (section 9), so these are computed at read time --
which means a seller learns about an undercut when they next look, not when it
happens. The UI has to say so rather than implying a watchdog.
"""
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from shared.config import settings
from shared.models.intel import ComparableObservation, TrackedComparable

from app.services import fetcher

logger = logging.getLogger(__name__)

ALERT_UNDERCUT = "undercut"

MIN_CONFIDENCE = 90
MAX_AGE_HOURS = 48
MIN_GAP_RATIO = Decimal("0.05")      # 5% below the seller's price
CONSECUTIVE_REQUIRED = 2


def _aware(moment: Optional[datetime]) -> Optional[datetime]:
    """MySQL hands back naive datetimes; treat them as UTC rather than guessing."""
    if moment is None:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _recent_readings(db: Session, comparable_id: int, limit: int = 5):
    """
    The most recent SUCCESSFUL readings, newest first.

    Failures are skipped rather than breaking the run: a competitor's site being
    down for a day should not reset the evidence that they cut their price.
    """
    return (
        db.query(ComparableObservation)
        .filter(
            ComparableObservation.comparable_id == comparable_id,
            ComparableObservation.status == fetcher.OK,
            ComparableObservation.price.isnot(None),
        )
        .order_by(ComparableObservation.observed_at.desc(),
                  ComparableObservation.id.desc())
        .limit(limit)
        .all()
    )


def evaluate(db: Session, product_id: int, own_price) -> List[Dict]:
    """
    Alerts worth showing for one product. Empty is the normal case.

    Returns dicts rather than model rows: nothing is persisted here. An alert is
    a statement about the data as it stands right now, and storing it would
    create a second source of truth that can disagree with the observations it
    came from.
    """
    if own_price is None:
        return []
    own = Decimal(str(own_price))
    if own <= 0:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    alerts: List[Dict] = []

    comparables = (
        db.query(TrackedComparable)
        .filter(
            TrackedComparable.product_id == product_id,
            TrackedComparable.is_active.is_(True),
        )
        .all()
    )

    for comparable in comparables:
        readings = _recent_readings(db, comparable.id)
        if len(readings) < CONSECUTIVE_REQUIRED:
            continue

        latest = readings[0]
        observed_at = _aware(latest.observed_at)
        if observed_at is None or observed_at < cutoff:
            continue
        if (latest.confidence or 0) < MIN_CONFIDENCE:
            continue

        # Every one of the last N readings must be below by the threshold, and
        # each must itself be trustworthy -- a confident low price preceded by
        # a tier-5 guess is one reading, not two.
        window = readings[:CONSECUTIVE_REQUIRED]
        if any((r.confidence or 0) < MIN_CONFIDENCE for r in window):
            continue

        gaps = [(own - Decimal(r.price)) / own for r in window]
        if not all(gap >= MIN_GAP_RATIO for gap in gaps):
            continue

        alerts.append({
            "type": ALERT_UNDERCUT,
            "comparable_id": comparable.id,
            "source_host": comparable.source_host,
            "label": comparable.label,
            "their_price": float(latest.price),
            "your_price": float(own),
            "gap_percent": round(float(gaps[0] * 100), 1),
            "observed_at": observed_at.isoformat(),
            "readings_agreeing": CONSECUTIVE_REQUIRED,
            # Said plainly, because the alternative reading -- that something is
            # watching continuously -- is one a seller would reasonably assume.
            "evaluated": "when you opened this screen",
        })

    alerts.sort(key=lambda a: -a["gap_percent"])
    return alerts
