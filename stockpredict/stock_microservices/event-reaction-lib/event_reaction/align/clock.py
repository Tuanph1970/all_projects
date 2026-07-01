"""align/ — UTC event clock, log returns, estimation/event windows (FR-ALIGN).

Pure stats stage: NO I/O. All timestamps are tz-aware UTC (EC6). Windows never
extend past the data (that would force look-ahead — EC1).

Index convention (the B5 off-by-one trap, handled once, here):
    ``log_returns`` returns a series indexed by ``prices.index[1:]`` — the return at
    date *d* is ``log(P_d / P_{d-1})``. Everything downstream (returns/jumps) works in
    this **returns-index space**. Resolve the event day against the *returns* index so
    the resolved position is the event-day return itself.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from event_reaction.exceptions import AlignmentError, InsufficientDataError
from event_reaction.types import AlignedEvent


def _require_utc_index(index: pd.Index, what: str) -> pd.DatetimeIndex:
    if not isinstance(index, pd.DatetimeIndex):
        raise AlignmentError(f"{what} must have a DatetimeIndex")
    if index.tz is None:
        raise AlignmentError(f"{what} index must be tz-aware UTC (got naive)")
    if not index.is_monotonic_increasing:
        raise AlignmentError(f"{what} index must be monotonic increasing")
    return index


def log_returns(prices: pd.Series) -> pd.Series:
    """Daily log returns ``log(P_t / P_{t-1})``.

    Returns a Series of length ``len(prices) - 1`` indexed by ``prices.index[1:]``,
    tz-aware UTC preserved.
    """
    _require_utc_index(prices.index, "prices")
    if len(prices) < 2:
        raise InsufficientDataError("need at least 2 prices to compute a return")
    r = np.log(prices.to_numpy()[1:] / prices.to_numpy()[:-1])
    return pd.Series(r, index=prices.index[1:], name="log_return")


def resolve_event_day(ts_utc: pd.Timestamp, index: pd.DatetimeIndex) -> int:
    """Position in ``index`` of the first bar whose UTC calendar date is on/after the
    event's UTC date (announcement-date convention, EC6).

    v1 (daily) uses the event timestamp only to derive its UTC calendar date; an
    after-close event still resolves to its announcement day. Modelling a session
    close (after-close → next session) is a deferred v2 refinement (EC5).

    Raises AlignmentError if ``ts_utc`` is naive or falls after the last bar.
    """
    ts = pd.Timestamp(ts_utc)
    if ts.tzinfo is None:
        raise AlignmentError("event timestamp must be tz-aware UTC (got naive)")
    index = _require_utc_index(index, "price/return")

    event_day = ts.tz_convert("UTC").normalize()
    idx_days = index.tz_convert("UTC").normalize()
    pos = int(idx_days.searchsorted(event_day, side="left"))
    if pos >= len(index):
        raise AlignmentError(
            f"event day {event_day.date()} is after the last available bar "
            f"{idx_days[-1].date()}"
        )
    return pos


def make_windows(
    t0_index: int,
    n: int,
    *,
    L: int = 120,
    g: int = 5,
    k1: int = 1,
    k2: int = 1,
    event_id: str = "",
) -> AlignedEvent:
    """Build estimation and event windows around ``t0_index`` in an array of length ``n``.

    Windows are **half-open** integer positions ``[start, end)``:
        est_window   = [t0-(L+g), t0-g)   — L observations, ends strictly before t0 (EC1)
        event_window = [t0-k1, t0+k2+1)   — includes t0+k2

    Raises AlignmentError if either window extends beyond ``[0, n)`` (no future
    padding — EC1).
    """
    if not 0 <= t0_index < n:
        raise AlignmentError(f"t0_index {t0_index} out of range [0, {n})")

    est_start = t0_index - (L + g)
    est_end = t0_index - g  # exclusive
    ev_start = t0_index - k1
    ev_end = t0_index + k2 + 1  # exclusive

    if est_start < 0:
        raise AlignmentError(
            f"estimation window starts at {est_start} < 0 (need {L + g} bars before t0)"
        )
    if est_end <= est_start:
        raise AlignmentError(f"empty estimation window [{est_start}, {est_end})")
    if ev_start < 0 or ev_end > n:
        raise AlignmentError(
            f"event window [{ev_start}, {ev_end}) out of range [0, {n})"
        )
    # EC1 guard: estimation must end strictly before the event window opens.
    if est_end > ev_start:
        raise AlignmentError(
            f"estimation window end {est_end} overlaps event window start {ev_start}"
        )

    return AlignedEvent(
        event_id=event_id,
        t0_index=t0_index,
        est_window=(est_start, est_end),
        event_window=(ev_start, ev_end),
        coverage="full",
    )
