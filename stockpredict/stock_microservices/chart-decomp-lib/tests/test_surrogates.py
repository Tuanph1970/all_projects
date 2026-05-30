"""CD-604 (A4) — Random-walk surrogate generator.

Prerequisite for the mandatory null-FPR machinery (FR-FPR-1). Asserts:
- Produces `n` surrogates each of the requested length.
- Per-step volatility matches the requested value (statistically).
- Reproducible from a seed (NFR-RP1): same seed → identical batch.
- Different seeds (and seed=None) produce different draws.
- estimate_volatility round-trips the generating volatility.
- Input validation.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.domain.exceptions import InputValidationError
from chart_decomp.infrastructure.validation.surrogates import (
    estimate_volatility,
    random_walk_surrogates,
)


class TestShape:
    def test_count_and_length(self):
        surr = list(random_walk_surrogates(length=500, volatility=1.0, n=10, seed=1))
        assert len(surr) == 10
        assert all(s.shape == (500,) for s in surr)
        assert all(np.all(np.isfinite(s)) for s in surr)

    def test_start_offset(self):
        s = next(random_walk_surrogates(length=200, volatility=1.0, n=1, seed=1, start=100.0))
        assert s[0] == pytest.approx(100.0)


class TestVolatilityMatch:
    def test_per_step_vol(self):
        s = next(random_walk_surrogates(length=4000, volatility=0.7, n=1, seed=2))
        assert np.std(np.diff(s)) == pytest.approx(0.7, rel=0.1)

    def test_estimate_volatility_roundtrip(self):
        s = next(random_walk_surrogates(length=4000, volatility=1.3, n=1, seed=3))
        assert estimate_volatility(s) == pytest.approx(1.3, rel=0.1)


class TestReproducibility:
    def test_same_seed_identical(self):
        a = list(random_walk_surrogates(length=300, volatility=1.0, n=5, seed=42))
        b = list(random_walk_surrogates(length=300, volatility=1.0, n=5, seed=42))
        assert len(a) == len(b) == 5
        for x, y in zip(a, b):
            np.testing.assert_array_equal(x, y)

    def test_different_seed_differs(self):
        a = next(random_walk_surrogates(length=300, volatility=1.0, n=1, seed=1))
        b = next(random_walk_surrogates(length=300, volatility=1.0, n=1, seed=2))
        assert not np.array_equal(a, b)

    def test_seed_none_varies(self):
        a = next(random_walk_surrogates(length=300, volatility=1.0, n=1, seed=None))
        b = next(random_walk_surrogates(length=300, volatility=1.0, n=1, seed=None))
        assert not np.array_equal(a, b)


class TestValidation:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"length": 1, "volatility": 1.0, "n": 5},
            {"length": 100, "volatility": -0.1, "n": 5},
            {"length": 100, "volatility": 1.0, "n": 0},
        ],
    )
    def test_invalid(self, kwargs):
        with pytest.raises(InputValidationError):
            list(random_walk_surrogates(**kwargs))
