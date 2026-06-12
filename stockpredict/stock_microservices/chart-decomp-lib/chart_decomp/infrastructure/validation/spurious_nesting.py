"""Spurious-nesting null rate (FR-MS-5 / FR-MS-TEST-5).

The multi-scale pipeline (B2–B4) reports parent→child nesting links by date-range
containment.  Some of those links arise purely by chance: on a structureless
random walk, two unrelated detections at adjacent scales can still satisfy the
containment + single-leg test.  Before any observed nesting is called meaningful
it must be compared against this **null rate** — the average number of nesting
links the same pipeline invents on pure random-walk series matched to the
target's length and volatility (Trap MS-B3 / Part II constraint L3).

This module reuses the Part A surrogate generator and runs the EXISTING
multi-scale pipeline over the surrogates; it never reimplements detection or
nesting.  A nesting structure is "noteworthy" only when its link count exceeds
the null rate (FR-MS-5).

Public API
----------
spurious_nesting_distribution(length, volatility, scales, ...) -> SpuriousNestingNull
spurious_nesting_fpr(length, volatility, scales, ...) -> float   # convenience
is_nesting_noteworthy(n_links, null_rate) -> bool
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Union

import numpy as np

from chart_decomp.infrastructure.validation.surrogates import random_walk_surrogates


@dataclass
class SpuriousNestingNull:
    """Null distribution of nesting links over random-walk surrogates (FR-MS-5).

    Attributes
    ----------
    fpr         : mean parent→child links per surrogate — THE null rate.  A real
                  nesting structure is noteworthy only above this (FR-MS-5).
    pct95       : 95th percentile of the per-surrogate link count.  A stricter,
                  optional gate for callers who want tail control rather than the
                  mean-rate gate the spec mandates.
    link_counts : per-surrogate parent→child link count, shape (n_null,).
    n_null      : number of surrogates evaluated.
    length      : sample length of each surrogate.
    volatility  : per-step std of each surrogate.
    """

    fpr: float
    pct95: float
    link_counts: np.ndarray
    n_null: int
    length: int
    volatility: float


def spurious_nesting_distribution(
    length: int,
    volatility: float,
    scales: tuple[int, ...] = (1, 2, 3),
    *,
    denoise_kw: Optional[dict] = None,
    swing_kw: Optional[dict] = None,
    detectors: Union[str, Iterable[str]] = "all",
    dedup_jaccard: float = 0.7,
    containment_tol: int = 2,
    n_null: int = 1000,
    seed: Optional[int] = None,
) -> SpuriousNestingNull:
    """Measure parent→child nesting links on random-walk surrogates (FR-MS-5).

    For each of ``n_null`` random-walk surrogates matched to ``(length,
    volatility)``, run the full multi-scale pipeline (sweep → de-dup → nesting
    forest) and count how many detections end up with a parent.  The mean of
    those counts is the spurious-nesting false-positive rate.

    Parameters mirror :func:`detect_multiscale` so the null is measured under the
    SAME configuration as the real run (matching scales, dedup, tolerance).

    Notes
    -----
    The inner :func:`detect_multiscale` calls run with ``compute_fpr=False`` —
    the surrogate sweep needs only the nesting forest, not a nested per-scale
    null sweep (and certainly not a recursive spurious-nesting measurement).
    """
    # Lazy import breaks the import cycle: detect_multiscale imports this module.
    from chart_decomp.application.multiscale_pipeline_usecase import detect_multiscale

    counts: list[int] = []
    for x in random_walk_surrogates(
        length=length, volatility=volatility, n=n_null, seed=seed
    ):
        if not np.all(np.isfinite(x)):
            counts.append(0)
            continue
        res = detect_multiscale(
            x,
            scales=scales,
            denoise_kw=denoise_kw,
            swing_kw=swing_kw,
            detectors=detectors,
            dedup_jaccard=dedup_jaccard,
            containment_tol=containment_tol,
            compute_fpr=False,
        )
        counts.append(sum(1 for d in res.detections if d.parent_id is not None))

    arr = np.asarray(counts, dtype=np.intp)
    fpr = float(arr.mean()) if arr.size else 0.0
    pct95 = float(np.percentile(arr, 95)) if arr.size else 0.0

    return SpuriousNestingNull(
        fpr=fpr,
        pct95=pct95,
        link_counts=arr,
        n_null=n_null,
        length=length,
        volatility=volatility,
    )


def spurious_nesting_fpr(
    length: int,
    volatility: float,
    scales: tuple[int, ...] = (1, 2, 3),
    *,
    denoise_kw: Optional[dict] = None,
    swing_kw: Optional[dict] = None,
    detectors: Union[str, Iterable[str]] = "all",
    dedup_jaccard: float = 0.7,
    containment_tol: int = 2,
    n_null: int = 1000,
    seed: Optional[int] = None,
) -> float:
    """Convenience wrapper returning only the null rate (mean links/surrogate)."""
    return spurious_nesting_distribution(
        length,
        volatility,
        scales,
        denoise_kw=denoise_kw,
        swing_kw=swing_kw,
        detectors=detectors,
        dedup_jaccard=dedup_jaccard,
        containment_tol=containment_tol,
        n_null=n_null,
        seed=seed,
    ).fpr


def is_nesting_noteworthy(n_links: int, null_rate: float) -> bool:
    """True iff an observed nesting link count exceeds the null rate (FR-MS-5).

    Nesting that occurs no more than the random-walk null rate is NOT noteworthy;
    only a count strictly above it is.  ``null_rate`` is ``SpuriousNestingNull.fpr``
    (or ``MultiScaleResult.spurious_nesting_fpr``).
    """
    return n_links > null_rate
