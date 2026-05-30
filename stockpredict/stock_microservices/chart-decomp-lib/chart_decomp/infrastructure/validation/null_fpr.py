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
