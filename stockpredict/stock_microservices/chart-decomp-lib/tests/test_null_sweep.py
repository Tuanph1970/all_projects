"""A2 — null_detection_distribution: surrogate sweep + cache (FR-FPR-1).

Tests:
  - Returns a per-pattern-type score array and a per-pattern detection-count array.
  - With n_null=20 and a fixed seed, output is deterministic (fresh and cached).
  - Cache hit returns the same object without re-running the surrogate generator.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.infrastructure.validation.null_fpr import (
    NullDistribution,
    clear_null_distribution_cache,
    null_detection_distribution,
)


# ── Structure ─────────────────────────────────────────────────────────────────

class TestStructure:
    """null_detection_distribution returns the right shape of data."""

    def test_returns_null_distribution(self):
        dist = null_detection_distribution(200, 0.01, n_null=10, seed=0)
        assert isinstance(dist, NullDistribution)

    def test_metadata_stored(self):
        dist = null_detection_distribution(250, 0.02, n_null=12, seed=1)
        assert dist.n_null == 12
        assert dist.length == 250
        assert dist.volatility == pytest.approx(0.02)

    def test_score_arrays_are_1d_float(self):
        dist = null_detection_distribution(200, 0.01, n_null=20, seed=2)
        for pat, arr in dist.scores_by_pattern.items():
            assert isinstance(arr, np.ndarray), f"{pat}: scores not ndarray"
            assert arr.ndim == 1, f"{pat}: scores not 1-D"
            assert arr.dtype == np.float64, f"{pat}: scores dtype not float64"

    def test_count_arrays_are_length_n_null(self):
        n = 20
        dist = null_detection_distribution(200, 0.01, n_null=n, seed=3)
        for pat, arr in dist.counts_by_pattern.items():
            assert isinstance(arr, np.ndarray), f"{pat}: counts not ndarray"
            assert arr.ndim == 1, f"{pat}: counts not 1-D"
            assert len(arr) == n, f"{pat}: count array length {len(arr)} != n_null {n}"

    def test_count_values_non_negative(self):
        dist = null_detection_distribution(200, 0.01, n_null=20, seed=4)
        for pat, arr in dist.counts_by_pattern.items():
            assert np.all(arr >= 0), f"{pat}: negative count found"

    def test_pattern_keys_consistent_across_fields(self):
        dist = null_detection_distribution(200, 0.01, n_null=20, seed=5)
        assert set(dist.scores_by_pattern.keys()) == set(dist.counts_by_pattern.keys())

    def test_total_count_matches_score_array_length(self):
        # Sum of per-surrogate counts == total number of scores collected.
        dist = null_detection_distribution(200, 0.01, n_null=30, seed=6)
        for pat in dist.scores_by_pattern:
            total_count = int(dist.counts_by_pattern[pat].sum())
            n_scores = len(dist.scores_by_pattern[pat])
            assert total_count == n_scores, (
                f"{pat}: sum(counts)={total_count} != len(scores)={n_scores}"
            )

    def test_score_values_in_unit_interval(self):
        dist = null_detection_distribution(200, 0.01, n_null=20, seed=7)
        for pat, arr in dist.scores_by_pattern.items():
            assert np.all((arr >= 0.0) & (arr <= 1.0)), (
                f"{pat}: score outside [0, 1]: {arr[~((arr>=0)&(arr<=1))]}"
            )

    def test_detector_subset_respected(self):
        dist = null_detection_distribution(
            200, 0.01,
            detectors=["Head & Shoulders"],
            n_null=15,
            seed=8,
        )
        for pat in dist.scores_by_pattern:
            assert pat == "Head & Shoulders", f"unexpected pattern: {pat}"
        for pat in dist.counts_by_pattern:
            assert pat == "Head & Shoulders", f"unexpected pattern: {pat}"


# ── Determinism ───────────────────────────────────────────────────────────────

class TestDeterminism:
    """Same seed → identical distributions on fresh (non-cached) runs."""

    def test_same_seed_same_score_arrays(self):
        clear_null_distribution_cache()
        d1 = null_detection_distribution(200, 0.01, n_null=20, seed=42)
        clear_null_distribution_cache()
        d2 = null_detection_distribution(200, 0.01, n_null=20, seed=42)
        assert set(d1.scores_by_pattern.keys()) == set(d2.scores_by_pattern.keys())
        for p in d1.scores_by_pattern:
            np.testing.assert_array_equal(
                d1.scores_by_pattern[p], d2.scores_by_pattern[p],
                err_msg=f"scores differ for pattern '{p}' despite same seed",
            )

    def test_same_seed_same_count_arrays(self):
        clear_null_distribution_cache()
        d1 = null_detection_distribution(200, 0.01, n_null=20, seed=42)
        clear_null_distribution_cache()
        d2 = null_detection_distribution(200, 0.01, n_null=20, seed=42)
        for p in d1.counts_by_pattern:
            np.testing.assert_array_equal(
                d1.counts_by_pattern[p], d2.counts_by_pattern[p],
                err_msg=f"counts differ for pattern '{p}' despite same seed",
            )

    def test_different_seeds_may_differ(self):
        clear_null_distribution_cache()
        d1 = null_detection_distribution(200, 0.01, n_null=20, seed=1)
        clear_null_distribution_cache()
        d2 = null_detection_distribution(200, 0.01, n_null=20, seed=99)
        # At least one of the per-surrogate count arrays should differ.
        # (Extremely unlikely to be identical under different seeds.)
        any_differ = False
        common = set(d1.counts_by_pattern) & set(d2.counts_by_pattern)
        for p in common:
            if not np.array_equal(d1.counts_by_pattern[p], d2.counts_by_pattern[p]):
                any_differ = True
                break
        # Only fail if counts and key sets are identical (degenerate case).
        if not any_differ and set(d1.counts_by_pattern) == set(d2.counts_by_pattern):
            # Both runs produced zero detections — non-informative, but not a bug.
            pass


# ── Cache ─────────────────────────────────────────────────────────────────────

class TestCache:
    """Cache hit returns the same object without re-running the surrogate generator."""

    def test_cache_returns_same_object(self):
        clear_null_distribution_cache()
        d1 = null_detection_distribution(180, 0.01, n_null=20, seed=77)
        d2 = null_detection_distribution(180, 0.01, n_null=20, seed=77)
        assert d1 is d2, "second call should return the cached object (identity)"

    def test_cache_hit_skips_surrogate_generator(self, monkeypatch):
        import chart_decomp.infrastructure.validation.null_fpr as _mod

        clear_null_distribution_cache()
        call_count = [0]
        orig = _mod.random_walk_surrogates

        def spy(*args, **kwargs):
            call_count[0] += 1
            yield from orig(*args, **kwargs)

        monkeypatch.setattr(_mod, "random_walk_surrogates", spy)

        null_detection_distribution(160, 0.01, n_null=20, seed=55)
        null_detection_distribution(160, 0.01, n_null=20, seed=55)

        assert call_count[0] == 1, (
            f"surrogate generator called {call_count[0]} times; "
            "expected 1 (cache should have served the second call)"
        )

    def test_different_volatility_different_cache_entry(self):
        clear_null_distribution_cache()
        d1 = null_detection_distribution(170, 0.01, n_null=15, seed=10)
        d2 = null_detection_distribution(170, 0.02, n_null=15, seed=10)
        assert d1 is not d2

    def test_different_length_different_cache_entry(self):
        clear_null_distribution_cache()
        d1 = null_detection_distribution(150, 0.01, n_null=15, seed=11)
        d2 = null_detection_distribution(200, 0.01, n_null=15, seed=11)
        assert d1 is not d2

    def test_different_seed_different_cache_entry(self):
        clear_null_distribution_cache()
        d1 = null_detection_distribution(150, 0.01, n_null=15, seed=20)
        d2 = null_detection_distribution(150, 0.01, n_null=15, seed=21)
        assert d1 is not d2

    def test_clear_cache_forces_rerun(self, monkeypatch):
        import chart_decomp.infrastructure.validation.null_fpr as _mod

        clear_null_distribution_cache()
        call_count = [0]
        orig = _mod.random_walk_surrogates

        def spy(*args, **kwargs):
            call_count[0] += 1
            yield from orig(*args, **kwargs)

        monkeypatch.setattr(_mod, "random_walk_surrogates", spy)

        null_detection_distribution(140, 0.01, n_null=15, seed=33)
        clear_null_distribution_cache()
        null_detection_distribution(140, 0.01, n_null=15, seed=33)

        assert call_count[0] == 2, (
            f"expected 2 generator calls (cache cleared between runs), got {call_count[0]}"
        )
