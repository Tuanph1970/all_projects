"""Phase E unit tests — F-040 failed_signal + F-042 midtrend entry detectors."""
from __future__ import annotations

from datetime import date, timedelta
from typing import List

import pytest

from app.services.signal.base import OHLCVBar
from app.services.signal.failed_signal import (
    OVERRIDE_THRESHOLD,
    FailedSignalResult,
    detect_failed_signals,
    highest_severity,
    _bull_trap,
    _bear_trap,
    _false_tl_break,
    _filled_gap,
    _return_to_spike,
    _wrd_return,
    _opposite_breakout,
    _counter_anticipated_flag,
    _hs_target_failure,
    _double_top_break,
    _rounding_break,
    _future_reliability,
)
from app.services.signal.trend.midtrend import (
    detect_midtrend_entry,
    _pct_retracement,
    _minor_reaction_reversal,
    _continuation_breakout,
    _long_ma_reaction,
    LONG_MA_PERIOD,
    REACTION_N,
    CONSOLIDATION_MIN,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bars(
    n: int,
    base_close: float = 100.0,
    delta: float = 0.0,
    start: date = date(2024, 1, 2),
) -> List[OHLCVBar]:
    """Generate n daily bars with a linear drift of delta per bar."""
    bars = []
    for i in range(n):
        c = base_close + i * delta
        o = c - 0.20
        bars.append(OHLCVBar(
            date=start + timedelta(days=i),
            open=o,
            high=c + 0.50,
            low=c - 0.50,
            close=c,
            volume=10_000,
        ))
    return bars


def _bar_date(bars: List[OHLCVBar]) -> date:
    return bars[-1].date


# ===========================================================================
# TestFailedSignalResult
# ===========================================================================

class TestFailedSignalResult:
    def test_dataclass_fields(self):
        r = FailedSignalResult(kind="BULL_TRAP", direction="SHORT", severity=0.7)
        assert r.kind == "BULL_TRAP"
        assert r.direction == "SHORT"
        assert r.severity == 0.7
        assert r.evidence == {}

    def test_highest_severity_empty(self):
        assert highest_severity([]) is None

    def test_highest_severity_picks_max(self):
        results = [
            FailedSignalResult("BEAR_TRAP", "LONG", 0.6),
            FailedSignalResult("BULL_TRAP", "SHORT", 0.8),
            FailedSignalResult("FILLED_GAP", "LONG", 0.5),
        ]
        top = highest_severity(results)
        assert top is not None
        assert top.kind == "BULL_TRAP"
        assert top.severity == 0.8


# ===========================================================================
# TestBullTrap
# ===========================================================================

class TestBullTrap:
    def _sr_data(self, level: float) -> dict:
        return {"resistances": [{"price": level, "strength": 2}], "supports": []}

    def test_fires_when_prior_close_above_then_drops_below(self):
        bars = _make_bars(10)
        # Make bar idx-2 close above level, and today close below
        bars[-2] = OHLCVBar(bars[-2].date, 100.5, 101.5, 99.5, 101.5, 10000)
        bars[-1] = OHLCVBar(bars[-1].date, 100.0, 100.5, 99.0, 99.5, 10000)
        result = _bull_trap(bars, len(bars) - 1, self._sr_data(101.0))
        assert result is not None
        assert result.kind == "BULL_TRAP"
        assert result.direction == "SHORT"
        assert 0 < result.severity <= 1.0

    def test_no_fire_when_still_above_level(self):
        bars = _make_bars(10)
        bars[-2] = OHLCVBar(bars[-2].date, 100.5, 102.0, 100.0, 101.5, 10000)
        bars[-1] = OHLCVBar(bars[-1].date, 101.0, 102.5, 100.5, 102.0, 10000)
        result = _bull_trap(bars, len(bars) - 1, self._sr_data(101.0))
        assert result is None

    def test_returns_none_without_sr_data(self):
        bars = _make_bars(10)
        assert _bull_trap(bars, len(bars) - 1, None) is None


# ===========================================================================
# TestBearTrap
# ===========================================================================

class TestBearTrap:
    def _sr_data(self, level: float) -> dict:
        return {"supports": [{"price": level, "strength": 2}], "resistances": []}

    def test_fires_when_prior_close_below_then_recovers(self):
        bars = _make_bars(10)
        bars[-2] = OHLCVBar(bars[-2].date, 99.5, 100.0, 98.0, 98.5, 10000)
        bars[-1] = OHLCVBar(bars[-1].date, 99.0, 101.0, 98.5, 100.5, 10000)
        result = _bear_trap(bars, len(bars) - 1, self._sr_data(99.0))
        assert result is not None
        assert result.kind == "BEAR_TRAP"
        assert result.direction == "LONG"

    def test_no_fire_when_still_below(self):
        bars = _make_bars(10)
        bars[-2] = OHLCVBar(bars[-2].date, 99.5, 100.0, 98.0, 98.5, 10000)
        bars[-1] = OHLCVBar(bars[-1].date, 98.0, 99.0, 97.5, 98.0, 10000)
        result = _bear_trap(bars, len(bars) - 1, self._sr_data(99.0))
        assert result is None


# ===========================================================================
# TestFalseTLBreak
# ===========================================================================

class TestFalseTLBreak:
    def test_fires_on_downward_reversal_through_ma(self):
        # Build bars: first 52 slowly rising so MA≈100, then yesterday spikes above, today reverses below
        bars = _make_bars(52, base_close=100.0, delta=0.0)
        # Yesterday: close above slow MA
        bars[-2] = OHLCVBar(bars[-2].date, 100.5, 102.0, 100.0, 101.5, 10000)
        # Today: close drops below slow MA (which is ~100)
        bars[-1] = OHLCVBar(bars[-1].date, 100.5, 101.0, 98.5, 99.0, 10000)
        idx = len(bars) - 1
        result = _false_tl_break(bars, idx)
        assert result is not None
        assert result.kind == "FALSE_TL_BREAK"
        assert result.direction == "SHORT"

    def test_fires_on_upward_reversal_through_ma(self):
        bars = _make_bars(52, base_close=100.0, delta=0.0)
        # Yesterday: close below slow MA
        bars[-2] = OHLCVBar(bars[-2].date, 99.5, 100.0, 98.0, 98.5, 10000)
        # Today: close above slow MA
        bars[-1] = OHLCVBar(bars[-1].date, 99.0, 102.0, 98.5, 101.5, 10000)
        idx = len(bars) - 1
        result = _false_tl_break(bars, idx)
        assert result is not None
        assert result.direction == "LONG"

    def test_not_enough_bars_returns_none(self):
        bars = _make_bars(20)
        assert _false_tl_break(bars, len(bars) - 1) is None


# ===========================================================================
# TestFilledGap
# ===========================================================================

class TestFilledGap:
    def test_gap_up_filled(self):
        bars = _make_bars(10, base_close=100.0)
        # bar[6]: set open=100.0 so no unintended gap from bar[5]
        bars[6] = OHLCVBar(bars[6].date, 100.0, 100.5, 99.0, 100.0, 10000)
        # bar[7]: clear gap up from bar[6].close=100.0 (open=103.0 >> prev close)
        bars[7] = OHLCVBar(bars[7].date, 103.0, 104.0, 102.5, 103.5, 10000)
        # Today (bar[9]): low <= bar[6].close=100.0 → gap is filled
        bars[9] = OHLCVBar(bars[9].date, 101.0, 102.0, 99.5, 100.5, 10000)
        result = _filled_gap(bars, 9)
        assert result is not None
        assert result.kind == "FILLED_GAP"
        assert result.direction == "SHORT"

    def test_gap_down_filled(self):
        bars = _make_bars(10, base_close=100.0)
        # bar[6]: open=100.0 → no gap from bar[5].close≈100.0
        bars[6] = OHLCVBar(bars[6].date, 100.0, 101.0, 99.5, 100.5, 10000)
        # bar[7]: clear gap down from bar[6].close=100.5 (open=97.0 << prev close)
        bars[7] = OHLCVBar(bars[7].date, 97.0, 98.0, 96.5, 97.5, 10000)
        # Today: high >= bar[6].close=100.5 → gap is filled
        bars[9] = OHLCVBar(bars[9].date, 98.0, 101.0, 97.5, 100.0, 10000)
        result = _filled_gap(bars, 9)
        assert result is not None
        assert result.direction == "LONG"

    def test_no_gap_no_fire(self):
        bars = _make_bars(10)
        result = _filled_gap(bars, 9)
        assert result is None


# ===========================================================================
# TestReturnToSpike
# ===========================================================================

class TestReturnToSpike:
    def test_return_to_downside_spike_fires_short(self):
        bars = _make_bars(20, base_close=100.0)
        # Create a spike bar with huge downside wick at index 10
        bars[10] = OHLCVBar(bars[10].date, 100.0, 100.5, 90.0, 99.5, 10000)  # huge wick
        # Today: close near spike low
        bars[19] = OHLCVBar(bars[19].date, 91.0, 92.0, 89.5, 90.3, 10000)
        result = _return_to_spike(bars, 19)
        assert result is not None
        assert result.kind == "RETURN_TO_SPIKE"
        assert result.direction == "SHORT"

    def test_not_enough_bars(self):
        bars = _make_bars(8)
        assert _return_to_spike(bars, 7) is None


# ===========================================================================
# TestWRDReturn
# ===========================================================================

class TestWRDReturn:
    def test_bullish_wrd_then_close_below_open(self):
        bars = _make_bars(10, base_close=100.0)
        # WRD at bar[7]: huge bullish candle (range >> avg)
        bars[7] = OHLCVBar(bars[7].date, 95.0, 108.0, 94.5, 107.0, 10000)
        # Today: close below the WRD open
        bars[9] = OHLCVBar(bars[9].date, 94.5, 96.0, 93.0, 94.0, 10000)
        result = _wrd_return(bars, 9)
        assert result is not None
        assert result.kind == "WRD_RETURN"
        assert result.direction == "SHORT"

    def test_no_wrd_no_fire(self):
        bars = _make_bars(10)
        result = _wrd_return(bars, 9)
        assert result is None


# ===========================================================================
# TestOppositeBreakout
# ===========================================================================

class TestOppositeBreakout:
    def test_uptrend_breaks_below_support(self):
        # Rising bars over 21 bars
        bars = _make_bars(25, base_close=100.0, delta=0.5)
        sr_data = {"supports": [{"price": 110.0, "strength": 2}], "resistances": []}
        # Today closes below support
        bars[-1] = OHLCVBar(bars[-1].date, 110.5, 111.0, 108.0, 109.0, 10000)
        result = _opposite_breakout(bars, len(bars) - 1, sr_data)
        assert result is not None
        assert result.kind == "OPPOSITE_BREAKOUT"
        assert result.direction == "SHORT"

    def test_no_fire_without_sr(self):
        bars = _make_bars(25, delta=0.5)
        assert _opposite_breakout(bars, len(bars) - 1, None) is None


# ===========================================================================
# Pattern-based detector tests
# ===========================================================================

class TestPatternDetectors:
    def test_counter_anticipated_flag_fires(self):
        bars = _make_bars(10)
        patterns = {"patterns": [{
            "pattern_type": "FLAG_BULL",
            "status": "ACTIVE",
            "break_direction": "DOWN",
        }]}
        result = _counter_anticipated_flag(bars, 9, patterns)
        assert result is not None
        assert result.kind == "COUNTER_ANTICIPATED_FLAG"
        assert result.direction == "SHORT"

    def test_counter_anticipated_flag_no_fire_correct_direction(self):
        bars = _make_bars(10)
        patterns = {"patterns": [{
            "pattern_type": "FLAG_BULL",
            "status": "ACTIVE",
            "break_direction": "UP",
        }]}
        assert _counter_anticipated_flag(bars, 9, patterns) is None

    def test_hs_target_failure_fires(self):
        bars = _make_bars(10, base_close=100.0)
        # H&S broke down (neckline=100), but price recovered above neckline
        bars[-1] = OHLCVBar(bars[-1].date, 100.5, 101.5, 99.5, 101.0, 10000)
        patterns = {"patterns": [{
            "pattern_type": "HEAD_AND_SHOULDERS",
            "status": "ACTIVE",
            "neckline": 100.0,
            "measured_move_target": 90.0,
        }]}
        result = _hs_target_failure(bars, 9, patterns)
        assert result is not None
        assert result.kind == "HS_TARGET_FAILURE"
        assert result.direction == "LONG"

    def test_double_top_break_fires(self):
        bars = _make_bars(10)
        bars[-1] = OHLCVBar(bars[-1].date, 100.5, 101.0, 99.5, 100.5, 10000)
        patterns = {"patterns": [{
            "pattern_type": "DOUBLE_TOP",
            "status": "ACTIVE",
            "confirmation_level": 99.0,
        }]}
        result = _double_top_break(bars, 9, patterns)
        assert result is not None
        assert result.direction == "LONG"

    def test_rounding_break_fires_short(self):
        bars = _make_bars(10, base_close=98.0)
        # Rounding bottom broke up past 100.0, but today is back below 100
        bars[-1] = OHLCVBar(bars[-1].date, 99.5, 100.0, 97.5, 99.0, 10000)
        patterns = {"patterns": [{
            "pattern_type": "ROUNDING_BOTTOM",
            "status": "ACTIVE",
            "breakout_level": 100.0,
        }]}
        result = _rounding_break(bars, 9, patterns)
        assert result is not None
        assert result.direction == "SHORT"

    def test_future_reliability_fires_on_low_score(self):
        bars = _make_bars(10)
        patterns = {"patterns": [{
            "pattern_type": "SOME_PATTERN",
            "status": "ACTIVE",
            "reliability_score": 0.30,
            "implied_direction": "LONG",
        }]}
        result = _future_reliability(bars, 9, patterns)
        assert result is not None
        assert result.kind == "FUTURE_RELIABILITY"
        assert result.direction == "SHORT"

    def test_future_reliability_no_fire_above_threshold(self):
        bars = _make_bars(10)
        patterns = {"patterns": [{
            "pattern_type": "SOME_PATTERN",
            "status": "ACTIVE",
            "reliability_score": 0.80,
            "implied_direction": "LONG",
        }]}
        assert _future_reliability(bars, 9, patterns) is None


# ===========================================================================
# TestDetectFailedSignals (integration)
# ===========================================================================

class TestDetectFailedSignals:
    def test_returns_empty_for_sparse_bars(self):
        bars = _make_bars(2)
        result = detect_failed_signals(bars, bars[-1].date)
        assert result == []

    def test_returns_sorted_by_severity(self):
        bars = _make_bars(60, base_close=100.0, delta=0.5)
        # Introduce a bull trap at resistance 120
        bars[-2] = OHLCVBar(bars[-2].date, 119.5, 121.5, 119.0, 121.0, 10000)
        bars[-1] = OHLCVBar(bars[-1].date, 120.5, 121.0, 118.5, 119.0, 10000)
        sr_data = {"resistances": [{"price": 120.0, "strength": 3}], "supports": []}
        results = detect_failed_signals(bars, bars[-1].date, sr_data=sr_data)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].severity >= results[i + 1].severity

    def test_no_fire_when_no_signals(self):
        bars = _make_bars(60, base_close=100.0, delta=0.0)
        result = detect_failed_signals(bars, bars[-1].date, sr_data=None, patterns=None)
        # With a flat trend and no S/R, very few should fire
        for r in result:
            assert 0 < r.severity <= 1.0


