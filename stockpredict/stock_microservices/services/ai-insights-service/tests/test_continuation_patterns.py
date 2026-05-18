"""Unit tests for F-005 Day 2 continuation / bar-pattern detectors.

Synthetic OHLCV fixtures are built analytically so that each pattern is
mathematically embedded.  Negative tests use flat or random-ish data and
assert no false positives at the configured tolerances.

Pattern math under test (Schwager Ch 5, 12):
  Flag        – measured move = pole projected from flag-body breakout
  Pennant     – measured move = pole projected from trendline breakout
  Sym. Tri.   – measured move = height at first bar projected from apex
  Asc. Tri.   – measured move = height projected up from flat resistance
  Desc. Tri.  – measured move = height projected down from flat support
  Gap         – classified as common / breakaway / runaway / exhaustion
  WRD         – bar range > N × ATR; close position sets directional bias
"""
from __future__ import annotations

import math
from typing import List, Sequence

import numpy as np
import pandas as pd
import pytest

from app.services.patterns.continuation import (
    AscendingTriangleDetector,
    DescendingTriangleDetector,
    FlagDetector,
    GapDetector,
    PennantDetector,
    SymmetricalTriangleDetector,
    WideRangingDayDetector,
    run_continuation_detectors,
)


# ---------------------------------------------------------------------------
# Fixture builders (shared with test_reversal_patterns.py helpers)
# ---------------------------------------------------------------------------

def _frame_from_arrays(
    close: np.ndarray,
    high: np.ndarray = None,
    low: np.ndarray = None,
    hl_pad: float = 0.5,
) -> pd.DataFrame:
    if high is None:
        high = close + hl_pad
    if low is None:
        low = close - hl_pad
    return pd.DataFrame({
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.full(len(close), 1000, dtype=int),
    })


def _frame_from_close(close: Sequence[float], hl_pad: float = 0.5) -> pd.DataFrame:
    arr = np.asarray(close, dtype=float)
    return _frame_from_arrays(arr, hl_pad=hl_pad)


def _piecewise_linear(segments: List[tuple]) -> np.ndarray:
    parts: List[np.ndarray] = []
    for i, (start, end, length) in enumerate(segments):
        seg = np.linspace(start, end, length, endpoint=True)
        if i > 0:
            seg = seg[1:]
        parts.append(seg)
    return np.concatenate(parts)


# ---------------------------------------------------------------------------
# Bull / Bear Flag fixtures
# ---------------------------------------------------------------------------

def _bull_flag_close(
    base: float = 100.0,
    n_base: int = 25,
    pole_bars: int = 6,
    pole_height: float = 15.0,
    flag_bars: int = 8,
    flag_retrace: float = 3.0,
) -> np.ndarray:
    return _piecewise_linear([
        (base, base, n_base),
        (base, base + pole_height, pole_bars + 1),
        (base + pole_height, base + pole_height - flag_retrace, flag_bars + 1),
    ])


def _bear_flag_close(
    base: float = 100.0,
    n_base: int = 25,
    pole_bars: int = 6,
    pole_height: float = 15.0,
    flag_bars: int = 8,
    flag_retrace: float = 3.0,
) -> np.ndarray:
    return _piecewise_linear([
        (base, base, n_base),
        (base, base - pole_height, pole_bars + 1),
        (base - pole_height, base - pole_height + flag_retrace, flag_bars + 1),
    ])


# ---------------------------------------------------------------------------
# Pennant fixtures (converging consolidation after a pole)
# ---------------------------------------------------------------------------

def _bull_pennant_frame(
    base: float = 100.0,
    n_base: int = 25,
    pole_bars: int = 6,
    pole_height: float = 15.0,
    pennant_bars: int = 8,
) -> pd.DataFrame:
    """Bull pennant: up-pole then explicit converging high/low channels.

    Pennant body: upper line slopes down (slope_h < 0), lower line slopes up
    (slope_l > 0).  Both converge at the apex so PennantDetector fires.
    """
    pole_top = base + pole_height
    n_total = n_base + pole_bars + pennant_bars
    close_arr = np.zeros(n_total)
    high_arr = np.zeros(n_total)
    low_arr = np.zeros(n_total)

    # Base bars.
    for i in range(n_base):
        close_arr[i] = base
        high_arr[i] = base + 0.5
        low_arr[i] = base - 0.5

    # Pole bars (sharp upward thrust).
    for j in range(pole_bars):
        i = n_base + j
        close_arr[i] = base + (j + 1) * pole_height / pole_bars
        high_arr[i] = close_arr[i] + 0.5
        low_arr[i] = close_arr[i] - 0.5

    # Pennant: upper declines, lower rises → converge at apex.
    ps = n_base + pole_bars
    for j in range(pennant_bars):
        t = j / max(pennant_bars - 1, 1)
        upper = (pole_top - 1.0) + (-3.0) * t   # 114 → 111, slope_h < 0
        lower = (pole_top - 7.0) + 3.0 * t       # 108 → 111, slope_l > 0
        close_arr[ps + j] = (upper + lower) / 2
        high_arr[ps + j] = upper
        low_arr[ps + j] = lower

    return pd.DataFrame({
        "open": close_arr,
        "high": high_arr,
        "low": low_arr,
        "close": close_arr,
        "volume": np.full(n_total, 1000, dtype=int),
    })


