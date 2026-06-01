"""decision.stop.triggered / decision.target.hit — exit notifications.

When a tracked position closes because its stop or target was hit, the state
machine tags the transition with a structured ``exit_reason`` and the daily
scheduler broadcasts an exit alert over the in-process alert_broker (same SSE
channel used for BUY / SELL_SHORT entry alerts).
"""
from __future__ import annotations

from datetime import date

import pytest

from app.services.position.state_machine import next_state


# ---------------------------------------------------------------------------
# State machine — structured exit_reason
# ---------------------------------------------------------------------------

def test_long_stop_hit_tags_stop():
    t = next_state("LONG", None, 94.0, 95.0, 110.0)
    assert t.action == "SELL"
    assert t.exit_reason == "STOP_HIT"


def test_long_target_hit_tags_target():
    t = next_state("LONG", None, 112.0, 95.0, 110.0)
    assert t.action == "SELL"
    assert t.exit_reason == "TARGET_HIT"


def test_short_stop_hit_tags_stop():
    t = next_state("SHORT", None, 106.0, 105.0, 90.0)
    assert t.action == "COVER"
    assert t.exit_reason == "STOP_HIT"


def test_short_target_hit_tags_target():
    t = next_state("SHORT", None, 89.0, 105.0, 90.0)
    assert t.action == "COVER"
    assert t.exit_reason == "TARGET_HIT"


def test_hold_has_no_exit_reason():
    t = next_state("LONG", None, 100.0, 95.0, 110.0)
    assert t.action == "HOLD"
    assert t.exit_reason is None


def test_reversal_is_not_a_stop_or_target_exit():
    t = next_state("LONG", "SHORT", 100.0, 95.0, 110.0, signal_confirmed=True)
    assert t.action == "REVERSE"
    assert t.exit_reason is None


def test_entry_has_no_exit_reason():
    t = next_state("FLAT", "LONG", 100.0, None, None, signal_confirmed=True)
    assert t.action == "BUY"
    assert t.exit_reason is None


# ---------------------------------------------------------------------------
# Scheduler — publishes an exit alert on stop/target hit
# ---------------------------------------------------------------------------

class _Entry:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.active = True


class _Rec:
    def __init__(self, action="HOLD", exit_reason=None):
        self.action = action
        self.exit_reason = exit_reason
        self.regime = "TREND_UP"
        self.confidence = 0.6
        self.stop_price = 95.0
        self.target_price = 110.0
        self.entry_price = 100.0


def _session_factory(entries):
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock

    scalars = MagicMock()
    scalars.all.return_value = entries
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars
    session = MagicMock()
    session.execute = AsyncMock(return_value=exec_result)

    @asynccontextmanager
    async def factory():
        yield session

    return factory


async def _run_scheduler_with(monkeypatch, rec):
    from unittest.mock import AsyncMock
    import app.services.scheduler as sched

    monkeypatch.setattr(sched, "async_session_factory", _session_factory([_Entry("VCB")]))
    monkeypatch.setattr(sched, "get_market_client", lambda: object())
    monkeypatch.setattr(sched, "run_recommendation", AsyncMock(return_value=rec))

    published = []
    monkeypatch.setattr(
        sched.alert_broker, "publish",
        AsyncMock(side_effect=lambda uid, payload: published.append((uid, payload))),
    )
    await sched.run_for_user(user_id=7, bar_date=date(2023, 6, 1))
    return published


async def test_scheduler_publishes_target_hit_alert(monkeypatch):
    published = await _run_scheduler_with(monkeypatch, _Rec(action="SELL", exit_reason="TARGET_HIT"))
    assert len(published) == 1
    uid, payload = published[0]
    assert uid == 7
    assert payload["exit_reason"] == "TARGET_HIT"
    assert payload["ticker"] == "VCB"
    assert payload["action"] == "SELL"


async def test_scheduler_publishes_stop_hit_alert(monkeypatch):
    published = await _run_scheduler_with(monkeypatch, _Rec(action="COVER", exit_reason="STOP_HIT"))
    assert len(published) == 1
    assert published[0][1]["exit_reason"] == "STOP_HIT"


async def test_scheduler_silent_on_hold(monkeypatch):
    published = await _run_scheduler_with(monkeypatch, _Rec(action="HOLD", exit_reason=None))
    assert published == []


async def test_scheduler_still_alerts_on_entry(monkeypatch):
    published = await _run_scheduler_with(monkeypatch, _Rec(action="BUY", exit_reason=None))
    assert len(published) == 1
    assert published[0][1]["action"] == "BUY"
    assert "exit_reason" not in published[0][1]
