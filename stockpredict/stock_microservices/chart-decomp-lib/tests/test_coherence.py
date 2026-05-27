"""CD-504 — Wavelet coherence tests.

Basic sanity tests run without optional deps.
Full statistical validation (shared factor + decoupling window) is marked slow.
"""
from __future__ import annotations

import numpy as np
import pytest

import chart_decomp as cd


class TestCoherenceBasic:
    def test_r_squared_bounded(self, rng):
        """R² must be in [0, 1]."""
        x = rng.normal(0, 1, 256)
        y = rng.normal(0, 1, 256)
        result = cd.wavelet_coherence(x, y)
        assert np.all(result.r_squared >= 0.0 - 1e-10)
        assert np.all(result.r_squared <= 1.0 + 1e-10)

    def test_identical_series_high_coherence(self, ar1_series):
        """Identical series should yield R² ≈ 1."""
        x = ar1_series[:256]
        result = cd.wavelet_coherence(x, x)
        median_r2 = float(np.median(result.r_squared))
        assert median_r2 > 0.9, f"Identical series gave median R²={median_r2:.3f}"

    def test_coi_present(self, rng):
        """COI is mandatory (Trap B7)."""
        x, y = rng.normal(0, 1, 128), rng.normal(0, 1, 128)
        result = cd.wavelet_coherence(x, y)
        assert result.coi is not None
        assert result.coi.shape == (128,)

    def test_output_shapes_consistent(self, rng):
        N = 200
        x, y = rng.normal(0, 1, N), rng.normal(0, 1, N)
        result = cd.wavelet_coherence(x, y)
        n_scales = result.r_squared.shape[0]
        assert result.r_squared.shape == (n_scales, N)
        assert result.phase.shape == (n_scales, N)
        assert result.frequencies.shape == (n_scales,)


@pytest.mark.slow
class TestCoherenceStatistical:
    """SRS §5.2 known-construction pair validation."""

    def test_shared_factor_coupling(self, rng):
        """R² > 0.5 at long scales in the coupled window."""
        N = 512
        slow_signal = np.cumsum(rng.normal(0, 1, N))
        x = slow_signal + rng.normal(0, 0.5, N)
        y = slow_signal + rng.normal(0, 0.5, N)

        result = cd.wavelet_coherence(x, y)
        # Use the coarsest 20% of scales (lowest frequencies → long periods)
        n_scales = result.r_squared.shape[0]
        coarse_r2 = result.r_squared[: n_scales // 5, :]

        # Exclude COI region (use middle 50% of time)
        t_lo, t_hi = N // 4, 3 * N // 4
        median_r2 = float(np.median(coarse_r2[:, t_lo:t_hi]))
        assert median_r2 > 0.5, (
            f"Shared factor: expected R²>0.5 at long scales; got {median_r2:.3f}"
        )