# ---------------------------------------------------------------------------
# Triangle fixtures
# ---------------------------------------------------------------------------

def _symmetrical_triangle_close(
    base: float = 100.0, n_bars: int = 80, start_amp: float = 18.0
) -> np.ndarray:
    """Oscillating price with linearly decreasing amplitude — creates
    descending swing highs and ascending swing lows."""
    bars = np.arange(n_bars, dtype=float)
    amplitude = start_amp * (1.0 - bars / n_bars)
    return base + amplitude * np.sin(2 * math.pi * bars / 10)


def _ascending_triangle_close(
    base: float = 100.0, resistance: float = 120.0, n_bars: int = 80
) -> np.ndarray:
    """Flat resistance (swing highs near 120) + rising swing lows."""
    bars = np.arange(n_bars, dtype=float)
    low_line = base + (resistance - base) * bars / n_bars
    amplitude = resistance - low_line  # shrinks as lows approach resistance
    return low_line + amplitude * (np.sin(2 * math.pi * bars / 12) + 1) / 2


def _descending_triangle_close(
    base: float = 80.0, top: float = 120.0, n_bars: int = 80
) -> np.ndarray:
    """Descending swing highs (from top) + flat swing lows near base."""
    bars = np.arange(n_bars, dtype=float)
    high_line = top - (top - base) * bars / n_bars  # falls toward base
    amplitude = high_line - base
    return base + amplitude * (np.sin(2 * math.pi * bars / 12) + 1) / 2


# ---------------------------------------------------------------------------
# Flag tests
# ---------------------------------------------------------------------------

class TestFlagDetector:
    def test_detects_bull_flag(self):
        df = _frame_from_close(_bull_flag_close())
        m = FlagDetector().detect(df)
        assert m is not None and m.found
        assert m.pattern_type == "bullish"
        assert m.confidence > 0.40

    def test_bull_flag_target_above_breakout(self):
        df = _frame_from_close(_bull_flag_close())
        m = FlagDetector().detect(df)
        assert m.measured_move_target > m.neckline

    def test_detects_bear_flag(self):
        df = _frame_from_close(_bear_flag_close())
        m = FlagDetector().detect(df)
        assert m is not None and m.found
        assert m.pattern_type == "bearish"

    def test_bear_flag_target_below_breakout(self):
        df = _frame_from_close(_bear_flag_close())
        m = FlagDetector().detect(df)
        assert m.measured_move_target < m.neckline

    def test_key_bars_ordered(self):
        df = _frame_from_close(_bull_flag_close())
        m = FlagDetector().detect(df)
        assert m.key_bars == sorted(m.key_bars)

    def test_rejects_series_without_pole(self):
        # Flat series — no directional pole.
        df = _frame_from_close(np.full(50, 100.0))
        assert FlagDetector().detect(df) is None

    def test_rejects_short_series(self):
        df = _frame_from_close(np.linspace(100, 102, 10))
        assert FlagDetector().detect(df) is None

    def test_flag_retrace_within_bounds(self):
        df = _frame_from_close(_bull_flag_close(flag_retrace=2.0, pole_height=15.0))
        m = FlagDetector().detect(df)
        assert m is not None
        assert m.details["flag_retrace_pct"] <= FlagDetector().flag_max_retrace_pct


# ---------------------------------------------------------------------------
# Pennant tests
# ---------------------------------------------------------------------------

class TestPennantDetector:
    def test_detects_bull_pennant(self):
        df = _bull_pennant_frame()
        m = PennantDetector().detect(df)
        assert m is not None and m.found
        assert m.pattern_type == "bullish"

    def test_pennant_target_above_breakout_for_bull(self):
        df = _bull_pennant_frame()
        m = PennantDetector().detect(df)
        assert m.measured_move_target > m.neckline

    def test_rejects_flat_data(self):
        df = _frame_from_close(np.full(50, 100.0))
        assert PennantDetector().detect(df) is None

    def test_rejects_too_short(self):
        df = _frame_from_close(np.linspace(100, 115, 10))
        assert PennantDetector().detect(df) is None


