"""Hybrid analysis pipelines (FR-HYB-A/B/C).

Hybrid A — Wavelet-Denoise → EMD:
    Zero the finest k_drop MODWT detail bands, reconstruct, then run EMD.
    Use case: remove noise-induced extrema from the signal before EMD.

Hybrid B — EMD → CWT-per-IMF:
    Run EMD, then compute a CWT scalogram for each individual IMF.
    Use case: detect residual mode mixing within a single IMF.

Hybrid C — MODWT → Hilbert Spectrum (recommended production pipeline):
    Run MODWT, apply Hilbert spectral analysis to each detail band.
    Use case: deterministic time-frequency view, no mode mixing.

Constraint C2: all pipelines return TimeFreqResults with mandatory COI.
"""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import EMDResult, MODWTResult, TimeFreqResult
from chart_decomp.domain.value_objects import (
    CWTParams,
    EMDParams,
    EEMDParams,
    HHTParams,
    MODWTParams,
    TimeSeries,
)
from chart_decomp.domain.value_objects import DenoiseParams
from chart_decomp.factories.decomposer_factory import DecomposerFactory
from chart_decomp.infrastructure.denoise.wavelet_denoiser import WaveletDenoiser
from chart_decomp.infrastructure.time_freq.cwt_analyzer import CWTAnalyzer
from chart_decomp.infrastructure.time_freq.hht_analyzer import HHTAnalyzer


class HybridPipelineUseCase:
    """Orchestrates the three named hybrid pipelines.

    Design patterns:
        Facade over multiple strategies and domain objects.
    """

    def __init__(self) -> None:
        self._factory = DecomposerFactory()
        self._denoiser = WaveletDenoiser()
        self._cwt = CWTAnalyzer()
        self._hht = HHTAnalyzer()

    # ── Hybrid A: Wavelet Denoise → EMD ───────────────────────────────────────

    def hybrid_a(
        self,
        x: np.ndarray,
        modwt_params: MODWTParams | None = None,
        emd_params: EMDParams | None = None,
        k_drop: int = 2,
    ) -> EMDResult:
        """Denoise x by dropping the finest k_drop MODWT bands, then run EMD.

        Parameters
        ----------
        x           : raw 1-D series
        modwt_params: MODWTParams; uses defaults if None
        emd_params  : EMDParams; uses defaults if None
        k_drop      : number of finest detail levels to zero out (default 2)
        """
        series = TimeSeries(x)
        mp = modwt_params or MODWTParams()
        ep = emd_params or EMDParams()

        # Reuse the Layer-1 denoiser: drop the finest k_drop MODWT detail bands.
        denoised = self._denoiser.denoise(
            series,
            DenoiseParams(wavelet=mp.wavelet, level=mp.level, k_drop=k_drop, method="drop"),
        )

        denoised_series = TimeSeries(denoised)
        return self._factory.create_emd().decompose(denoised_series, ep)

    # ── Hybrid B: EMD → CWT per IMF ───────────────────────────────────────────

    def hybrid_b(
        self,
        x: np.ndarray,
        emd_params: EMDParams | None = None,
        cwt_params: CWTParams | None = None,
    ) -> list[TimeFreqResult]:
        """CWT scalogram for each IMF (excluding residue).

        Returns a list of TimeFreqResult, one per non-residue IMF.
        """
        series = TimeSeries(x)
        ep = emd_params or EMDParams()
        cp = cwt_params or CWTParams()

        emd_result = self._factory.create_emd().decompose(series, ep)

        results = []
        for imf_idx in range(emd_result.n_imfs - 1):  # exclude residue
            imf_series = TimeSeries(emd_result.imfs[imf_idx])
            results.append(self._cwt.analyze(imf_series, cp))
        return results

    # ── Hybrid C: MODWT → Hilbert Spectrum ────────────────────────────────────

    def hybrid_c(
        self,
        x: np.ndarray,
        modwt_params: MODWTParams | None = None,
        hht_params: HHTParams | None = None,
    ) -> TimeFreqResult:
        """Hilbert spectrum from MODWT detail bands (recommended production pipeline).

        Stacks all detail bands [D_1, …, D_J] as input to the Hilbert analyzer.
        The approximation A_J is excluded (it carries no oscillatory information).
        """
        series = TimeSeries(x)
        mp = modwt_params or MODWTParams()
        hp = hht_params or HHTParams()

        modwt_result = self._factory.create_modwt().decompose(series, mp)

        # Stack details: shape (J, N)
        detail_matrix = np.vstack(modwt_result.details)
        return self._hht.analyze(detail_matrix, hp)
