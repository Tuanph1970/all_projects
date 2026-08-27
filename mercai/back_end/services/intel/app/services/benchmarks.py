"""
Category-wide price benchmarks from an external marketplace.

WHY THIS IS NOT A SET OF COMPARABLES, and why that matters:

A comparable is one competitor listing matched to one of the seller's products.
Getting that match wrong shows a seller the price of a different item, which is
the failure this whole design is organised around avoiding. A benchmark sidesteps
the problem entirely -- it aggregates a whole category with no matching at all,
so there is no match to get wrong, and one bad row cannot move a median over a
hundred items.

WHY IT IS NEVER BLENDED INTO THE SELLER'S POSITION:

It is a different market. Measured 2026-08-27, Tiki's tableware category has a
median around 200,000-275,000d, but it is dominated by multi-piece SETS while a
Mercai listing is usually a single hand-made bowl. Folding those numbers into
the seller's quartiles would silently move a median they might act on, and the
seller would have no way to see why. So it is returned as its own labelled
block, with its sample size and its caveat attached, and the interpretation
stays with the person who knows their own product.

See docs/ai-features/05-price-intelligence.md sections 8 and 13.
"""
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from shared.models.intel import CategoryBenchmark

from app.services import fetcher

logger = logging.getLogger(__name__)

SOURCE_TIKI = "tiki"
PAGES = 3
PAGE_SIZE = 40
# Between pages of the same refresh. The per-host token bucket is built for
# seller-triggered bursts; this is a once-a-day background job, so it sets its
# own pace rather than being refused by a bucket sized for a different purpose.
PAGE_DELAY_SECONDS = 2.0
# Below this the quartiles are not worth showing, for the same reason
# MIN_COMPARABLE_N exists on the internal side.
MIN_SAMPLE = 20

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "adapters", "_benchmarks.yml"
)


def config() -> List[Dict]:
    try:
        import yaml
        with open(CONFIG_PATH, encoding="utf-8") as handle:
            return list((yaml.safe_load(handle) or {}).get("benchmarks") or [])
    except Exception:
        logger.warning("Could not read benchmark config", exc_info=True)
        return []


def for_category(db: Session, category_name: Optional[str]) -> Optional[CategoryBenchmark]:
    if not category_name:
        return None
    return (
        db.query(CategoryBenchmark)
        .filter(
            CategoryBenchmark.mercai_category_name == category_name,
            CategoryBenchmark.status == "ok",
        )
        .order_by(CategoryBenchmark.computed_at.desc())
        .first()
    )


def is_stale(benchmark: CategoryBenchmark, hours: int = 24) -> bool:
    if benchmark is None or benchmark.computed_at is None:
        return True
    computed = benchmark.computed_at
    if computed.tzinfo is None:
        computed = computed.replace(tzinfo=timezone.utc)
    return computed < datetime.now(timezone.utc) - timedelta(hours=hours)