# ---------------------------------------------------------------------------
# Symmetrical Triangle tests
# ---------------------------------------------------------------------------

class TestSymmetricalTriangleDetector:
    def test_detects_symmetrical_triangle(self):
        df = _frame_from_close(_symmetrical_triangle_close())
        m = SymmetricalTriangleDetector().detect(df)
        assert m is not None and m.found
        assert m.pattern_type == "neutral"

    def test_sym_triangle_upper_slope_negative(self):
        df = _frame_from_close(_symmetrical_triangle_close())
        m = SymmetricalTriangleDetector().detect(df)
        assert m.details["upper_slope"] < 0

    def test_sym_triangle_lower_slope_positive(self):
        df = _frame_from_close(_symmetrical_triangle_close())
        m = SymmetricalTriangleDetector().detect(df)
        assert m.details["lower_slope"] > 0

    def test_sym_triangle_has_both_targets(self):
        df = _frame_from_close(_symmetrical_triangle_close())
        m = SymmetricalTriangleDetector().detect(df)
        assert m.details["target_up"] > m.neckline
        assert m.details["target_dn"] < m.neckline

    def test_rejects_flat_data(self):
        df = _frame_from_close(np.full(60, 100.0))
        assert SymmetricalTriangleDetector().detect(df) is None


# ---------------------------------------------------------------------------
# Ascending Triangle tests
# ---------------------------------------------------------------------------

class TestAscendingTriangleDetector:
    def test_detects_ascending_triangle(self):
        df = _frame_from_close(_ascending_triangle_close())
        m = AscendingTriangleDetector().detect(df)
        assert m is not None and m.found
        assert m.pattern_type == "bullish"

    def test_ascending_triangle_target_above_resistance(self):
        df = _frame_from_close(_ascending_triangle_close())
        m = AscendingTriangleDetector().detect(df)
        assert m.measured_move_target > m.neckline

    def test_ascending_triangle_upper_slope_near_flat(self):
        df = _frame_from_close(_ascending_triangle_close())
        m = AscendingTriangleDetector().detect(df)
        avg_price = float(df["close"].mean())
        assert abs(m.details["upper_slope"] / avg_price) <= AscendingTriangleDetector().flat_threshold_pct

    def test_ascending_triangle_lower_slope_positive(self):
        df = _frame_from_close(_ascending_triangle_close())
        m = AscendingTriangleDetector().detect(df)
        assert m.details["lower_slope"] > 0

    def test_does_not_fire_on_descending_triangle_data(self):
        df = _frame_from_close(_descending_triangle_close())
        assert AscendingTriangleDetector().detect(df) is None


# ---------------------------------------------------------------------------
# Descending Triangle tests
# ---------------------------------------------------------------------------

class TestDescendingTriangleDetector:
    def test_detects_descending_triangle(self):
        df = _frame_from_close(_descending_triangle_close())
        m = DescendingTriangleDetector().detect(df)
        assert m is not None and m.found
        assert m.pattern_type == "bearish"

    def test_descending_triangle_target_below_support(self):
        df = _frame_from_close(_descending_triangle_close())
        m = DescendingTriangleDetector().detect(df)
        assert m.measured_move_target < m.neckline

    def test_descending_triangle_lower_slope_near_flat(self):
        df = _frame_from_close(_descending_triangle_close())
        m = DescendingTriangleDetector().detect(df)
        avg_price = float(df["close"].mean())
        assert abs(m.details["lower_slope"] / avg_price) <= DescendingTriangleDetector().flat_threshold_pct

    def test_does_not_fire_on_ascending_triangle_data(self):
        df = _frame_from_close(_ascending_triangle_close())
        assert DescendingTriangleDetector().detect(df) is None


# ---------------------------------------------------------------------------
# Gap tests
# ---------------------------------------------------------------------------

