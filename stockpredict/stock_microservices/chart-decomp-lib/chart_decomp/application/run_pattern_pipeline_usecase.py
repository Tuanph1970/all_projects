"""Use-case: Run the end-to-end chart-pattern pipeline (SRS §II.4).

Orchestrates the three Part II layers:
    Layer 1  — wavelet denoising      (FR-DN-1)
    Layer 2a — swing extraction       (FR-SW-*)
    Layer 2b — pattern detection      (FR-PAT-*)
    Layer 2c — null FPR + noteworthy gate (FR-FPR-1/2, optional)

Right-edge confirmation (B6/C2): any detection whose end_index falls within
the cone-of-influence of the MODWT denoising step is marked confirmed=False,
because the denoised values near the right edge may still change as new data
arrives. The COI width is determined by the finest kept MODWT detail band
(level k_drop+1), using the formula coi_width = (2^(k_drop+1) - 1) * (L-1)
where L is the wavelet filter length.
"""
from __future__ import annotations

from typing import Iterable, Optional, Union

import numpy as np
import pywt

from chart_decomp.domain.entities import PatternPipelineResult, SwingSkeleton
from chart_decomp.domain.value_objects import (
    DenoiseParams,
    NullFPRParams,
    SwingParams,
    TimeSeries,
)
from chart_decomp.factories.pattern_detector_factory import detect_patterns
from chart_decomp.infrastructure.denoise.wavelet_denoiser import WaveletDenoiser
from chart_decomp.infrastructure.swings.swing_extractor import SwingExtractor
from chart_decomp.infrastructure.validation.null_fpr import (
    annotate_significance,
    null_detection_distribution,
    null_thresholds,
)
from chart_decomp.infrastructure.validation.surrogates import estimate_volatility


def _edge_lag(params: DenoiseParams) -> int:
    """COI half-width in samples for the finest kept detail band (B6/C2).

    After dropping the finest k_drop bands, the finest kept band is at level
    k_drop+1.  Its COI half-width = (2^(k_drop+1) - 1) * (L - 1), where L is
    the wavelet filter length.
    """
    try:
        wavelet = pywt.Wavelet(params.wavelet)
        L = len(wavelet.dec_lo)
    except Exception:
        L = 16  # fallback for sym8
    kept_level = params.k_drop + 1
    return (2 ** kept_level - 1) * (L - 1)


class RunPatternPipelineUseCase:
    """Orchestrates the full Part II pipeline.

    Design pattern: Use-Case (Application Service) — owns no domain state,
    wires infrastructure collaborators, and enforces invariants (causality,
    edge confidence) that no single layer can enforce alone.
    """

    def __init__(self) -> None:
        self._denoiser = WaveletDenoiser()
        self._extractor = SwingExtractor()

    def execute(
        self,
        x: np.ndarray,
        *,
        denoise_params: Optional[DenoiseParams] = None,
        swing_params: Optional[SwingParams] = None,
        detectors: Union[str, Iterable[str]] = "all",
        compute_fpr: bool = True,
        fpr_params: Optional[NullFPRParams] = None,
    ) -> PatternPipelineResult:
        """Run denoise → swings → detect → (FPR) → edge-flag.

        Parameters
        ----------
        x              : raw price/return series (1-D float).
        denoise_params : Layer-1 config; defaults to DenoiseParams().
        swing_params   : Layer-2a config; defaults to SwingParams().
        detectors      : 'all' or list of registered detector names.
        compute_fpr    : if True, run null_fpr and annotate detections with
                         null_percentile.  Set False for speed when FPR is not
                         needed.
        fpr_params     : NullFPRParams for the null evaluator.  Defaults to
                         NullFPRParams() (n_null=1000).  Pass a smaller n_null
                         for interactive use.
        """
        denoise_params = denoise_params or DenoiseParams()
        swing_params = swing_params or SwingParams()

        # ── Layer 1: denoise ────────────────────────────────────────────────
        ts = TimeSeries(x)
        denoised = self._denoiser.denoise(ts, denoise_params)

        # ── Layer 2a: extract swings from the denoised series ────────────────
        try:
            denoised_ts = TimeSeries(denoised)
            swings = self._extractor.extract(denoised_ts, swing_params)
        except Exception:
            swings = []

        if len(swings) < 2:
            return PatternPipelineResult(
                raw=np.asarray(x, dtype=np.float64).copy(),
                denoised=denoised,
                swings=swings,
                detections=[],
                fpr_by_pattern={},
            )

        skeleton = SwingSkeleton(swings)

        # ── Layer 2b: detect patterns ────────────────────────────────────────
        detections = detect_patterns(skeleton, denoised, detectors)

        # ── Right-edge confirmation flag (B6/C2) ─────────────────────────────
        lag = _edge_lag(denoise_params)
        n = len(x)
        for d in detections:
            if d.end_index >= n - lag:
                d.confirmed = False

        # ── Layer 2c: null FPR + noteworthy annotation (FR-FPR-1/2) ─────────
        fpr_by_pattern: dict = {}
        if compute_fpr and detections:
            fpr_params = fpr_params or NullFPRParams()
            vol = max(float(estimate_volatility(x)), 1e-8)
            dist = null_detection_distribution(
                length=n,
                volatility=vol,
                detectors=detectors,
                n_null=fpr_params.n_null,
                seed=fpr_params.seed,
                swing_params=swing_params,
            )
            thresholds = annotate_significance(
                detections, dist, noteworthy_pct=fpr_params.noteworthy_pct
            )
            fpr_by_pattern = {p: t.fpr for p, t in thresholds.items()}

        return PatternPipelineResult(
            raw=np.asarray(x, dtype=np.float64).copy(),
            denoised=denoised,
            swings=swings,
            detections=detections,
            fpr_by_pattern=fpr_by_pattern,
        )
