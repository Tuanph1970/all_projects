"""Wavelet denoiser — Layer 1 of the pattern-detection pipeline (FR-DN-1).

This is the *only* point where Part II reuses Part I's wavelet engine (SRS
§II.1.3). It produces a smooth, skeleton-ready series for swing extraction; it
does NOT find or define patterns (Trap B5).

Two strategies (DenoiseParams.method):
    'drop'        — zero the finest ``k_drop`` MODWT detail bands and
                    reconstruct. With k_drop=0 this is the identity (MODWT
                    round-trip). This is the band-drop logic also used by the
                    Hybrid-A pipeline (FR-HYB-A).
    'soft'/'hard' — universal-threshold coefficient shrinkage on every detail
                    band, threshold = σ·√(2 ln N) with σ from the MAD of the
                    finest band (Donoho–Johnstone).

Constraint C2 / Trap B6: at the right edge the reconstruction is
boundary-contaminated; downstream live use must flag edge detections as
unconfirmed (handled by the pipeline, not here).
"""
from __future__ import annotations

import numpy as np
import pywt

from chart_decomp.domain.value_objects import DenoiseParams, MODWTParams, TimeSeries
from chart_decomp.infrastructure.decomposition.modwt_decomposer import MODWTDecomposer


class WaveletDenoiser:
    """Implements IDenoiser via MODWT band-drop or threshold shrinkage.

    Design patterns:
        Concrete Strategy — selected by DenoiseParams.method.
        Reuses MODWTDecomposer rather than re-implementing the transform.
    """

    def __init__(self) -> None:
        self._modwt = MODWTDecomposer()

    def denoise(self, series: TimeSeries, params: DenoiseParams) -> np.ndarray:
        """Return a denoised copy of ``series`` of the same length N.

        Parameters
        ----------
        series : validated TimeSeries
        params : DenoiseParams (wavelet, level, k_drop, method)
        """
        modwt = self._modwt.decompose(
            series, MODWTParams(wavelet=params.wavelet, level=params.level)
        )

        if params.method == "drop":
            # details[0] is the finest band; drop the finest k_drop, keep the rest.
            denoised = modwt.approximation.copy()
            for j, d in enumerate(modwt.details):
                if j >= params.k_drop:
                    denoised = denoised + d
            return denoised

        # 'soft' / 'hard' — universal-threshold shrinkage on the detail bands.
        thr = self._universal_threshold(modwt.details[0])
        denoised = modwt.approximation.copy()
        for d in modwt.details:
            denoised = denoised + pywt.threshold(d, thr, mode=params.method)
        return denoised

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _universal_threshold(finest_detail: np.ndarray) -> float:
        """Donoho–Johnstone universal threshold σ·√(2 ln N).

        σ is the robust noise scale estimated from the finest detail band via
        the median absolute deviation (MAD), σ ≈ median(|d|) / 0.6745.
        """
        n = len(finest_detail)
        if n < 2:
            return 0.0
        sigma = float(np.median(np.abs(finest_detail))) / 0.6745
        return sigma * float(np.sqrt(2.0 * np.log(n)))
