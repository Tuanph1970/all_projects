"""CD-602 (A2) — Layer-1 wavelet denoiser (FR-DN-1).

Properties asserted (not synthetic magnitudes):
- Output length == N for every method.
- method='drop' with k_drop=0 reconstructs the input (≈ MODWT round-trip).
- 'drop' is exactly approximation + sum of the kept (coarser) detail bands.
- Dropping more finest bands removes energy (monotone non-increasing).
- soft/hard universal-threshold denoising shrinks detail energy (var ≤ var(x))
  and actually changes the series.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.domain.value_objects import DenoiseParams, MODWTParams, TimeSeries
from chart_decomp.infrastructure.decomposition.modwt_decomposer import MODWTDecomposer
from chart_decomp.infrastructure.denoise.wavelet_denoiser import WaveletDenoiser


@pytest.fixture
def den():
    return WaveletDenoiser()


class TestDropMethod:
    def test_output_length(self, den, sinusoidal):
        out = den.denoise(TimeSeries(sinusoidal), DenoiseParams(level=4, k_drop=1))
        assert out.shape == (len(sinusoidal),)
        assert np.all(np.isfinite(out))

    def test_kdrop_zero_is_identity(self, den, sinusoidal):
        # keeping all bands == MODWT round-trip == the input
        out = den.denoise(TimeSeries(sinusoidal), DenoiseParams(level=4, k_drop=0))
        np.testing.assert_allclose(out, sinusoidal, atol=1e-8)

    def test_drop_equals_manual_band_drop(self, den, sinusoidal):
        # The denoiser must reproduce the band-drop logic hybrid_a relied on:
        # approximation + sum of detail bands EXCEPT the finest k_drop.
        k_drop = 2
        params = DenoiseParams(wavelet="sym8", level=4, k_drop=k_drop)
        out = den.denoise(TimeSeries(sinusoidal), params)

        mr = MODWTDecomposer().decompose(
            TimeSeries(sinusoidal), MODWTParams(wavelet="sym8", level=4)
        )
        manual = mr.approximation.copy()
        for j, d in enumerate(mr.details):
            if j >= k_drop:  # details[0] is the finest band
                manual = manual + d
        np.testing.assert_allclose(out, manual, atol=1e-10)

    def test_energy_monotone_non_increasing(self, den, sinusoidal):
        # Removing successively more finest bands cannot add energy.
        energies = []
        for k in range(0, 5):
            out = den.denoise(TimeSeries(sinusoidal), DenoiseParams(level=4, k_drop=k))
            energies.append(float(np.sum(out**2)))
        e0 = energies[0]
        for k in range(4):
            assert energies[k + 1] <= energies[k] + 1e-6 * e0
        assert energies[-1] < energies[0]  # meaningful reduction

    def test_drop_reduces_variance_vs_raw(self, den, sinusoidal):
        out = den.denoise(TimeSeries(sinusoidal), DenoiseParams(level=4, k_drop=2))
        assert np.var(out) < np.var(sinusoidal)


class TestThresholdMethods:
    @pytest.mark.parametrize("method", ["soft", "hard"])
    def test_threshold_shrinks_and_changes(self, den, sinusoidal, method):
        out = den.denoise(
            TimeSeries(sinusoidal), DenoiseParams(level=4, method=method)
        )
        assert out.shape == (len(sinusoidal),)
        assert np.all(np.isfinite(out))
        # thresholding shrinks detail energy → variance not increased
        assert np.var(out) <= np.var(sinusoidal) * (1 + 1e-9)
        # and it actually denoised something
        assert not np.allclose(out, sinusoidal)
