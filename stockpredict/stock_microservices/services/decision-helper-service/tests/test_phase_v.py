"""Phase V (F-210..F-213) — Performance attribution unit tests."""
from datetime import date, datetime

import pytest

from app.models.schemas import AttributionRow, AttributionResponse
from app.services.attribution import (
    _hold_bucket,
    _stats,
    compute_attribution,
)


# ── AttributionRow schema ─────────────────────────────────────────────────────

class TestAttributionRow:
    def test_basic(self):
        r = AttributionRow(
            label="MA_CROSS", count=10, wins=6, losses=3, breakevens=1,
            win_rate=0.6, avg_r=0.8, expectancy=0.4,
        )
        assert r.label == "MA_CROSS"
        assert r.win_rate == 0.6

    def test_optional_r(self):
        r = AttributionRow(
            label="UNKNOWN", count=1, wins=0, losses=1, breakevens=0,
            win_rate=0.0,
        )
        assert r.avg_r is None
        assert r.expectancy is None


class TestAttributionResponse:
    def _make(self, **kw):
        defaults = dict(
            user_id=1, computed_at=datetime.utcnow(), days=90, total_tagged=5,
            by_signal=[], by_regime=[], by_weekday=[], by_hold_duration=[],
        )
        defaults.update(kw)
        return AttributionResponse(**defaults)

    def test_construction(self):
        r = self._make()
        assert r.total_tagged == 5
        assert r.by_signal == []

    def test_populated(self):
        row = AttributionRow(label="X", count=2, wins=1, losses=1, breakevens=0, win_rate=0.5)
        r = self._make(by_signal=[row])
        assert len(r.by_signal) == 1
        assert r.by_signal[0].label == "X"


# ── _hold_bucket ──────────────────────────────────────────────────────────────

class TestHoldBucket:
    def test_same_day(self):
        assert _hold_bucket(date(2025, 1, 10), date(2025, 1, 10)) == "1d"

    def test_one_day(self):
        assert _hold_bucket(date(2025, 1, 10), date(2025, 1, 11)) == "1d"

    def test_two_days(self):
        assert _hold_bucket(date(2025, 1, 10), date(2025, 1, 12)) == "2-3d"

    def test_three_days(self):
        assert _hold_bucket(date(2025, 1, 10), date(2025, 1, 13)) == "2-3d"

    def test_four_days(self):
        assert _hold_bucket(date(2025, 1, 10), date(2025, 1, 14)) == "4-7d"

    def test_seven_days(self):
        assert _hold_bucket(date(2025, 1, 10), date(2025, 1, 17)) == "4-7d"

    def test_eight_days(self):
        assert _hold_bucket(date(2025, 1, 10), date(2025, 1, 18)) == "8-14d"

    def test_fourteen_days(self):
        assert _hold_bucket(date(2025, 1, 10), date(2025, 1, 24)) == "8-14d"

    def test_fifteen_days(self):
        assert _hold_bucket(date(2025, 1, 10), date(2025, 1, 25)) == "15d+"

    def test_no_exit_date(self):
        assert _hold_bucket(date(2025, 1, 10), None) == "unknown"

    def test_no_entry_date(self):
        assert _hold_bucket(None, date(2025, 1, 10)) == "unknown"


# ── _stats ────────────────────────────────────────────────────────────────────

class TestStats:
    def test_empty(self):
        s = _stats([])
        assert s["count"] == 0
        assert s["avg_r"] is None
        assert s["expectancy"] is None

    def test_all_wins(self):
        s = _stats([("WIN", 2.0), ("WIN", 1.5), ("WIN", 1.0)])
        assert s["wins"] == 3
        assert s["losses"] == 0
        assert abs(s["win_rate"] - 1.0) < 1e-6
        assert s["avg_r"] is not None

    def test_all_losses(self):
        s = _stats([("LOSS", -1.0), ("LOSS", -0.5)])
        assert s["win_rate"] == 0.0
        assert s["losses"] == 2
        assert s["avg_r"] < 0

    def test_mixed(self):
        s = _stats([("WIN", 2.0), ("LOSS", -1.0)])
        assert s["count"] == 2
        assert s["wins"] == 1
        assert s["losses"] == 1
        assert abs(s["win_rate"] - 0.5) < 1e-6
        assert abs(s["avg_r"] - 0.5) < 1e-6

    def test_breakeven_counted(self):
        s = _stats([("WIN", 0.5), ("BREAKEVEN", 0.0), ("LOSS", -0.5)])
        assert s["breakevens"] == 1

    def test_none_r_excluded_from_avg(self):
        s = _stats([("WIN", None), ("WIN", 2.0)])
        assert s["avg_r"] == 2.0  # None excluded

    def test_all_none_r_gives_none(self):
        s = _stats([("WIN", None), ("LOSS", None)])
        assert s["avg_r"] is None