def _gap_frame(
    n_pre: int = 25,
    gap_direction: str = "up",
    gap_size: float = 4.0,
    n_post: int = 10,
    fill_after: int = 0,       # 0 = no fill; > 0 = fill at bar fill_after
    trend_slope: float = 0.0,  # per-bar close increment for pre-gap bars
) -> pd.DataFrame:
    """Build a frame with a gap at bar n_pre.

    fill_after: if > 0, the close at n_pre + fill_after goes back inside the
    gap so the gap is classified as filled.
    """
    closes = np.zeros(n_pre + 1 + n_post)
    # Pre-gap bars with optional trend.
    for i in range(n_pre):
        closes[i] = 100.0 + i * trend_slope
    pre_last = closes[n_pre - 1]

    # Gap bar.
    if gap_direction == "up":
        closes[n_pre] = pre_last + gap_size + 1.0  # close well above gap
    else:
        closes[n_pre] = pre_last - gap_size - 1.0

    # Post-gap bars.
    for j in range(n_post):
        idx = n_pre + 1 + j
        closes[idx] = closes[n_pre]  # flat after gap

    # Build explicit high/low so the gap is in the OHLC (no hl_pad overlap).
    high = closes + 0.5
    low = closes - 0.5

    # Enforce gap: bar n_pre's low must be above bar n_pre-1's high (gap up).
    if gap_direction == "up":
        low[n_pre] = pre_last + gap_size       # gap bottom
        high[n_pre] = pre_last + gap_size + 2  # gap top
        closes[n_pre] = pre_last + gap_size + 1
    else:
        high[n_pre] = pre_last - gap_size
        low[n_pre] = pre_last - gap_size - 2
        closes[n_pre] = pre_last - gap_size - 1

    # Simulate fill: lower a post-gap close back into the gap.
    # high[fill_idx] must reach the previous bar's low so no NEW gap is created
    # between bar fill_idx-1 and bar fill_idx (scanner goes right-to-left and
    # would otherwise find that spurious gap first).
    if fill_after > 0 and fill_after < n_post:
        fill_idx = n_pre + fill_after
        if gap_direction == "up":
            closes[fill_idx] = pre_last + 0.5   # back below gap bottom
            low[fill_idx] = pre_last + 0.3
            high[fill_idx] = max(low[fill_idx - 1], pre_last + 1.0)
        else:
            closes[fill_idx] = pre_last - 0.5
            high[fill_idx] = pre_last - 0.3
            low[fill_idx] = min(high[fill_idx - 1], pre_last - 1.0)

    return pd.DataFrame({
        "open": closes,
        "high": high,
        "low": low,
        "close": closes,
        "volume": np.full(len(closes), 1000, dtype=int),
    })


class TestGapDetector:
    def test_detects_gap_up(self):
        df = _gap_frame(gap_direction="up", gap_size=3.0)
        m = GapDetector().detect(df)
        assert m is not None and m.found
        assert m.details["gap_direction"] == "up"

    def test_detects_gap_down(self):
        df = _gap_frame(gap_direction="down", gap_size=3.0)
        m = GapDetector().detect(df)
        assert m is not None and m.found
        assert m.details["gap_direction"] == "down"

    def test_common_gap_fills_quickly(self):
        df = _gap_frame(gap_direction="up", gap_size=3.0, fill_after=2)
        m = GapDetector().detect(df)
        assert m is not None
        assert m.details["gap_type"] == "common"
        assert m.details["filled"] is True

    def test_runaway_gap_in_uptrend_not_filled(self):
        # Moderate uptrend before gap; gap not filled.
        df = _gap_frame(gap_direction="up", gap_size=3.0, trend_slope=0.3, fill_after=0)
        m = GapDetector().detect(df)
        assert m is not None
        assert m.details["gap_type"] in ("runaway", "breakaway")

    def test_breakaway_gap_counter_to_downtrend(self):
        # Prior downtrend + gap UP → breakaway (counter-trend).
        df = _gap_frame(gap_direction="up", gap_size=3.0, trend_slope=-0.4, fill_after=0)
        m = GapDetector().detect(df)
        assert m is not None
        assert m.details["gap_type"] == "breakaway"

    def test_exhaustion_gap_fills_after_long_trend(self):
        # Large prior uptrend + gap up + fills within 3 bars → exhaustion.
        df = _gap_frame(gap_direction="up", gap_size=3.0, trend_slope=0.8, fill_after=2)
        m = GapDetector().detect(df)
        assert m is not None
        # With large trend_slope, this should classify as exhaustion.
        # trend_atr_units = |slope * n_pre| / ATR; ATR ≈ 1-2 for 0.5 hl_pad.
        # 0.8 * 25 = 20 >> exhaustion_move_atr=5 → exhaustion.
        assert m.details["gap_type"] == "exhaustion"

    def test_no_gap_returns_none(self):
        # Smooth trending series — no price gap.
        df = _frame_from_close(np.linspace(100, 115, 40))
        assert GapDetector().detect(df) is None

    def test_rejects_short_series(self):
        df = _frame_from_close(np.linspace(100, 105, 10))
        assert GapDetector().detect(df) is None


# ---------------------------------------------------------------------------
# Wide-Ranging Day tests
# ---------------------------------------------------------------------------

