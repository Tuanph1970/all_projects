"""Tests for Phase Q — Trade outcome tagging (F-160..F-163)."""
from __future__ import annotations

import pytest
from datetime import date, datetime
from app.models.schemas import (
    OutcomeRecord,
    OutcomeSummary,
    OutcomesResponse,
)


# ---------------------------------------------------------------------------
# F-160 — OutcomeRecord schema
# ---------------------------------------------------------------------------

class TestOutcomeRecord:
    def _rec(self, **kw):
        defaults = dict(
            run_id=1,
            ticker="VIC",
            bar_date=date(2025, 5, 1),
            action="BUY",
            entry_price=50.0,
            stop_price=47.0,
            exit_price=56.0,
            outcome="WIN",
            r_multiple=2.0,
            exit_run_id=2,
            signal_kind="MA_CROSS",
            regime="TREND_UP",
            created_at=datetime(2025, 5, 1, 9, 0),
        )
        defaults.update(kw)
        return OutcomeRecord(**defaults)

    def test_win_record(self):
        rec = self._rec(outcome="WIN", r_multiple=2.0)
        assert rec.outcome == "WIN"
        assert rec.r_multiple == 2.0

    def test_loss_record(self):
        rec = self._rec(outcome="LOSS", r_multiple=-1.5, exit_price=45.5)
        assert rec.outcome == "LOSS"
        assert rec.r_multiple < 0

    def test_breakeven_record(self):
        rec = self._rec(outcome="BREAKEVEN", r_multiple=0.05)
        assert rec.outcome == "BREAKEVEN"

    def test_sell_short_record(self):
        rec = self._rec(action="SELL_SHORT", outcome="WIN", entry_price=50.0, exit_price=44.0)
        assert rec.action == "SELL_SHORT"

    def test_optional_fields_none(self):
        rec = OutcomeRecord(
            run_id=1, ticker="VIC", bar_date=date(2025, 5, 1),
            action="BUY", created_at=datetime(2025, 5, 1),
        )
        assert rec.entry_price is None
        assert rec.exit_price is None
        assert rec.outcome is None
        assert rec.r_multiple is None

    def test_stop_price_field(self):
        rec = self._rec(stop_price=47.0)
        assert rec.stop_price == 47.0

    def test_exit_run_id_field(self):
        rec = self._rec(exit_run_id=99)
        assert rec.exit_run_id == 99


# ---------------------------------------------------------------------------
# F-161 — OutcomeSummary schema
# ---------------------------------------------------------------------------

class TestOutcomeSummary:
    def test_basic_summary(self):
        s = OutcomeSummary(
            total_tagged=10, wins=6, losses=3, breakevens=1,
            win_rate=0.6, avg_r=0.8, expectancy=0.35,
        )
        assert s.total_tagged == 10
        assert s.win_rate == 0.6

    def test_zero_trades(self):
        s = OutcomeSummary(
            total_tagged=0, wins=0, losses=0, breakevens=0, win_rate=0.0,
        )
        assert s.avg_r is None
        assert s.expectancy is None

    def test_all_wins(self):
        s = OutcomeSummary(
            total_tagged=5, wins=5, losses=0, breakevens=0,
            win_rate=1.0, avg_r=2.0, expectancy=2.0,
        )
        assert s.wins == 5
        assert s.losses == 0

    def test_all_losses(self):
        s = OutcomeSummary(
            total_tagged=3, wins=0, losses=3, breakevens=0,
            win_rate=0.0, avg_r=-1.0, expectancy=-1.0,
        )
        assert s.win_rate == 0.0

    def test_avg_r_optional(self):
        s = OutcomeSummary(
            total_tagged=0, wins=0, losses=0, breakevens=0, win_rate=0.0,
        )
        assert s.avg_r is None


# ---------------------------------------------------------------------------
# F-162 — OutcomesResponse schema
# ---------------------------------------------------------------------------

