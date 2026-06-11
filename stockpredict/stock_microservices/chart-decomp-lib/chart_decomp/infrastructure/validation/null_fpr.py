"""Null false-positive rate evaluator (FR-FPR-1/2).

Measures how often each detector fires on pure random-walk series — the
indispensable null comparison that makes any detection interpretable (SRS
§II.2.2 L3, Trap B3).

Public API
----------
null_fpr(length, volatility, detectors, params, swing_params) -> NullFPRResult
    Run the full pattern pipeline on ``params.n_null`` random-walk surrogates
    and return per-pattern FPR (mean detections per series) and 95th-percentile
    quality scores for the significance gate.

is_noteworthy(detection, null_result) -> bool
    FR-FPR-2: True iff the detection's score exceeds the null 95th percentile
    for that pattern (or the pattern never appeared in the null, which makes it
    unconditionally significant).

Notes
-----
- Seeded via ``NullFPRParams.seed`` — identical seed → identical results (II.5.4).
- Surrogates are streamed lazily so 1000+ series can be processed without
  materialising them all in memory at once.
- Swing and detection parameters default to SwingParams() and registry 'all'.
  Pass explicit overrides for calibrated experiments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Union

import numpy as np

from chart_decomp.domain.entities import Detection, SwingSkeleton
from chart_decomp.domain.value_objects import NullFPRParams, SwingParams, TimeSeries
from chart_decomp.factories.pattern_detector_factory import detect_patterns
from chart_decomp.infrastructure.swings.swing_extractor import SwingExtractor
from chart_decomp.infrastructure.validation.surrogates import random_walk_surrogates


@dataclass
class NullFPRResult:
    """Result of a null-FPR evaluation (FR-FPR-1/2).

    Attributes
    ----------
    fpr_by_pattern         : mean detections per surrogate per pattern.
    score_pct95_by_pattern : 95th-percentile quality score on the null, per
                             pattern.  Used by is_noteworthy() to gate
                             significance (FR-FPR-2).  Only populated for
                             patterns that fired at least once.
    n_null                 : number of surrogates evaluated.
    length                 : sample length of each surrogate.
    volatility             : per-step std of each surrogate.
    """

    fpr_by_pattern: dict[str, float]
    score_pct95_by_pattern: dict[str, float]
    n_null: int
    length: int
    volatility: float


@dataclass
class PatternThresholds:
    """Per-pattern null thresholds derived from a NullDistribution (FR-FPR-1/2).

    Attributes
    ----------
    pct95 : noteworthy_pct-th percentile of null quality scores for this pattern.
            None when the pattern never fired on any null surrogate — callers
            should treat detections of that pattern as unconditionally noteworthy
            (matches the existing is_noteworthy() convention).
    fpr   : mean detections per surrogate (false-positive rate).
            0.0 when the pattern never fired on any null surrogate.
    """

    pct95: Optional[float]
    fpr: float


@dataclass
class NullDistribution:
    """Raw per-pattern distributions from the surrogate sweep (FR-FPR-1).

    Attributes
    ----------
    scores_by_pattern  : all quality scores produced across all surrogates,
                         concatenated into one flat array per pattern.  Only
                         patterns that fired at least once appear as keys.
    counts_by_pattern  : per-surrogate detection count, one integer per
                         surrogate.  Shape (n_null,) per pattern; element i is
                         how many times pattern p was detected in surrogate i
                         (0 when not detected in that surrogate).
    n_null             : number of surrogates swept.
    length             : sample length of each surrogate.
    volatility         : per-step std of each surrogate.
    """

    scores_by_pattern: dict[str, np.ndarray]
    counts_by_pattern: dict[str, np.ndarray]
    n_null: int
    length: int
    volatility: float


# ── Module-level result cache ─────────────────────────────────────────────────
# Keyed by (length, rounded_volatility, det_key, n_null, seed, swing_params).
# SwingParams is a frozen dataclass and is therefore hashable.
_null_dist_cache: dict = {}


def clear_null_distribution_cache() -> None:
    """Evict all cached NullDistribution results.

    Intended for test teardown and interactive experimentation.  Production code
    does not need to call this; the cache is process-scoped and safe to retain.
    """
    _null_dist_cache.clear()


def _det_key(detectors: Union[str, Iterable[str]]) -> object:
    """Stable, hashable representation of the detectors selector."""
    if detectors == "all":
        return "all"
    return tuple(sorted(detectors))


def null_fpr(
    length: int,
    volatility: float,
    detectors: Union[str, Iterable[str]] = "all",
    params: Optional[NullFPRParams] = None,
    swing_params: Optional[SwingParams] = None,
) -> NullFPRResult:
    """Run the pattern pipeline on random-walk surrogates and report FPR.

    Parameters
    ----------
    length      : samples per surrogate (>= 2).
    volatility  : per-step std of surrogate increments.  Pass
                  ``estimate_volatility(target_series)`` to match a real series.
    detectors   : 'all' or an iterable of registered detector names.
    params      : NullFPRParams (n_null, noteworthy_pct, seed).
    swing_params: SwingParams forwarded to SwingExtractor.  Defaults to
                  SwingParams() (same as the pattern pipeline).

    Returns
    -------
    NullFPRResult with per-pattern FPR and 95th-pct null scores.

    Notes
    -----
    Surrogates with fewer than 2 retained swing pivots are skipped (the swing
    extractor returns an empty list, making detection impossible).  The n_null
    denominator remains the full requested count so FPR reflects the true
    probability of detection — including the probability of an uninformative
    (near-flat) surrogate.
    """
    params = params or NullFPRParams()
    swing_params = swing_params or SwingParams()

    extractor = SwingExtractor()
    det_counts: dict[str, int] = {}
    all_scores: dict[str, list[float]] = {}

    for x in random_walk_surrogates(
        length=length,
        volatility=volatility,
        n=params.n_null,
        seed=params.seed,
    ):
        # TimeSeries validation: skip degenerate (all-equal) surrogates.
        if not np.all(np.isfinite(x)):
            continue
        ts = TimeSeries(x)
        swings = extractor.extract(ts, swing_params)
        if len(swings) < 2:
            continue
        skeleton = SwingSkeleton(swings)
        dets = detect_patterns(skeleton, x, detectors)
        for d in dets:
            det_counts[d.pattern] = det_counts.get(d.pattern, 0) + 1
            all_scores.setdefault(d.pattern, []).append(d.score)

    fpr_by_pattern: dict[str, float] = {
        p: count / params.n_null for p, count in det_counts.items()
    }
    score_pct95: dict[str, float] = {
        p: float(np.percentile(scores, params.noteworthy_pct))
        for p, scores in all_scores.items()
        if scores
    }

    return NullFPRResult(
        fpr_by_pattern=fpr_by_pattern,
        score_pct95_by_pattern=score_pct95,
        n_null=params.n_null,
        length=length,
        volatility=volatility,
    )


def null_detection_distribution(
    length: int,
    volatility: float,
    detectors: Union[str, Iterable[str]] = "all",
    *,
    n_null: int = 1000,
    seed: Optional[int] = None,
    swing_params: Optional[SwingParams] = None,
) -> NullDistribution:
    """Run the swing→detect pipeline on random-walk surrogates; return raw distributions.

    This is the data-collection layer for the null-FPR machinery (FR-FPR-1).
    A3 derives thresholds (pct95, mean FPR) from this output; A4 uses the raw
    score arrays to compute per-detection percentile ranks.

    Results are cached so repeated calls with identical parameters are free.
    The cache key covers (length, rounded_volatility, detectors, n_null, seed,
    swing_params); changing any of these forces a fresh sweep.

    Parameters
    ----------
    length      : samples per surrogate (>= 2).
    volatility  : per-step std of surrogate increments.  Pass
                  ``estimate_volatility(target_series)`` to match a real series.
    detectors   : 'all' or an iterable of registered detector names.
    n_null      : number of random-walk surrogates to sweep.
    seed        : seeds the RNG for reproducibility (NFR-RP1).
    swing_params: SwingParams forwarded to SwingExtractor.  Defaults to
                  SwingParams() (same default as null_fpr).

    Returns
    -------
    NullDistribution with:
      scores_by_pattern  — flat array of all null scores per pattern
      counts_by_pattern  — per-surrogate detection count array (length n_null)
    """
    swing_params = swing_params or SwingParams()
    cache_key = (
        length,
        round(volatility, 4),
        _det_key(detectors),
        n_null,
        seed,
        swing_params,
    )
    if cache_key in _null_dist_cache:
        return _null_dist_cache[cache_key]

    extractor = SwingExtractor()
    all_scores: dict[str, list[float]] = {}
    # One dict per surrogate recording how many detections each pattern had.
    per_surr_counts: list[dict[str, int]] = []

    for x in random_walk_surrogates(
        length=length, volatility=volatility, n=n_null, seed=seed
    ):
        if not np.all(np.isfinite(x)):
            per_surr_counts.append({})
            continue
        ts = TimeSeries(x)
        swings = extractor.extract(ts, swing_params)
        surr_counts: dict[str, int] = {}
        if len(swings) >= 2:
            skeleton = SwingSkeleton(swings)
            dets = detect_patterns(skeleton, x, detectors)
            for d in dets:
                all_scores.setdefault(d.pattern, []).append(d.score)
                surr_counts[d.pattern] = surr_counts.get(d.pattern, 0) + 1
        per_surr_counts.append(surr_counts)

    # Build per-pattern arrays from the collected data.
    all_patterns: set[str] = set(all_scores.keys())
    counts_by_pattern: dict[str, np.ndarray] = {
        p: np.array([sc.get(p, 0) for sc in per_surr_counts], dtype=np.intp)
        for p in all_patterns
    }
    scores_by_pattern: dict[str, np.ndarray] = {
        p: np.asarray(s, dtype=np.float64) for p, s in all_scores.items()
    }

    result = NullDistribution(
        scores_by_pattern=scores_by_pattern,
        counts_by_pattern=counts_by_pattern,
        n_null=n_null,
        length=length,
        volatility=volatility,
    )
    _null_dist_cache[cache_key] = result
    return result


def null_thresholds(
    dist: NullDistribution,
    extra_patterns: Optional[Iterable[str]] = None,
    *,
    noteworthy_pct: float = 95.0,
) -> dict[str, PatternThresholds]:
    """Derive pct95 threshold and FPR per pattern from a NullDistribution (FR-FPR-1/2).

    Parameters
    ----------
    dist             : NullDistribution returned by null_detection_distribution().
    extra_patterns   : additional pattern names to include in the output even if
                       they never appeared in the null sweep.  Those entries get
                       the sentinel PatternThresholds(pct95=None, fpr=0.0).
                       Useful when a detector rarely fires on short null series
                       but callers still need a threshold dict keyed by every
                       possible pattern (e.g. for a real-detection annotation loop).
    noteworthy_pct   : percentile used as the significance threshold (default 95,
                       matching NullFPRParams.noteworthy_pct).

    Returns
    -------
    dict mapping each pattern name to PatternThresholds(pct95, fpr):
      • Patterns that fired at least once: pct95 = np.quantile(scores, p/100),
        fpr = mean(counts_by_pattern[p]).
      • Patterns listed in extra_patterns but absent from dist: sentinel
        PatternThresholds(pct95=None, fpr=0.0).

    Notes
    -----
    A pct95 of None signals "the null never produced this pattern" — callers
    should treat detections of such patterns as unconditionally noteworthy,
    consistent with is_noteworthy()'s existing None-guard logic.
    """
    result: dict[str, PatternThresholds] = {}

    for pat, scores in dist.scores_by_pattern.items():
        pct95 = float(np.quantile(scores, noteworthy_pct / 100.0))
        fpr = float(dist.counts_by_pattern[pat].mean())
        result[pat] = PatternThresholds(pct95=pct95, fpr=fpr)

    if extra_patterns is not None:
        for pat in extra_patterns:
            if pat not in result:
                result[pat] = PatternThresholds(pct95=None, fpr=0.0)

    return result


def annotate_significance(
    detections: list[Detection],
    dist: NullDistribution,
    *,
    noteworthy_pct: float = 95.0,
) -> dict[str, PatternThresholds]:
    """Annotate detections with null_percentile and noteworthy in-place (FR-FPR-2).

    For each detection, sets:
      null_percentile — fraction of null scores ≤ detection.score, scaled to [0, 100].
                        100.0 for patterns that never fired on any null surrogate.
      noteworthy      — True iff detection.score > null pct95 threshold.
                        Unconditionally True when the pattern has no null distribution.

    Parameters
    ----------
    detections    : list of Detection objects to annotate (mutated in-place).
    dist          : NullDistribution from null_detection_distribution().
    noteworthy_pct: percentile used as the significance threshold (default 95).

    Returns
    -------
    dict mapping each pattern name to its PatternThresholds (pct95, fpr).
    Includes sentinel entries for patterns present in detections but absent from dist.
    """
    extra = [d.pattern for d in detections]
    thresholds = null_thresholds(dist, extra_patterns=extra, noteworthy_pct=noteworthy_pct)

    for d in detections:
        thresh = thresholds[d.pattern]
        null_scores = dist.scores_by_pattern.get(d.pattern)
        if null_scores is not None and len(null_scores) > 0:
            d.null_percentile = float(np.mean(null_scores <= d.score)) * 100.0
        else:
            d.null_percentile = 100.0
        if thresh.pct95 is None:
            d.noteworthy = True
        else:
            d.noteworthy = bool(d.score > thresh.pct95)

    return thresholds


def is_noteworthy(detection: Detection, null_result: NullFPRResult) -> bool:
    """FR-FPR-2: True iff detection.score exceeds the null 95th-pct score.

    If the pattern never appeared in the null runs (pct95 undefined), the
    detection is unconditionally noteworthy — any signal in a regime where
    random walks produce nothing is significant by definition.
    """
    pct95 = null_result.score_pct95_by_pattern.get(detection.pattern)
    if pct95 is None:
        return True
    return float(detection.score) > pct95
