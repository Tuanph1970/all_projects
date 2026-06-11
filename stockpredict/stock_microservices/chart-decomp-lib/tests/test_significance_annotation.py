"""A4 — annotate_significance: populate null_percentile + noteworthy (FR-FPR-2).

Mandatory tests:
  - Known-junk test: detection with a deliberately low score is marked NOT noteworthy.
  - Detection with score above null pct95 is marked noteworthy.
  - null_percentile is in [0, 100] for every annotated detection.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.domain.entities import Detection
from chart_decomp.infrastructure.validation.null_fpr import (
    NullDistribution,
    PatternThresholds,
    annotate_significance,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_det(pattern: str, score: float) -> Detection:
    return Detection(
        pattern=pattern,
        start_index=0,
        end_index=50,
        pivots=[0, 10, 20, 30, 40, 50],
        score=score,
    )


def _make_dist(
    scores_dict: dict[str, np.ndarray],
    n_null: int = 20,
) -> NullDistribution:
    """Build a NullDistribution with one detection per surrogate per pattern."""
    counts = {p: np.ones(n_null, dtype=np.intp) for p in scores_dict}
    return NullDistribution(
        scores_by_pattern={p: np.asarray(s, dtype=np.float64) for p, s in scores_dict.items()},
        counts_by_pattern=counts,
        n_null=n_null,
        length=200,
        volatility=0.01,
    )


def _zigzag(control, n):
    idxs   = [c[0] for c in control]
    prices = [c[1] for c in control]
    return np.interp(np.arange(n), idxs, prices).astype(float)


_HS_CTRL = [
    (0, 80), (80, 130), (120, 100), (160, 160), (200, 102), (230, 132), (260, 90),
    (299, 90),
]
_HS_N = 300


# ── Detection field defaults ──────────────────────────────────────────────────

class TestDetectionDefaults:
    """New fields default to None before annotation (backward-compatible)."""

    def test_null_percentile_defaults_to_none(self):
        det = _make_det("Pat", score=0.5)
        assert det.null_percentile is None

    def test_noteworthy_defaults_to_none(self):
        det = _make_det("Pat", score=0.5)
        assert det.noteworthy is None

    def test_existing_fields_unaffected(self):
        det = _make_det("Pat", score=0.5)
        assert det.score == pytest.approx(0.5)
        assert det.confirmed is True
        assert det.details == {}


# ── MANDATORY: known-junk test ────────────────────────────────────────────────

class TestKnownJunkNotNoteworthy:
    """The null-FPR gate: a low-quality detection must be rejected (FR-FPR-2)."""

    def test_low_score_descending_triangle_not_noteworthy(self):
        # 100 uniform scores in [0, 1] → pct95 ≈ 0.95.
        # Score 0.25 is well below that → NOT noteworthy.
        scores = np.linspace(0.0, 1.0, 100)
        dist   = _make_dist({"DescTriangle": scores}, n_null=100)
        det    = _make_det("DescTriangle", score=0.25)
        annotate_significance([det], dist)
        assert det.noteworthy is False, (
            f"Low-score detection (score=0.25) should be NOT noteworthy; "
            f"pct95≈{float(np.quantile(scores, 0.95)):.3f}"
        )

    def test_score_at_5th_percentile_not_noteworthy(self):
        rng    = np.random.default_rng(0)
        scores = rng.uniform(0.4, 1.0, 200)
        dist   = _make_dist({"BullFlag": scores}, n_null=20)
        # Score equal to the 10th percentile of the null distribution
        low_score = float(np.quantile(scores, 0.10))
        det = _make_det("BullFlag", score=low_score)
        annotate_significance([det], dist)
        assert det.noteworthy is False

    def test_score_just_below_pct95_not_noteworthy(self):
        scores = np.linspace(0.0, 1.0, 1000)
        dist   = _make_dist({"Pat": scores}, n_null=20)
        pct95  = float(np.quantile(scores, 0.95))
        # Score slightly below threshold
        det = _make_det("Pat", score=pct95 - 1e-6)
        annotate_significance([det], dist)
        assert det.noteworthy is False


# ── Noteworthy when above threshold ──────────────────────────────────────────

class TestAboveThresholdIsNoteworthy:
    def test_high_score_is_noteworthy(self):
        scores = np.linspace(0.0, 1.0, 100)
        dist   = _make_dist({"DescTriangle": scores})
        det    = _make_det("DescTriangle", score=0.99)
        annotate_significance([det], dist)
        assert det.noteworthy is True

    def test_score_strictly_above_pct95_is_noteworthy(self):
        scores = np.linspace(0.0, 1.0, 1000)
        dist   = _make_dist({"Pat": scores})
        pct95  = float(np.quantile(scores, 0.95))
        det = _make_det("Pat", score=pct95 + 1e-6)
        annotate_significance([det], dist)
        assert det.noteworthy is True

    def test_score_equal_to_pct95_not_noteworthy(self):
        # Strict greater-than: score == pct95 is NOT noteworthy
        scores = np.linspace(0.0, 1.0, 1000)
        dist   = _make_dist({"Pat": scores})
        pct95  = float(np.quantile(scores, 0.95))
        det = _make_det("Pat", score=pct95)
        annotate_significance([det], dist)
        assert det.noteworthy is False


# ── null_percentile correctness ───────────────────────────────────────────────

class TestNullPercentileRange:
    """null_percentile must be a float in [0, 100] for every annotated detection."""

    def test_percentile_in_range_for_multiple_scores(self):
        scores = np.linspace(0.0, 1.0, 200)
        dist   = _make_dist({"Pat": scores}, n_null=20)
        dets   = [_make_det("Pat", score=s) for s in [0.0, 0.1, 0.5, 0.9, 1.0]]
        annotate_significance(dets, dist)
        for d in dets:
            assert d.null_percentile is not None, "null_percentile not set"
            assert 0.0 <= d.null_percentile <= 100.0, (
                f"null_percentile={d.null_percentile} out of [0, 100]"
            )

    def test_percentile_rank_correctness(self):
        # scores = [0.0, 0.1, ..., 0.9] (10 values).
        # Detection score = 0.5 → 6 null scores <= 0.5 → rank = 60.0.
        scores = np.arange(0.0, 1.0, 0.1)   # [0.0, 0.1, ..., 0.9], len=10
        dist   = _make_dist({"Pat": scores}, n_null=10)
        det    = _make_det("Pat", score=0.5)
        annotate_significance([det], dist)
        assert det.null_percentile == pytest.approx(60.0)

    def test_percentile_is_python_float(self):
        scores = np.linspace(0.0, 1.0, 50)
        dist   = _make_dist({"Pat": scores})
        det    = _make_det("Pat", score=0.5)
        annotate_significance([det], dist)
        assert isinstance(det.null_percentile, float)


# ── Sentinel: pattern never fired on null ─────────────────────────────────────

class TestSentinelPattern:
    """Pattern absent from null → noteworthy=True, null_percentile=100.0 (FR-FPR-2)."""

    def test_never_fired_pattern_is_noteworthy(self):
        dist = _make_dist({})          # empty null distribution
        det  = _make_det("GhostPat", score=0.5)
        annotate_significance([det], dist)
        assert det.noteworthy is True

    def test_never_fired_pattern_percentile_is_100(self):
        dist = _make_dist({})
        det  = _make_det("GhostPat", score=0.5)
        annotate_significance([det], dist)
        assert det.null_percentile == pytest.approx(100.0)

    def test_sentinel_alongside_real_pattern(self):
        scores = np.linspace(0.0, 1.0, 100)
        dist   = _make_dist({"Real": scores})
        det_ghost = _make_det("GhostPat", score=0.5)
        det_real  = _make_det("Real", score=0.25)
        annotate_significance([det_ghost, det_real], dist)
        # Ghost: unconditionally noteworthy
        assert det_ghost.noteworthy is True
        assert det_ghost.null_percentile == pytest.approx(100.0)
        # Real: low score → not noteworthy
        assert det_real.noteworthy is False


# ── Multiple patterns annotated independently ─────────────────────────────────

class TestMultiplePatterns:
    def test_patterns_annotated_independently(self):
        # PatA: pct95 ≈ 0.57 (scores in [0, 0.6])
        # PatB: pct95 ≈ 0.95 (scores in [0, 1.0])
        scores_a = np.linspace(0.0, 0.6, 50)
        scores_b = np.linspace(0.0, 1.0, 50)
        dist = _make_dist({"PatA": scores_a, "PatB": scores_b})
        det_a = _make_det("PatA", score=0.62)   # above PatA pct95≈0.57 → noteworthy
        det_b = _make_det("PatB", score=0.50)   # below PatB pct95≈0.95 → NOT noteworthy
        annotate_significance([det_a, det_b], dist)
        assert det_a.noteworthy is True,  f"PatA score=0.62 should beat pct95={float(np.quantile(scores_a, 0.95)):.3f}"
        assert det_b.noteworthy is False, f"PatB score=0.50 should not beat pct95={float(np.quantile(scores_b, 0.95)):.3f}"

    def test_each_detection_has_independent_percentile(self):
        scores_a = np.linspace(0.0, 0.5, 100)
        scores_b = np.linspace(0.5, 1.0, 100)
        dist = _make_dist({"A": scores_a, "B": scores_b})
        det_a = _make_det("A", score=0.4)
        det_b = _make_det("B", score=0.8)
        annotate_significance([det_a, det_b], dist)
        # Both ranks must be in [0, 100] and computed from their own null arrays
        assert 0.0 <= det_a.null_percentile <= 100.0
        assert 0.0 <= det_b.null_percentile <= 100.0
        # 0.8 in [0.5, 1.0] is around the 60th pct; 0.4 in [0.0, 0.5] ≈ 80th pct
        # Exact values don't matter — just ensure they differ
        assert det_a.null_percentile != pytest.approx(det_b.null_percentile, abs=5.0)


# ── Return value ──────────────────────────────────────────────────────────────

class TestReturnValue:
    def test_returns_thresholds_dict(self):
        scores = np.linspace(0.0, 1.0, 50)
        dist   = _make_dist({"Pat": scores})
        det    = _make_det("Pat", score=0.5)
        result = annotate_significance([det], dist)
        assert isinstance(result, dict)

    def test_thresholds_dict_contains_detection_patterns(self):
        scores = np.linspace(0.0, 1.0, 50)
        dist   = _make_dist({"Pat": scores})
        det    = _make_det("Pat", score=0.5)
        result = annotate_significance([det], dist)
        assert "Pat" in result
        assert isinstance(result["Pat"], PatternThresholds)

    def test_thresholds_dict_includes_sentinel_patterns(self):
        dist   = _make_dist({})
        det    = _make_det("Ghost", score=0.5)
        result = annotate_significance([det], dist)
        assert "Ghost" in result
        assert result["Ghost"].pct95 is None


# ── Integration: full pipeline sets both fields ───────────────────────────────

class TestPipelineAnnotation:
    def test_noteworthy_set_when_compute_fpr_true(self):
        from chart_decomp import run_pattern_pipeline
        from chart_decomp.domain.value_objects import NullFPRParams

        x = _zigzag(_HS_CTRL, _HS_N)
        r = run_pattern_pipeline(
            x,
            compute_fpr=True,
            fpr_params=NullFPRParams(n_null=20, seed=0),
        )
        for d in r.detections:
            assert d.noteworthy is not None, f"{d.pattern}: noteworthy not set"
            assert isinstance(d.noteworthy, bool), f"{d.pattern}: noteworthy not bool"

    def test_null_percentile_in_range_when_compute_fpr_true(self):
        from chart_decomp import run_pattern_pipeline
        from chart_decomp.domain.value_objects import NullFPRParams

        x = _zigzag(_HS_CTRL, _HS_N)
        r = run_pattern_pipeline(
            x,
            compute_fpr=True,
            fpr_params=NullFPRParams(n_null=20, seed=0),
        )
        for d in r.detections:
            assert d.null_percentile is not None, f"{d.pattern}: null_percentile not set"
            assert 0.0 <= d.null_percentile <= 100.0, (
                f"{d.pattern}: null_percentile={d.null_percentile} outside [0, 100]"
            )

    def test_noteworthy_none_when_compute_fpr_false(self):
        from chart_decomp import run_pattern_pipeline

        x = _zigzag(_HS_CTRL, _HS_N)
        r = run_pattern_pipeline(x, compute_fpr=False)
        for d in r.detections:
            assert d.noteworthy is None

    def test_null_percentile_none_when_compute_fpr_false(self):
        from chart_decomp import run_pattern_pipeline

        x = _zigzag(_HS_CTRL, _HS_N)
        r = run_pattern_pipeline(x, compute_fpr=False)
        for d in r.detections:
            assert d.null_percentile is None