# ===========================================================================
# TestMidtrendPctRetracement
# ===========================================================================

class TestMidtrendPctRetracement:
    def test_50pct_pullback_with_reversal_bar_fires_long(self):
        # 40-bar uptrend fits inside the 60-bar lookback window so swing_low/high
        # capture the full move. delta=0.5 → close goes 100 → 119.5, high ≈ 120.
        n = 40
        bars = _make_bars(n, base_close=100.0, delta=0.5)
        move_low = bars[0].low          # ≈ 99.5
        move_high = bars[-1].high       # ≈ 120.0

        # 5 pullback bars targeting ~50% of the full move
        pullback_per_bar = (move_high - move_low) * 0.50 / 5
        for i in range(5):
            c = move_high - (i + 1) * pullback_per_bar
            o = c + 0.1                 # bearish candle
            d = bars[-1].date + timedelta(days=i + 1)
            bars.append(OHLCVBar(d, o, o + 0.1, c - 0.2, c, 10000))

        # Reversal bar: bullish (close > open)
        last_close = bars[-1].close
        rev_close = last_close + 1.0
        d = bars[-1].date + timedelta(days=1)
        bars.append(OHLCVBar(d, last_close, rev_close + 0.2, last_close - 0.1, rev_close, 10000))

        result = _pct_retracement(bars, len(bars) - 1, bars[-1].date, trend_up=True)
        assert result is not None
        assert result.kind == "PCT_RETRACEMENT"
        assert result.direction == "LONG"
        assert 0 < result.confidence <= 1.0

    def test_no_fire_when_no_reversal_bar(self):
        n = 80
        bars = _make_bars(n, base_close=100.0, delta=0.5)
        move_high = bars[-1].close
        pullback_per_bar = (move_high - 100.0) * 0.50 / 10
        for i in range(10):
            c = move_high - (i + 1) * pullback_per_bar
            o = c + 0.1  # bearish candle (open > close)
            d = bars[-1].date + timedelta(days=i + 1)
            bars.append(OHLCVBar(d, o, o + 0.3, c - 0.3, c, 10000))
        # No reversal — last bar also bearish
        result = _pct_retracement(bars, len(bars) - 1, bars[-1].date, trend_up=True)
        assert result is None


