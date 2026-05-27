"""Time-frequency view tests (CWT, HHT).

Verifies output shapes, COI presence, and basic sanity checks.
Trap B7: COI must always be present.
"""
from __future__ import annotations

import numpy as np
import pytest

import chart_decomp as cd


class TestCWT:
    def test_output_shapes(self, sinusoidal):
        result = cd.cwt_scalogram(sinusoidal)
        N = len(sinusoidal)
        n_scales = result.power.shape[0]
        assert result.power.shape == (n_scales, N)
        assert result.frequencies.shape == (n_scales,)
        assert result.periods.shape == (n_scales,)
        assert result.coi.shape == (N,), "COI must have length N (Trap B7)"

    def test_coi_is_mandatory(self, brownian):
        """COI array must not be all zeros or all inf — it has real content."""
        result = cd.cwt_scalogram(brownian[:256])
        assert result.coi is not None
        assert not np.all(result.coi == 0)

    def test_power_non_negative(self, ar1_series):
        result = cd.cwt_scalogram(ar1_series[:256])
        assert np.all(result.power >= 0)

    def test_phase_shape_matches_power(self, sinusoidal):
        result = cd.cwt_scalogram(sinusoidal)
        assert result.phase is not None
        assert result.phase.shape == result.power.shape

    def test_periods_inverse_frequencies(self, sinusoidal):
        result = cd.cwt_scalogram(sinusoidal)
        np.testing.assert_allclose(
            result.periods,
            1.0 / result.frequencies,
            rtol=1e-10,
        )


class TestHHT:
    def test_output_shape(self, sinusoidal):
        """Hilbert spectrum output shape: (n_bins, N)."""
        N = len(sinusoidal)
        # Create fake 3 IMFs
        components = np.vstack([sinusoidal, np.roll(sinusoidal, 10), np.roll(sinusoidal, 20)])
        result = cd.hilbert_spectrum(components, n_freq_bins=60)
        assert result.power.shape == (60, N)
        assert result.coi.shape == (N,)

    def test_power_non_negative(self, sinusoidal):
        components = sinusoidal[np.newaxis, :]
        result = cd.hilbert_spectrum(components)
        assert np.all(result.power >= 0)
