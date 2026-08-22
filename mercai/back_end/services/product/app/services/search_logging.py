"""
Best-effort search telemetry.

Reliability class: TELEMETRY (see docs/ai-features/01-instrumentation.md).
A failed write here must never fail a buyer's search, so every path swallows
its own exceptions and logs at warning level instead of propagating.

Why this opens its own session rather than reusing the request's:
FastAPI >= 0.106 exits `yield` dependencies *before* background tasks run, so
the session provided by `get_db()` is already closed by the time this executes.
Reusing it would raise on every single search.
"""
import logging
from typing import Any, Dict, Optional

from shared.database import SessionLocal
from shared.models.analytics import SearchLog

logger = logging.getLogger(__name__)

# Clients that fire a request per keystroke would otherwise fill the table with
# prefixes ("v", "va", "vas") and swamp every aggregate. Queries shorter than
# this are dropped rather than stored.
MIN_QUERY_LENGTH = 3

SOURCE_BASIC = "basic"
SOURCE_ADVANCED = "advanced"


def normalize_query(query_text: Optional[str]) -> Optional[str]:
    """Lowercase and collapse whitespace so aggregates group sensibly."""
    if not query_text:
        return None
    normalized = " ".join(query_text.lower().split())
    return normalized[:500] or None


def _clean_filters(filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Drop unset filter values so the JSON column stores only what was applied."""
    if not filters:
        return None
    applied = {k: v for k, v in filters.items() if v is not None and v != ""}
    return applied or None


def record_search(
    *,
    query_text: Optional[str],
    filters: Optional[Dict[str, Any]],
    result_count: int,
    source: str,
    user_id: Optional[int] = None,
    anon_id: Optional[str] = None,
) -> None:
    """
    Persist one search event. Never raises.

    `result_count` must be the TOTAL number of matches, not the length of the
    returned page -- otherwise a paginated search looks like a zero-result
    search once the buyer scrolls past the end, and the assortment-gap signal
    becomes noise.
    """
    db = None
    try:
        query_norm = normalize_query(query_text)
        applied_filters = _clean_filters(filters)

        # A too-short query is noise. A query-less, filter-less call is just a
        # product listing, not a search.
        if query_norm is not None and len(query_norm) < MIN_QUERY_LENGTH:
            return
        if query_norm is None and applied_filters is None:
            return

        db = SessionLocal()
        db.add(
            SearchLog(
                query_text=query_text.strip()[:500] if query_text else None,
                query_norm=query_norm,
                filters=applied_filters,
                result_count=result_count,
                source=source,
                user_id=user_id,
                anon_id=anon_id.strip()[:64] if anon_id else None,
            )
        )
        db.commit()
    except Exception:
        # Telemetry is never worth an error response.
        logger.warning("Search telemetry write failed", exc_info=True)
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass
