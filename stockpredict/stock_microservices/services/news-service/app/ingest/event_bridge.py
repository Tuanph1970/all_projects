"""ingest/ EventReactionBridge — forward numeric macro releases to event-reaction (FR-NEWS-BRIDGE).

A macro item that is a numeric economic release (parseable `actual` + a pre-event
`consensus`/`forecast` in its raw payload) and whose category is whitelisted is POSTed to
event-reaction-service's /events with event_id == news_id, so it becomes a measurable
surprise. event_id == news_id makes re-posts idempotent (the event store upserts by
event_id — EC-N2). Free-text items and non-whitelisted categories are never bridged.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# macro category -> event-reaction `kind` (v1 whitelist, SRS Appendix A).
KIND_MAP = {"monetary": "rate_decision", "tariff": "tariff", "tax": "tax"}


def _num(v) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class EventReactionBridge:
    def __init__(self, base_url: str, *, api_prefix: str = "stock_helper",
                 client: Optional[httpx.Client] = None, timeout: float = 10.0):
        self._base = base_url.rstrip("/")
        self._prefix = api_prefix
        self._client = client
        self._timeout = timeout

    def maybe_bridge(self, tagged) -> bool:
        """Bridge if this is a whitelisted numeric release; return True iff posted."""
        kind = KIND_MAP.get(tagged.category)
        if kind is None:
            return False
        try:
            rec = json.loads(tagged.item.raw_json or "{}")
        except (ValueError, TypeError):
            return False
        if not isinstance(rec, dict):
            return False
        actual = _num(rec.get("actual"))
        consensus = _num(rec.get("consensus"))
        if consensus is None:
            consensus = _num(rec.get("forecast"))
        if actual is None or consensus is None:
            return False  # not a numeric release -> store only, don't bridge

        payload = {"events": [{
            "event_id": tagged.item.news_id(),
            "ts_utc": tagged.item.ts_utc.isoformat(),
            "kind": kind,
            "actual": actual,
            "consensus": consensus,
            "asset_scope": None,
        }]}
        url = f"{self._base}/{self._prefix}/api/v2/event-reaction/events"
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.post(url, json=payload)
        except Exception as exc:  # noqa: BLE001 — bridge is best-effort; retry next tick
            logger.warning("event-reaction bridge failed for %s: %s",
                           tagged.item.news_id(), exc)
            return False
        finally:
            if self._client is None:
                client.close()
        if resp.status_code != 200:
            logger.warning("event-reaction /events returned %s for %s",
                           resp.status_code, tagged.item.news_id())
            return False
        logger.info("bridged %s -> event-reaction (%s)", tagged.item.news_id(), kind)
        return True
