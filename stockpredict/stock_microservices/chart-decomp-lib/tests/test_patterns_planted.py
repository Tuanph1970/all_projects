"""Planted-pattern harness (II.5.1 — MANDATORY).

Introduced with the Head & Shoulders detector (A6) and EXTENDED by later detector
tasks (A7 double, A8 flag, A9 triangle). Construct synthetic series with a
deliberately planted pattern at a known location, run swing extraction + the
detector, and assert the pattern is recovered near its true location.

This is the regression harness for L1/L2: it catches both over-smoothing
(missed plants) and detector-logic bugs. Asserts PROPERTIES (recovery near the
planted pivots, a meaningful score), never synthetic magnitudes.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.domain.entities import SwingSkeleton
from chart_decomp.domain.value_objects import SwingParams, TimeSeries
from chart_decomp.infrastructure.patterns.double import (
    DoubleBottomDetector,
    DoubleTopDetector,
)
from chart_decomp.infrastructure.patterns.head_shoulders import (
    HeadAndShouldersDetector,
    InverseHeadAndShouldersDetector,
)
from chart_decomp.infrastructure.swings.swing_extractor import SwingExtractor


def zigzag(control, n, noise=0.0, seed=0):
    idxs = [c[0] for c in control]
    prices = [c[1] for c in control]
    x = np.interp(np.arange(n), idxs, prices).astype(float)
    if noise:
        x = x + np.random.default_rng(seed).normal(0.0, noise, n)
    return x


def skeleton_of(x, order=10, threshold=0.08):
    swings = SwingExtractor().extract(TimeSeries(x), SwingParams(order=order, threshold=threshold))
    return SwingSkeleton(swings)


def _near(got, true, tol=3):
    return any(abs(true - g) <= tol for g in got)


# ── Head & Shoulders (top) ────────────────────────────────────────────────────

class TestHeadAndShouldersPlanted:
    # LS@30=130, T1@50=100, Head@70=160, T2@90=102, RS@110=132
    CTRL = [(0, 80), (30, 130), (50, 100), (70, 160), (90, 102), (110, 132), (140, 90)]

    def test_detected_near_location(self):
        x = zigzag(self.CTRL, 150)
        dets = HeadAndShouldersDetector().detect(skeleton_of(x), x)
        assert dets, "planted H&S not detected"
        d = dets[0]
        assert d.pattern == "Head & Shoulders"
        assert d.pivots[2] == pytest.approx(70, abs=3)   # head
        assert abs(d.start_index - 30) <= 3 and abs(d.end_index - 110) <= 3
        assert d.score > 0.5

    def test_detected_with_noise(self):
        x = zigzag(self.CTRL, 150, noise=1.0, seed=11)
        dets = HeadAndShouldersDetector().detect(skeleton_of(x), x)
        assert dets
        assert _near([d.pivots[2] for d in dets], 70, tol=4)

    def test_head_not_highest_rejected(self):
        # middle high (150) is LOWER than the left shoulder (160) → not an H&S
        ctrl = [(0, 80), (30, 160), (50, 100), (70, 150), (90, 102), (110, 132), (140, 90)]
        x = zigzag(ctrl, 150)
        assert HeadAndShouldersDetector().detect(skeleton_of(x), x) == []

    def test_too_few_pivots(self):
        # a simple V (2 pivots) cannot be an H&S
        x = zigzag([(0, 100), (50, 50), (99, 120)], 100)
        assert HeadAndShouldersDetector().detect(skeleton_of(x), x) == []


# ── Inverse Head & Shoulders (bottom) ──────────────────────────────────────────

class TestInverseHeadAndShouldersPlanted:
    # LS@30=130, P1@50=160, Head@70=100, P2@90=158, RS@110=128
    CTRL = [(0, 180), (30, 130), (50, 160), (70, 100), (90, 158), (110, 128), (140, 170)]

    def test_detected_near_location(self):
        x = zigzag(self.CTRL, 150)
        dets = InverseHeadAndShouldersDetector().detect(skeleton_of(x), x)
        assert dets, "planted inverse H&S not detected"
        d = dets[0]
        assert d.pattern == "Inverse Head & Shoulders"
        assert d.pivots[2] == pytest.approx(70, abs=3)   # head (lowest)
        assert d.score > 0.5

    def test_top_detector_does_not_fire_on_inverse(self):
        x = zigzag(self.CTRL, 150)
        assert HeadAndShouldersDetector().detect(skeleton_of(x), x) == []


# ── Double Top ─────────────────────────────────────────────────────────────────

class TestDoubleTopPlanted:
    # two near-equal peaks (150, 151) around a trough (110)
    CTRL = [(0, 90), (40, 150), (70, 110), (100, 151), (140, 95)]

    def test_detected_near_location(self):
        x = zigzag(self.CTRL, 150)
        dets = DoubleTopDetector().detect(skeleton_of(x), x)
        assert dets, "planted double top not detected"
        d = dets[0]
        assert d.pattern == "Double Top"
        assert abs(d.start_index - 40) <= 3 and abs(d.end_index - 100) <= 3
        assert d.pivots[1] == pytest.approx(70, abs=3)   # trough / neckline
        assert d.score > 0.5

    def test_unequal_peaks_rejected(self):
        # peaks 150 vs 125 differ by ~17% ≫ tol_equal (3%)
        ctrl = [(0, 90), (40, 150), (70, 110), (100, 125), (140, 95)]
        x = zigzag(ctrl, 150)
        assert DoubleTopDetector().detect(skeleton_of(x), x) == []

    def test_shallow_trough_rejected(self):
        # genuine local min but only ~1.3% below the peaks → below min_trough_depth.
        # Use a tiny swing threshold so the shallow trough still registers as a pivot.
        ctrl = [(0, 140), (40, 150), (70, 148), (100, 150), (140, 140)]
        x = zigzag(ctrl, 150)
        sk = skeleton_of(x, threshold=1e-9)
        assert DoubleTopDetector().detect(sk, x) == []


# ── Double Bottom ──────────────────────────────────────────────────────────────

class TestDoubleBottomPlanted:
    # two near-equal lows (100, 101) around a peak (140)
    CTRL = [(0, 160), (40, 100), (70, 140), (100, 101), (140, 155)]

    def test_detected_near_location(self):
        x = zigzag(self.CTRL, 150)
        dets = DoubleBottomDetector().detect(skeleton_of(x), x)
        assert dets, "planted double bottom not detected"
        d = dets[0]
        assert d.pattern == "Double Bottom"
        assert d.pivots[1] == pytest.approx(70, abs=3)   # peak / neckline
        assert d.score > 0.5

    def test_top_detector_silent_on_bottom(self):
        x = zigzag(self.CTRL, 150)
        assert DoubleTopDetector().detect(skeleton_of(x), x) == []
