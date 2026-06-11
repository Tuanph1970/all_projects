"""Multi-scale pattern detection pipeline (FR-MS-1 / FR-MS-5).

Runs the existing single-scale pipeline (denoise → swing → detect) at
several wavelet denoising levels (k_drop values) and collects detections
from each scale into a unified MultiScaleResult.

Layer relationships
-------------------
This module is a **loop-and-reconciliation layer** on top of the
single-scale infrastructure; it never reimplements denoising, swing
extraction, or detection logic.

Part B task map
---------------
B2  this module: multi-scale sweep + per-scale null-FPR
B3  (future): cross-scale de-duplication (dedup_jaccard)
B4  (future): nesting forest (containment_tol)
B5  (future): agreement/conflict annotation
B6  (future): spurious-nesting null rate (spurious_nesting_fpr)
"""
from __future__ import annotations

from typing import Iterable, Optional, Union

import numpy as np

from chart_decomp.domain.entities import MultiScaleResult, SwingSkeleton
from chart_decomp.domain.value_objects import DenoiseParams, SwingParams, TimeSeries
from chart_decomp.factories.pattern_detector_factory import detect_patterns
from chart_decomp.infrastructure.denoise.wavelet_denoiser import WaveletDenoiser
from chart_decomp.infrastructure.swings.swing_extractor import SwingExtractor
from chart_decomp.infrastructure.validation.null_fpr import (
    annotate_significance,
    null_detection_distribution,
)
from chart_decomp.infrastructure.validation.surrogates import estimate_volatility


def detect_multiscale(
    x: np.ndarray,
    scales: tuple[int, ...] = (1, 2, 3),
    denoise_kw: Optional[dict] = None,
    swing_kw: Optional[dict] = None,
    detectors: Union[str, Iterable[str]] = "all",
    dedup_jaccard: float = 0.7,
    containment_tol: int = 2,
    compute_fpr: bool = True,
    n_null: int = 1000,
    seed: Optional[int] = None,
) -> MultiScaleResult:
    """Run the detection pipeline at each denoising level in ``scales``.

    Each ``k_drop`` value in ``scales`` is one "scale level": a larger k_drop
    drops more fine MODWT detail bands, yielding a smoother denoised series
    and therefore fewer, larger swings and coarser-scale patterns.

    Parameters
    ----------
    x             : raw price series (1-D float array).
    scales        : ordered k_drop values to sweep, fine → coarse.
                    Default (1, 2, 3) covers three levels of denoising.
    denoise_kw    : shared DenoiseParams kwargs (wavelet, level, method).
                    The k_drop field is always overridden by the scale loop.
                    Pass e.g. ``{'level': 5}`` to use a deeper wavelet tree.
    swing_kw      : SwingParams kwargs shared across all scales.
    detectors     : 'all' or a list of registered detector names.
    dedup_jaccard : Jaccard overlap threshold for cross-scale de-duplication
                    (FR-MS-2). Reserved for B3; accepted but not used in B2.
    containment_tol: sample tolerance for date-range containment tests
                    (FR-MS-3). Reserved for B4; accepted but not used in B2.
    compute_fpr   : if True, run the null-FPR sweep per scale (FR-MS-5) and
                    annotate detections with null_percentile / noteworthy.
                    Slow for large n_null; set False for fast exploratory runs.
    n_null        : random-walk surrogates per scale for FPR estimation.
    seed          : seeds the RNG for reproducible null sweeps (NFR-RP1).

    Returns
    -------
    MultiScaleResult with:
      raw                    — original input series
      denoised_by_scale      — {k_drop: denoised_array} for every scale
      detections             — flat detection list, each tagged with .scale
                               and a globally-unique .detection_id
      roots                  — [] (populated by B4 build_nesting_forest)
      fpr_by_pattern_by_scale— {k_drop: {pattern: fpr}} for every scale;
                               empty inner dict when compute_fpr=False or no
                               detections fired on the null at that scale
      spurious_nesting_fpr   — 0.0 (populated by B6)

    Notes
    -----
    - Existing single-scale code is untouched; this is a loop on top.
    - Per-scale null-FPR (FR-MS-5) uses the matching k_drop when denoising
      null surrogates, so the significance thresholds reflect genuine
      scale-specific false-positive rates.
    - detection_id values are globally unique within the returned
      MultiScaleResult (they are renumbered after each per-scale collect).
    """
    x = np.asarray(x, dtype=np.float64)

    # Build shared denoise base (k_drop will be overridden per scale)
    _base_denoise = {k: v for k, v in (denoise_kw or {}).items() if k != "k_drop"}
    swing_params = SwingParams(**(swing_kw or {}))

    denoiser = WaveletDenoiser()
    extractor = SwingExtractor()

    all_detections = []
    denoised_by_scale: dict = {}
    fpr_by_pattern_by_scale: dict = {k: {} for k in scales}  # always has all keys

    n = len(x)
    vol = max(float(estimate_volatility(x)), 1e-8)
    global_id = 0  # monotonic counter for globally-unique detection_id

    for k_drop in sorted(scales):
        denoise_params = DenoiseParams(**_base_denoise, k_drop=k_drop)

        # Layer 1: denoise at this scale
        try:
            ts = TimeSeries(x)
            denoised = denoiser.denoise(ts, denoise_params)
        except Exception:
            denoised_by_scale[k_drop] = x.copy()
            continue
        denoised_by_scale[k_drop] = denoised

        # Layer 2a: extract swings from the denoised series
        try:
            denoised_ts = TimeSeries(denoised)
            swings = extractor.extract(denoised_ts, swing_params)
        except Exception:
            swings = []

        if len(swings) < 2:
            continue

        skeleton = SwingSkeleton(swings)

        # Layer 2b: detect patterns (registry assigns IDs 0..N-1 per call)
        dets = detect_patterns(skeleton, denoised, detectors)

        # Tag with scale; renumber to globally unique IDs
        for d in dets:
            d.scale = k_drop
            d.detection_id = global_id
            global_id += 1

        all_detections.extend(dets)

        # Layer 2c: per-scale null-FPR (FR-MS-5)
        if compute_fpr and dets:
            dist = null_detection_distribution(
                length=n,
                volatility=vol,
                detectors=detectors,
                n_null=n_null,
                seed=seed,
                swing_params=swing_params,
                denoise_params=denoise_params,
            )
            thresholds = annotate_significance(dets, dist)
            fpr_by_pattern_by_scale[k_drop] = {
                p: t.fpr for p, t in thresholds.items()
            }

    return MultiScaleResult(
        raw=x.copy(),
        denoised_by_scale=denoised_by_scale,
        detections=all_detections,
        roots=[],               # B4 fills this in
        fpr_by_pattern_by_scale=fpr_by_pattern_by_scale,
        spurious_nesting_fpr=0.0,   # B6 fills this in
    )
