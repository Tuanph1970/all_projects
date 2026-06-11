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
from chart_decomp.infrastructure.patterns.flag_pennant import (
    BearFlagDetector,
    BullFlagDetector,
)
from chart_decomp.factories.pattern_detector_factory import detect_patterns
from chart_decomp.infrastructure.patterns.triangle import (
    AscendingTriangleDetector,
    DescendingTriangleDetector,
    SymmetricTriangleDetector,
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


# ── Bull Flag ─────────────────────────────────────────────────────────────────

class TestBullFlagPlanted:
    # Pole: L(~20, 85) → H(~45, 155), height=70, ~93% of range >> pole_min(40%).
    # Consolidation: H(~75,152), H(~105,151) and L(~60,145), L(~90,143).
    # Both bound lines slope slightly negative → parallel → "Bull Flag".
    CTRL = [
        (0, 100), (20, 85), (45, 155),
        (60, 145), (75, 152), (90, 143), (105, 151),
        (150, 80),
    ]
    N = 160

    def test_detected_near_location(self):
        x = zigzag(self.CTRL, self.N)
        dets = BullFlagDetector().detect(skeleton_of(x), x)
        assert dets, "planted bull flag not detected"
        d = dets[0]
        assert d.pattern == "Bull Flag"
        assert abs(d.start_index - 20) <= 3   # pole base near index 20
        assert d.score > 0.5

    def test_large_retrace_rejected(self):
        # Consolidation L(~90, 103): retrace = 155-103=52, 52/70=74% > retr_max(60%).
        ctrl = [
            (0, 100), (20, 85), (45, 155),
            (60, 108), (75, 150), (90, 103), (105, 148),
            (150, 80),
        ]
        x = zigzag(ctrl, self.N)
        assert BullFlagDetector().detect(skeleton_of(x), x) == []

    def test_bear_detector_silent_on_bull_flag(self):
        x = zigzag(self.CTRL, self.N)
        # No H→L pole exceeds pole_min in this series.
        assert BearFlagDetector().detect(skeleton_of(x), x) == []


# ── Bull Pennant ──────────────────────────────────────────────────────────────

class TestBullPennantPlanted:
    # Same pole as bull flag. Consolidation: H(~75,152), H(~105,148) slope down;
    # L(~60,133), L(~90,140) slope up → converging → "Bull Pennant".
    # Each H↔L move ≥ 8 pts, well above the 8%-of-range threshold (5.6 pt).
    CTRL = [
        (0, 100), (20, 85), (45, 155),
        (60, 133), (75, 152), (90, 140), (105, 148),
        (150, 100),
    ]
    N = 160

    def test_detected_near_location(self):
        x = zigzag(self.CTRL, self.N)
        dets = BullFlagDetector().detect(skeleton_of(x), x)
        assert dets, "planted bull pennant not detected"
        d = dets[0]
        assert d.pattern == "Bull Pennant"
        assert d.score > 0.5


# ── Bear Flag ────────────────────────────────────────────────────────────────

class TestBearFlagPlanted:
    # Pole: H(~25, 155) → L(~50, 85), height=70 >> pole_min.
    # Consolidation: H(~70,95), H(~105,96) and L(~85,87), L(~120,88).
    # All moves ≥ 8 pts (> 7.2-pt threshold = 8% of range=90).
    # Brief H(130,96) ensures L(120) has a higher right neighbour for argrelextrema.
    # Both bound lines slope slightly positive → parallel → "Bear Flag".
    CTRL = [
        (0, 100), (25, 155), (50, 85),
        (70, 95), (85, 87), (105, 96), (120, 88), (130, 96),
        (190, 65),
    ]
    N = 200

    def test_detected_near_location(self):
        x = zigzag(self.CTRL, self.N)
        dets = BearFlagDetector().detect(skeleton_of(x), x)
        assert dets, "planted bear flag not detected"
        d = dets[0]
        assert d.pattern == "Bear Flag"
        assert abs(d.start_index - 25) <= 3   # pole top near index 25
        assert d.score > 0.5

    def test_bull_detector_silent_on_bear_flag(self):
        x = zigzag(self.CTRL, self.N)
        # No L→H pole exceeds pole_min in this series.
        assert BullFlagDetector().detect(skeleton_of(x), x) == []


# ── Symmetric Triangle ────────────────────────────────────────────────────────

class TestSymmetricTrianglePlanted:
    # H pivots descend (150→145→140) and L pivots ascend (112→116→120):
    # converging from both sides → Symmetric Triangle.
    # Each H↔L move ≥ 24 pts >> 8%-of-range threshold (≈3 pts).
    CTRL = [
        (0, 130),
        (20, 150), (40, 112),   # H1 L1
        (60, 145), (80, 116),   # H2 L2
        (100, 140), (120, 120), # H3 L3
        (160, 130),
    ]
    N = 170

    def test_detected_near_location(self):
        x = zigzag(self.CTRL, self.N)
        dets = SymmetricTriangleDetector().detect(skeleton_of(x), x)
        assert dets, "planted symmetric triangle not detected"
        d = dets[0]
        assert d.pattern == "Symmetric Triangle"
        assert abs(d.start_index - 20) <= 3   # first pivot near index 20
        assert d.score > 0.5


# ── Ascending Triangle ────────────────────────────────────────────────────────

class TestAscendingTrianglePlanted:
    # H pivots all at 150 (flat resistance); L pivots at 113→120→127 (rising support).
    CTRL = [
        (0, 130),
        (20, 150), (45, 113),   # H1 L1
        (70, 150), (95, 120),   # H2 L2
        (120, 150), (145, 127), # H3 L3
        (180, 140),
    ]
    N = 190

    def test_detected_near_location(self):
        x = zigzag(self.CTRL, self.N)
        dets = AscendingTriangleDetector().detect(skeleton_of(x), x)
        assert dets, "planted ascending triangle not detected"
        d = dets[0]
        assert d.pattern == "Ascending Triangle"
        assert d.score > 0.5

    def test_descending_silent_on_ascending(self):
        x = zigzag(self.CTRL, self.N)
        assert DescendingTriangleDetector().detect(skeleton_of(x), x) == []


# ── Descending Triangle ───────────────────────────────────────────────────────

class TestDescendingTrianglePlanted:
    # H pivots at 150→143→136 (falling resistance); L pivots all at 113 (flat support).
    CTRL = [
        (0, 130),
        (20, 150), (45, 113),   # H1 L1
        (70, 143), (95, 113),   # H2 L2
        (120, 136), (145, 113), # H3 L3
        (180, 120),
    ]
    N = 190

    def test_detected_near_location(self):
        x = zigzag(self.CTRL, self.N)
        dets = DescendingTriangleDetector().detect(skeleton_of(x), x)
        assert dets, "planted descending triangle not detected"
        d = dets[0]
        assert d.pattern == "Descending Triangle"
        assert d.score > 0.5

    def test_ascending_silent_on_descending(self):
        x = zigzag(self.CTRL, self.N)
        assert AscendingTriangleDetector().detect(skeleton_of(x), x) == []

    def test_too_few_pivots_rejected(self):
        # 2H + 1L → no window satisfies ≥2H + ≥2L (min_pivots default ≥ 4).
        ctrl = [(0, 80), (30, 150), (70, 80), (110, 150), (150, 130)]
        x = zigzag(ctrl, 160)
        assert SymmetricTriangleDetector().detect(skeleton_of(x), x) == []
        assert AscendingTriangleDetector().detect(skeleton_of(x), x) == []
        assert DescendingTriangleDetector().detect(skeleton_of(x), x) == []


# ── Default-registry end-to-end (A10 — CD-610) ───────────────────────────────

class TestDefaultRegistryEndToEnd:
    """II.5.1 consolidated: all four pattern families via detect_patterns('all').

    Verifies that the default_registry is populated with all built-in detectors
    and that detect_patterns('all') finds each pattern family in a planted series.
    """

    def test_head_and_shoulders_via_registry(self):
        ctrl = [(0, 80), (30, 130), (50, 100), (70, 160), (90, 102), (110, 132), (140, 90)]
        x = zigzag(ctrl, 150)
        dets = detect_patterns(skeleton_of(x), x, "all")
        assert any(d.pattern == "Head & Shoulders" for d in dets), (
            "H&S not found via default registry"
        )

    def test_double_top_via_registry(self):
        ctrl = [(0, 90), (40, 150), (70, 110), (100, 151), (140, 95)]
        x = zigzag(ctrl, 150)
        dets = detect_patterns(skeleton_of(x), x, "all")
        assert any(d.pattern == "Double Top" for d in dets), (
            "Double Top not found via default registry"
        )

    def test_bull_flag_via_registry(self):
        ctrl = [
            (0, 100), (20, 85), (45, 155),
            (60, 145), (75, 152), (90, 143), (105, 151),
            (150, 80),
        ]
        x = zigzag(ctrl, 160)
        dets = detect_patterns(skeleton_of(x), x, "all")
        assert any(d.pattern == "Bull Flag" for d in dets), (
            "Bull Flag not found via default registry"
        )

    def test_symmetric_triangle_via_registry(self):
        ctrl = [
            (0, 130),
            (20, 150), (40, 112), (60, 145), (80, 116),
            (100, 140), (120, 120),
            (160, 130),
        ]
        x = zigzag(ctrl, 170)
        dets = detect_patterns(skeleton_of(x), x, "all")
        assert any(d.pattern == "Symmetric Triangle" for d in dets), (
            "Symmetric Triangle not found via default registry"
        )


# ── Double Top — score redesign ────────────────────────────────────────────────

class TestDoubleTopScoreRedesign:
    """Unit tests for the range-relative depth + trajectory-quality score (A6b)."""

    # Clean M-shape: two equal peaks, deep trough, smooth legs
    CTRL_CLEAN = [(0, 90), (40, 150), (80, 110), (120, 151), (159, 90)]
    # Junk: two near-equal peaks but tiny trough (only ~2% below peak) → filtered
    CTRL_SHALLOW = [(0, 140), (40, 150), (70, 148), (100, 150), (140, 140)]

    def test_clean_double_top_scores_above_0_8(self):
        x    = zigzag(self.CTRL_CLEAN, 160)
        dets = DoubleTopDetector().detect(skeleton_of(x), x)
        assert dets, "planted double top not detected"
        assert dets[0].score > 0.80, (
            f"clean double top score={dets[0].score:.3f} should be > 0.80"
        )

    def test_shallow_trough_still_rejected(self):
        # ~1.3% trough depth < min_trough_depth=0.03 → [] even before scoring
        x  = zigzag(self.CTRL_SHALLOW, 150)
        sk = skeleton_of(x, threshold=1e-9)
        assert DoubleTopDetector().detect(sk, x) == []

    @pytest.mark.slow
    def test_planted_clean_double_top_clears_null_gate(self):
        """MANDATORY (FR-FPR-2): planted double top must beat null pct95 (score redesign)."""
        from chart_decomp.infrastructure.validation.null_fpr import (
            annotate_significance,
            null_detection_distribution,
        )

        x    = zigzag(self.CTRL_CLEAN, 160)
        skel = skeleton_of(x)
        dets = DoubleTopDetector().detect(skel, x)
        assert dets, "planted double top not detected (precondition)"
        d = dets[0]

        dist = null_detection_distribution(
            length=160, volatility=0.01, detectors="all",
            n_null=200, seed=42,
        )
        annotate_significance([d], dist)
        assert d.noteworthy is True, (
            f"planted double top (score={d.score:.3f}) did not clear null pct95 "
            f"(null_percentile={d.null_percentile:.1f})"
        )


# ── Double Bottom — score redesign ────────────────────────────────────────────

class TestDoubleBottomScoreRedesign:
    """Unit tests for the range-relative height + trajectory-quality score (A6b)."""

    # Clean W-shape: two equal lows, high intervening peak, smooth legs
    CTRL_CLEAN = [(0, 160), (40, 100), (80, 140), (120, 101), (159, 160)]

    def test_clean_double_bottom_scores_above_0_8(self):
        x    = zigzag(self.CTRL_CLEAN, 160)
        dets = DoubleBottomDetector().detect(skeleton_of(x), x)
        assert dets, "planted double bottom not detected"
        assert dets[0].score > 0.80, (
            f"clean double bottom score={dets[0].score:.3f} should be > 0.80"
        )

    @pytest.mark.slow
    def test_planted_clean_double_bottom_clears_null_gate(self):
        """MANDATORY (FR-FPR-2): planted double bottom must beat null pct95."""
        from chart_decomp.infrastructure.validation.null_fpr import (
            annotate_significance,
            null_detection_distribution,
        )

        x    = zigzag(self.CTRL_CLEAN, 160)
        skel = skeleton_of(x)
        dets = DoubleBottomDetector().detect(skel, x)
        assert dets, "planted double bottom not detected (precondition)"
        d = dets[0]

        dist = null_detection_distribution(
            length=160, volatility=0.01, detectors="all",
            n_null=200, seed=42,
        )
        annotate_significance([d], dist)
        assert d.noteworthy is True, (
            f"planted double bottom (score={d.score:.3f}) did not clear null pct95 "
            f"(null_percentile={d.null_percentile:.1f})"
        )
