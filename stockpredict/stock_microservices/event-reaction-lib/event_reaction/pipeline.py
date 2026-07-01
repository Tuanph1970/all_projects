"""pipeline — single-event orchestration + the no-leakage guard (FR-NOLEAK, EC1).

Pure stats orchestration: NO I/O. Wires align -> surprise -> returns -> jumps into one
``EventReaction``. ``assert_no_leakage`` is the executable causality guard: mutating data
strictly AFTER the event window must not change any pre-event/at-event quantity.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from event_reaction.align import log_returns, make_windows, resolve_event_day
from event_reaction.exceptions import InsufficientDataError, LeakageError
from event_reaction.jumps import jump_test_daily
from event_reaction.returns import abnormal_returns
from event_reaction.surprise import make_surprise
from event_reaction.types import DEFAULTS, EventReaction, Params


def measure_event_reaction(
    event_row,
    prices: pd.Series,
    market: pd.Series,
    *,
    params: Params = DEFAULTS,
    odds: Optional[pd.Series] = None,
    prior_same_kind: Optional[pd.DataFrame] = None,
    surprise_method: str = "consensus",
    jump_n_null: int = 0,
) -> EventReaction:
    """Measure one event's reaction (SRS §4.2).

    ``prices``/``market`` are tz-aware UTC daily price series on the same index.
    ``prior_same_kind`` (strictly-before same-kind events) feeds the surprise scale;
    the caller is responsible for filtering it to pre-event rows (EC1). ``jump_n_null``
    opt-in requests the EC4 null-FPR (perf: 0 by default).
    """
    ri = log_returns(prices)
    rm = log_returns(market)
    if len(ri) != len(rm) or not ri.index.equals(rm.index):
        raise InsufficientDataError("prices and market must share the same tz-aware index")

    t0 = resolve_event_day(pd.Timestamp(event_row["ts_utc"]), ri.index)
    aligned = make_windows(
        t0, len(ri),
        L=params.L, g=params.g, k1=params.k1, k2=params.k2,
        event_id=str(event_row.get("event_id", "")),
    )
    surprise = make_surprise(event_row, prior_same_kind, method=surprise_method, odds=odds)
    abnormal = abnormal_returns(ri, rm, aligned.est_window, aligned.event_window)
    jump = jump_test_daily(
        ri, t0,
        level=params.jump_level, local_window=params.jump_local_window,
        n_null=jump_n_null, seed=params.seed,
    )
    return EventReaction(aligned=aligned, surprise=surprise, abnormal=abnormal, jump=jump)


def assert_no_leakage(
    event_row,
    prices: pd.Series,
    market: pd.Series,
    *,
    params: Params = DEFAULTS,
    odds: Optional[pd.Series] = None,
    prior_same_kind: Optional[pd.DataFrame] = None,
    surprise_method: str = "consensus",
    seed: int = 0,
) -> None:
    """Assert no look-ahead (EC1, FR-NOLEAK).

    Recompute the measurement after replacing all prices strictly AFTER the event window
    with noise; every pre-event/at-event quantity (surprise, alpha, beta, sigma_AR,
    sigma_local, CAR) must be unchanged. Raises ``LeakageError`` otherwise.
    """
    base = measure_event_reaction(
        event_row, prices, market,
        params=params, odds=odds, prior_same_kind=prior_same_kind,
        surprise_method=surprise_method,
    )
    t0 = base.aligned.t0_index
    # Last price index used by the event window: ri[t0+k2] = log(P[t0+k2+1]/P[t0+k2]).
    first_unused_price = t0 + params.k2 + 2
    rng = np.random.default_rng(seed)

    def _mutate(series: pd.Series) -> pd.Series:
        out = series.copy()
        n_tail = len(out) - first_unused_price
        if n_tail > 0:
            anchor = float(out.iloc[first_unused_price - 1])
            noise = anchor * np.exp(np.cumsum(rng.normal(0.0, 0.05, n_tail)))
            out.iloc[first_unused_price:] = noise
        return out

    after = measure_event_reaction(
        event_row, _mutate(prices), _mutate(market),
        params=params, odds=odds, prior_same_kind=prior_same_kind,
        surprise_method=surprise_method,
    )

    checks = {
        "surprise.s": (base.surprise.s, after.surprise.s),
        "alpha": (base.abnormal.alpha, after.abnormal.alpha),
        "beta": (base.abnormal.beta, after.abnormal.beta),
        "sigma_ar": (base.abnormal.sigma_ar, after.abnormal.sigma_ar),
        "car": (base.abnormal.car, after.abnormal.car),
        "sigma_local": (base.jump.sigma_local, after.jump.sigma_local),
    }
    for name, (b, a) in checks.items():
        if not np.isclose(b, a, rtol=1e-9, atol=1e-12):
            raise LeakageError(
                f"post-event mutation changed pre-event quantity {name!r}: {b} -> {a}"
            )
