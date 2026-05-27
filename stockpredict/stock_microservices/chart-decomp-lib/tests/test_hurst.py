"""CD-503 — Hurst exponent statistical validation.

Tests Ĥ on AR(1) series (expected H > 0.5 due to autocorrelation)
and on white noise (expected H ≈ 0.5).

Full fGn statistical validation (50 seeds × 4 H values) is marked
@pytest.mark.slow and skipped in normal test runs.
"""
from __future__ import annotations

import numpy as np
import pytest

import chart_decomp as cd


class TestHurstBasic:
    def test_output_fields(self, ar1_series):
        """HurstResult has required fields."""
        result = cd.hurst_wavelet(ar1_series)
        assert hasattr(result, "H")
        assert hasattr(result, "slope")
        assert hasattr(result, "variances")
        assert hasattr(result, "scale_mask")
        assert np.isfinite(result.H)

    def test_white_noise_near_half(self, rng):
        """White noise should give H close to 0.5 (bias-corrected)."""
        x = rng.normal(0, 1, 4096)
        result = cd.hurst_wavelet(x, j_range=(2, 8))
        assert 0.3 <= result.H <= 0.7, (
            f"H={result.H:.3f} for white noise is too far from 0.5"
        )

    def test_ar1_higher_than_random_walk(self, ar1_series):
        """AR(1) series should have H > 0.5 due to positive autocorrelation."""
        x = ar1_series  # φ=0.8
        result = cd.hurst_wavelet(x, j_range=(2, 7))
        assert result.H > 0.5, f"AR(1) with φ=0.8 expected H>0.5; got H={result.H:.3f}"

    def test_variances_length_matches_level(self, ar1_series):
        """variances array length == actual number of decomposition levels."""
        result = cd.hurst_wavelet(ar1_series, j_range=(2, 8))
        assert len(result.variances) > 0
        assert len(result.scale_mask) == len(result.variances)


@pytest.mark.slow
class TestHurstFGN:
    """Statistical validation against fractional Gaussian noise (SRS §5.2).

    Requires: fbm package (`pip install fbm`).
    Run with: pytest -m slow tests/test_hurst.py
    """

    @pytest.mark.parametrize("H_true", [0.3, 0.5, 0.7, 0.85])
    def test_fgn_estimation_error(self, H_true):
        try:
            from fbm import fgn  # type: ignore
        except ImportError:
            pytest.skip("fbm not installed")

        n_seeds = 50
        N = 4096
        errors = []
        for seed in range(n_seeds):
            rng = np.random.default_rng(seed)
            noise = fgn(n=N, hurst=H_true, length=1.0, method="daviesharte")
            result = cd.hurst_wavelet(noise, j_range=(2, 8))
            errors.append(abs(result.H - H_true))

        mean_err = np.mean(errors)
        assert mean_err <= 0.07, (
            f"Hurst estimation error {mean_err:.4f} > 0.07 for H_true={H_true}"
        )
