"""Shared base for chart-pattern detectors (F-005, Schwager Ch 5/11/12).

Every detector implements `.detect(ohlc) -> Optional[PatternMatch]`. The
caller (`InsightsService` aggregator + future decision-helper-service) treats
detectors as interchangeable behind this interface, so adding a new pattern
in Day 2 / Day 3 is local to a single file.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class PatternMatch:
    """Uniform detector result.

    `measured_move_target` is the price the pattern projects to (Schwager
    Ch 5): for bearish patterns it is below the breakout line, for bullish
    patterns above. Callers use it as a first-cut profit target (Ch 10) and
    as the reference price for the failed-signal detector (Ch 11, F-006).
    """
    pattern_name: str
    pattern_type: str                    # "bullish" | "bearish"
    found: bool
    confidence: float                    # 0..1
    key_bars: List[int] = field(default_factory=list)
    measured_move_target: Optional[float] = None
    neckline: Optional[float] = None     # breakout level for the pattern
    details: dict = field(default_factory=dict)


class PatternDetector:
    """Base interface for chart-pattern detectors."""

    pattern_name: str = "Pattern"
    pattern_type: str = "neutral"

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        raise NotImplementedError

    # ---- shared helpers ---------------------------------------------------

    @staticmethod
    def _find_swing_highs(
        prices: np.ndarray, window: int = 3
    ) -> List[int]:
        """Indices of fractal swing highs: bar i is a high iff prices[i] is
        strictly greater than every other bar in [i-window, i+window].

        Deterministic (no randomness) — mirrors analysis-service's F-002
        detector so detectors here line up with the same swing structure
        the regime classifier sees.
        """
        n = len(prices)
        pivots: List[int] = []
        for i in range(window, n - window):
            left = prices[i - window: i]
            right = prices[i + 1: i + 1 + window]
            if prices[i] > left.max() and prices[i] > right.max():
                pivots.append(i)
        return pivots

    @staticmethod
    def _find_swing_lows(
        prices: np.ndarray, window: int = 3
    ) -> List[int]:
        n = len(prices)
        pivots: List[int] = []
        for i in range(window, n - window):
            left = prices[i - window: i]
            right = prices[i + 1: i + 1 + window]
            if prices[i] < left.min() and prices[i] < right.min():
                pivots.append(i)
        return pivots

    @staticmethod
    def _min_idx_between(prices: np.ndarray, lo: int, hi: int) -> int:
        """Index of the minimum bar in (lo, hi). Used to anchor the
        neckline troughs of a Head & Shoulders top."""
        seg = prices[lo + 1: hi]
        if seg.size == 0:
            return lo + 1
        return int(np.argmin(seg)) + lo + 1

    @staticmethod
    def _max_idx_between(prices: np.ndarray, lo: int, hi: int) -> int:
        seg = prices[lo + 1: hi]
        if seg.size == 0:
            return lo + 1
        return int(np.argmax(seg)) + lo + 1

    @staticmethod
    def _within_tolerance(a: float, b: float, tol_pct: float) -> bool:
        """True iff |a-b| / mean(a,b) <= tol_pct (e.g. 0.03 for 3%)."""
        mean = (abs(a) + abs(b)) / 2.0
        if mean == 0:
            return a == b
        return abs(a - b) / mean <= tol_pct

    @staticmethod
    def _line_at(x1: int, y1: float, x2: int, y2: float, x: int) -> float:
        """Linear interpolation of (x1,y1)-(x2,y2) at x. Used to compute
        the projected neckline price at the breakout bar so the measured
        move is anchored on the actual neckline, not just the trough."""
        if x2 == x1:
            return y1
        slope = (y2 - y1) / (x2 - x1)
        return y1 + slope * (x - x1)

    @staticmethod
    def _validate_ohlc(ohlc: pd.DataFrame, min_bars: int) -> Tuple[bool, str]:
        if ohlc is None or len(ohlc) < min_bars:
            return False, f"need >= {min_bars} bars"
        required = {"high", "low", "close"}
        if not required.issubset(ohlc.columns):
            return False, f"missing columns: {required - set(ohlc.columns)}"
        return True, ""
