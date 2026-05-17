"""Unit tests for the F-005 Day 1 reversal-pattern detectors.

Each detector is exercised against deterministic synthetic OHLCV that
mathematically embeds the pattern (peaks at specified bars, troughs at
specified prices). Negative tests use flat / random-ish data and assert
no false positives at the configured tolerances.

Pattern math under test (Schwager Ch 5):
  H&S top    — measured move = neckline - (head - neckline)
  Inv H&S    — measured move = neckline + (neckline - head)
  Double Top — measured move = trough - (peak - trough)
  Double Bot — measured move = peak + (peak - trough)
"""
from __future__ import annotations

from typing import List, Sequence

import numpy as np
import pandas as pd
import pytest

from app.services.patterns.base import PatternDetector, PatternMatch
from app.services.patterns.reversal import (
    DoubleBottomDetector,
    DoubleTopDetector,
    HeadAndShouldersDetector,
    InverseHeadAndShouldersDetector,
    run_reversal_detectors,
)


# ---------------------------------------------------------------------------
# Synthetic OHLCV fixture builders
# ---------------------------------------------------------------------------

def _frame_from_close(close: Sequence[float], *, hl_pad: float = 0.5) -> pd.DataFrame:
    """Build an OHLC frame from a close-series. high/low pad by `hl_pad`
    so swing detection on `high`/`low` mirrors the close pivots."""
    close_arr = np.asarray(close, dtype=float)
    return pd.DataFrame({
        "open": close_arr,
        "high": close_arr + hl_pad,
        "low": close_arr - hl_pad,
        "close": close_arr,
        "volume": np.full(close_arr.size, 1000, dtype=int),
    })


def _piecewise_linear(segments: List[tuple]) -> np.ndarray:
    """Concatenate (start_price, end_price, length) segments into a single
    linear series. Used to draw shoulders / heads / troughs analytically."""
    parts: List[np.ndarray] = []
    for i, (start, end, length) in enumerate(segments):
        # Skip the duplicate junction point after the first segment so
        # adjacent peaks/troughs land on a single bar instead of two.
        seg = np.linspace(start, end, length, endpoint=True)
        if i > 0:
            seg = seg[1:]
        parts.append(seg)
    return np.concatenate(parts)


def _hs_top_close(
    base: float = 100.0,
    shoulder_height: float = 10.0,
    head_height: float = 18.0,
    leg: int = 8,
) -> np.ndarray:
    """Synthetic H&S top close-series.

    Layout (peaks at bars 8, 24, 40 with leg=8):
        0 -> shoulder (base+sh) -> trough1 -> head -> trough2 -> shoulder -> tail
    """
    return _piecewise_linear([
        (base, base + shoulder_height, leg + 1),                   # rise to LS
        (base + shoulder_height, base, leg + 1),                   # fall to T1
        (base, base + head_height, leg + 1),                       # rise to head
        (base + head_height, base, leg + 1),                       # fall to T2
        (base, base + shoulder_height, leg + 1),                   # rise to RS
        (base + shoulder_height, base - 3, leg + 1),               # fall (post-pattern)
    ])


def _inv_hs_close(
    base: float = 100.0,
    shoulder_depth: float = 10.0,
    head_depth: float = 18.0,
    leg: int = 8,
) -> np.ndarray:
    return _piecewise_linear([
        (base, base - shoulder_depth, leg + 1),
        (base - shoulder_depth, base, leg + 1),
        (base, base - head_depth, leg + 1),
        (base - head_depth, base, leg + 1),
        (base, base - shoulder_depth, leg + 1),
        (base - shoulder_depth, base + 3, leg + 1),
    ])


def _double_top_close(
    base: float = 100.0,
    peak_height: float = 15.0,
    trough_depth: float = 8.0,
    leg: int = 8,
) -> np.ndarray:
    peak = base + peak_height
    trough = peak - trough_depth
    return _piecewise_linear([
        (base, peak, leg + 1),
        (peak, trough, leg + 1),
        (trough, peak, leg + 1),
        (peak, base - 3, leg + 1),
    ])


def _double_bottom_close(
    base: float = 100.0,
    trough_depth: float = 15.0,
    peak_height: float = 8.0,
    leg: int = 8,
) -> np.ndarray:
    trough = base - trough_depth
    peak = trough + peak_height
    return _piecewise_linear([
        (base, trough, leg + 1),
        (trough, peak, leg + 1),
        (peak, trough, leg + 1),
        (trough, base + 3, leg + 1),
    ])


# ---------------------------------------------------------------------------
# PatternDetector.base helpers
# ---------------------------------------------------------------------------

