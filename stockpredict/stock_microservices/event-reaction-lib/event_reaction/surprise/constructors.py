"""surprise/ — observed surprise constructors (FR-SURP, EC1, EC2).

Surprise is OBSERVED/external, never modelled from the price series. Every constructor
uses only pre-event values. A surprise is standardised by the pre-event dispersion of
prior same-kind surprises (``scale``); with too little history the scale falls back to
1.0 (``s == s_raw``), documented below.

Constructors (registry ``CONSTRUCTORS``):
    consensus  (default) : s_raw = actual - consensus
    futures    (Kuttner) : s_raw = actual - futures-implied level
    odds                 : s_raw = actual - last odds strictly before the event
    llm        (DEFERRED): raises NotImplementedError (chatbot subsystem, v2)
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np
import pandas as pd

from event_reaction.exceptions import InsufficientDataError
from event_reaction.types import Surprise


def _scale_from_prior(raw_prior: np.ndarray) -> float:
    """Standardisation scale = sample std of prior same-kind raw surprises.

    Fallback to 1.0 when fewer than 2 finite priors or a degenerate (zero) spread —
    the surprise is then reported unstandardised (``s == s_raw``).
    """
    raw_prior = np.asarray(raw_prior, dtype=float)
    raw_prior = raw_prior[np.isfinite(raw_prior)]
    if raw_prior.size < 2:
        return 1.0
    sd = float(np.std(raw_prior, ddof=1))
    return sd if sd > 0 else 1.0


def _finalize(method: str, actual: float, expected: float, scale: float) -> Surprise:
    s_raw = float(actual) - float(expected)
    s = s_raw / scale
    return Surprise(
        method=method,
        s_raw=s_raw,
        s=s,
        expected=float(expected),
        scale=float(scale),
        sign=int(np.sign(s_raw)),
    )


def _consensus(event_row, prior_same_kind, *, odds=None, futures=None) -> Surprise:
    if "consensus" not in event_row or pd.isna(event_row["consensus"]):
        raise InsufficientDataError("consensus constructor requires a 'consensus' value")
    expected = float(event_row["consensus"])
    if prior_same_kind is not None and len(prior_same_kind) and {
        "actual",
        "consensus",
    } <= set(prior_same_kind.columns):
        raw_prior = (prior_same_kind["actual"] - prior_same_kind["consensus"]).to_numpy()
    else:
        raw_prior = np.empty(0)
    return _finalize("consensus", event_row["actual"], expected, _scale_from_prior(raw_prior))


def _futures(event_row, prior_same_kind, *, odds=None, futures=None) -> Surprise:
    expected = futures if futures is not None else event_row.get("futures_implied")
    if expected is None or pd.isna(expected):
        raise InsufficientDataError(
            "futures/Kuttner constructor requires a pre-event futures-implied level "
            "(pass futures= or an events 'futures_implied' column)"
        )
    if prior_same_kind is not None and len(prior_same_kind) and {
        "actual",
        "futures_implied",
    } <= set(prior_same_kind.columns):
        raw_prior = (
            prior_same_kind["actual"] - prior_same_kind["futures_implied"]
        ).to_numpy()
    else:
        raw_prior = np.empty(0)
    return _finalize("futures", event_row["actual"], expected, _scale_from_prior(raw_prior))


def _odds(event_row, prior_same_kind, *, odds=None, futures=None) -> Surprise:
    if odds is None:
        raise InsufficientDataError("odds constructor requires an odds series")
    if not isinstance(odds.index, pd.DatetimeIndex) or odds.index.tz is None:
        raise InsufficientDataError("odds series must have a tz-aware UTC DatetimeIndex")
    ts = pd.Timestamp(event_row["ts_utc"])
    # EC1: use ONLY odds strictly before the event timestamp (the join key).
    pre = odds[odds.index < ts]
    if pre.empty:
        raise InsufficientDataError("no odds value strictly before the event")
    expected = float(pre.iloc[-1])
    if prior_same_kind is not None and len(prior_same_kind) and {
        "actual",
        "odds_implied",
    } <= set(prior_same_kind.columns):
        raw_prior = (prior_same_kind["actual"] - prior_same_kind["odds_implied"]).to_numpy()
    else:
        raw_prior = np.empty(0)
    return _finalize("odds", event_row["actual"], expected, _scale_from_prior(raw_prior))


def _llm(event_row, prior_same_kind, *, odds=None, futures=None) -> Surprise:
    raise NotImplementedError(
        "the 'llm' surprise constructor is deferred to v2 (chatbot subsystem); its "
        "network call belongs in ingest/, not the pure surprise/ stage"
    )


CONSTRUCTORS: dict[str, Callable[..., Surprise]] = {
    "consensus": _consensus,
    "futures": _futures,
    "odds": _odds,
    "llm": _llm,
}


def make_surprise(
    event_row,
    prior_same_kind: Optional[pd.DataFrame] = None,
    *,
    method: str = "consensus",
    odds: Optional[pd.Series] = None,
    futures: Optional[float] = None,
) -> Surprise:
    """Construct a standardised surprise for one event (FR-SURP).

    Parameters
    ----------
    event_row : mapping/Series with at least ``actual``; ``consensus`` for the default
        method; ``ts_utc`` for the odds method.
    prior_same_kind : DataFrame of PAST same-kind events (strictly before the event),
        used only to compute the standardisation scale. May be None/empty.
    method : "consensus" (default) | "futures" | "odds" | "llm" (deferred).
    odds : tz-aware UTC series in [0,1] (required by the odds method).
    futures : pre-event futures-implied level (Kuttner method).
    """
    if method not in CONSTRUCTORS:
        raise ValueError(f"unknown surprise method {method!r}; known: {list(CONSTRUCTORS)}")
    if "actual" not in event_row or pd.isna(event_row["actual"]):
        raise InsufficientDataError("event_row requires a non-null 'actual'")
    return CONSTRUCTORS[method](event_row, prior_same_kind, odds=odds, futures=futures)
