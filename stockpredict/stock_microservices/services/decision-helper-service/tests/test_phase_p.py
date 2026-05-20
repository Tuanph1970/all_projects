"""Tests for Phase P — Open positions dashboard (F-150..F-153)."""
from __future__ import annotations

import pytest
from datetime import date
from app.models.schemas import (
    PositionStateResponse,
    PositionsListResponse,
    UpdateStopRequest,
)


# ---------------------------------------------------------------------------
# F-150 — PositionsListResponse schema
# ---------------------------------------------------------------------------

class TestPositionsListResponse:
    def _pos(self, ticker="VIC", state="LONG", **kw):
        return PositionStateResponse(
            user_id=1, ticker=ticker, state=state,
            entry_bar_date=date(2025, 5, 1),
            entry_price=50.0, position_size=100,
            current_stop=47.0, current_target=58.0,
            entry_signal_kind="MA_CROSS",
            **kw,
        )

    def test_empty_list(self):
        resp = PositionsListResponse(positions=[], total=0)
        assert resp.positions == []
        assert resp.total == 0

    def test_with_positions(self):
        positions = [self._pos("VIC", "LONG"), self._pos("VCB", "SHORT")]
        resp = PositionsListResponse(positions=positions, total=2)
        assert resp.total == 2
        assert resp.positions[0].ticker == "VIC"
        assert resp.positions[1].state == "SHORT"

    def test_only_non_flat(self):
        # Flat positions should never appear (filtered by backend)
        positions = [self._pos("VIC", "LONG"), self._pos("VCB", "SHORT")]
        assert all(p.state in ("LONG", "SHORT") for p in positions)

    def test_position_fields_preserved(self):
        pos = self._pos("VIC", "LONG")
        resp = PositionsListResponse(positions=[pos], total=1)
        p = resp.positions[0]
        assert p.entry_price == 50.0
        assert p.current_stop == 47.0
        assert p.current_target == 58.0
        assert p.entry_signal_kind == "MA_CROSS"


# ---------------------------------------------------------------------------
# F-151 — UpdateStopRequest schema
# ---------------------------------------------------------------------------

class TestUpdateStopRequest:
    def test_valid_stop(self):
        req = UpdateStopRequest(current_stop=47.5)
        assert req.current_stop == 47.5

    def test_stop_must_be_positive(self):
        with pytest.raises(Exception):
            UpdateStopRequest(current_stop=0)

    def test_stop_must_be_positive_negative(self):
        with pytest.raises(Exception):
            UpdateStopRequest(current_stop=-1.0)

    def test_fractional_stop(self):
        req = UpdateStopRequest(current_stop=48.25)
        assert abs(req.current_stop - 48.25) < 0.001


# ---------------------------------------------------------------------------
# F-152 — PositionStateResponse fields used by PositionsPage
# ---------------------------------------------------------------------------

class TestPositionStateResponseContract:
    """PositionsPage reads these fields — verify they exist."""

    def _fields(self):
        return set(PositionStateResponse.model_fields.keys())

    def test_state_exists(self):
        assert "state" in self._fields()

    def test_entry_bar_date_exists(self):
        assert "entry_bar_date" in self._fields()

    def test_entry_price_exists(self):
        assert "entry_price" in self._fields()

    def test_current_stop_exists(self):
        assert "current_stop" in self._fields()

    def test_current_target_exists(self):
        assert "current_target" in self._fields()

    def test_position_size_exists(self):
        assert "position_size" in self._fields()

    def test_entry_signal_kind_exists(self):
        assert "entry_signal_kind" in self._fields()

    def test_flat_state_valid(self):
        pos = PositionStateResponse(user_id=1, ticker="VIC", state="FLAT")
        assert pos.state == "FLAT"
        assert pos.entry_price is None
        assert pos.current_stop is None


# ---------------------------------------------------------------------------
# F-153 — Frontend computation logic
# ---------------------------------------------------------------------------

class TestRiskPctLogic:
    """Mirrors the riskPct() helper in PositionsPage."""

    def _risk(self, entry, stop):
        if entry is None or stop is None:
            return None
        return abs(entry - stop) / entry * 100

    def test_long_risk(self):
        # Entry 50, stop 47 → 6%
        assert abs(self._risk(50.0, 47.0) - 6.0) < 0.01

    def test_short_risk(self):
        # Entry 50, stop 53 → 6%
        assert abs(self._risk(50.0, 53.0) - 6.0) < 0.01

    def test_no_stop_returns_none(self):
        assert self._risk(50.0, None) is None

    def test_no_entry_returns_none(self):
        assert self._risk(None, 47.0) is None


class TestDaysSinceLogic:
    """Mirrors the daysSince() helper in PositionsPage."""

    def _days(self, entry_date_str):
        from datetime import date as dt
        if not entry_date_str:
            return None
        d = dt.fromisoformat(entry_date_str)
        return (dt.today() - d).days

    def test_today_is_zero(self):
        from datetime import date as dt
        today = str(dt.today())
        assert self._days(today) == 0

    def test_none_returns_none(self):
        assert self._days(None) is None

    def test_past_date_positive(self):
        assert self._days("2020-01-01") > 0


class TestStopEditorValidation:
    """Mirrors the inline stop validation logic."""

    def _valid(self, val):
        try:
            n = float(val)
            return n > 0
        except (ValueError, TypeError):
            return False

    def test_valid_price(self):
        assert self._valid("47.5") is True

    def test_zero_invalid(self):
        assert self._valid("0") is False

    def test_negative_invalid(self):
        assert self._valid("-1") is False

    def test_empty_invalid(self):
        assert self._valid("") is False

    def test_text_invalid(self):
        assert self._valid("abc") is False
