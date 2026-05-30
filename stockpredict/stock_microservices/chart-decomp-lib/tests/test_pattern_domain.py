"""CD-601 (A1) — Part II domain types.

Covers the new pattern-detection domain layer (SRS §II.4):
- Entities: Swing, SwingSkeleton, Detection, PatternPipelineResult
- Value objects: DenoiseParams, SwingParams, HSParams, FlagParams,
  TriangleParams, DoubleParams, NullFPRParams (frozen + self-validating)
- Interfaces: IDenoiser, ISwingExtractor, IPatternDetector, INullEvaluator
- Reuse of the existing TimeSeries input wrapper.

These assert PROPERTIES of the data model (construction, defaults, validation,
immutability) — there are no algorithms here yet.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from chart_decomp.domain.entities import (
    Detection,
    PatternPipelineResult,
    Swing,
    SwingSkeleton,
)
from chart_decomp.domain.exceptions import InputValidationError
from chart_decomp.domain.value_objects import (
    DenoiseParams,
    DoubleParams,
    FlagParams,
    HSParams,
    NullFPRParams,
    SwingParams,
    TimeSeries,
    TriangleParams,
)
from chart_decomp.domain import interfaces as ifaces


# ── Entities ────────────────────────────────────────────────────────────────

class TestSwingAndSkeleton:
    def test_swing_fields(self):
        s = Swing(index=12, price=101.5, kind="H")
        assert s.index == 12
        assert s.price == pytest.approx(101.5)
        assert s.kind == "H"

    def test_skeleton_views(self):
        swings = [
            Swing(0, 10.0, "L"),
            Swing(5, 20.0, "H"),
            Swing(9, 8.0, "L"),
        ]
        sk = SwingSkeleton(swings=swings)
        assert len(sk) == 3
        np.testing.assert_array_equal(sk.indices, np.array([0, 5, 9]))
        np.testing.assert_array_equal(sk.prices, np.array([10.0, 20.0, 8.0]))
        assert sk.kinds == ["L", "H", "L"]

    def test_empty_skeleton(self):
        sk = SwingSkeleton(swings=[])
        assert len(sk) == 0
        assert sk.indices.shape == (0,)
        assert sk.kinds == []


class TestDetection:
    def test_defaults(self):
        d = Detection(
            pattern="Head & Shoulders",
            start_index=10,
            end_index=40,
            pivots=[10, 18, 25, 33, 40],
            score=0.72,
        )
        assert d.null_percentile is None
        assert d.confirmed is True
        assert d.details == {}

    def test_details_are_independent(self):
        # field(default_factory=dict) — each instance gets its own dict
        a = Detection("Double Top", 0, 5, [0, 3, 5], 0.5)
        b = Detection("Double Top", 6, 9, [6, 8, 9], 0.6)
        a.details["x"] = 1
        assert b.details == {}

    def test_explicit_optional_fields(self):
        d = Detection(
            pattern="Bull Flag",
            start_index=0,
            end_index=20,
            pivots=[0, 10, 20],
            score=0.9,
            null_percentile=98.5,
            confirmed=False,
            details={"pole": 12.3},
        )
        assert d.null_percentile == pytest.approx(98.5)
        assert d.confirmed is False
        assert d.details["pole"] == pytest.approx(12.3)


class TestPatternPipelineResult:
    def test_construction(self):
        raw = np.linspace(0, 1, 50)
        den = raw * 0.99
        swings = [Swing(0, 0.0, "L"), Swing(49, 1.0, "H")]
        dets = [Detection("Ascending Triangle", 0, 49, [0, 49], 0.6)]
        res = PatternPipelineResult(
            raw=raw,
            denoised=den,
            swings=swings,
            detections=dets,
            fpr_by_pattern={"Ascending Triangle": 0.12},
        )
        assert res.raw.shape == (50,)
        assert res.denoised.shape == (50,)
        assert len(res.swings) == 2
        assert res.detections[0].pattern == "Ascending Triangle"
        assert res.fpr_by_pattern["Ascending Triangle"] == pytest.approx(0.12)


# ── Value objects: defaults, validation, immutability ─────────────────────────

class TestDenoiseParams:
    def test_defaults(self):
        p = DenoiseParams()
        assert (p.wavelet, p.level, p.k_drop, p.method) == ("sym8", 4, 1, "drop")

    def test_frozen(self):
        p = DenoiseParams()
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.k_drop = 2  # type: ignore[misc]

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"level": 0},          # level must be >= 1
            {"k_drop": -1},        # k_drop must be >= 0
            {"level": 2, "k_drop": 3},  # cannot drop more bands than levels
            {"method": "bogus"},   # method must be drop/soft/hard
        ],
    )
    def test_invalid(self, kwargs):
        with pytest.raises(InputValidationError):
            DenoiseParams(**kwargs)

    def test_k_drop_equal_level_ok(self):
        # dropping all detail bands (keep only approximation) is heavy but valid
        DenoiseParams(level=4, k_drop=4)


class TestSwingParams:
    def test_defaults(self):
        p = SwingParams()
        assert p.order == 10
        assert p.threshold_mode == "range_frac"
        assert p.threshold == pytest.approx(0.08)
        assert p.atr_period == 14
        assert p.min_gap == 8

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"order": 0},
            {"threshold": -0.1},
            {"atr_period": 0},
            {"min_gap": 0},
            {"threshold_mode": "percent_of_price"},  # forbidden as sole option (L4)
        ],
    )
    def test_invalid(self, kwargs):
        with pytest.raises(InputValidationError):
            SwingParams(**kwargs)

    @pytest.mark.parametrize("mode", ["range_frac", "atr", "absolute"])
    def test_valid_threshold_modes(self, mode):
        assert SwingParams(threshold_mode=mode).threshold_mode == mode


class TestDetectorParams:
    def test_hs_defaults_and_validation(self):
        assert HSParams().tol_shoulder == pytest.approx(0.35)
        assert HSParams().tol_neckline == pytest.approx(0.50)
        with pytest.raises(InputValidationError):
            HSParams(tol_shoulder=-0.1)

    def test_flag_defaults_and_validation(self):
        assert FlagParams().pole_min == pytest.approx(0.40)
        assert FlagParams().retr_max == pytest.approx(0.60)
        with pytest.raises(InputValidationError):
            FlagParams(retr_max=1.5)      # must be in (0, 1)
        with pytest.raises(InputValidationError):
            FlagParams(pole_min=0.0)      # must be > 0

    def test_triangle_defaults_and_validation(self):
        assert TriangleParams().min_pivots >= 4
        with pytest.raises(InputValidationError):
            TriangleParams(min_pivots=3)

    def test_double_defaults_and_validation(self):
        assert DoubleParams().tol_equal == pytest.approx(0.03)
        with pytest.raises(InputValidationError):
            DoubleParams(min_separation=0)


class TestNullFPRParams:
    def test_defaults(self):
        p = NullFPRParams()
        assert p.n_null == 1000
        assert p.noteworthy_pct == pytest.approx(95.0)
        assert p.seed is None

    @pytest.mark.parametrize("kwargs", [{"n_null": 0}, {"noteworthy_pct": 150.0}, {"noteworthy_pct": -1.0}])
    def test_invalid(self, kwargs):
        with pytest.raises(InputValidationError):
            NullFPRParams(**kwargs)

    def test_seed_is_accepted(self):
        assert NullFPRParams(seed=7).seed == 7


# ── Reuse of existing input wrapper ───────────────────────────────────────────

class TestTimeSeriesReuse:
    def test_timeseries_still_validates(self):
        # Part II reuses the existing TimeSeries VO; no parallel "PriceSeries".
        ts = TimeSeries(np.arange(10, dtype=float))
        assert len(ts) == 10
        with pytest.raises(InputValidationError):
            TimeSeries(np.array([1.0, np.nan, 3.0]))


# ── Interfaces are runtime-checkable Protocols ────────────────────────────────

class TestInterfaces:
    def test_protocols_exist(self):
        for name in ("IDenoiser", "ISwingExtractor", "IPatternDetector", "INullEvaluator"):
            assert hasattr(ifaces, name), f"missing Protocol {name}"

    def test_duck_typed_detector_isinstance(self):
        # A minimal object with the right shape should satisfy IPatternDetector
        class _Stub:
            name = "stub"

            def detect(self, skeleton, x, params=None):
                return []

        assert isinstance(_Stub(), ifaces.IPatternDetector)