class TestOutcomesResponse:
    def _summary(self):
        return OutcomeSummary(
            total_tagged=2, wins=1, losses=1, breakevens=0,
            win_rate=0.5, avg_r=0.25, expectancy=0.0,
        )

    def _rec(self, run_id=1, outcome="WIN"):
        return OutcomeRecord(
            run_id=run_id, ticker="VIC", bar_date=date(2025, 5, 1),
            action="BUY", outcome=outcome, r_multiple=1.5 if outcome == "WIN" else -1.0,
            created_at=datetime(2025, 5, 1),
        )

    def test_empty_response(self):
        resp = OutcomesResponse(
            user_id=1, days=90,
            computed_at=datetime(2025, 5, 1),
            summary=self._summary(),
            records=[],
        )
        assert resp.records == []

    def test_with_records(self):
        resp = OutcomesResponse(
            user_id=1, days=90,
            computed_at=datetime(2025, 5, 1),
            summary=self._summary(),
            records=[self._rec(1, "WIN"), self._rec(2, "LOSS")],
        )
        assert len(resp.records) == 2
        assert resp.records[0].outcome == "WIN"

    def test_days_field(self):
        resp = OutcomesResponse(
            user_id=1, days=180,
            computed_at=datetime(2025, 5, 1),
            summary=self._summary(),
            records=[],
        )
        assert resp.days == 180


# ---------------------------------------------------------------------------
# F-163 — R-multiple computation logic (mirrors _tag_origin_run)
# ---------------------------------------------------------------------------

class TestRMultipleLogic:
    def _compute_r(self, action, entry, stop, exit_price):
        risk = abs(entry - stop)
        if risk < 1e-9:
            return None
        if action == "BUY":
            return (exit_price - entry) / risk
        else:  # SELL_SHORT
            return (entry - exit_price) / risk

    def _classify(self, r):
        if r is None:
            return None
        return "WIN" if r > 0.1 else ("LOSS" if r < -0.1 else "BREAKEVEN")

    def test_long_win(self):
        r = self._compute_r("BUY", entry=50, stop=47, exit_price=56)
        assert r == pytest.approx(2.0)
        assert self._classify(r) == "WIN"

    def test_long_loss(self):
        r = self._compute_r("BUY", entry=50, stop=47, exit_price=47)
        assert r == pytest.approx(-1.0)
        assert self._classify(r) == "LOSS"

    def test_long_breakeven(self):
        r = self._compute_r("BUY", entry=50, stop=47, exit_price=50.05)
        assert self._classify(r) == "BREAKEVEN"

    def test_short_win(self):
        r = self._compute_r("SELL_SHORT", entry=50, stop=53, exit_price=44)
        assert r == pytest.approx(2.0)
        assert self._classify(r) == "WIN"

    def test_short_loss(self):
        r = self._compute_r("SELL_SHORT", entry=50, stop=53, exit_price=53)
        assert r == pytest.approx(-1.0)
        assert self._classify(r) == "LOSS"

    def test_zero_risk_guard(self):
        r = self._compute_r("BUY", entry=50, stop=50, exit_price=55)
        assert r is None

    def test_large_win(self):
        r = self._compute_r("BUY", entry=50, stop=49, exit_price=55)
        assert r == pytest.approx(5.0)
        assert self._classify(r) == "WIN"

    def test_breakeven_boundary_positive(self):
        # r = 0.1 exactly → boundary → WIN by > 0.1 is False → BREAKEVEN
        r = 0.1
        assert self._classify(r) == "BREAKEVEN"

    def test_breakeven_boundary_negative(self):
        r = -0.1
        assert self._classify(r) == "BREAKEVEN"


# ---------------------------------------------------------------------------
# F-163 — Win-rate / expectancy helpers (mirrors OutcomesPage frontend)
# ---------------------------------------------------------------------------

class TestSummaryComputations:
    def _compute(self, r_values):
        total = len(r_values)
        if total == 0:
            return dict(win_rate=0.0, avg_r=None, expectancy=None)
        wins = sum(1 for r in r_values if r > 0.1)
        losses = sum(1 for r in r_values if r < -0.1)
        win_rate = wins / total
        avg_r = sum(r_values) / total
        expectancy = avg_r * win_rate - abs(avg_r) * (1 - win_rate)
        return dict(win_rate=win_rate, avg_r=avg_r, expectancy=expectancy)

    def test_empty(self):
        res = self._compute([])
        assert res["win_rate"] == 0.0
        assert res["avg_r"] is None

    def test_all_wins(self):
        res = self._compute([2.0, 1.5, 3.0])
        assert res["win_rate"] == pytest.approx(1.0)
        assert res["avg_r"] == pytest.approx(2.167, abs=0.01)

    def test_mixed(self):
        res = self._compute([2.0, -1.0])
        assert res["win_rate"] == pytest.approx(0.5)
        assert res["avg_r"] == pytest.approx(0.5)

    def test_all_losses(self):
        res = self._compute([-1.0, -2.0])
        assert res["win_rate"] == 0.0