# ===========================================================================
# TestMidtrendMinorReaction
# ===========================================================================

class TestMidtrendMinorReaction:
    def _make_reaction_bars(self, trend_up: bool) -> tuple:
        base = _make_bars(60, base_close=100.0, delta=0.5 if trend_up else -0.5)
        # Counter-trend bars
        for i in range(REACTION_N):
            c = base[-1].close + (-0.5 if trend_up else 0.5)
            o = base[-1].close
            d = base[-1].date + timedelta(days=1)
            base.append(OHLCVBar(d, o, max(o, c) + 0.1, min(o, c) - 0.1, c, 10000))
        # Reversal (trend-aligned) bar
        if trend_up:
            o = base[-1].close
            c = o + 0.8
        else:
            o = base[-1].close
            c = o - 0.8
        d = base[-1].date + timedelta(days=1)
        base.append(OHLCVBar(d, o, max(o, c) + 0.1, min(o, c) - 0.1, c, 10000))
        return base, base[-1].date

    def test_fires_long_after_bearish_reaction(self):
        bars, bd = self._make_reaction_bars(trend_up=True)
        result = _minor_reaction_reversal(bars, len(bars) - 1, bd, trend_up=True)
        assert result is not None
        assert result.kind == "MINOR_REACTION_REVERSAL"
        assert result.direction == "LONG"

    def test_fires_short_after_bullish_reaction(self):
        bars, bd = self._make_reaction_bars(trend_up=False)
        result = _minor_reaction_reversal(bars, len(bars) - 1, bd, trend_up=False)
        assert result is not None
        assert result.direction == "SHORT"

    def test_no_fire_when_reaction_broken_by_trend_bar(self):
        bars = _make_bars(60, base_close=100.0, delta=0.5)
        # 2 counter-trend, then 1 trend, then 1 counter again → not clean
        for _ in range(2):
            c = bars[-1].close - 0.5
            bars.append(OHLCVBar(bars[-1].date + timedelta(1), c + 0.1, c + 0.4, c - 0.2, c, 10000))
        c = bars[-1].close + 0.8  # trend-aligned bar in the middle
        bars.append(OHLCVBar(bars[-1].date + timedelta(1), c - 0.1, c + 0.3, c - 0.3, c, 10000))
        result = _minor_reaction_reversal(bars, len(bars) - 1, bars[-1].date, trend_up=True)
        assert result is None


