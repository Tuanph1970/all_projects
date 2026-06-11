"""B1 — Detection type extended with multi-scale fields (FR-MS).

Acceptance criteria:
  1. Existing single-scale code constructs Detection without passing new fields
     (backward-compatible defaults).
  2. Every detection returned by the pipeline has a unique, non-None detection_id.
  3. MultiScaleResult type exists and is constructable with the expected fields.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.domain.entities import Detection, MultiScaleResult, PatternPipelineResult


# ── 1. Backward-compatible defaults ───────────────────────────────────────────

class TestDetectionBackwardCompat:
    """Existing call sites that do not pass the new multi-scale fields must work."""

    def _minimal(self) -> Detection:
        return Detection(
            pattern="Head & Shoulders",
            start_index=0,
            end_index=50,
            pivots=[0, 10, 25, 40, 50],
            score=0.8,
        )

    def test_construct_without_new_fields(self):
        d = self._minimal()
        assert d.pattern == "Head & Shoulders"
        assert d.score == 0.8

    def test_null_percentile_defaults_none(self):
        assert self._minimal().null_percentile is None

    def test_noteworthy_defaults_none(self):
        assert self._minimal().noteworthy is None

    def test_confirmed_defaults_true(self):
        assert self._minimal().confirmed is True

    def test_detection_id_defaults_none(self):
        d = self._minimal()
        # detection_id is None until the pipeline/registry assigns it
        assert d.detection_id is None

    def test_scale_defaults_none(self):
        assert self._minimal().scale is None

    def test_also_seen_at_scales_defaults_empty(self):
        d = self._minimal()
        assert d.also_seen_at_scales == []

    def test_parent_id_defaults_none(self):
        assert self._minimal().parent_id is None

    def test_children_ids_defaults_empty(self):
        d = self._minimal()
        assert d.children_ids == []

    def test_nesting_depth_defaults_zero(self):
        assert self._minimal().nesting_depth == 0

    def test_directional_bias_defaults_none(self):
        assert self._minimal().directional_bias is None

    def test_relation_to_parent_defaults_none(self):
        assert self._minimal().relation_to_parent is None

    def test_also_seen_at_scales_is_independent_between_instances(self):
        """Mutable list defaults must not be shared across instances."""
        d1 = self._minimal()
        d2 = self._minimal()
        d1.also_seen_at_scales.append(2)
        assert d2.also_seen_at_scales == []

    def test_children_ids_is_independent_between_instances(self):
        d1 = self._minimal()
        d2 = self._minimal()
        d1.children_ids.append(99)
        assert d2.children_ids == []


# ── 2. Pipeline assigns unique detection_ids ──────────────────────────────────

class TestPipelineDetectionIds:
    """Every detection from the pipeline must have a unique, non-None detection_id."""

    @pytest.fixture(scope="class")
    def pipeline_detections(self):
        """Run the single-scale pipeline on a series long enough to yield ≥1 detection."""
        from chart_decomp.application.run_pattern_pipeline_usecase import (
            RunPatternPipelineUseCase,
        )
        from chart_decomp.domain.value_objects import DenoiseParams, NullFPRParams

        rng = np.random.default_rng(42)
        # Synthesise a 300-bar random-walk with moderate volatility
        returns = rng.normal(0, 0.01, 300)
        x = 100.0 + np.cumsum(returns)

        uc = RunPatternPipelineUseCase()
        result = uc.execute(
            x,
            denoise_params=DenoiseParams(k_drop=1),
            compute_fpr=False,
        )
        return result.detections

    def test_all_detection_ids_are_not_none(self, pipeline_detections):
        assert all(d.detection_id is not None for d in pipeline_detections), (
            "Some detections have detection_id=None; the registry must assign IDs."
        )

    def test_all_detection_ids_are_unique(self, pipeline_detections):
        ids = [d.detection_id for d in pipeline_detections]
        assert len(ids) == len(set(ids)), (
            f"Duplicate detection_ids found: {ids}"
        )

    def test_detection_ids_are_integers(self, pipeline_detections):
        assert all(isinstance(d.detection_id, int) for d in pipeline_detections)

    def test_new_fields_are_at_defaults_after_single_scale_run(self, pipeline_detections):
        """Fields introduced for multi-scale must remain at their single-scale defaults."""
        for d in pipeline_detections:
            assert d.scale is None, f"scale should be None in single-scale run; got {d.scale}"
            assert d.also_seen_at_scales == [], (
                f"also_seen_at_scales should be [] in single-scale run; got {d.also_seen_at_scales}"
            )
            assert d.parent_id is None
            assert d.children_ids == []
            assert d.nesting_depth == 0
            assert d.directional_bias is None
            assert d.relation_to_parent is None


# ── 3. MultiScaleResult type ──────────────────────────────────────────────────

class TestMultiScaleResultType:
    """MultiScaleResult must exist with the required fields (MS.4)."""

    def _make(self) -> MultiScaleResult:
        x = np.arange(10, dtype=float)
        return MultiScaleResult(
            raw=x,
            denoised_by_scale={1: x.copy(), 2: x.copy()},
            detections=[],
            roots=[],
            fpr_by_pattern_by_scale={1: {}, 2: {}},
            spurious_nesting_fpr=0.0,
        )

    def test_construct(self):
        r = self._make()
        assert isinstance(r, MultiScaleResult)

    def test_raw_field(self):
        r = self._make()
        assert len(r.raw) == 10

    def test_denoised_by_scale_keys(self):
        r = self._make()
        assert set(r.denoised_by_scale.keys()) == {1, 2}

    def test_detections_field(self):
        r = self._make()
        assert r.detections == []

    def test_roots_field(self):
        r = self._make()
        assert r.roots == []

    def test_fpr_by_pattern_by_scale_field(self):
        r = self._make()
        assert set(r.fpr_by_pattern_by_scale.keys()) == {1, 2}

    def test_spurious_nesting_fpr_defaults_zero(self):
        x = np.arange(5, dtype=float)
        r = MultiScaleResult(
            raw=x,
            denoised_by_scale={},
            detections=[],
            roots=[],
            fpr_by_pattern_by_scale={},
        )
        assert r.spurious_nesting_fpr == 0.0

    def test_detections_with_ids(self):
        """MultiScaleResult holds Detections that carry detection_ids."""
        d = Detection(
            pattern="Bull Flag",
            start_index=10,
            end_index=40,
            pivots=[10, 25, 40],
            score=0.75,
            detection_id=0,
            scale=1,
        )
        x = np.arange(50, dtype=float)
        r = MultiScaleResult(
            raw=x,
            denoised_by_scale={1: x},
            detections=[d],
            roots=[0],
            fpr_by_pattern_by_scale={1: {"Bull Flag": 0.3}},
            spurious_nesting_fpr=0.05,
        )
        assert r.detections[0].detection_id == 0
        assert r.detections[0].scale == 1
        assert r.roots == [0]
        assert r.spurious_nesting_fpr == pytest.approx(0.05)


# ── 4. Manual field assignment (mutable dataclass) ────────────────────────────

class TestDetectionFieldAssignment:
    """Multi-scale fields can be set after construction (Detection is not frozen)."""

    def test_set_scale(self):
        d = Detection("Double Top", 0, 30, [0, 15, 30], 0.9)
        d.scale = 2
        assert d.scale == 2

    def test_set_parent_id(self):
        d = Detection("Bull Flag", 5, 20, [5, 12, 20], 0.7)
        d.parent_id = 0
        assert d.parent_id == 0

    def test_set_nesting_depth(self):
        d = Detection("Bear Flag", 0, 40, [0, 20, 40], 0.65)
        d.nesting_depth = 1
        assert d.nesting_depth == 1

    def test_set_directional_bias(self):
        d = Detection("Head & Shoulders", 0, 60, [0, 20, 40, 50, 60], 0.85)
        d.directional_bias = "bearish"
        assert d.directional_bias == "bearish"

    def test_set_relation_to_parent(self):
        d = Detection("Bull Flag", 10, 30, [10, 20, 30], 0.7)
        d.relation_to_parent = "conflict"
        assert d.relation_to_parent == "conflict"

    def test_append_to_also_seen_at_scales(self):
        d = Detection("Symmetric Triangle", 0, 50, [0, 10, 20, 30, 40, 50], 0.8)
        d.also_seen_at_scales.append(3)
        assert d.also_seen_at_scales == [3]

    def test_append_to_children_ids(self):
        d = Detection("Head & Shoulders", 0, 80, [0, 10, 40, 70, 80], 0.9)
        d.children_ids.extend([1, 2])
        assert d.children_ids == [1, 2]
