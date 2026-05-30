"""CD-603 (A3) — Swing extractor (FR-SW-1/2/3).

Asserts PROPERTIES of the extractor:
- Built on the vetted primitive scipy.signal.argrelextrema, NOT a bespoke loop (L2).
- Output strictly alternates H/L (FR-SW-2).
- Minimum index spacing is respected.
- The prominence filter removes sub-threshold swings (FR-SW-3 / L4).
- All three scale-robust threshold modes run and produce valid skeletons.
- Planted pivots are recovered near their true locations.
"""
from __future__ import annotations

from unittest import mock

import numpy as np
import pytest

from chart_decomp.domain.entities import Swing
from chart_decomp.domain.value_objects import SwingParams, TimeSeries
from chart_decomp.infrastructure.swings import swing_extractor as se_mod
from chart_decomp.infrastructure.swings.swing_extractor import SwingExtractor


def zigzag(control, n, noise=0.0, seed=0):
    """Piecewise-linear series through (index, price) control points."""
    idxs = [c[0] for c in control]
    prices = [c[1] for c in control]
    x = np.interp(np.arange(n), idxs, prices).astype(float)
    if noise:
        x = x + np.random.default_rng(seed).normal(0.0, noise, n)
    return x


@pytest.fixture
def ext():
    return SwingExtractor()


def _assert_alternating(swings):
    kinds = [s.kind for s in swings]
    for a, b in zip(kinds, kinds[1:]):
        assert a != b, f"non-alternating kinds: {kinds}"
    assert all(k in ("H", "L") for k in kinds)


class TestVettedPrimitive:
    def test_uses_argrelextrema(self, ext):
        # L2: the extractor MUST be built on argrelextrema, not a hand loop.
        x = zigzag([(0, 100), (40, 160), (80, 100), (120, 170), (160, 90), (199, 140)], 200)
        with mock.patch.object(
            se_mod, "argrelextrema", wraps=se_mod.argrelextrema
        ) as spy:
            ext.extract(TimeSeries(x), SwingParams(order=10))
        assert spy.called, "argrelextrema was not used"


class TestAlternationAndSpacing:
    def test_strict_alternation_clean(self, ext):
        x = zigzag([(0, 100), (40, 150), (80, 100), (120, 160), (160, 90), (199, 140)], 200)
        swings = ext.extract(TimeSeries(x), SwingParams(order=10))
        assert len(swings) >= 3
        _assert_alternating(swings)

    def test_strict_alternation_noisy(self, ext):
        x = zigzag(
            [(0, 100), (40, 150), (80, 100), (120, 160), (160, 90), (199, 140)],
            200, noise=1.0, seed=7,
        )
        swings = ext.extract(TimeSeries(x), SwingParams(order=10))
        _assert_alternating(swings)

    def test_min_gap_respected(self, ext):
        x = zigzag([(0, 100), (40, 150), (80, 100), (120, 160), (160, 90), (199, 140)], 200)
        swings = ext.extract(TimeSeries(x), SwingParams(order=5, min_gap=12))
        idx = [s.index for s in swings]
        for a, b in zip(idx, idx[1:]):
            assert b - a >= 12

    def test_returns_swing_objects(self, ext):
        x = zigzag([(0, 100), (40, 150), (80, 100), (120, 160), (160, 90), (199, 140)], 200)
        swings = ext.extract(TimeSeries(x), SwingParams(order=10))
        assert all(isinstance(s, Swing) for s in swings)
        for s in swings:
            assert s.price == pytest.approx(x[s.index])


class TestPlantedRecovery:
    def test_recovers_known_pivots(self, ext):
        ctrl = [(0, 100), (40, 150), (80, 100), (120, 160), (160, 90), (199, 140)]
        x = zigzag(ctrl, 200)
        swings = ext.extract(TimeSeries(x), SwingParams(order=10))
        got = sorted(s.index for s in swings)
        # interior extrema only (argrelextrema excludes endpoints)
        for true_idx in (40, 80, 120, 160):
            assert any(abs(true_idx - g) <= 2 for g in got), f"missed pivot near {true_idx}: {got}"


class TestProminenceFilter:
    def test_small_swings_dropped(self, ext):
        # Big swings plus a tiny dip that IS a local extremum over the window but
        # whose amplitude is below the prominence threshold.
        ctrl = [(0, 100), (40, 160), (55, 156), (70, 185), (110, 100), (160, 175), (199, 120)]
        x = zigzag(ctrl, 200)
        loose = ext.extract(TimeSeries(x), SwingParams(order=10, threshold=1e-9))
        tight = ext.extract(TimeSeries(x), SwingParams(order=10, threshold=0.08))
        assert len(tight) < len(loose), (len(tight), len(loose))
        _assert_alternating(tight)


class TestThresholdModes:
    @pytest.mark.parametrize("mode", ["range_frac", "atr", "absolute"])
    def test_modes_run_and_alternate(self, ext, mode):
        x = zigzag([(0, 100), (40, 150), (80, 100), (120, 160), (160, 90), (199, 140)], 200)
        thr = {"range_frac": 0.08, "atr": 1.5, "absolute": 10.0}[mode]
        swings = ext.extract(TimeSeries(x), SwingParams(order=10, threshold_mode=mode, threshold=thr))
        _assert_alternating(swings)
        assert len(swings) >= 1

    def test_absolute_threshold_filters(self, ext):
        x = zigzag([(0, 100), (40, 150), (80, 100), (120, 160), (160, 90), (199, 140)], 200)
        many = ext.extract(TimeSeries(x), SwingParams(order=10, threshold_mode="absolute", threshold=1.0))
        few = ext.extract(TimeSeries(x), SwingParams(order=10, threshold_mode="absolute", threshold=1000.0))
        assert len(few) <= len(many)
        assert len(few) == 0


class TestDegenerate:
    def test_flat_series_no_swings(self, ext):
        x = np.full(100, 5.0)
        assert ext.extract(TimeSeries(x), SwingParams(order=10)) == []
