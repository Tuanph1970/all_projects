"""Unit tests for app.models.events — DomainEvent + concrete constructors."""
from __future__ import annotations

import uuid

from app.models.events import DomainEvent, recommendation_created, signal_failed


def test_domain_event_has_uuid_and_timestamp_defaults():
    """A bare DomainEvent gets an auto-generated event_id and occurred_at."""
    ev = DomainEvent(event_type="x.y", payload={"k": "v"}, aggregate_id="1:VCB:2026-05-20")
    # uuid4 format is parseable as UUID
    uuid.UUID(ev.event_id)
    # ISO 8601 with trailing Z
    assert ev.occurred_at.endswith("Z")
    assert ev.event_version == 1
    assert ev.trace_id == ""


def test_domain_event_frozen():
    """DomainEvent is a frozen dataclass — mutation must raise."""
    ev = DomainEvent(event_type="x", payload={}, aggregate_id="1:V:b")
    import dataclasses
    try:
        ev.event_type = "y"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("expected FrozenInstanceError")


def test_domain_event_as_dict_round_trip():
    payload = {"action": "BUY", "price": 100.0}
    ev = DomainEvent(
        event_type="decision.action.fired",
        payload=payload,
        aggregate_id="1:VCB:2026-05-20",
        trace_id="t-1",
    )
    d = ev.as_dict()
    assert d["event_id"] == ev.event_id
    assert d["event_type"] == "decision.action.fired"
    assert d["event_version"] == 1
    assert d["aggregate_id"] == "1:VCB:2026-05-20"
    assert d["trace_id"] == "t-1"
    assert d["payload"] == payload
    assert "occurred_at" in d


def test_two_events_get_distinct_ids():
    """The event_id default_factory yields fresh values per instance."""
    a = DomainEvent(event_type="x", payload={}, aggregate_id="a")
    b = DomainEvent(event_type="x", payload={}, aggregate_id="a")
    assert a.event_id != b.event_id


def test_recommendation_created_carries_canonical_payload():
    ev = recommendation_created(
        run_id=42, user_id=7, ticker="VCB", bar_date="2026-05-20",
        action="BUY", trigger="ON_DEMAND",
        payload={"stop_price": 80.0, "confidence": 0.82},
    )
    assert ev.event_type == "decision.recommendation.created"
    assert ev.aggregate_id == "7:VCB:2026-05-20"
    # User-supplied payload keys are merged in alongside the structural keys.
    assert ev.payload["run_id"] == 42
    assert ev.payload["user_id"] == 7
    assert ev.payload["ticker"] == "VCB"
    assert ev.payload["bar_date"] == "2026-05-20"
    assert ev.payload["action"] == "BUY"
    assert ev.payload["trigger"] == "ON_DEMAND"
    assert ev.payload["stop_price"] == 80.0
    assert ev.payload["confidence"] == 0.82


def test_recommendation_created_user_payload_can_override_structural_keys():
    """The constructor uses `**payload` last — explicit user payload
    silently overrides the structural keys.  Pin this behavior so a
    future refactor doesn't accidentally invert it."""
    ev = recommendation_created(
        run_id=1, user_id=1, ticker="A", bar_date="2026-01-01",
        action="BUY", trigger="ON_DEMAND",
        payload={"action": "REVERSE"},   # collides with the structural key
    )
    assert ev.payload["action"] == "REVERSE"


def test_signal_failed_carries_failure_kind():
    ev = signal_failed(
        user_id=9, ticker="HPG", bar_date="2026-05-19",
        signal_kind="ma_cross_up", failure_kind="bull_trap",
    )
    assert ev.event_type == "decision.signal.failed"
    assert ev.aggregate_id == "9:HPG:2026-05-19"
    assert ev.payload == {
        "signal_kind": "ma_cross_up",
        "failure_kind": "bull_trap",
        "ticker": "HPG",
        "bar_date": "2026-05-19",
    }
