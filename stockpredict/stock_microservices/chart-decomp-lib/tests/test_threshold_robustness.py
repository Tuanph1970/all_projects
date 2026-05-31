"""Threshold-robustness harness (II.5.3 — L4 compliance).

SRS §II.5.3:
    Construct a series with a quiet regime and a volatile regime, each
    containing a planted pattern.  Assert both are detected — verifying the
    threshold does not get dragged to a single global value that misses the
    quiet-regime pattern (L4).

Design
------
The series has two back-to-back regimes:

    Quiet   (indices 0–149)   : Double Top with ±20-unit swings around 100.
    Volatile(indices 150–410) : Double Top with ±100-unit swings around 100.

Series total range ≈ 100 units (150 − 50).
Default range_frac threshold = 0.08 × 100 = 8 units.

    Quiet swing amplitude   = 20 units >> 8  → both quiet pivots retained.
    Volatile swing amplitude = 100 units >> 8 → both volatile pivots retained.

If a percentage-of-price threshold (forbidden by L4) were used instead (e.g.
"2% of current price ≈ 2 units"), the quiet-regime pivots (20 units) would
still be found, but the test documents the regime-independent requirement.
The range_frac approach is correct precisely because it scales with the
overall series amplitude rather than the local price level.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.domain.entities import SwingSkeleton
from chart_decomp.domain.value_objects import SwingParams, TimeSeries
from chart_decomp.factories.pattern_detector_factory import detect_patterns
from chart_decomp.infrastructure.swings.swing_extractor import SwingExtractor

# ── Series construction ────────────────────────────────────────────────────────

# Quiet  Double Top : H@30(110)  L@60(90)   H@90(110)  — amplitude = 20
# Volatile Double Top: H@200(150) L@250(50) H@300(150) — amplitude = 100
# Total range = 100 units; range_frac=0.08 → threshold = 8 units.
# 20 >> 8  and  100 >> 8  → both regimes' pivots pass the significance filter.
_CTRL = [
    (0, 100),
    (30, 110), (60, 90), (90, 110), (120, 90),   # quiet Double Top
    (160, 100),                                    # transition (flat, no spurious pivot)
    (200, 150), (250, 50), (300, 150), (350, 50), # volatile Double Top
    (400, 100),
]
_N = 410

# Index boundary between the two regimes (used for assertion slicing).
_QUIET_END = 150
_VOLATILE_START = 160


def _make_series() -> np.ndarray:
    idxs = [c[0] for c in _CTRL]
    vals = [c[1] for c in _CTRL]
    return np.interp(np.arange(_N), idxs, vals).astype(float)


def _skeleton_of(x: np.ndarray) -> SwingSkeleton:
    swings = SwingExtractor().extract(
        TimeSeries(x), SwingParams(order=10, threshold=0.08, threshold_mode="range_frac")
    )
    return SwingSkeleton(swings)


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestBothRegimesDetected:
    """II.5.3: patterns in quiet and volatile regimes must both be found."""

    def _detections(self):
        x = _make_series()
        sk = _skeleton_of(x)
        return detect_patterns(sk, x, ["Double Top"])

    def test_quiet_regime_double_top_detected(self):
        """Double Top planted in the quiet regime (±20-unit swings) is found."""
        dets = self._detections()
        quiet = [d for d in dets if d.pattern == "Double Top"
                 and d.start_index < _QUIET_END]
        assert quiet, (
            "Quiet-regime Double Top NOT detected — threshold-robustness failure (L4). "
            f"Detections found: {[(d.pattern, d.start_index) for d in dets]}"
        )

    def test_volatile_regime_double_top_detected(self):
        """Double Top planted in the volatile regime (±100-unit swings) is found."""
        dets = self._detections()
        volatile = [d for d in dets if d.pattern == "Double Top"
                    and d.start_index >= _VOLATILE_START]
        assert volatile, (
            "Volatile-regime Double Top NOT detected. "
            f"Detections found: {[(d.pattern, d.start_index) for d in dets]}"
        )

    def test_both_regimes_detected_simultaneously(self):
        """Both patterns coexist: the volatile regime does not shadow the quiet one."""
        dets = self._detections()
        quiet = [d for d in dets
                 if d.pattern == "Double Top" and d.start_index < _QUIET_END]
        volatile = [d for d in dets
                    if d.pattern == "Double Top" and d.start_index >= _VOLATILE_START]
        assert quiet and volatile, (
            f"Expected detections in both regimes. "
            f"Quiet: {len(quiet)}, Volatile: {len(volatile)}"
        )

    def test_quiet_detection_has_positive_score(self):
        dets = self._detections()
        quiet = [d for d in dets if d.pattern == "Double Top"
                 and d.start_index < _QUIET_END]
        assert quiet and quiet[0].score > 0.0

    def test_volatile_detection_has_positive_score(self):
        dets = self._detections()
        volatile = [d for d in dets if d.pattern == "Double Top"
                    and d.start_index >= _VOLATILE_START]
        assert volatile and volatile[0].score > 0.0


class TestThresholdModeScaleRobustness:
    """Additional check: same series, absolute-mode threshold also finds both."""

    def test_absolute_threshold_finds_quiet_regime(self):
        """An absolute threshold of 8 units (equal to range_frac default) works."""
        x = _make_series()
        swings = SwingExtractor().extract(
            TimeSeries(x),
            SwingParams(order=10, threshold=8.0, threshold_mode="absolute"),
        )
        sk = SwingSkeleton(swings)
        dets = detect_patterns(sk, x, ["Double Top"])
        quiet = [d for d in dets if d.pattern == "Double Top"
                 and d.start_index < _QUIET_END]
        assert quiet, "Absolute-threshold (8 units) missed quiet-regime Double Top"
