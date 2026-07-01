"""ingest/ HttpPriceSource — daily OHLC over HTTP from stock-data-service (gap map §2).

Mirrors the prediction-service fetch pattern (prediction_service.py:36-54): GET
``/{prefix}/api/v2/stocks/{symbol}/history``. Does NOT import stock-data-service's
StockRepository (B8). Network I/O lives here only.
"""
from __future__ import annotations

from typing import Optional

import httpx
import pandas as pd

from event_reaction.exceptions import InsufficientDataError


def _fmt(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


class HttpPriceSource:
    def __init__(
        self,
        base_url: str,
        *,
        api_prefix: str = "stock_helper",
        client: Optional[httpx.Client] = None,
        timeout: float = 60.0,
    ):
        self._base = base_url.rstrip("/")
        self._prefix = api_prefix
        self._client = client
        self._timeout = timeout

    def history(
        self,
        symbol: str,
        start: Optional[pd.Timestamp] = None,
        end: Optional[pd.Timestamp] = None,
    ) -> pd.Series:
        url = f"{self._base}/{self._prefix}/api/v2/stocks/{symbol}/history"
        params: dict[str, str] = {}
        if start is not None:
            params["start_date"] = _fmt(start)
        if end is not None:
            params["end_date"] = _fmt(end)

        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.get(url, params=params)
        finally:
            if self._client is None:
                client.close()

        if resp.status_code != 200:
            raise InsufficientDataError(
                f"stock-data-service returned {resp.status_code} for {symbol}"
            )
        data = (resp.json() or {}).get("data") or []
        if not data:
            raise InsufficientDataError(f"no price history returned for {symbol}")

        df = pd.DataFrame(data)
        idx = pd.to_datetime(df["date"], utc=True)  # tz-aware UTC (EC6)
        s = pd.Series(df["close"].astype(float).to_numpy(), index=idx, name="close")
        return s[~s.index.duplicated(keep="last")].sort_index()
