"""Wavelet coherence between two series (FR-COH).

Method (Torrence & Webster 1999):
    1. Compute CWT of both series.
    2. Form cross-wavelet: W_xy = W_x * conj(W_y).
    3. Smooth in time (Gaussian, σ ∝ scale) and in scale dimension.
    4. R²(a,b) = |S(W_xy)|² / (S(|W_x|²) · S(|W_y|²)).

COI is returned from the CWT; phase arrows can be derived from
phase = angle(S(W_xy)).

Design patterns:
    Concrete Strategy implementing ICoherenceAnalyzer.
    Composition with CWTAnalyzer for CWT computation.
"""
from __future__ import annotations

import numpy as np
import pywt
from scipy.ndimage import gaussian_filter

from chart_decomp.domain.entities import CoherenceResult, TimeFreqResult
from chart_decomp.domain.exceptions import DecompositionError
from chart_decomp.domain.value_objects import BivariateSeries, CoherenceParams, CWTParams
from chart_decomp.infrastructure.time_freq.cwt_analyzer import CWTAnalyzer, _MORLET_COI_FACTOR


class WaveletCoherenceAnalyzer:
    """Implements ICoherenceAnalyzer."""

    def __init__(self) -> None:
        self._cwt = CWTAnalyzer()

    def analyze(self, pair: BivariateSeries, params: CoherenceParams) -> CoherenceResult:
        """Compute R² coherence and phase between pair.x and pair.y.

        Returns
        -------
        CoherenceResult:
            r_squared   — shape (n_scales, N), bounded [0, 1]
            phase       — angle(S(W_xy)), shape (n_scales, N)
            frequencies — shape (n_scales,)
            coi         — shape (N,) max reliable period at each time
        """
        N = len(pair.x)
        cwt_params = CWTParams(
            scales=params.scales,
            wavelet=params.wavelet,
            sampling_period=1.0,
        )

        # Compute raw CWT coefficients (we need complex, not just power)
        scales = self._cwt._resolve_scales(cwt_params, N)
        try:
            Wx, freqs = pywt.cwt(pair.x.values, scales, params.wavelet)
            Wy, _    = pywt.cwt(pair.y.values, scales, params.wavelet)
        except Exception as exc:
            raise DecompositionError(f"pywt.cwt failed: {exc}") from exc

        # Cross-wavelet spectrum
        Wxy = Wx * np.conj(Wy)

        # Smooth in time and scale
        Sxy   = self._smooth(Wxy,  scales, params)
        Sxx   = self._smooth(np.abs(Wx) ** 2, scales, params)
        Syy   = self._smooth(np.abs(Wy) ** 2, scales, params)

        denom = np.abs(Sxx).real * np.abs(Syy).real
        denom = np.where(denom < 1e-30, 1e-30, denom)
        r_squared = (np.abs(Sxy) ** 2).real / denom
        r_squared = np.clip(r_squared, 0.0, 1.0)

        phase = np.angle(Sxy)

        coi = self._cwt._compute_coi(scales, N, dt=1.0)

        return CoherenceResult(
            r_squared=r_squared,
            phase=phase,
            frequencies=freqs,
            coi=coi,
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _smooth(
        W: np.ndarray,
        scales: np.ndarray,
        params: CoherenceParams,
    ) -> np.ndarray:
        """Smooth in time (σ ∝ scale) then in the scale dimension.

        For each scale row j, the time-domain Gaussian sigma is
        σ_t = params.smoothing_sigma_time * scales[j].
        Scale-domain sigma is params.smoothing_sigma_scale (in scale-index units).
        """
        result = np.empty_like(W, dtype=complex)
        for j, s in enumerate(scales):
            sigma_t = max(params.smoothing_sigma_time * s, 0.5)
            row = W[j]
            if np.iscomplexobj(row):
                result[j] = (
                    gaussian_filter(row.real, sigma=sigma_t)
                    + 1j * gaussian_filter(row.imag, sigma=sigma_t)
                )
            else:
                result[j] = gaussian_filter(row.real, sigma=sigma_t)

        # Scale-direction smoothing
        if params.smoothing_sigma_scale > 0:
            if np.iscomplexobj(result):
                result = (
                    gaussian_filter(result.real, sigma=(params.smoothing_sigma_scale, 0))
                    + 1j * gaussian_filter(result.imag, sigma=(params.smoothing_sigma_scale, 0))
                )
            else:
                result = gaussian_filter(result.real, sigma=(params.smoothing_sigma_scale, 0))
        return result