class TestBaseHelpers:
    def test_within_tolerance_true_at_3pct_when_diff_is_2pct(self):
        assert PatternDetector._within_tolerance(100.0, 102.0, 0.03)

    def test_within_tolerance_false_at_3pct_when_diff_is_5pct(self):
        assert not PatternDetector._within_tolerance(100.0, 105.0, 0.03)

    def test_within_tolerance_handles_equal_values(self):
        assert PatternDetector._within_tolerance(50.0, 50.0, 0.0)

    def test_within_tolerance_handles_zero_mean(self):
        # Defensive — degenerate input shouldn't divide by zero.
        assert PatternDetector._within_tolerance(0.0, 0.0, 0.05)

    def test_line_at_interpolates_correctly(self):
        # Line through (10, 100) -> (30, 120) at x=20 should be 110.
        assert PatternDetector._line_at(10, 100.0, 30, 120.0, 20) == pytest.approx(110.0)

    def test_line_at_returns_y1_when_x1_eq_x2(self):
        # Defensive: vertical line is degenerate; fall back to y1.
        assert PatternDetector._line_at(5, 50.0, 5, 80.0, 7) == 50.0

    def test_find_swing_highs_picks_local_max(self):
        # Need >= window bars of clearance on each side of the candidate.
        prices = np.array([1, 2, 3, 5, 3, 2, 1, 2, 4, 2, 1, 0, 1], dtype=float)
        highs = PatternDetector._find_swing_highs(prices, window=3)
        # Bar 3 (value 5) and bar 8 (value 4) are both fractal highs.
        assert 3 in highs
        assert 8 in highs

    def test_find_swing_lows_picks_local_min(self):
        prices = np.array([5, 4, 3, 1, 3, 4, 5, 4, 2, 4, 5, 6, 5], dtype=float)
        lows = PatternDetector._find_swing_lows(prices, window=3)
        assert 3 in lows
        assert 8 in lows


# ---------------------------------------------------------------------------
# Head & Shoulders top
# ---------------------------------------------------------------------------

class TestHeadAndShoulders:
    def test_detects_textbook_h_and_s(self):
        df = _frame_from_close(_hs_top_close())
        match = HeadAndShouldersDetector().detect(df)
        assert match is not None
        assert match.found
        assert match.pattern_type == "bearish"
        assert match.confidence > 0.6

    def test_measured_move_target_below_neckline(self):
        df = _frame_from_close(_hs_top_close())
        match = HeadAndShouldersDetector().detect(df)
        # H&S top projects DOWN by head height. The neckline sits near the
        # trough lows (~99.5 with hl_pad=0.5), the head at ~118.5; target
        # should clear at least 17 below the neckline.
        assert match.measured_move_target < match.neckline
        assert match.neckline - match.measured_move_target == pytest.approx(
            match.details["head_height"], rel=1e-3
        )

    def test_key_bars_in_increasing_order(self):
        df = _frame_from_close(_hs_top_close())
        match = HeadAndShouldersDetector().detect(df)
        assert match.key_bars == sorted(match.key_bars)
        # Five anchors: LS, T1, head, T2, RS.
        assert len(match.key_bars) == 5

    def test_rejects_when_head_not_above_shoulders(self):
        # Three roughly equal peaks (~110) — a triple-top, not an H&S.
        close = _piecewise_linear([
            (100, 110, 9), (110, 100, 9), (100, 110, 9),
            (110, 100, 9), (100, 110, 9), (110, 97, 9),
        ])
        df = _frame_from_close(close)
        assert HeadAndShouldersDetector().detect(df) is None

    def test_rejects_when_shoulders_asymmetric(self):
        # LS at 110, RS at 130 — far outside the 5% shoulder tolerance.
        close = _piecewise_linear([
            (100, 110, 9),  # LS
            (110, 100, 9),  # T1
            (100, 140, 9),  # head
            (140, 100, 9),  # T2
            (100, 130, 9),  # RS (too tall vs LS=110)
            (130, 95, 9),
        ])
        df = _frame_from_close(close)
        assert HeadAndShouldersDetector().detect(df) is None

    def test_rejects_short_series(self):
        df = _frame_from_close(np.linspace(100, 105, 5))
        assert HeadAndShouldersDetector().detect(df) is None


# ---------------------------------------------------------------------------
# Inverse Head & Shoulders
# ---------------------------------------------------------------------------

class TestInverseHeadAndShoulders:
    def test_detects_textbook_inv_h_and_s(self):
        df = _frame_from_close(_inv_hs_close())
        match = InverseHeadAndShouldersDetector().detect(df)
        assert match is not None
        assert match.found
        assert match.pattern_type == "bullish"

    def test_measured_move_above_neckline(self):
        df = _frame_from_close(_inv_hs_close())
        match = InverseHeadAndShouldersDetector().detect(df)
        # Inverse H&S projects UP by head depth.
        assert match.measured_move_target > match.neckline
        assert match.measured_move_target - match.neckline == pytest.approx(
            match.details["head_depth"], rel=1e-3
        )

    def test_normal_h_and_s_does_not_fire_inverse_detector(self):
        df = _frame_from_close(_hs_top_close())
        assert InverseHeadAndShouldersDetector().detect(df) is None


