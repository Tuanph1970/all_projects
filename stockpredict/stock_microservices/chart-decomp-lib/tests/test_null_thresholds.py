"""A3 — null_thresholds: pct95 + FPR from NullDistribution (FR-FPR-1/2).

Tests:
  - pct95 lies within [min, max] of the score array and equals np.quantile(scores, 0.95).
  - A pattern type never produced on nulls yields a sentinel (pct95=None, fpr=0.0),
    handled without error.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.infrastructure.validation.null_fpr import (
    NullDistribution,
    PatternThresholds,
    clear_null_distribution_cache,
    null_detection_distribution,
    null_thresholds,
)


# ── Test helpers ──────────────────────────────────────────────────────────────

def _dist(
    data: dict[str, tuple[np.ndarray, np.ndarray]],
    n_null: int = 20,
) -> NullDistribution:
    """Build a NullDistribution from {pattern: (scores_arr, counts_arr)}."""
    return NullDistribution(
        scores_by_pattern={p: np.asarray(s, dtype=np.float64) for p, (s, _) in data.items()},
        counts_by_pattern={p: np.asarray(c, dtype=np.intp)    for p, (_, c) in data.items()},
        n_null=n_null,
        length=200,
        volatility=0.01,
    )


def _uniform_dist(pat: str = "Pat", n: int = 100) -> NullDistribution:
    """Uniform scores in [0.1, 0.9] with one detection per surrogate."""
    scores = np.linspace(0.1, 0.9, n)
    counts = np.ones(20, dtype=np.intp)
    return _dist({pat: (scores, counts)})


# ── Return type ───────────────────────────────────────────────────────────────

class TestReturnType:
    def test_returns_dict(self):
        result = null_thresholds(_uniform_dist())
        assert isinstance(result, dict)

    def test_values_are_pattern_thresholds(self):
        result = null_thresholds(_uniform_dist())
        for val in result.values():
            assert isinstance(val, PatternThresholds)

    def test_keys_match_distribution_patterns(self):
        scores_a = np.linspace(0.2, 0.8, 50)
        scores_b = np.linspace(0.3, 0.9, 30)
        dist = _dist({
            "Alpha": (scores_a, np.ones(20, dtype=np.intp)),
            "Beta":  (scores_b, np.ones(20, dtype=np.intp)),
        })
        result = null_thresholds(dist)
        assert set(result.keys()) == {"Alpha", "Beta"}


# ── pct95 correctness ─────────────────────────────────────────────────────────

class TestPct95:
    """pct95 equals np.quantile(scores, 0.95) and lies within [min, max]."""

    def test_equals_np_quantile(self):
        scores = np.linspace(0.1, 0.9, 100)
        dist = _dist({"Pat": (scores, np.ones(20, dtype=np.intp))})
        result = null_thresholds(dist)
        assert result["Pat"].pct95 == pytest.approx(float(np.quantile(scores, 0.95)))

    def test_within_score_range(self):
        scores = np.array([0.20, 0.35, 0.50, 0.62, 0.78])
        dist = _dist({"Pat": (scores, np.ones(5, dtype=np.intp))})
        result = null_thresholds(dist)
        pct95 = result["Pat"].pct95
        assert scores.min() <= pct95 <= scores.max()

    def test_within_range_for_skewed_scores(self):
        rng = np.random.default_rng(0)
        scores = np.abs(rng.standard_t(df=3, size=200)).clip(0.0, 1.0)
        dist = _dist({"Pat": (scores, np.ones(20, dtype=np.intp))})
        result = null_thresholds(dist)
        pct95 = result["Pat"].pct95
        assert scores.min() <= pct95 <= scores.max()
        assert pct95 == pytest.approx(float(np.quantile(scores, 0.95)))

    def test_custom_noteworthy_pct_50(self):
        scores = np.linspace(0.0, 1.0, 1000)
        dist = _dist({"Pat": (scores, np.ones(20, dtype=np.intp))})
        result = null_thresholds(dist, noteworthy_pct=50.0)
        assert result["Pat"].pct95 == pytest.approx(float(np.quantile(scores, 0.50)))

    def test_custom_noteworthy_pct_99(self):
        scores = np.linspace(0.0, 1.0, 1000)
        dist = _dist({"Pat": (scores, np.ones(20, dtype=np.intp))})
        result = null_thresholds(dist, noteworthy_pct=99.0)
        assert result["Pat"].pct95 == pytest.approx(float(np.quantile(scores, 0.99)))

    def test_pct95_is_python_float(self):
        dist = _uniform_dist()
        result = null_thresholds(dist)
        assert isinstance(result["Pat"].pct95, float)

    def test_multiple_patterns_independent(self):
        s1 = np.linspace(0.1, 0.5, 100)
        s2 = np.linspace(0.6, 0.9, 80)
        dist = _dist({
            "Low":  (s1, np.ones(20, dtype=np.intp)),
            "High": (s2, np.ones(20, dtype=np.intp)),
        })
        result = null_thresholds(dist)
        assert result["Low"].pct95  == pytest.approx(float(np.quantile(s1, 0.95)))
        assert result["High"].pct95 == pytest.approx(float(np.quantile(s2, 0.95)))


# ── FPR correctness ───────────────────────────────────────────────────────────

class TestFPR:
    """fpr equals the mean of the per-surrogate count array."""

    def test_fpr_equals_mean_counts(self):
        # 8 surrogates; pattern fired 0/1/0/2/1/0/0/1 times → mean = 5/8
        counts = np.array([0, 1, 0, 2, 1, 0, 0, 1], dtype=np.intp)
        scores = np.linspace(0.3, 0.9, int(counts.sum()))  # 5 scores
        dist = _dist({"Pat": (scores, counts)}, n_null=len(counts))
        result = null_thresholds(dist)
        assert result["Pat"].fpr == pytest.approx(float(counts.mean()))

    def test_fpr_is_python_float(self):
        dist = _uniform_dist()
        result = null_thresholds(dist)
        assert isinstance(result["Pat"].fpr, float)

    def test_fpr_non_negative(self):
        dist = _uniform_dist()
        result = null_thresholds(dist)
        assert result["Pat"].fpr >= 0.0


# ── Sentinel for never-produced patterns ─────────────────────────────────────

class TestSentinel:
    """Never-fired patterns in extra_patterns yield pct95=None, fpr=0.0."""

    def test_pct95_is_none_for_never_fired(self):
        dist = _dist({})  # empty distribution
        result = null_thresholds(dist, extra_patterns=["Ghost"])
        assert result["Ghost"].pct95 is None

    def test_fpr_is_zero_for_never_fired(self):
        dist = _dist({})
        result = null_thresholds(dist, extra_patterns=["Ghost"])
        assert result["Ghost"].fpr == 0.0

    def test_sentinel_alongside_real_pattern(self):
        scores = np.linspace(0.2, 0.8, 50)
        dist = _dist({"Real": (scores, np.ones(20, dtype=np.intp))})
        result = null_thresholds(dist, extra_patterns=["Ghost"])
        # Sentinel for never-fired
        assert result["Ghost"].pct95 is None
        assert result["Ghost"].fpr == 0.0
        # Real pattern still computed correctly
        assert result["Real"].pct95 == pytest.approx(float(np.quantile(scores, 0.95)))

    def test_multiple_never_fired_no_error(self):
        dist = _dist({})
        result = null_thresholds(dist, extra_patterns=["A", "B", "C"])
        for pat in ["A", "B", "C"]:
            assert result[pat].pct95 is None
            assert result[pat].fpr == 0.0

    def test_extra_patterns_does_not_overwrite_existing(self):
        scores = np.linspace(0.1, 0.9, 100)
        dist = _dist({"Real": (scores, np.ones(20, dtype=np.intp))})
        # "Real" is in extra_patterns too — should not be overwritten with sentinel
        result = null_thresholds(dist, extra_patterns=["Real", "Ghost"])
        assert result["Real"].pct95 is not None
        assert result["Real"].pct95 == pytest.approx(float(np.quantile(scores, 0.95)))

    def test_no_extra_patterns_no_sentinel_in_output(self):
        dist = _dist({})
        result = null_thresholds(dist)
        assert result == {}

    def test_extra_patterns_none_is_default(self):
        dist = _uniform_dist()
        result_default = null_thresholds(dist)
        result_explicit = null_thresholds(dist, None)
        assert set(result_default.keys()) == set(result_explicit.keys())


# ── Integration with A2 null_detection_distribution ──────────────────────────

class TestIntegration:
    """null_thresholds on a real NullDistribution matches direct np.quantile."""

    def test_pct95_matches_raw_scores(self):
        clear_null_distribution_cache()
        dist = null_detection_distribution(200, 0.01, n_null=20, seed=0)
        result = null_thresholds(dist)
        for pat, thresh in result.items():
            expected = float(np.quantile(dist.scores_by_pattern[pat], 0.95))
            assert thresh.pct95 == pytest.approx(expected), (
                f"{pat}: pct95={thresh.pct95} != np.quantile={expected}"
            )

    def test_fpr_matches_mean_counts(self):
        clear_null_distribution_cache()
        dist = null_detection_distribution(200, 0.01, n_null=20, seed=1)
        result = null_thresholds(dist)
        for pat, thresh in result.items():
            expected = float(dist.counts_by_pattern[pat].mean())
            assert thresh.fpr == pytest.approx(expected), (
                f"{pat}: fpr={thresh.fpr} != mean(counts)={expected}"
            )