def _wrd_frame(
    n_bars: int = 30,
    wrd_bar: int = -1,       # bar index of WRD (negative → from end)
    wrd_range: float = 10.0, # high - low for that bar
    close_pct: float = 0.8,  # close position within range (0=low end, 1=high end)
    normal_hl_pad: float = 1.0,
) -> pd.DataFrame:
    """Build a frame with one WRD bar and otherwise small-range bars."""
    close_arr = np.full(n_bars, 100.0)
    high_arr = close_arr + normal_hl_pad
    low_arr = close_arr - normal_hl_pad

    idx = wrd_bar if wrd_bar >= 0 else n_bars + wrd_bar
    low_arr[idx] = close_arr[idx] - wrd_range / 2
    high_arr[idx] = close_arr[idx] + wrd_range / 2
    close_arr[idx] = low_arr[idx] + wrd_range * close_pct

    return pd.DataFrame({
        "open": close_arr,
        "high": high_arr,
        "low": low_arr,
        "close": close_arr,
        "volume": np.full(n_bars, 1000, dtype=int),
    })


class TestWideRangingDayDetector:
    def test_detects_bullish_wrd(self):
        # close_pct=0.8 → close in upper half → bullish.
        df = _wrd_frame(wrd_bar=-2, wrd_range=10.0, close_pct=0.8)
        m = WideRangingDayDetector(atr_multiple=2.0).detect(df)
        assert m is not None and m.found
        assert m.pattern_type == "bullish"

    def test_detects_bearish_wrd(self):
        df = _wrd_frame(wrd_bar=-2, wrd_range=10.0, close_pct=0.2)
        m = WideRangingDayDetector(atr_multiple=2.0).detect(df)
        assert m is not None and m.found
        assert m.pattern_type == "bearish"

    def test_bullish_wrd_target_above_close(self):
        df = _wrd_frame(wrd_bar=-2, wrd_range=10.0, close_pct=0.8)
        m = WideRangingDayDetector(atr_multiple=2.0).detect(df)
        assert m.measured_move_target > m.neckline

    def test_bearish_wrd_target_below_close(self):
        df = _wrd_frame(wrd_bar=-2, wrd_range=10.0, close_pct=0.2)
        m = WideRangingDayDetector(atr_multiple=2.0).detect(df)
        assert m.measured_move_target < m.neckline

    def test_no_wrd_when_all_bars_normal(self):
        df = _frame_from_close(np.full(30, 100.0))
        # hl_pad=0.5 → range=1.0; ATR≈1.0; 1.0 < 2.0 * 1.0 = 2.0 → no WRD.
        assert WideRangingDayDetector(atr_multiple=2.0).detect(df) is None

    def test_rejects_short_series(self):
        df = _frame_from_close(np.linspace(100, 102, 5))
        assert WideRangingDayDetector().detect(df) is None

    def test_wrd_bar_index_in_key_bars(self):
        wrd_idx = 25  # absolute 0-indexed bar
        df = _wrd_frame(n_bars=30, wrd_bar=wrd_idx, wrd_range=10.0, close_pct=0.8)
        m = WideRangingDayDetector(atr_multiple=2.0).detect(df)
        assert m is not None
        assert wrd_idx in m.key_bars


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

class TestContinuationAggregator:
    def test_run_returns_list_on_flat_data(self):
        df = _frame_from_close(np.full(80, 100.0))
        results = run_continuation_detectors(df)
        assert isinstance(results, list)

    def test_run_finds_flag_in_flag_data(self):
        df = _frame_from_close(_bull_flag_close())
        results = run_continuation_detectors(df)
        names = [r.pattern_name for r in results]
        assert "Flag" in names

    def test_run_finds_wrd_in_wrd_data(self):
        df = _wrd_frame(wrd_bar=-2, wrd_range=10.0)
        results = run_continuation_detectors(df)
        names = [r.pattern_name for r in results]
        assert "Wide-Ranging Day" in names

    def test_run_all_patterns_have_standard_shape(self):
        df = _frame_from_close(_bull_flag_close())
        for m in run_continuation_detectors(df):
            assert isinstance(m.pattern_name, str)
            assert isinstance(m.confidence, float)
            assert 0.0 <= m.confidence <= 1.0
            assert isinstance(m.key_bars, list)
            assert m.found is True

    def test_run_sorted_newest_first(self):
        df = _frame_from_close(_bull_flag_close())
        results = run_continuation_detectors(df)
        if len(results) >= 2:
            for a, b in zip(results, results[1:]):
                assert (a.key_bars[-1] if a.key_bars else 0) >= (b.key_bars[-1] if b.key_bars else 0)
