"""Multi-scale pattern detection pipeline (FR-MS-1 / FR-MS-2 / FR-MS-5).

Runs the existing single-scale pipeline (denoise → swing → detect) at
several wavelet denoising levels (k_drop values), de-duplicates detections
that survive at adjacent scales, and collects the result into a unified
MultiScaleResult.

Layer relationships
-------------------
This module is a **loop-and-reconciliation layer** on top of the
single-scale infrastructure; it never reimplements denoising, swing
extraction, or detection logic.

Part B task map
---------------
B2  multi-scale sweep + per-scale null-FPR
B3  this module: cross-scale de-duplication (_dedup_detections)
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


# ── B3 helpers ────────────────────────────────────────────────────────────────

def _jaccard_interval(start_a: int, end_a: int, start_b: int, end_b: int) -> float:
    """Jaccard overlap of two closed integer intervals (inclusive bar indices)."""
    inter = max(0, min(end_a, end_b) - max(start_a, start_b) + 1)
    union = max(end_a, end_b) - min(start_a, start_b) + 1
    return inter / union if union > 0 else 0.0


def _dedup_detections(
    detections: list,
    dedup_jaccard: float = 0.7,
) -> list:
    """Merge near-duplicate cross-scale detections in-place (FR-MS-2).

    Two detections are candidates for merging when:
      (a) same ``pattern`` name,
      (b) interval Jaccard overlap > ``dedup_jaccard``, and
      (c) ``|scale_a - scale_b| <= 1`` (adjacent or same scale).

    A union-find provides transitive closure: if A qualifies with B and B
    qualifies with C, all three are merged even if A and C do not directly
    qualify (e.g. because |scale_A - scale_C| = 2 but B bridges them).

    For each merged group:
      - The detection with the highest ``score`` is the *keeper*.
      - ``keeper.scale`` is set to the **coarsest** (largest) k_drop across
        the group — the most "certain" scale where the pattern survived.
      - ``keeper.also_seen_at_scales`` records every other k_drop in the
        group (sorted ascending).
      - All other group members are discarded.

    Detections that do not qualify with any partner pass through unchanged.
    The returned list is sorted by ``start_index``.

    Parameters
    ----------
    detections   : flat list of Detection objects (scale-tagged by B2).
    dedup_jaccard: Jaccard threshold; pairs with overlap ≤ this value are
                   NOT merged.  Default 0.7 per FR-MS-2.
    """
    n = len(detections)
    if n < 2:
        return list(detections)

    # ── Union-Find ────────────────────────────────────────────────────────────
    parent = list(range(n))

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]   # path halving
            x = parent[x]
        return x

    def _union(x: int, y: int) -> None:
        px, py = _find(x), _find(y)
        if px != py:
            parent[px] = py

    # Evaluate all O(n²) pairs; n is typically small (< 50 detections).
    for i in range(n):
        for j in range(i + 1, n):
            di, dj = detections[i], detections[j]
            if di.pattern != dj.pattern:
                continue
            si = di.scale if di.scale is not None else 0
            sj = dj.scale if dj.scale is not None else 0
            if abs(si - sj) > 1:
                continue
            if _jaccard_interval(
                di.start_index, di.end_index, dj.start_index, dj.end_index
            ) > dedup_jaccard:
                _union(i, j)

    # ── Collect groups and pick keeper ───────────────────────────────────────
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(_find(i), []).append(i)

    result = []
    for indices in groups.values():
        group = [detections[i] for i in indices]
        keeper = max(group, key=lambda d: d.score)

        if len(group) > 1:
            all_scales: set[int] = set()
            for d in group:
                if d.scale is not None:
                    all_scales.add(d.scale)
                all_scales.update(d.also_seen_at_scales)

            coarsest = max(all_scales) if all_scales else keeper.scale
            keeper.scale = coarsest
            keeper.also_seen_at_scales = sorted(s for s in all_scales if s != coarsest)

        result.append(keeper)

    result.sort(key=lambda d: d.start_index)
    return result


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
                    (FR-MS-2).  Detections of the same pattern at adjacent
                    scales with overlap > this value are merged into one.
    containment_tol: sample tolerance for date-range containment tests
                    (FR-MS-3). Reserved for B4; accepted but not used yet.
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
      detections             — de-duplicated flat list, each tagged with
                               .scale (coarsest surviving level) and a
                               globally-unique .detection_id; merged members
                               record their other scales in .also_seen_at_scales
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
      MultiScaleResult; dedup may leave gaps in the sequence (that is fine —
      IDs only need to be unique, not contiguous).
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

    # B3: cross-scale de-duplication (FR-MS-2)
    deduped = _dedup_detections(all_detections, dedup_jaccard=dedup_jaccard)

    return MultiScaleResult(
        raw=x.copy(),
        denoised_by_scale=denoised_by_scale,
        detections=deduped,
        roots=[],               # B4 fills this in
        fpr_by_pattern_by_scale=fpr_by_pattern_by_scale,
        spurious_nesting_fpr=0.0,   # B6 fills this in
    )
