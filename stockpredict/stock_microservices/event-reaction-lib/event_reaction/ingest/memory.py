"""ingest/ in-memory adapters — offline test doubles for the ports (SRS §4.3, NFR-1).

No I/O: they let the entire stats core + orchestration run with fixtures only.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

_EVENTS_COLUMNS = ["event_id", "ts_utc", "kind", "actual", "consensus"]


class InMemoryEventSource:
    def __init__(self, events: pd.DataFrame):
        self._events = events.reset_index(drop=True)

    def fetch(
        self,
        kind: Optional[str] = None,
        since: Optional[pd.Timestamp] = None,
        until: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        df = self._events
        if kind is not None:
            df = df[df["kind"] == kind]
        if since is not None:
            df = df[df["ts_utc"] >= since]
        if until is not None:
            df = df[df["ts_utc"] <= until]
        return df.reset_index(drop=True)


class InMemoryPriceSource:
    def __init__(self, prices: dict[str, pd.Series]):
        self._prices = prices

    def history(
        self,
        symbol: str,
        start: Optional[pd.Timestamp] = None,
        end: Optional[pd.Timestamp] = None,
    ) -> pd.Series:
        s = self._prices[symbol]
        if start is not None:
            s = s[s.index >= start]
        if end is not None:
            s = s[s.index <= end]
        return s


class InMemoryOddsSource:
    def __init__(self, series: dict[str, pd.Series]):
        self._series = series

    def series(
        self,
        ref: str,
        start: Optional[pd.Timestamp] = None,
        end: Optional[pd.Timestamp] = None,
    ) -> pd.Series:
        s = self._series[ref]
        if start is not None:
            s = s[s.index >= start]
        if end is not None:
            s = s[s.index <= end]
        return s