# ---------------------------------------------------------------------------
# Double Top
# ---------------------------------------------------------------------------

class TestDoubleTop:
    def test_detects_textbook_double_top(self):
        df = _frame_from_close(_double_top_close())
        match = DoubleTopDetector().detect(df)
        assert match is not None
        assert match.pattern_type == "bearish"
        assert len(match.key_bars) == 3  # p1, trough, p2

    def test_measured_move_target_below_trough(self):
        df = _frame_from_close(_double_top_close())
        match = DoubleTopDetector().detect(df)
        assert match.measured_move_target < match.neckline  # neckline = trough
        assert match.neckline - match.measured_move_target == pytest.approx(
            match.details["pattern_height"], rel=1e-3
        )

    def test_rejects_when_peaks_too_far_apart_in_price(self):
        # p1 at 115, p2 at 130 — outside the 3% peak_tolerance default.
        close = _piecewise_linear([
            (100, 115, 9),
            (115, 105, 9),
            (105, 130, 9),
            (130, 95, 9),
        ])
        df = _frame_from_close(close)
        assert DoubleTopDetector().detect(df) is None

    def test_rejects_when_trough_too_shallow(self):
        # Peaks at 115, trough at 114 — depth ~0.9%, below 3% threshold.
        close = _piecewise_linear([
            (100, 115, 9),
            (115, 114, 9),
            (114, 115, 9),
            (115, 100, 9),
        ])
        df = _frame_from_close(close)
        assert DoubleTopDetector().detect(df) is None

    def test_rejects_when_peaks_too_close_in_time(self):
        det = DoubleTopDetector(min_peak_separation=10)
        # Peaks 4 bars apart — below the 10-bar floor.
        close = _piecewise_linear([
            (100, 115, 3),  # p1 at bar 2
            (115, 110, 3),
            (110, 115, 3),  # p2 at bar 8 (separation=6, still below 10)
            (115, 100, 9),
        ])
        df = _frame_from_close(close)
        assert det.detect(df) is None


# ---------------------------------------------------------------------------
# Double Bottom
# ---------------------------------------------------------------------------

class TestDoubleBottom:
    def test_detects_textbook_double_bottom(self):
        df = _frame_from_close(_double_bottom_close())
        match = DoubleBottomDetector().detect(df)
        assert match is not None
        assert match.pattern_type == "bullish"

    def test_measured_move_above_peak(self):
        df = _frame_from_close(_double_bottom_close())
        match = DoubleBottomDetector().detect(df)
        # Neckline = intervening peak. Target projects UP by pattern height.
        assert match.measured_move_target > match.neckline
        assert match.measured_move_target - match.neckline == pytest.approx(
            match.details["pattern_height"], rel=1e-3
        )

    def test_does_not_fire_on_double_top_shape(self):
        df = _frame_from_close(_double_top_close())
        assert DoubleBottomDetector().detect(df) is None


# ---------------------------------------------------------------------------
# Aggregator + no-pattern paths
# ---------------------------------------------------------------------------

class TestAggregator:
    def test_run_reversal_detectors_returns_empty_on_flat_data(self):
        # Constant prices — no swing pivots at all.
        df = _frame_from_close(np.full(80, 100.0))
        assert run_reversal_detectors(df) == []

    def test_run_reversal_detectors_finds_double_top(self):
        df = _frame_from_close(_double_top_close())
        results = run_reversal_detectors(df)
        names = [r.pattern_name for r in results]
        assert "Double Top" in names

    def test_run_reversal_detectors_sorted_newest_first(self):
        # Build a series where Double Top appears late, after a Double
        # Bottom earlier. The Double Top's right-most key bar should sort
        # ahead of the Double Bottom's.
        early = _double_bottom_close(leg=6)
        late = _double_top_close(leg=6)
        # Stitch them so the late pattern starts at a price comparable to
        # the end of the early one.
        stitched = np.concatenate([early, late + (early[-1] - late[0])])
        df = _frame_from_close(stitched)
        results = run_reversal_detectors(df)
        if len(results) >= 2:
            assert results[0].key_bars[-1] >= results[1].key_bars[-1]

    def test_run_reversal_detectors_handles_short_input(self):
        # Below every detector's min_bars guard — should return [] cleanly.
        df = _frame_from_close(np.linspace(100, 102, 5))
        assert run_reversal_detectors(df) == []
