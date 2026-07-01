"""returns/ — market-model abnormal returns + CAR (FR-AR, EC4).

Pure stats stage: NO I/O. Inputs are log-return series/arrays in the same index space
as ``align.log_returns`` output. The market-model parameters are estimated on the
estimation window ONLY (which ends strictly before the event window — EC1), so no
event-window information leaks into alpha/beta or sigma_AR.
"""
from __future__ import annotations

import numpy as np

from event_reaction.exceptions import InsufficientDataError
from event_reaction.types import AbnormalReturns, Window


def _as_array(x) -> np.ndarray:
    return x.to_numpy(dtype=float) if hasattr(x, "to_numpy") else np.asarray(x, dtype=float)


def abnormal_returns(
    asset_logret,
    market_logret,
    est_window: Window,
    event_window: Window,
) -> AbnormalReturns:
    """Market-model abnormal returns over ``event_window``.

    Fits ``r_i = alpha + beta*r_m`` by OLS on ``est_window``; the abnormal return is the
    realised-minus-fitted residual over ``event_window``; ``CAR`` is their sum. Also
    returns a placebo-CAR distribution: the CAR of every event-length window sliding
    across the estimation region (EC4 benchmark).
    """
    ri = _as_array(asset_logret)
    rm = _as_array(market_logret)
    if ri.shape != rm.shape:
        raise InsufficientDataError("asset and market return series must be the same length")

    e0, e1 = est_window
    v0, v1 = event_window
    n = ri.shape[0]
    if not (0 <= e0 < e1 <= n and 0 <= v0 < v1 <= n):
        raise InsufficientDataError("windows out of range")
    if e1 - e0 < 3:
        raise InsufficientDataError("estimation window too short for a market-model fit")

    am, ai = rm[e0:e1], ri[e0:e1]
    beta, alpha = np.polyfit(am, ai, 1)  # deg-1: [slope, intercept]
    resid = ai - (alpha + beta * am)
    dof = max(len(ai) - 2, 1)
    sigma_ar = float(np.sqrt(np.sum(resid ** 2) / dof))

    vm, vi = rm[v0:v1], ri[v0:v1]
    ar = vi - (alpha + beta * vm)
    car = float(ar.sum())

    # Placebo: CAR of each event-length window inside the estimation region (null).
    w = v1 - v0
    placebo = [
        float((ri[s:s + w] - (alpha + beta * rm[s:s + w])).sum())
        for s in range(e0, e1 - w + 1)
    ]

    return AbnormalReturns(
        ar=ar,
        car=car,
        alpha=float(alpha),
        beta=float(beta),
        sigma_ar=sigma_ar,
        est_window=est_window,
        event_window=event_window,
        placebo_car=np.asarray(placebo, dtype=float),
    )
