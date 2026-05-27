"""Hilbert-Huang Transform spectrum analyzer (FR-TF-HHT).

Accepts either EMD IMFs or MODWT detail bands as an (K, N) array, computes
the instantaneous amplitude and frequency of each component via the Hilbert
analytic signal, and accumulates energy into a time-frequency histogram.

Gaussian smoothing is applied to reduce speckle (configurable sigma).
COI is not well-defined for HHT in the same way as CWT, but a simple
edge-exclusion band (first/last floor(N*0.05) samples at each scale) is
returned so the frontend can shade it consistently.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.signal import hilbert

from chart_decomp.domain.entities import TimeFreqResult
from chart_decomp.domain.exceptions import InputValidationError
from chart_decomp.domain.value_objects import HHTParams


class HHTAnalyzer:
    """Implements IHHTAnalyzer.

    Design patterns:
        Concrete Strategy.
    """

    def analyze(self, components: np.ndarray, params: HHTParams) -> TimeFreqResult:
        """Compute Hilbert spectrum from K components.

        Parameters
        ----------
        components : shape (K, N) — IMFs or MODWT detail bands.
                     The residue / approximation should NOT be included
                     (they carry no oscillatory meaning).
        params     : HHTParams

        Returns
        -------
        TimeFreqResult:
            power      — A(t)² accumulated in freq bins, shape (n_bins, N)
            frequencies — bin centres in cycles/sample, shape (n_bins,)
            periods    — 1/frequencies
            coi        — constant edge buffer (N,)
            phase      — None (HHT phase is per-component, not meaningful globally)
        """
        if components.ndim != 2:
            raise InputValidationError(
                f"components must be 2-D (K, N); got shape {components.shape}"
            )
        K, N = components.shape
        n_bins = params.n_freq_bins

        # Frequency bins: 0..0.5 cycles/sample
        freq_bins = np.linspace(0.0, 0.5, n_bins + 1)
        freq_centers = 0.5 * (freq_bins[:-1] + freq_bins[1:])

        spectrum = np.zeros((n_bins, N), dtype=np.float64)

        for k in range(K):
            c = components[k]
            analytic = hilbert(c)
            amplitude = np.abs(analytic)
            phase = np.unwrap(np.angle(analytic))

            # Instantaneous frequency: d(phase)/dt / (2π)
            # diff gives N-1 values; pad with the first value to keep length N
            inst_freq = np.diff(phase) / (2.0 * np.pi)
            inst_freq = np.concatenate([[inst_freq[0]], inst_freq])

            # Accumulate A²  into frequency bins for each time step
            energy = amplitude ** 2
            bin_idx = np.searchsorted(freq_bins[1:], np.clip(inst_freq, 0.0, 0.5))
            bin_idx = np.clip(bin_idx, 0, n_bins - 1)
            for t in range(N):
                spectrum[bin_idx[t], t] += energy[t]

        # Gaussian smoothing (sigma in [freq_bins, time] dimensions)
        s_freq, s_time = params.smoothing_sigma
        if s_freq > 0 or s_time > 0:
            spectrum = gaussian_filter(spectrum, sigma=(s_freq, s_time))

        # COI: simple edge exclusion band — reliable between 5% margins
        coi = self._edge_coi(N)
        periods = np.where(freq_centers > 1e-10, 1.0 / freq_centers, np.inf)

        return TimeFreqResult(
            power=spectrum,
            frequencies=freq_centers,
            periods=periods,
            coi=coi,
            phase=None,
        )

    @staticmethod
    def _edge_coi(N: int) -> np.ndarray:
        """Return max-reliable-period proxy based on edge distance.

        Scaled to [0, 0.5] so it maps to the freq/period domain consistently
        with CWT COI.
        """
        t = np.arange(N, dtype=np.float64)
        edge = np.minimum(t, N - 1 - t)
        # Normalised to fraction of Nyquist: larger edge distance → longer periods ok
        coi = edge / (N * np.sqrt(2.0))
        coi = np.where(coi > 0, 1.0 / coi, np.inf)
        return coi