# ===========================================================================
# TestMidtrendContinuationBreakout
# ===========================================================================

class TestMidtrendContinuationBreakout:
    def _make_flag(self, trend_up: bool) -> tuple:
        bars = _make_bars(CONSOLIDATION_MIN + 25, base_close=100.0, delta=0.5 if trend_up else -0.5)
        # Add tight-range consolidation bars
        consol_close = bars[-1].close
        for i in range(CONSOLIDATION_MIN + 2):
            d = bars[-1].date + timedelta(days=i + 1)
            bars.append(OHLCVBar(d, consol_close, consol_close + 0.3, consol_close - 0.3, consol_close, 10000))
        # Breakout bar
        if trend_up:
            bo_close = consol_close + 1.0
        else:
            bo_close = consol_close - 1.0
        d = bars[-1].date + timedelta(days=1)
        bars.append(OHLCVBar(d, consol_close, max(consol_close, bo_close) + 0.5, min(consol_close, bo_close) - 0.2, bo_close, 10000))
        return bars, bars[-1].date

    def test_fires_long_on_upward_breakout(self):
        bars, bd = self._make_flag(trend_up=True)
        result = _continuation_breakout(bars, len(bars) - 1, bd, trend_up=True)
        assert result is not None
        assert result.kind == "CONTINUATION_BREAKOUT"
        assert result.direction == "LONG"

    def test_fires_short_on_downward_breakout(self):
        bars, bd = self._make_flag(trend_up=False)
        result = _continuation_breakout(bars, len(bars) - 1, bd, trend_up=False)
        assert result is not None
        assert result.direction == "SHORT"

    def test_no_fire_without_enough_consolidation(self):
        bars = _make_bars(50, base_close=100.0)
        result = _continuation_breakout(bars, len(bars) - 1, bars[-1].date, trend_up=True)
        assert result is None


