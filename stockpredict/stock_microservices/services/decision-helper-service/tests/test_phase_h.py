"""Tests for Phase H — Automation (F-070..F-073)."""
from __future__ import annotations

import pytest

from app.models.schemas import (
    ScheduledRunSummary,
    ScheduledRunsResponse,
    WatchlistAddRequest,
    WatchlistEntryResponse,
)
from app.services.scheduler import _ALERT_ACTIONS


# ---------------------------------------------------------------------------
# F-070 — WatchlistAddRequest validation
# ---------------------------------------------------------------------------

class TestWatchlistSchemas:
    def test_add_request_normalised(self):
        req = WatchlistAddRequest(ticker="vic", note="buy the dip")
        assert req.ticker == "vic"   # schema doesn't uppercase — route does

    def test_add_request_note_optional(self):
        req = WatchlistAddRequest(ticker="VIC")
        assert req.note is None

    def test_add_request_ticker_max_length(self):
        with pytest.raises(Exception):
            WatchlistAddRequest(ticker="A" * 17)

    def test_entry_response_fields(self):
        from datetime import datetime
        e = WatchlistEntryResponse(
            id=1, user_id=42, ticker="VIC", active=True, note=None,
            created_at=datetime(2025, 1, 1),
        )
        assert e.ticker == "VIC"
        assert e.active is True


# ---------------------------------------------------------------------------
# F-072 — Alert actions set
# ---------------------------------------------------------------------------

class TestAlertActions:
    def test_buy_is_alert(self):
        assert "BUY" in _ALERT_ACTIONS

    def test_sell_short_is_alert(self):
        assert "SELL_SHORT" in _ALERT_ACTIONS

    def test_hold_not_alert(self):
        assert "HOLD" not in _ALERT_ACTIONS

    def test_wait_not_alert(self):
        assert "WAIT" not in _ALERT_ACTIONS

    def test_sell_not_alert(self):
        assert "SELL" not in _ALERT_ACTIONS


# ---------------------------------------------------------------------------
# F-073 — ScheduledRunSummary / ScheduledRunsResponse
# ---------------------------------------------------------------------------

class TestScheduledRunSchemas:
    def _make_run(self, action="BUY"):
        from datetime import date, datetime
        return ScheduledRunSummary(
            id=1,
            ticker="VIC",
            bar_date=date(2025, 1, 15),
            action=action,
            regime="TREND_UP",
            confidence=0.75,
            latency_ms=120,
            created_at=datetime(2025, 1, 15, 8, 30),
            is_alert=action in _ALERT_ACTIONS,
        )

    def test_buy_is_alert(self):
        run = self._make_run("BUY")
        assert run.is_alert is True

    def test_sell_short_is_alert(self):
        run = self._make_run("SELL_SHORT")
        assert run.is_alert is True

    def test_hold_not_alert(self):
        run = self._make_run("HOLD")
        assert run.is_alert is False

    def test_wait_not_alert(self):
        run = self._make_run("WAIT")
        assert run.is_alert is False

    def test_response_wraps_runs(self):
        runs = [self._make_run("BUY"), self._make_run("WAIT")]
        resp = ScheduledRunsResponse(runs=runs, total=2)
        assert resp.total == 2
        assert len(resp.runs) == 2

    def test_optional_fields_nullable(self):
        from datetime import date, datetime
        run = ScheduledRunSummary(
            id=2, ticker="HPG", bar_date=date(2025, 1, 16),
            action="HOLD", regime=None, confidence=None, latency_ms=None,
            created_at=datetime(2025, 1, 16), is_alert=False,
        )
        assert run.regime is None
        assert run.confidence is None
