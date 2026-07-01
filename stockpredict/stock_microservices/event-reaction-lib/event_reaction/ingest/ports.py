"""ingest/ ports — the mockable data-source interfaces (SRS §4.3).

These Protocols are the ONLY seam through which the (pure) stats core receives data.
Adapters that perform network/DB I/O implement them; tests use in-memory fakes.
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class EventSource(Protocol):
    """Materialises the events contract: DataFrame[event_id, ts_utc(UTC), kind, actual, consensus]."""

    def fetch(
        self,
        kind: Optional[str] = None,
        since: Optional[pd.Timestamp] = None,
        until: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        ...


@runtime_checkable
class PriceSource(Protocol):
    """Daily OHLC close as a tz-aware UTC ``pd.Series`` (v1)."""

    def history(
        self,
        symbol: str,
        start: Optional[pd.Timestamp] = None,
        end: Optional[pd.Timestamp] = None,
    ) -> pd.Series:
        ...

    # def intraday(self, symbol, start, end) -> pd.Series: ...   # specified, deferred (EC5)


@runtime_checkable
class OddsSource(Protocol):
    """Pre-event market-implied odds in [0,1] as a tz-aware UTC ``pd.Series``."""

    def series(
        self,
        ref: str,
        start: Optional[pd.Timestamp] = None,
        end: Optional[pd.Timestamp] = None,
    ) -> pd.Series:
        ...
