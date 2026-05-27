"""CWT scalogram analyzer (FR-TF-CWT).

Computes the Continuous Wavelet Transform power spectrum using pywt.cwt.
The cone-of-influence (COI) array is ALWAYS computed and returned — per
Constraint C2 and Trap B7 it is mandatory on every time-frequency output.

COI convention: coi[t] holds the maximum RELIABLE period at time step t.
Any period in the scalogram above coi[t] for that column is edge-contaminated.
"""
from __future__ import annotations

import numpy as np
import pywt
from scipy.ndimage import gaussian_filter

from chart_decomp.domain.entities import TimeFreqResult
from chart_decomp.domain.exceptions import DecompositionError
from chart_decomp.domain.value_objects import CWTParams, TimeSeries

# Fourier factor for complex Morlet cmor{B}-{C}:
# period = scale * fourier_factor;  fourier_factor ≈ 1/(center_freq * dt)
# For cmor1.5-1.0: center_freq=1.0 cycles/sample → fourier_factor = 1.0
_MORLET_FOURIER_FACTOR = 1.0
# e-folding time for complex Morlet (determines COI extent)
# τ_s = sqrt(2) * scale  (Torrence & Compo 1998, eq. 19)
_MORLET_COI_FACTOR = np.sqrt(2.0)


class CWTAnalyzer:
    """Implements ICWTAnalyzer.

    Design patterns:
        Concrete Strategy — plugged in via TimeFreqFactory (future extension).
    """

    def analyze(self, series: TimeSeries, params: CWTParams) -> TimeFreqResult:
        """Compute CWT power scalogram.

        Parameters
        ----------
        series : validated TimeSeries of length N
        params : CWTParams

        Returns
        -------
        TimeFreqResult:
            power      — |W|² shape (n_scales, N)
            frequencies — shape (n_scales,) in cycles/sample
            periods    — shape (n_scales,) = 1/frequencies
            coi        — shape (N,) max reliable period at each time (mandatory)
            phase      — angle(W) shape (n_scales, N)
        """
        x = series.values
        N = len(x)
        scales = self._resolve_scales(params, N)

        try:
            coeffs, freqs = pywt.cwt(
                x,
                scales,
                params.wavelet,
                sampling_period=params.sampling_period,
            )
        except Exception as exc:
            raise DecompositionError(f"pywt.cwt failed: {exc}") from exc

        power = np.abs(coeffs) ** 2  # shape (n_scales, N)
        phase = np.angle(coeffs)

        coi = self._compute_coi(scales, N, params.sampling_period)
        periods = 1.0 / freqs

        return TimeFreqResult(
            power=power,
            frequencies=freqs,
            periods=periods,
            coi=coi,
            phase=phase,
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_scales(params: CWTParams, N: int) -> np.ndarray:
        if params.scales is not None:
            return np.asarray(params.scales, dtype=np.float64)
        # Default: 64 log-spaced scales from 2 to min(256, N//4)
        s_max = min(256.0, N / 4.0)
        return np.geomspace(2.0, s_max, num=64)

    @staticmethod
    def _compute_coi(scales: np.ndarray, N: int, dt: float) -> np.ndarray:
        """COI array — max reliable period at each time step.

        For complex Morlet, the e-folding distance is sqrt(2)*scale samples.
        At time t the maximum reliable period is determined by the smaller of
        the distance from each edge: min(t, N-1-t) samples / coi_factor.

        coi[t] = min(t, N-1-t) * dt / coi_factor * fourier_factor
        """
        t_arr = np.arange(N, dtype=np.float64)
        edge_dist = np.minimum(t_arr, N - 1 - t_arr)  # samples from nearest edge
        coi = edge_dist * dt * _MORLET_FOURIER_FACTOR / _MORLET_COI_FACTOR
        return coi
