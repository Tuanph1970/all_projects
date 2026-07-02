"""N13 — event-reaction bridge (FR-NEWS-BRIDGE, EC-N2).

Forwards a macro numeric release (parseable actual + consensus, whitelisted category) to
event-reaction POST /events with event_id == news_id (idempotent upsert). Free-text items
and non-whitelisted categories are not bridged.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

from app.ingest.event_bridge import EventReactionBridge
from app.ingest.macro_feeds import TaggedItem
from app.models.news_item import NewsItem

_BASE = "http://event-reaction-service:8012"


def _tagged(category, raw, guid="m1") -> TaggedItem:
    item = NewsItem(
        source="econ_api", stream="macro", symbol=None,
        ts_utc=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
        title="Fed decision", body="b", url="https://x/1", lang=None,
        raw_json=json.dumps(raw), guid=guid,
    )
    return TaggedItem(item, category)


def _bridge(captured) -> EventReactionBridge:
    def handler(req: httpx.Request) -> httpx.Response:
        captured.append(json.loads(req.content))
        assert req.url.path.endswith("/event-reaction/events")
        return httpx.Response(200, json={"ingested": 1})
    return EventReactionBridge(_BASE, client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_bridges_numeric_monetary_release_with_news_id():
    cap = []
    ti = _tagged("monetary", {"actual": 5.5, "consensus": 5.25}, guid="fed-1")
    assert _bridge(cap).maybe_bridge(ti) is True
    assert len(cap) == 1
    ev = cap[0]["events"][0]
    assert ev["event_id"] == ti.item.news_id()   # idempotency key (EC-N2)
    assert ev["kind"] == "rate_decision"
    assert ev["actual"] == 5.5 and ev["consensus"] == 5.25


def test_tax_maps_to_tax_kind():
    cap = []
    ti = _tagged("tax", {"actual": 21, "consensus": 20})
    assert _bridge(cap).maybe_bridge(ti) is True
    assert cap[0]["events"][0]["kind"] == "tax"


def test_accepts_forecast_as_consensus_and_string_numbers():
    cap = []
    ti = _tagged("tariff", {"actual": "10", "forecast": "7.5"})
    assert _bridge(cap).maybe_bridge(ti) is True
    ev = cap[0]["events"][0]
    assert ev["kind"] == "tariff" and ev["actual"] == 10.0 and ev["consensus"] == 7.5


def test_non_whitelisted_category_not_bridged():
    cap = []
    ti = _tagged("war", {"actual": 1, "consensus": 0})
    assert _bridge(cap).maybe_bridge(ti) is False
    assert cap == []


def test_missing_numbers_not_bridged():
    cap = []
    ti = _tagged("monetary", {"headline": "no numbers here"})
    assert _bridge(cap).maybe_bridge(ti) is False
    assert cap == []


def test_non_200_response_returns_false():
    def handler(req):
        return httpx.Response(500)
    b = EventReactionBridge(_BASE, client=httpx.Client(transport=httpx.MockTransport(handler)))
    ti = _tagged("monetary", {"actual": 5.5, "consensus": 5.25})
    assert b.maybe_bridge(ti) is False


def test_network_error_returns_false():
    def handler(req):
        raise httpx.ConnectError("down")
    b = EventReactionBridge(_BASE, client=httpx.Client(transport=httpx.MockTransport(handler)))
    ti = _tagged("monetary", {"actual": 5.5, "consensus": 5.25})
    assert b.maybe_bridge(ti) is False