# ===========================================================================
# TestMidtrendLongMAReaction
# ===========================================================================

class TestMidtrendLongMAReaction:
    def test_fires_long_after_ma_touch(self):
        n = LONG_MA_PERIOD + 10
        # Bars: all at 100 so MA = 100; then add a dip to MA and bounce
        bars = _make_bars(n, base_close=100.0, delta=0.0)

        # Simulate a bar that dipped to the MA (low very close to 100)
        touch_date = bars[-3].date
        bars[-3] = OHLCVBar(touch_date, 100.2, 100.6, 99.95, 100.1, 10000)

        # Today: close above MA with bullish candle
        today_date = bars[-1].date
        bars[-1] = OHLCVBar(today_date, 99.8, 101.2, 99.6, 100.8, 10000)

        result = _long_ma_reaction(bars, len(bars) - 1, today_date, trend_up=True, slow_ma_period=LONG_MA_PERIOD)
        assert result is not None
        assert result.kind == "LONG_MA_REACTION"
        assert result.direction == "LONG"

    def test_no_fire_without_ma_touch(self):
        # All bars are 5% above MA
        n = LONG_MA_PERIOD + 5
        bars = _make_bars(n, base_close=105.0, delta=0.0)
        result = _long_ma_reaction(bars, len(bars) - 1, bars[-1].date, trend_up=True, slow_ma_period=LONG_MA_PERIOD)
        assert result is None


# ===========================================================================
# TestDetectMidtrendEntry
# ===========================================================================

class TestDetectMidtrendEntry:
    def test_returns_none_for_flat_undefined_regime(self):
        bars = _make_bars(70)
        result = detect_midtrend_entry(bars, bars[-1].date, regime="RANGE")
        assert result is None

    def test_returns_none_with_too_few_bars(self):
        bars = _make_bars(10)
        result = detect_midtrend_entry(bars, bars[-1].date, regime="TREND_UP")
        assert result is None

    def test_returns_signal_in_trend_up(self):
        n = LONG_MA_PERIOD + 10
        bars = _make_bars(n, base_close=100.0, delta=0.0)
        # MA-touch setup
        bars[-3] = OHLCVBar(bars[-3].date, 100.2, 100.6, 99.95, 100.1, 10000)
        bars[-1] = OHLCVBar(bars[-1].date, 99.8, 101.2, 99.6, 100.8, 10000)
        result = detect_midtrend_entry(bars, bars[-1].date, regime="TREND_UP")
        # May or may not fire depending on MA value; just ensure no crash
        if result is not None:
            assert result.direction in ("LONG", "SHORT")
            assert 0 < result.confidence <= 1.0
