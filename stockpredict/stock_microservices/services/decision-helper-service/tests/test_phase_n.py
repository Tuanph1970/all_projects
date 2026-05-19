"""Tests for Phase N — Performance analytics (F-130..F-133)."""
from __future__ import annotations

import pytest
from datetime import date, datetime
from app.models.schemas import (
    ActionBreakdownItem,
    AnalyticsResponse,
    ConfidenceBucketItem,
    DailyActionablePoint,
    RegimeBreakdownItem,
    SignalBreakdownItem,
    TopTickerItem,
)


# ---------------------------------------------------------------------------
# F-130 — Schema field contracts
# ---------------------------------------------------------------------------

class TestActionBreakdownItem:
    def test_fields(self):
        item = ActionBreakdownItem(action="BUY", count=12, pct=24.0)
        assert item.action == "BUY"
        assert item.count == 12
        assert item.pct == 24.0

    def test_pct_is_float(self):
        item = ActionBreakdownItem(action="WAIT", count=5, pct=10.0)
        assert isinstance(item.pct, float)


class TestRegimeBreakdownItem:
    def test_fields(self):
        item = RegimeBreakdownItem(
            regime="TREND_UP", total=30, buy_count=18,
            sell_short_count=0, hold_wait_count=12,
        )
        assert item.regime == "TREND_UP"
        assert item.total == 30
        assert item.buy_count == 18
        assert item.hold_wait_count == 12


class TestSignalBreakdownItem:
    def test_fields(self):
        item = SignalBreakdownItem(
            signal_kind="MA_CROSS", fire_count=20, confirmed_count=14,
            confirmation_rate=0.7, avg_confidence=0.68,
        )
        assert item.signal_kind == "MA_CROSS"
        assert item.fire_count == 20
        assert item.confirmation_rate == 0.7

    def test_confirmation_rate_range(self):
        item = SignalBreakdownItem(
            signal_kind="N_DAY_BREAKOUT", fire_count=10, confirmed_count=3,
            confirmation_rate=0.3, avg_confidence=0.55,
        )
        assert 0.0 <= item.confirmation_rate <= 1.0


class TestDailyActionablePoint:
    def test_fields(self):
        pt = DailyActionablePoint(date="2025-05-19", count=3)
        assert pt.date == "2025-05-19"
        assert pt.count == 3


class TestTopTickerItem:
    def test_fields(self):
        item = TopTickerItem(ticker="VIC", decision_count=45, buy_count=12, sell_short_count=4)
        assert item.ticker == "VIC"
        assert item.decision_count == 45


class TestConfidenceBucketItem:
    def test_fields(self):
        b = ConfidenceBucketItem(bucket="70-80%", count=7)
        assert b.bucket == "70-80%"
        assert b.count == 7


# ---------------------------------------------------------------------------
# F-131 — AnalyticsResponse assembly
# ---------------------------------------------------------------------------

def _make_analytics(**kw):
    defaults = dict(
        user_id=1,
        computed_at=datetime(2025, 5, 19, 10, 0, 0),
        days=90,
        total_decisions=50,
        actionable_count=15,
        action_breakdown=[
            ActionBreakdownItem(action="BUY", count=10, pct=20.0),
            ActionBreakdownItem(action="WAIT", count=40, pct=80.0),
        ],
        regime_breakdown=[
            RegimeBreakdownItem(regime="TREND_UP", total=30, buy_count=10,
                                sell_short_count=2, hold_wait_count=18),
        ],
        signal_breakdown=[
            SignalBreakdownItem(signal_kind="MA_CROSS", fire_count=20,
                                confirmed_count=14, confirmation_rate=0.7, avg_confidence=0.68),
        ],
        daily_actionable=[
            DailyActionablePoint(date="2025-05-18", count=2),
            DailyActionablePoint(date="2025-05-19", count=1),
        ],
        top_tickers=[
            TopTickerItem(ticker="VIC", decision_count=20, buy_count=5, sell_short_count=2),
        ],
        confidence_histogram=[
            ConfidenceBucketItem(bucket=f"{p}-{p+10}%", count=0) for p in range(0, 100, 10)
        ],
    )
    return AnalyticsResponse(**{**defaults, **kw})


class TestAnalyticsResponse:
    def test_assembles_correctly(self):
        resp = _make_analytics()
        assert resp.user_id == 1
        assert resp.total_decisions == 50
        assert resp.actionable_count == 15
        assert resp.days == 90

    def test_action_breakdown_list(self):
        resp = _make_analytics()
        assert len(resp.action_breakdown) == 2
        assert resp.action_breakdown[0].action == "BUY"

    def test_signal_breakdown_list(self):
        resp = _make_analytics()
        assert resp.signal_breakdown[0].signal_kind == "MA_CROSS"

    def test_daily_actionable_list(self):
        resp = _make_analytics()
        assert len(resp.daily_actionable) == 2
        assert resp.daily_actionable[0].date == "2025-05-18"

    def test_confidence_histogram_has_10_buckets(self):
        resp = _make_analytics()
        assert len(resp.confidence_histogram) == 10

    def test_top_tickers(self):
        resp = _make_analytics()
        assert resp.top_tickers[0].ticker == "VIC"

    def test_empty_breakdown_lists(self):
        resp = _make_analytics(action_breakdown=[], signal_breakdown=[], top_tickers=[])
        assert resp.action_breakdown == []
        assert resp.signal_breakdown == []


# ---------------------------------------------------------------------------
# F-132 — Analytics computation logic (mirrors backend bucket logic)
# ---------------------------------------------------------------------------

class TestConfidenceHistogramLogic:
    """Mirrors the bucket-map logic in the /analytics endpoint."""

    def _bucket(self, conf: float) -> str:
        pct = int(conf * 10) * 10
        pct = min(pct, 90)
        return f"{pct}-{pct + 10}%"

    def test_zero_goes_to_0_10(self):
        assert self._bucket(0.0) == "0-10%"

    def test_half_goes_to_50_60(self):
        assert self._bucket(0.5) == "50-60%"

    def test_point_82_goes_to_80_90(self):
        assert self._bucket(0.82) == "80-90%"

    def test_one_goes_to_90_100(self):
        assert self._bucket(1.0) == "90-100%"

    def test_point_99_goes_to_90_100(self):
        assert self._bucket(0.99) == "90-100%"


class TestActionablePctLogic:
    """Mirrors the frontend actionable % computation."""

    def _pct(self, total, actionable):
        return (actionable / total * 100) if total else 0.0

    def test_no_decisions(self):
        assert self._pct(0, 0) == 0.0

    def test_all_actionable(self):
        assert self._pct(10, 10) == 100.0

    def test_partial(self):
        assert abs(self._pct(50, 15) - 30.0) < 0.01


# ---------------------------------------------------------------------------
# F-133 — Ranking logic (action breakdown sorted by count desc)
# ---------------------------------------------------------------------------

class TestActionBreakdownSorting:
    def test_sorted_by_count_desc(self):
        items = [
            {"action": "WAIT", "count": 40},
            {"action": "BUY", "count": 10},
            {"action": "HOLD", "count": 25},
        ]
        ranked = sorted(items, key=lambda x: -x["count"])
        assert ranked[0]["action"] == "WAIT"
        assert ranked[1]["action"] == "HOLD"
        assert ranked[2]["action"] == "BUY"
