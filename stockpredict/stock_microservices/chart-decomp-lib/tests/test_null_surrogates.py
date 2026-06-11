"""A1 — make_surrogate: surrogate price-path generator (FR-FPR-1 supporting).

Tests:
  - Output length equals input length (both methods).
  - Determinism: same seed + same input → identical path; different seed → different path.
  - Shuffled surrogate has the same sorted return multiset as the input (within fp tol).
  - Gaussian surrogate has approximately the right per-step volatility.
  - Input validation.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.domain.exceptions import InputValidationError
from chart_decomp.infrastructure.validation.surrogates import make_surrogate


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fat_tail_returns(n: int = 200, seed: int = 0) -> np.ndarray:
    """Student-t returns — fat tails preserved by the shuffle method."""
    rng = np.random.default_rng(seed)
    return rng.standard_t(df=3, size=n) * 0.01


def _increments_from_path(path: np.ndarray) -> np.ndarray:
    """Recover per-step increments: diff(prepend_zero(path))."""
    return np.diff(np.concatenate([[0.0], path]))


# ── Output length ─────────────────────────────────────────────────────────────

class TestOutputLength:
    def test_shuffle_length_equals_input(self):
        r = _fat_tail_returns(150)
        assert len(make_surrogate(r, method="shuffle", seed=0)) == len(r)

    def test_gaussian_length_equals_input(self):
        r = _fat_tail_returns(150)
        assert len(make_surrogate(r, method="gaussian", seed=0)) == len(r)

    def test_single_element_shuffle(self):
        r = np.array([0.01])
        assert len(make_surrogate(r, method="shuffle", seed=0)) == 1

    def test_single_element_gaussian(self):
        r = np.array([0.01])
        assert len(make_surrogate(r, method="gaussian", seed=0)) == 1

    def test_output_is_finite(self):
        r = _fat_tail_returns(300)
        for method in ("shuffle", "gaussian"):
            path = make_surrogate(r, method=method, seed=1)
            assert np.all(np.isfinite(path)), f"{method}: output contains non-finite values"


# ── Determinism ───────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_shuffle_same_seed_identical(self):
        r = _fat_tail_returns(200)
        a = make_surrogate(r, method="shuffle", seed=42)
        b = make_surrogate(r, method="shuffle", seed=42)
        np.testing.assert_array_equal(a, b)

    def test_gaussian_same_seed_identical(self):
        r = _fat_tail_returns(200)
        a = make_surrogate(r, method="gaussian", seed=42)
        b = make_surrogate(r, method="gaussian", seed=42)
        np.testing.assert_array_equal(a, b)

    def test_shuffle_different_seeds_differ(self):
        r = _fat_tail_returns(200)
        a = make_surrogate(r, method="shuffle", seed=1)
        b = make_surrogate(r, method="shuffle", seed=2)
        assert not np.array_equal(a, b)

    def test_gaussian_different_seeds_differ(self):
        r = _fat_tail_returns(200)
        a = make_surrogate(r, method="gaussian", seed=1)
        b = make_surrogate(r, method="gaussian", seed=2)
        assert not np.array_equal(a, b)


# ── Shuffle: return multiset preserved ───────────────────────────────────────

class TestShuffleDistribution:
    """FR-FPR-1: shuffle preserves the full return distribution."""

    def test_sorted_multiset_equals_input(self):
        r = _fat_tail_returns(300, seed=7)
        path = make_surrogate(r, method="shuffle", seed=7)
        recovered = _increments_from_path(path)
        np.testing.assert_allclose(np.sort(recovered), np.sort(r), atol=1e-12)

    def test_multiset_preserved_with_extreme_values(self):
        # Returns with planted extreme outliers (fat tails matter)
        rng = np.random.default_rng(99)
        base = rng.normal(0.0, 0.01, 195)
        outliers = np.array([0.15, -0.12, 0.08, -0.20, 0.11])
        r = np.concatenate([base, outliers])
        path = make_surrogate(r, method="shuffle", seed=3)
        recovered = _increments_from_path(path)
        np.testing.assert_allclose(np.sort(recovered), np.sort(r), atol=1e-12)

    def test_temporal_structure_destroyed(self):
        # A monotone series: shuffle should not produce a monotone series
        r = np.linspace(0.001, 0.01, 200)
        paths = [make_surrogate(r, method="shuffle", seed=s) for s in range(5)]
        # Monotone original → all positive increments.  Shuffled paths still
        # have all positive increments (same multiset), but their ordering
        # should differ from the original at least sometimes.
        orig_order = np.argsort(r)
        for path in paths:
            recovered = _increments_from_path(path)
            assert not np.array_equal(
                np.argsort(recovered), orig_order
            ), "shuffle preserved original increment order — seed may be degenerate"


# ── Gaussian method ───────────────────────────────────────────────────────────

class TestGaussianMethod:
    def test_volatility_approximately_matched(self):
        # Use a large series so the estimate is stable
        r = _fat_tail_returns(3000, seed=5)
        path = make_surrogate(r, method="gaussian", seed=5)
        surr_vol = float(np.std(_increments_from_path(path)))
        input_vol = float(np.std(r))
        assert surr_vol == pytest.approx(input_vol, rel=0.2)

    def test_gaussian_does_not_preserve_exact_multiset(self):
        # Unlike shuffle, gaussian draws fresh increments — multiset will differ
        r = _fat_tail_returns(500)
        path = make_surrogate(r, method="gaussian", seed=0)
        recovered = _increments_from_path(path)
        assert not np.allclose(np.sort(recovered), np.sort(r), atol=1e-6)


# ── Input validation ──────────────────────────────────────────────────────────

class TestValidation:
    def test_2d_input_raises(self):
        r = np.ones((10, 2))
        with pytest.raises(InputValidationError):
            make_surrogate(r)

    def test_bad_method_raises(self):
        r = _fat_tail_returns(50)
        with pytest.raises(InputValidationError):
            make_surrogate(r, method="bad_method")

    def test_empty_array_raises(self):
        with pytest.raises((InputValidationError, Exception)):
            make_surrogate(np.array([]))
