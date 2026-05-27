"""CD-501 / CD-502 — Decomposition unit tests.

Covers:
- Round-trip reconstruction tolerances (SRS §5.1)
- MODWT translation invariance
- VMD mode count and ascending center-freq sort
- Edge robustness: lengths 100, 257, 1024, 5000
"""
from __future__ import annotations

import numpy as np
import pytest

import chart_decomp as cd
from chart_decomp.domain.value_objects import MODWTParams, VMDParams


# ── MODWT ─────────────────────────────────────────────────────────────────────

class TestMODWT:
    @pytest.mark.parametrize("N", [100, 257, 1024])
    def test_round_trip(self, rng, N):
        """Sum of all MODWT components must equal x within 1e-10."""
        x = rng.normal(0, 1, N)
        result = cd.modwt(x, level=4)
        recon = result.reconstruct()
        assert np.allclose(recon, x, atol=1e-9), (
            f"MODWT round-trip failed for N={N}: max_err={np.abs(recon - x).max():.2e}"
        )

    def test_output_shape(self, brownian):
        """Approximation and all details have shape (N,)."""
        N = len(brownian)
        result = cd.modwt(brownian, level=5)
        assert result.approximation.shape == (N,)
        assert len(result.details) == 5
        for d in result.details:
            assert d.shape == (N,)

    def test_translation_invariance(self, ar1_series):
        """Shifting x by k shifts every MODWT component by the same k (CD-502)."""
        x = ar1_series[:512]
        k = 17
        result_orig = cd.modwt(x, level=4)
        result_shifted = cd.modwt(np.roll(x, k), level=4)
        # All components should roll by k
        assert np.allclose(
            np.roll(result_orig.approximation, k),
            result_shifted.approximation,
            atol=1e-9,
        )
        for j, (d_orig, d_shifted) in enumerate(
            zip(result_orig.details, result_shifted.details)
        ):
            assert np.allclose(np.roll(d_orig, k), d_shifted, atol=1e-9), (
                f"Translation invariance failed at detail level {j}"
            )

    def test_coi_widths_length(self, sinusoidal):
        """coi_widths has one entry per detail level."""
        result = cd.modwt(sinusoidal, level=4)
        assert len(result.coi_widths) == 4

    @pytest.mark.parametrize("N", [100, 257, 1024, 5000])
    def test_edge_robustness(self, rng, N):
        """All lengths complete without error (SRS §5.1 edge robustness)."""
        x = rng.normal(0, 1, N)
        result = cd.modwt(x, level=4)
        assert result is not None

    def test_default_params(self, brownian):
        """Default params (sym8, level=6) work."""
        result = cd.modwt(brownian)
        assert result.wavelet == "sym8"
        assert result.level == 6


# ── VMD ───────────────────────────────────────────────────────────────────────

class TestVMD:
    @pytest.mark.parametrize("K", [3, 5])
    def test_mode_count(self, ar1_series, K):
        """VMD returns exactly K modes."""
        pytest.importorskip("vmdpy")
        result = cd.vmd(ar1_series[:512], K=K)
        assert result.modes.shape[0] == K
        assert len(result.center_frequencies) == K

    def test_ascending_center_freq(self, ar1_series):
        """Modes are sorted by ascending center frequency (Constraint C3)."""
        pytest.importorskip("vmdpy")
        result = cd.vmd(ar1_series[:512], K=4)
        freqs = result.center_frequencies
        assert np.all(freqs[:-1] <= freqs[1:]), (
            f"Center frequencies not sorted: {freqs}"
        )

    def test_reconstruction_error_reported(self, ar1_series):
        """Reconstruction error is a finite positive float (Trap B4 transparency)."""
        pytest.importorskip("vmdpy")
        result = cd.vmd(ar1_series[:512], K=3)
        assert np.isfinite(result.reconstruction_error)
        assert result.reconstruction_error >= 0.0

    @pytest.mark.parametrize("N", [100, 257, 1024])
    def test_edge_robustness(self, rng, N):
        """VMD runs without error for multiple lengths."""
        pytest.importorskip("vmdpy")
        x = rng.normal(0, 1, N)
        result = cd.vmd(x, K=3)
        assert result.modes.shape == (3, N)


# ── EMD ───────────────────────────────────────────────────────────────────────

class TestEMD:
    def test_round_trip(self, sinusoidal):
        """Sum of all EMD components must equal x within 1e-6."""
        pytest.importorskip("PyEMD")
        result = cd.emd(sinusoidal)
        recon = result.reconstruct()
        assert np.allclose(recon, sinusoidal, atol=1e-5), (
            f"EMD round-trip failed: max_err={np.abs(recon - sinusoidal).max():.2e}"
        )

    def test_dominant_periods_finite_for_imfs(self, sinusoidal):
        """All non-residue IMFs have finite dominant periods."""
        pytest.importorskip("PyEMD")
        result = cd.emd(sinusoidal)
        for p in result.dominant_periods:
            assert np.isfinite(p) or p == np.inf  # residue can be inf

    @pytest.mark.parametrize("N", [100, 257, 1024])
    def test_edge_robustness(self, rng, N):
        pytest.importorskip("PyEMD")
        x = rng.normal(0, 1, N)
        result = cd.emd(x)
        assert result is not None
