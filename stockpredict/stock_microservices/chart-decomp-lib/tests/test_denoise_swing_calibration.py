"""A13 — Joint denoise-swing calibration tests (FR-DN-2).

Covers:
- CalibrationResult has one point per (k_drop, threshold) pair.
- swing_count is a non-negative integer for every point.
- recall is None when no labeled swings are provided.
- recall is in [0.0, 1.0] when labeled swings are provided.
- With loose threshold, planted pivots are recovered (recall = 1.0).
- best_recall() returns the point with highest recall (or None if no labels).
- as_grid() gives dict-style access by (k_drop, threshold) key.
- Facade: calibrate_denoise_swings importable from chart_decomp.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.domain.entities import Swing
from chart_decomp.application.denoise_swings_usecase import (
    CalibrationPoint,
    CalibrationResult,
    DenoiseSwingtUseCase,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _zigzag(control, n):
    idxs = [c[0] for c in control]
    prices = [c[1] for c in control]
    return np.interp(np.arange(n), idxs, prices).astype(float)


# Clear alternating H/L pivots spaced 30 bars apart, well inside the 190-sample range.
# L at 30,90,150; H at 60,120.  range=70; each step move=70 >> any reasonable threshold.
_CTRL = [(0, 100), (30, 80), (60, 150), (90, 80), (120, 150), (150, 80), (180, 150)]
_N = 190

# Ground-truth labels for the inner pivots (far from edges so argrelextrema finds them).
_LABELS = [
    Swing(30,  80.0, "L"),
    Swing(60,  150.0, "H"),
    Swing(90,  80.0, "L"),
    Swing(120, 150.0, "H"),
    Swing(150, 80.0, "L"),
]

_K_DROPS = [0, 1, 2]
_THRESHOLDS = [0.04, 0.08, 0.12]


# ── Structure ──────────────────────────────────────────────────────────────────

class TestCalibrationResultStructure:
    def _run(self, labels=None):
        uc = DenoiseSwingtUseCase()
        x = _zigzag(_CTRL, _N)
        return uc.calibrate(x, _K_DROPS, _THRESHOLDS, labeled_swings=labels)

    def test_returns_calibration_result(self):
        r = self._run()
        assert isinstance(r, CalibrationResult)

    def test_point_count_equals_grid_size(self):
        r = self._run()
        assert len(r.points) == len(_K_DROPS) * len(_THRESHOLDS)

    def test_every_point_is_calibration_point(self):
        r = self._run()
        assert all(isinstance(p, CalibrationPoint) for p in r.points)

    def test_k_drop_and_threshold_values_stored(self):
        r = self._run()
        assert r.k_drop_values == _K_DROPS
        assert r.threshold_values == _THRESHOLDS

    def test_series_length_stored(self):
        r = self._run()
        assert r.series_length == _N

    def test_swing_counts_non_negative(self):
        r = self._run()
        assert all(p.swing_count >= 0 for p in r.points)

    def test_recall_none_without_labels(self):
        r = self._run(labels=None)
        assert all(p.recall is None for p in r.points)

    def test_recall_in_unit_interval_with_labels(self):
        r = self._run(labels=_LABELS)
        assert all(0.0 <= p.recall <= 1.0 for p in r.points)


# ── Swing-count behaviour ──────────────────────────────────────────────────────

class TestSwingCountBehaviour:
    def test_more_aggressive_denoising_fewer_swings(self):
        """Higher k_drop → smoother series → fewer or equal swing pivots."""
        uc = DenoiseSwingtUseCase()
        x = _zigzag(_CTRL, _N)
        r = uc.calibrate(x, k_drop_values=[0, 1, 2, 3], threshold_values=[0.08])
        counts = [p.swing_count for p in r.points]
        # Counts must be non-increasing as k_drop rises (same threshold).
        for c1, c2 in zip(counts, counts[1:]):
            assert c1 >= c2, f"swing_count rose from {c1} to {c2} when k_drop increased"

    def test_stricter_threshold_fewer_swings(self):
        """Higher threshold → only larger pivots retained → fewer swings."""
        uc = DenoiseSwingtUseCase()
        x = _zigzag(_CTRL, _N)
        r = uc.calibrate(x, k_drop_values=[1], threshold_values=[0.04, 0.08, 0.20])
        counts = [p.swing_count for p in r.points]
        for c1, c2 in zip(counts, counts[1:]):
            assert c1 >= c2, f"swing_count rose from {c1} to {c2} when threshold increased"


# ── Recall with labeled swings ─────────────────────────────────────────────────

class TestRecallWithLabels:
    def test_perfect_recall_with_loose_threshold(self):
        """k_drop=0, threshold=0.04 (very loose) must recover all 5 planted pivots."""
        uc = DenoiseSwingtUseCase()
        x = _zigzag(_CTRL, _N)
        r = uc.calibrate(x, k_drop_values=[0], threshold_values=[0.04],
                         labeled_swings=_LABELS)
        pt = r.points[0]
        assert pt.recall == pytest.approx(1.0), (
            f"Expected recall=1.0 with loose threshold; got {pt.recall:.3f}"
        )

    def test_recall_drops_with_very_aggressive_denoising(self):
        """With k_drop=4 and tight threshold some labeled pivots may be lost."""
        uc = DenoiseSwingtUseCase()
        x = _zigzag(_CTRL, _N)
        r = uc.calibrate(x, k_drop_values=[0, 4], threshold_values=[0.04],
                         labeled_swings=_LABELS)
        # Recall at k_drop=0 should be >= recall at k_drop=4.
        recall_0 = r.points[0].recall
        recall_4 = r.points[1].recall
        assert recall_0 >= recall_4, (
            f"Expected lighter denoising (k_drop=0) recall {recall_0:.3f} >= "
            f"heavier (k_drop=4) recall {recall_4:.3f}"
        )


# ── Grid access helpers ────────────────────────────────────────────────────────

class TestGridAccess:
    def test_as_grid_has_all_keys(self):
        uc = DenoiseSwingtUseCase()
        x = _zigzag(_CTRL, _N)
        r = uc.calibrate(x, _K_DROPS, _THRESHOLDS)
        g = r.as_grid()
        for k in _K_DROPS:
            for t in _THRESHOLDS:
                assert (k, t) in g, f"key ({k}, {t}) missing from grid"

    def test_best_recall_none_without_labels(self):
        uc = DenoiseSwingtUseCase()
        x = _zigzag(_CTRL, _N)
        r = uc.calibrate(x, [0, 1], [0.08])
        assert r.best_recall() is None

    def test_best_recall_returns_valid_point(self):
        uc = DenoiseSwingtUseCase()
        x = _zigzag(_CTRL, _N)
        r = uc.calibrate(x, _K_DROPS, _THRESHOLDS, labeled_swings=_LABELS)
        best = r.best_recall()
        assert best is not None
        assert best.recall is not None
        assert all(best.recall >= p.recall for p in r.points if p.recall is not None)


# ── Facade ──────────────────────────────────────────────────────────────────────

class TestFacadeImport:
    def test_calibrate_denoise_swings_importable(self):
        from chart_decomp import calibrate_denoise_swings  # noqa: F401
        assert callable(calibrate_denoise_swings)

    def test_facade_returns_calibration_result(self):
        from chart_decomp import calibrate_denoise_swings
        x = _zigzag(_CTRL, _N)
        r = calibrate_denoise_swings(x, k_drop_values=[0, 1], threshold_values=[0.08])
        assert isinstance(r, CalibrationResult)
