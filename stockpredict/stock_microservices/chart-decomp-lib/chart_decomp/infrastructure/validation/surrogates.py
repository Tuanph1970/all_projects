"""Random-walk surrogate generator for the mandatory null comparison (FR-FPR-1).

A pattern detector's significance is only interpretable against a null: how
often does the full pipeline fire on pure random-walk series matched to the
target's length and volatility? (SRS §II.2.2 L3, Trap B3.) This module produces
those surrogates; the null evaluator (A11) runs the pipeline over them.

All draws are reproducible from a single ``seed`` (NFR-RP1 / II.5.4).
"""
from __future__ import annotations

from typing import Iterator, Optional

import numpy as np

from chart_decomp.domain.exceptions import InputValidationError


def random_walk_surrogates(
    length: int,
    volatility: float,
    n: int = 1000,
    *,
    seed: Optional[int] = None,
    start: float = 0.0,
) -> Iterator[np.ndarray]:
    """Yield ``n`` independent Gaussian random-walk paths.

    Each path has ``length`` samples, starts at ``start``, and is the cumulative
    sum of i.i.d. ``N(0, volatility)`` increments — so its per-step volatility
    matches ``volatility`` and it has no genuine chart pattern by construction.

    Parameters
    ----------
    length     : samples per surrogate (>= 2)
    volatility : per-step standard deviation of increments (>= 0)
    n          : number of surrogates to yield (>= 1)
    seed       : seeds a single Generator for the whole batch (reproducible)
    start      : value of the first sample

    Yields
    ------
    np.ndarray of shape (length,)

    Notes
    -----
    A generator (lazy) is used so the null evaluator can stream 1000+ surrogates
    through the pipeline without materialising them all at once.
    """
    if length < 2:
        raise InputValidationError("surrogate length must be >= 2")
    if volatility < 0:
        raise InputValidationError("surrogate volatility must be >= 0")
    if n < 1:
        raise InputValidationError("surrogate n must be >= 1")

    rng = np.random.default_rng(seed)
    for _ in range(n):
        inc = rng.normal(0.0, volatility, size=length)
        inc[0] = 0.0  # first sample == start
        yield start + np.cumsum(inc)


def estimate_volatility(x: np.ndarray) -> float:
    """Per-step volatility of a series: the std of its first differences.

    Convenience for matching a surrogate batch to a target series."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1 or len(x) < 2:
        raise InputValidationError("estimate_volatility needs a 1-D series of length >= 2")
    return float(np.std(np.diff(x)))