# ── compute_attribution ───────────────────────────────────────────────────────

def _rec(outcome="WIN", r=1.0, signal="MA_CROSS", regime="TREND_UP",
         bar_date=date(2025, 1, 6), exit_date=date(2025, 1, 9)):  # Monday, 3-day hold
    return {
        "outcome": outcome, "r_multiple": r,
        "signal_kind": signal, "regime": regime,
        "bar_date": bar_date, "exit_bar_date": exit_date,
    }


class TestComputeAttribution:
    def test_empty_records(self):
        result = compute_attribution([])
        assert result["by_signal"] == []
        assert result["by_regime"] == []
        assert result["by_weekday"] == []
        assert result["by_hold_duration"] == []

    def test_single_record_appears_in_all_dimensions(self):
        result = compute_attribution([_rec()])
        assert len(result["by_signal"]) == 1
        assert len(result["by_regime"]) == 1
        assert len(result["by_weekday"]) == 1
        assert len(result["by_hold_duration"]) == 1

    def test_signal_label_correct(self):
        result = compute_attribution([_rec(signal="BREAKOUT")])
        assert result["by_signal"][0]["label"] == "BREAKOUT"

    def test_regime_label_correct(self):
        result = compute_attribution([_rec(regime="RANGE")])
        assert result["by_regime"][0]["label"] == "RANGE"

    def test_weekday_label_monday(self):
        # date(2025,1,6) is a Monday
        result = compute_attribution([_rec(bar_date=date(2025, 1, 6))])
        assert result["by_weekday"][0]["label"] == "Monday"

    def test_weekday_label_friday(self):
        # date(2025,1,10) is a Friday
        result = compute_attribution([_rec(bar_date=date(2025, 1, 10))])
        assert result["by_weekday"][0]["label"] == "Friday"

    def test_hold_bucket_label(self):
        result = compute_attribution([_rec(bar_date=date(2025, 1, 6), exit_date=date(2025, 1, 7))])
        assert result["by_hold_duration"][0]["label"] == "1d"

    def test_multiple_signals_grouped(self):
        records = [
            _rec(signal="MA_CROSS", outcome="WIN"),
            _rec(signal="MA_CROSS", outcome="LOSS"),
            _rec(signal="BREAKOUT", outcome="WIN"),
        ]
        result = compute_attribution(records)
        by_sig = {r["label"]: r for r in result["by_signal"]}
        assert by_sig["MA_CROSS"]["count"] == 2
        assert by_sig["BREAKOUT"]["count"] == 1

    def test_win_rate_computed_correctly(self):
        records = [_rec(outcome="WIN")] * 3 + [_rec(outcome="LOSS")] * 1
        result = compute_attribution(records)
        assert result["by_signal"][0]["win_rate"] == 0.75

    def test_none_signal_bucketed_as_unknown(self):
        result = compute_attribution([_rec(signal=None)])
        assert result["by_signal"][0]["label"] == "UNKNOWN"

    def test_weekday_order(self):
        records = [
            _rec(bar_date=date(2025, 1, 10)),  # Friday
            _rec(bar_date=date(2025, 1, 6)),   # Monday
            _rec(bar_date=date(2025, 1, 8)),   # Wednesday
        ]
        result = compute_attribution(records)
        labels = [r["label"] for r in result["by_weekday"]]
        assert labels.index("Monday") < labels.index("Wednesday") < labels.index("Friday")

    def test_hold_duration_order(self):
        records = [
            _rec(bar_date=date(2025, 1, 1), exit_date=date(2025, 1, 16)),  # 15d+
            _rec(bar_date=date(2025, 1, 1), exit_date=date(2025, 1, 2)),   # 1d
        ]
        result = compute_attribution(records)
        labels = [r["label"] for r in result["by_hold_duration"]]
        assert labels.index("1d") < labels.index("15d+")

    def test_avg_r_computed(self):
        records = [_rec(r=2.0), _rec(r=1.0)]
        result = compute_attribution(records)
        assert abs(result["by_signal"][0]["avg_r"] - 1.5) < 1e-6
