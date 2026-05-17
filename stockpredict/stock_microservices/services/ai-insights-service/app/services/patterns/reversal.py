"""Reversal-pattern detectors (Schwager Ch 5).

Day 1 of F-005. Four classical reversal patterns:

  * Head & Shoulders Top      — bearish, three peaks with the middle highest
  * Inverse Head & Shoulders  — bullish, three troughs with the middle lowest
  * Double Top                — bearish, two peaks at ~the same price
  * Double Bottom             — bullish, two troughs at ~the same price

All detectors share the same fractal-swing scaffolding from PatternDetector
and emit a `PatternMatch` with the measured-move target so the decision
helper can lift the projected price straight into its target_module
(Ch 10).
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd

from app.services.patterns.base import PatternDetector, PatternMatch


# ---------------------------------------------------------------------------
# Head & Shoulders (top, bearish)
# ---------------------------------------------------------------------------

class HeadAndShouldersDetector(PatternDetector):
    """Classical H&S top.

    Structure (left to right):
        LS  H  RS    — three highs, H is the highest, LS & RS at similar price
        T1, T2       — the two intervening troughs form the neckline

    Confirmation (not enforced here — left to the decision helper's
    confirmation_layer): close below the neckline.

    Measured move: (H - neckline) projected DOWN from neckline.
    """

    pattern_name = "Head and Shoulders"
    pattern_type = "bearish"

    def __init__(
        self,
        swing_window: int = 3,
        shoulder_tolerance_pct: float = 0.05,
        min_head_prominence_pct: float = 0.02,
    ):
        self.swing_window = swing_window
        self.shoulder_tolerance_pct = shoulder_tolerance_pct
        # Head must be at least this % above the higher shoulder; prevents
        # three near-equal peaks (which would be a triple-top, not H&S).
        self.min_head_prominence_pct = min_head_prominence_pct

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        ok, _ = self._validate_ohlc(ohlc, min_bars=self.swing_window * 6 + 1)
        if not ok:
            return None

        highs = ohlc["high"].to_numpy(dtype=float)
        lows = ohlc["low"].to_numpy(dtype=float)

        pivot_idx = self._find_swing_highs(highs, self.swing_window)
        if len(pivot_idx) < 3:
            return None

        # Scan the three most recent swing highs for an H&S triple. We walk
        # from the right so the most recent (and therefore actionable)
        # formation wins on overlap.
        for i in range(len(pivot_idx) - 1, 1, -1):
            rs = pivot_idx[i]
            head = pivot_idx[i - 1]
            ls = pivot_idx[i - 2]

            ls_h, head_h, rs_h = highs[ls], highs[head], highs[rs]

            # Head must dominate both shoulders.
            shoulder_max = max(ls_h, rs_h)
            if head_h <= shoulder_max * (1 + self.min_head_prominence_pct):
                continue
            if not self._within_tolerance(ls_h, rs_h, self.shoulder_tolerance_pct):
                continue

            t1_idx = self._min_idx_between(lows, ls, head)
            t2_idx = self._min_idx_between(lows, head, rs)
            t1_p, t2_p = lows[t1_idx], lows[t2_idx]

            # Project the neckline forward to the right-shoulder bar so the
            # measured move is anchored on the line, not just t2.
            neckline_at_rs = self._line_at(t1_idx, t1_p, t2_idx, t2_p, rs)
            head_height = head_h - neckline_at_rs
            if head_height <= 0:
                continue

            target = neckline_at_rs - head_height

            # Confidence: shoulder symmetry + head prominence. Both are
            # 0..1 contributions, weighted equally.
            symmetry = 1.0 - abs(ls_h - rs_h) / max(ls_h, rs_h)
            prominence = min(1.0, (head_h - shoulder_max) / shoulder_max / 0.1)
            confidence = round(min(0.95, 0.4 + 0.3 * symmetry + 0.3 * prominence), 3)

            return PatternMatch(
                pattern_name=self.pattern_name,
                pattern_type=self.pattern_type,
                found=True,
                confidence=confidence,
                key_bars=[ls, t1_idx, head, t2_idx, rs],
                measured_move_target=float(round(target, 4)),
                neckline=float(round(neckline_at_rs, 4)),
                details={
                    "left_shoulder_price": float(ls_h),
                    "head_price": float(head_h),
                    "right_shoulder_price": float(rs_h),
                    "head_height": float(round(head_height, 4)),
                },
            )

        return None


# ---------------------------------------------------------------------------
# Inverse Head & Shoulders (bottom, bullish)
# ---------------------------------------------------------------------------

class InverseHeadAndShouldersDetector(PatternDetector):
    """Mirror of H&S top: three troughs with the middle lowest. Measured
    move = (neckline - head) projected UP from neckline."""

    pattern_name = "Inverse Head and Shoulders"
    pattern_type = "bullish"

    def __init__(
        self,
        swing_window: int = 3,
        shoulder_tolerance_pct: float = 0.05,
        min_head_prominence_pct: float = 0.02,
    ):
        self.swing_window = swing_window
        self.shoulder_tolerance_pct = shoulder_tolerance_pct
        self.min_head_prominence_pct = min_head_prominence_pct

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        ok, _ = self._validate_ohlc(ohlc, min_bars=self.swing_window * 6 + 1)
        if not ok:
            return None

        highs = ohlc["high"].to_numpy(dtype=float)
        lows = ohlc["low"].to_numpy(dtype=float)

        pivot_idx = self._find_swing_lows(lows, self.swing_window)
        if len(pivot_idx) < 3:
            return None

        for i in range(len(pivot_idx) - 1, 1, -1):
            rs = pivot_idx[i]
            head = pivot_idx[i - 1]
            ls = pivot_idx[i - 2]

            ls_l, head_l, rs_l = lows[ls], lows[head], lows[rs]

            shoulder_min = min(ls_l, rs_l)
            if head_l >= shoulder_min * (1 - self.min_head_prominence_pct):
                continue
            if not self._within_tolerance(ls_l, rs_l, self.shoulder_tolerance_pct):
                continue

            t1_idx = self._max_idx_between(highs, ls, head)
            t2_idx = self._max_idx_between(highs, head, rs)
            t1_p, t2_p = highs[t1_idx], highs[t2_idx]

            neckline_at_rs = self._line_at(t1_idx, t1_p, t2_idx, t2_p, rs)
            head_depth = neckline_at_rs - head_l
            if head_depth <= 0:
                continue

            target = neckline_at_rs + head_depth

            symmetry = 1.0 - abs(ls_l - rs_l) / max(ls_l, rs_l)
            prominence = min(1.0, (shoulder_min - head_l) / shoulder_min / 0.1)
            confidence = round(min(0.95, 0.4 + 0.3 * symmetry + 0.3 * prominence), 3)

            return PatternMatch(
                pattern_name=self.pattern_name,
                pattern_type=self.pattern_type,
                found=True,
                confidence=confidence,
                key_bars=[ls, t1_idx, head, t2_idx, rs],
                measured_move_target=float(round(target, 4)),
                neckline=float(round(neckline_at_rs, 4)),
                details={
                    "left_shoulder_price": float(ls_l),
                    "head_price": float(head_l),
                    "right_shoulder_price": float(rs_l),
                    "head_depth": float(round(head_depth, 4)),
                },
            )

        return None


# ---------------------------------------------------------------------------
# Double Top (bearish)
# ---------------------------------------------------------------------------

class DoubleTopDetector(PatternDetector):
    """Two peaks within `peak_tolerance_pct` and separated by at least
    `min_peak_separation` bars, with a measurable trough between them.

    Measured move: (peak - neckline) projected DOWN from neckline, where
    neckline = the trough price.
    """

    pattern_name = "Double Top"
    pattern_type = "bearish"

    def __init__(
        self,
        swing_window: int = 3,
        peak_tolerance_pct: float = 0.03,
        min_peak_separation: int = 5,
        min_trough_depth_pct: float = 0.03,
    ):
        self.swing_window = swing_window
        self.peak_tolerance_pct = peak_tolerance_pct
        self.min_peak_separation = min_peak_separation
        # Trough between the two peaks must dip at least this % below the
        # lower peak — otherwise the pattern is too shallow to act on.
        self.min_trough_depth_pct = min_trough_depth_pct

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        ok, _ = self._validate_ohlc(ohlc, min_bars=self.swing_window * 4 + 1)
        if not ok:
            return None

        highs = ohlc["high"].to_numpy(dtype=float)
        lows = ohlc["low"].to_numpy(dtype=float)

        pivot_idx = self._find_swing_highs(highs, self.swing_window)
        if len(pivot_idx) < 2:
            return None

        # Walk newest-first.
        for i in range(len(pivot_idx) - 1, 0, -1):
            p2 = pivot_idx[i]
            p1 = pivot_idx[i - 1]
            if p2 - p1 < self.min_peak_separation:
                continue

            p1_h, p2_h = highs[p1], highs[p2]
            if not self._within_tolerance(p1_h, p2_h, self.peak_tolerance_pct):
                continue

            trough_idx = self._min_idx_between(lows, p1, p2)
            trough = lows[trough_idx]
            lower_peak = min(p1_h, p2_h)
            depth = (lower_peak - trough) / lower_peak
            if depth < self.min_trough_depth_pct:
                continue

            height = lower_peak - trough
            target = trough - height

            similarity = 1.0 - abs(p1_h - p2_h) / max(p1_h, p2_h)
            depth_score = min(1.0, depth / 0.10)
            confidence = round(min(0.95, 0.45 + 0.3 * similarity + 0.25 * depth_score), 3)

            return PatternMatch(
                pattern_name=self.pattern_name,
                pattern_type=self.pattern_type,
                found=True,
                confidence=confidence,
                key_bars=[p1, trough_idx, p2],
                measured_move_target=float(round(target, 4)),
                neckline=float(round(trough, 4)),
                details={
                    "first_peak_price": float(p1_h),
                    "second_peak_price": float(p2_h),
                    "trough_price": float(trough),
                    "pattern_height": float(round(height, 4)),
                },
            )

        return None


# ---------------------------------------------------------------------------
# Double Bottom (bullish)
# ---------------------------------------------------------------------------

class DoubleBottomDetector(PatternDetector):
    """Mirror of Double Top. Measured move = (neckline - trough) projected
    UP from neckline, where neckline = the intervening peak."""

    pattern_name = "Double Bottom"
    pattern_type = "bullish"

    def __init__(
        self,
        swing_window: int = 3,
        trough_tolerance_pct: float = 0.03,
        min_trough_separation: int = 5,
        min_peak_height_pct: float = 0.03,
    ):
        self.swing_window = swing_window
        self.trough_tolerance_pct = trough_tolerance_pct
        self.min_trough_separation = min_trough_separation
        self.min_peak_height_pct = min_peak_height_pct

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        ok, _ = self._validate_ohlc(ohlc, min_bars=self.swing_window * 4 + 1)
        if not ok:
            return None

        highs = ohlc["high"].to_numpy(dtype=float)
        lows = ohlc["low"].to_numpy(dtype=float)

        pivot_idx = self._find_swing_lows(lows, self.swing_window)
        if len(pivot_idx) < 2:
            return None

        for i in range(len(pivot_idx) - 1, 0, -1):
            t2 = pivot_idx[i]
            t1 = pivot_idx[i - 1]
            if t2 - t1 < self.min_trough_separation:
                continue

            t1_l, t2_l = lows[t1], lows[t2]
            if not self._within_tolerance(t1_l, t2_l, self.trough_tolerance_pct):
                continue

            peak_idx = self._max_idx_between(highs, t1, t2)
            peak = highs[peak_idx]
            higher_trough = max(t1_l, t2_l)
            height_pct = (peak - higher_trough) / higher_trough
            if height_pct < self.min_peak_height_pct:
                continue

            height = peak - higher_trough
            target = peak + height

            similarity = 1.0 - abs(t1_l - t2_l) / max(t1_l, t2_l)
            height_score = min(1.0, height_pct / 0.10)
            confidence = round(min(0.95, 0.45 + 0.3 * similarity + 0.25 * height_score), 3)

            return PatternMatch(
                pattern_name=self.pattern_name,
                pattern_type=self.pattern_type,
                found=True,
                confidence=confidence,
                key_bars=[t1, peak_idx, t2],
                measured_move_target=float(round(target, 4)),
                neckline=float(round(peak, 4)),
                details={
                    "first_trough_price": float(t1_l),
                    "second_trough_price": float(t2_l),
                    "peak_price": float(peak),
                    "pattern_height": float(round(height, 4)),
                },
            )

        return None


# ---------------------------------------------------------------------------
# Aggregator helper used by the API layer
# ---------------------------------------------------------------------------

REVERSAL_DETECTORS: List[PatternDetector] = [
    HeadAndShouldersDetector(),
    InverseHeadAndShouldersDetector(),
    DoubleTopDetector(),
    DoubleBottomDetector(),
]


def run_reversal_detectors(ohlc: pd.DataFrame) -> List[PatternMatch]:
    """Run every reversal detector against `ohlc`; skip Nones. The output
    is a list of *found* PatternMatch objects, newest-pattern-first by
    position of the right-most key bar — so callers iterating top-down
    see the most actionable pattern first."""
    results: List[PatternMatch] = []
    for det in REVERSAL_DETECTORS:
        try:
            m = det.detect(ohlc)
            if m is not None and m.found:
                results.append(m)
        except Exception:  # noqa: BLE001 — a detector bug shouldn't 500 the API
            continue
    results.sort(key=lambda m: (m.key_bars[-1] if m.key_bars else 0), reverse=True)
    return results