def _quantile(values, q):
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    pos = (len(values) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    if lo == hi:
        return float(values[lo])
    return float(values[lo]) + (float(values[hi]) - float(values[lo])) * (pos - lo)


def _sample_tiki(category_id: str):
    """
    Prices across several pages of one Tiki category.

    Sampled over pages rather than a single call because a 20-item sample gave
    a median of 690,000d where 120 items give ~200,000d -- small-sample noise
    large enough to be actively misleading.
    """
    prices, total = [], None
    for page in range(1, PAGES + 1):
        if page > 1:
            time.sleep(PAGE_DELAY_SECONDS)
        url = (
            f"https://tiki.vn/api/v2/products?category={category_id}"
            f"&limit={PAGE_SIZE}&page={page}"
        )
        try:
            result = fetcher.fetch(url, respect_budget=False)
        except fetcher.FetchRefused as refused:
            logger.warning("Benchmark fetch refused: %s", refused.detail)
            return [], total, refused.status
        if result.status != fetcher.OK:
            return prices, total, result.status
        try:
            payload = json.loads(result.body)
        except Exception:
            return prices, total, fetcher.NO_PRICE_FOUND
        total = (payload.get("paging") or {}).get("total", total)
        for row in payload.get("data") or []:
            price = row.get("price")
            if price:
                prices.append(int(price))
    return prices, total, fetcher.OK


def refresh(db: Session, entry: Dict) -> Optional[CategoryBenchmark]:
    """Re-sample one configured benchmark and upsert it."""
    source = entry.get("source", SOURCE_TIKI)
    category_id = str(entry.get("external_category_id") or "")
    if source != SOURCE_TIKI or not category_id:
        return None

    prices, total, status = _sample_tiki(category_id)
    prices = sorted(prices)

    row = (
        db.query(CategoryBenchmark)
        .filter(
            CategoryBenchmark.source == source,
            CategoryBenchmark.external_category_id == category_id,
        )
        .first()
    )
    if row is None:
        row = CategoryBenchmark(source=source, external_category_id=category_id)
        db.add(row)

    row.external_category_label = entry.get("label")
    row.mercai_category_name = entry.get("mercai_category")
    row.sample_size = len(prices)
    row.pages_sampled = PAGES
    row.catalogue_total = total
    row.currency = "VND"
    row.computed_at = datetime.now(timezone.utc)

    if status != fetcher.OK or len(prices) < MIN_SAMPLE:
        # A thin or failed sample is recorded as such rather than published as
        # a number. Showing quartiles over eleven items would be the same
        # mistake MIN_COMPARABLE_N exists to prevent, one market over.
        row.status = status if status != fetcher.OK else "insufficient_sample"
        row.p25 = row.median = row.p75 = row.price_min = row.price_max = None
    else:
        row.status = "ok"
        row.p25 = Decimal(str(round(_quantile(prices, 0.25), 2)))
        row.median = Decimal(str(round(_quantile(prices, 0.50), 2)))
        row.p75 = Decimal(str(round(_quantile(prices, 0.75), 2)))
        row.price_min = Decimal(prices[0])
        row.price_max = Decimal(prices[-1])

    try:
        db.commit()
        db.refresh(row)
    except Exception:
        logger.warning("Could not persist benchmark", exc_info=True)
        db.rollback()
        return None
    return row


def refresh_all(db: Session) -> List[CategoryBenchmark]:
    done, seen = [], set()
    for entry in config():
        key = (entry.get("source"), str(entry.get("external_category_id")))
        # Two Mercai categories can point at one external category (Tiki has no
        # separate teaware leaf). Sample it once and reuse.
        if key in seen:
            continue
        seen.add(key)
        row = refresh(db, entry)
        if row is not None:
            done.append(row)
    return done


def refresh_for_category(db: Session, category_name: str) -> Optional[CategoryBenchmark]:
    for entry in config():
        if entry.get("mercai_category") == category_name:
            return refresh(db, entry)
    return None


def as_payload(benchmark: Optional[CategoryBenchmark]) -> Optional[Dict]:
    if benchmark is None or benchmark.status != "ok" or benchmark.median is None:
        return None
    entry_notes = None
    for entry in config():
        if str(entry.get("external_category_id")) == benchmark.external_category_id:
            entry_notes = entry.get("notes")
            break
    return {
        "source": benchmark.source,
        "label": benchmark.external_category_label,
        "sample_size": benchmark.sample_size,
        "catalogue_total": benchmark.catalogue_total,
        "p25": float(benchmark.p25) if benchmark.p25 is not None else None,
        "median": float(benchmark.median),
        "p75": float(benchmark.p75) if benchmark.p75 is not None else None,
        "min": float(benchmark.price_min) if benchmark.price_min is not None else None,
        "max": float(benchmark.price_max) if benchmark.price_max is not None else None,
        "computed_at": benchmark.computed_at.isoformat() if benchmark.computed_at else None,
        "stale": is_stale(benchmark),
        # Shipped WITH the numbers, not buried in a doc: whoever reads the
        # median needs to know what it is a median of.
        "caveat": entry_notes,
    }
