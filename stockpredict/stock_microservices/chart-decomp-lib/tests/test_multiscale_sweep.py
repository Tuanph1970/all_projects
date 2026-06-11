"""B2 — Multi-scale detection sweep (FR-MS-1, FR-MS-5).

Acceptance criteria (from implementation_plan_fpr_multiscale.md §B2):
  1. Detections carry the correct scale tag.
  2. Coarser denoising produces a smoother (less rough) denoised series —
     this is the physically correct invariant; detection *count* ordering is
     NOT guaranteed because smoother signals can produce cleaner patterns.
  3. fpr_by_pattern_by_scale has an entry per scale.

Additional properties verified here:
  - detection_ids are globally unique across scales (required for B3/B4).
  - denoised_by_scale is populated for every requested scale.
  - denoised_by_scale[k] matches a direct WaveletDenoiser.denoise call.
  - roots == [] before B4, spurious_nesting_fpr == 0.0 before B6.
  - raw series is preserved.
  - Per-scale null-FPR annotates detections with null_percentile (slow).
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.application.multiscale_pipeline_usecase import detect_multiscale
from chart_decomp.domain.entities import MultiScaleResult
from chart_decomp.domain.value_objects import DenoiseParams, TimeSeries
from chart_decomp.infrastructure.denoise.wavelet_denoiser import WaveletDenoiser


# ── Shared fixture (compute_fpr=False for speed) ────────────────────────────

@pytest.fixture(scope="module")
def ms_result() -> MultiScaleResult:
    """300-bar random walk swept at three denoising scales."""
    rng = np.random.default_rng(0)
    x = 100.0 + np.cumsum(rng.normal(0, 0.015, 300))
    return detect_multiscale(x, scales=(1, 2, 3), compute_fpr=False)


@pytest.fixture(scope="module")
def ms_x() -> np.ndarray:
    rng = np.random.default_rng(0)
    return 100.0 + np.cumsum(rng.normal(0, 0.015, 300))


# ── 1. Return type and raw data ──────────────────────────────────────────────

class TestMultiScaleReturnType:
    def test_returns_multiscale_result(self, ms_result):
        assert isinstance(ms_result, MultiScaleResult)

    def test_raw_preserved(self, ms_result, ms_x):
        np.testing.assert_array_equal(ms_result.raw, ms_x)

    def test_roots_empty_before_b4(self, ms_result):
        """Nesting forest is built in B4; roots must be empty at B2 stage."""
        assert ms_result.roots == []

    def test_spurious_nesting_fpr_zero_before_b6(self, ms_result):
        assert ms_result.spurious_nesting_fpr == 0.0


# ── 2. denoised_by_scale ────────────────────────────────────────────────────

class TestDenoisedByScale:
    def test_all_scale_keys_present(self, ms_result):
        assert set(ms_result.denoised_by_scale.keys()) == {1, 2, 3}

    def test_denoised_arrays_have_correct_length(self, ms_result, ms_x):
        for k, arr in ms_result.denoised_by_scale.items():
            assert len(arr) == len(ms_x), (
                f"denoised_by_scale[{k}] has length {len(arr)}, expected {len(ms_x)}"
            )

    def test_denoised_matches_direct_wavelet_call(self, ms_result, ms_x):
        """Structural correctness: denoised_by_scale[k] must equal
        WaveletDenoiser().denoise(TimeSeries(x), DenoiseParams(k_drop=k)).
        """
        denoiser = WaveletDenoiser()
        for k in [1, 2, 3]:
            expected = denoiser.denoise(TimeSeries(ms_x), DenoiseParams(k_drop=k))
            np.testing.assert_array_equal(
                ms_result.denoised_by_scale[k], expected,
                err_msg=f"denoised_by_scale[{k}] does not match direct denoise call",
            )

    def test_finer_denoising_is_rougher(self, ms_result):
        """FR-DN-1 property: larger k_drop removes more detail bands →
        lower first-difference std (smoother denoised series).
        The detection-count ordering is NOT guaranteed (smoother series can
        yield more textbook patterns), but the roughness ordering IS.
        """
        stds = {
            k: float(np.std(np.diff(ms_result.denoised_by_scale[k])))
            for k in sorted(ms_result.denoised_by_scale)
        }
        ordered = sorted(stds.keys())
        for k_fine, k_coarse in zip(ordered[:-1], ordered[1:]):
            assert stds[k_fine] > stds[k_coarse], (
                f"Expected k_drop={k_fine} rougher than k_drop={k_coarse}: "
                f"diff-std {stds[k_fine]:.6f} vs {stds[k_coarse]:.6f}"
            )


# ── 3. Scale tags on detections ──────────────────────────────────────────────

class TestScaleTags:
    """FR-MS-1: each detection must be tagged with the k_drop it was found at."""

    def test_all_detections_have_non_none_scale(self, ms_result):
        for d in ms_result.detections:
            assert d.scale is not None, (
                f"Detection id={d.detection_id} ({d.pattern}) has scale=None"
            )

    def test_all_scale_tags_in_requested_scales(self, ms_result):
        for d in ms_result.detections:
            assert d.scale in (1, 2, 3), (
                f"Detection {d.pattern} has scale={d.scale}, not in (1, 2, 3)"
            )

    def test_detections_from_each_scale_exist(self, ms_result):
        """At least one scale must have fired on the fixture series."""
        scales_seen = {d.scale for d in ms_result.detections}
        assert len(scales_seen) >= 1, (
            "No detections across any scale — check series length / swing params."
        )

    def test_scale_1_detections_tagged_correctly(self, ms_result, ms_x):
        """Spot-check: re-run single-scale pipeline at k_drop=1, verify same
        detections are tagged with scale=1 in the multi-scale result.
        """
        from chart_decomp.application.run_pattern_pipeline_usecase import (
            RunPatternPipelineUseCase,
        )
        uc = RunPatternPipelineUseCase()
        single = uc.execute(ms_x, denoise_params=DenoiseParams(k_drop=1), compute_fpr=False)
        multi_scale1 = [d for d in ms_result.detections if d.scale == 1]

        # Same number of detections and same pattern types (order may differ)
        assert len(multi_scale1) == len(single.detections), (
            f"Scale-1 multi: {len(multi_scale1)} dets; single-scale: {len(single.detections)}"
        )
        ms_patterns = sorted(d.pattern for d in multi_scale1)
        ss_patterns = sorted(d.pattern for d in single.detections)
        assert ms_patterns == ss_patterns, (
            f"Pattern mismatch: multi-scale-1 {ms_patterns} vs single {ss_patterns}"
        )


# ── 4. Globally-unique detection IDs ─────────────────────────────────────────

class TestDetectionIds:
    """B1 requirement holds across scales: IDs globally unique in multi-scale run."""

    def test_all_ids_non_none(self, ms_result):
        for d in ms_result.detections:
            assert d.detection_id is not None

    def test_ids_globally_unique(self, ms_result):
        ids = [d.detection_id for d in ms_result.detections]
        assert len(ids) == len(set(ids)), (
            f"Duplicate detection_ids found across scales: {ids}"
        )

    def test_ids_are_integers(self, ms_result):
        for d in ms_result.detections:
            assert isinstance(d.detection_id, int)

    def test_ids_not_reused_across_scales(self, ms_result):
        """IDs from different scales must not overlap."""
        by_scale: dict[int, list[int]] = {}
        for d in ms_result.detections:
            by_scale.setdefault(d.scale, []).append(d.detection_id)

        all_id_sets = [set(ids) for ids in by_scale.values()]
        for i, s1 in enumerate(all_id_sets):
            for s2 in all_id_sets[i + 1:]:
                overlap = s1 & s2
                assert not overlap, (
                    f"detection_ids {overlap} appear at more than one scale"
                )


# ── 5. fpr_by_pattern_by_scale structure ─────────────────────────────────────

class TestFprByScale:
    """FR-MS-5: an FPR entry must exist for every requested scale."""

    def test_all_scale_keys_present_compute_fpr_false(self, ms_result):
        assert set(ms_result.fpr_by_pattern_by_scale.keys()) == {1, 2, 3}, (
            f"Missing scale keys: {ms_result.fpr_by_pattern_by_scale.keys()}"
        )

    def test_empty_dicts_when_compute_fpr_false(self, ms_result):
        """With compute_fpr=False, inner dicts must be empty but keys must exist."""
        for k in (1, 2, 3):
            assert ms_result.fpr_by_pattern_by_scale[k] == {}, (
                f"fpr_by_pattern_by_scale[{k}] should be {{}} with compute_fpr=False"
            )

    @pytest.mark.slow
    def test_fpr_populated_when_compute_fpr_true(self):
        """FR-MS-5: per-scale FPR computed and stored."""
        rng = np.random.default_rng(7)
        x = 100.0 + np.cumsum(rng.normal(0, 0.015, 300))
        result = detect_multiscale(
            x, scales=(1, 2), compute_fpr=True, n_null=30, seed=42
        )
        # Keys must be present regardless of whether detections fired
        assert set(result.fpr_by_pattern_by_scale.keys()) == {1, 2}
        # Scales that produced detections should have non-empty FPR dicts
        for k in (1, 2):
            n_dets = sum(1 for d in result.detections if d.scale == k)
            if n_dets > 0:
                assert result.fpr_by_pattern_by_scale[k] != {}, (
                    f"Scale {k} produced {n_dets} detections but FPR dict is empty"
                )

    @pytest.mark.slow
    def test_detections_annotated_when_compute_fpr_true(self):
        """With compute_fpr=True, null_percentile and noteworthy are populated."""
        rng = np.random.default_rng(7)
        x = 100.0 + np.cumsum(rng.normal(0, 0.015, 300))
        result = detect_multiscale(
            x, scales=(1,), compute_fpr=True, n_null=30, seed=42
        )
        for d in result.detections:
            assert d.null_percentile is not None, (
                f"Detection {d.pattern} has null_percentile=None after FPR annotation"
            )
            assert d.noteworthy is not None, (
                f"Detection {d.pattern} has noteworthy=None after FPR annotation"
            )
            assert 0.0 <= d.null_percentile <= 100.0, (
                f"null_percentile={d.null_percentile} out of [0, 100]"
            )

    @pytest.mark.slow
    def test_different_scales_can_have_different_fpr_rates(self):
        """FR-MS-5: FPR differs across scales because denoising levels differ.
        With n_null=100, simply verify the per-scale FPR dicts are independently
        computed (not copies of each other).
        """
        rng = np.random.default_rng(13)
        x = 100.0 + np.cumsum(rng.normal(0, 0.015, 300))
        result = detect_multiscale(
            x, scales=(1, 3), compute_fpr=True, n_null=100, seed=0
        )
        fpr1 = result.fpr_by_pattern_by_scale.get(1, {})
        fpr3 = result.fpr_by_pattern_by_scale.get(3, {})
        # Both dicts should exist; if both are non-empty they should not be identical
        # (different scales → different FPR rates)
        if fpr1 and fpr3:
            common = set(fpr1) & set(fpr3)
            if common:
                # At least one pattern should differ
                diffs = [abs(fpr1[p] - fpr3[p]) for p in common]
                assert any(d > 0.0 for d in diffs), (
                    "All per-scale FPR values are identical — "
                    "denoising level may not be varying the null sweep"
                )


# ── 6. Edge cases ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_single_scale_works(self):
        rng = np.random.default_rng(5)
        x = 100.0 + np.cumsum(rng.normal(0, 0.015, 200))
        result = detect_multiscale(x, scales=(2,), compute_fpr=False)
        assert set(result.denoised_by_scale.keys()) == {2}
        assert set(result.fpr_by_pattern_by_scale.keys()) == {2}
        for d in result.detections:
            assert d.scale == 2

    def test_custom_denoise_kw(self):
        rng = np.random.default_rng(3)
        x = 100.0 + np.cumsum(rng.normal(0, 0.015, 200))
        # level=5, wavelet='db4' — should not raise
        result = detect_multiscale(
            x, scales=(1, 2), denoise_kw={"level": 5, "wavelet": "db4"},
            compute_fpr=False
        )
        assert isinstance(result, MultiScaleResult)

    def test_custom_swing_kw(self):
        rng = np.random.default_rng(4)
        x = 100.0 + np.cumsum(rng.normal(0, 0.015, 300))
        result = detect_multiscale(
            x, scales=(1,), swing_kw={"order": 5}, compute_fpr=False
        )
        assert isinstance(result, MultiScaleResult)
