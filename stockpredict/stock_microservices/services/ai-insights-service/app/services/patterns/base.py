"""Shared base for chart-pattern detectors (F-005, Schwager Ch 5/11/12).

Every detector implements `.detect(ohlc) -> Optional[PatternMatch]`. The
caller (`InsightsService` aggregator + future decision-helper-service) treats
detectors as interchangeable behind this interface, so adding a new pattern
in Day 2 / Day 3 is local to a single file.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.services.patterns.volume import (
    NEUTRAL_FACTOR,
    VolumeVerdict,
    evaluate_pattern_volume,
)


@dataclass
class PatternMatch:
    """Uniform detector result.

    `measured_move_target` is the price the pattern projects to (Schwager
    Ch 5): for bearish patterns it is below the breakout line, for bullish
    patterns above. Callers use it as a first-cut profit target (Ch 10) and
    as the reference price for the failed-signal detector (Ch 11, F-006).

    EM-1 (`FR-EM-V7`) adds the volume layer. `confidence` becomes the
    **composite** `geometric_confidence x volume_factor`, and the geometric
    reading is preserved rather than overwritten, so a caller — and the UI —
    can see that volume moved the number and by how much. Every volume field
    is `Optional` and defaulted, so existing construction sites and HTTP
    clients are unaffected (`EC-V3`).

    Volume **weights** the score; it never gates `found`. That is deliberate:
    `found` is consumed by `PatternPanel.js`, `AIInsights.js` and
    decision-helper's `failed_signal.py`, where flipping it on volume grounds
    would read as patterns disappearing.
    """
    pattern_name: str
    pattern_type: str                    # "bullish" | "bearish"
    found: bool
    confidence: float                    # 0..1 — composite once volume is read
    key_bars: List[int] = field(default_factory=list)
    measured_move_target: Optional[float] = None
    neckline: Optional[float] = None     # breakout level for the pattern
    details: dict = field(default_factory=dict)
    # --- EM-1 / FR-EM-V7 ---
    volume_score: Optional[float] = None       # 0..1; None = unknown, never 0.0
    volume_factor: float = NEUTRAL_FACTOR      # the multiplier actually applied
    volume_evidence: dict = field(default_factory=dict)
    geometric_confidence: Optional[float] = None   # the pre-volume reading


def apply_volume_evidence(
    match: Optional[PatternMatch], ohlc: pd.DataFrame
) -> Optional[PatternMatch]:
    """Compose the volume verdict onto one detection (`FR-EM-V7`).

    Idempotent — a second call is a no-op, which matters because a detector
    may be invoked through a runner that has already finalised the match.

    Failure isolation (`NFR-V1`) is the reason for the bare `except`: each
    detector is already wrapped in a `try/except` by its runner
    (`reversal.py:386`, `continuation.py:789`), so an exception escaping here
    would swallow the **detection** along with the error. Volume therefore
    fails *inward*, to a neutral factor, and the pattern survives.
    """
    if match is None or not match.found:
        return match
    if match.geometric_confidence is not None:
        return match

    geometric = float(match.confidence)
    try:
        verdict = evaluate_pattern_volume(match, ohlc)
    except Exception:  # noqa: BLE001 — NFR-V1: a volume bug must not drop a detection
        verdict = VolumeVerdict.neutral("volume_evaluation_failed")

    match.geometric_confidence = geometric
    match.volume_score = verdict.score
    match.volume_factor = verdict.factor
    match.volume_evidence = verdict.evidence
    match.confidence = float(round(min(1.0, max(0.0, geometric * verdict.factor)), 3))

    # FR-EM-V5 row 10: the gap family is the one place volume changes a
    # pattern's LABEL and not just its score (Ch 12's exhaustion gap, which
    # the geometry-only classifier cannot express). The previous label is kept
    # in both `details` and `volume_evidence`, because `pattern_name` is what
    # PatternPanel.js renders and a label that moved with no record of what it
    # was would be indistinguishable from a detector bug.
    if verdict.reclassify_to:
        match.details = {
            **match.details,
            "gap_type_before_volume": match.details.get("gap_type"),
            "gap_type": verdict.reclassify_to.removeprefix("Gap (").removesuffix(")"),
            "reclassified_by": "volume",
        }
        match.pattern_name = verdict.reclassify_to
    return match


class PatternDetector:
    """Base interface for chart-pattern detectors."""

    pattern_name: str = "Pattern"
    pattern_type: str = "neutral"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Wrap every subclass's `detect` so the volume layer is applied
        exactly once, in exactly one place.

        `FR-EM-V3` must be *"encoded once, as data"* — a call to
        `apply_volume_evidence` written into each of the twelve detectors
        would be twelve places to forget it, and a thirteenth detector added
        later would silently return no volume verdict while looking correct.
        Wrapping here also keeps the object consistent however it is reached:
        a direct `Detector().detect(df)` and the `run_*_detectors` aggregator
        return the same fields.

        Only a class that defines `detect` itself is wrapped, and the wrapper
        marks itself, so neither inheritance nor a re-import double-applies it
        (`apply_volume_evidence` is idempotent regardless).
        """
        super().__init_subclass__(**kwargs)
        inner: Optional[Callable[..., Any]] = cls.__dict__.get("detect")
        if inner is None or getattr(inner, "_em1_volume_wrapped", False):
            return

        @functools.wraps(inner)
        def wrapper(self: "PatternDetector", ohlc: pd.DataFrame, *args: Any, **kw: Any):
            return apply_volume_evidence(inner(self, ohlc, *args, **kw), ohlc)

        wrapper._em1_volume_wrapped = True  # type: ignore[attr-defined]
        cls.detect = wrapper  # type: ignore[assignment]

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
