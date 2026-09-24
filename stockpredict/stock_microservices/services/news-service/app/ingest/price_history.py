"""ingest/ PriceHistorySource — daily closes over HTTP from stock-data-service.

Follows the same boundary rule as `event_reaction/ingest/http_price_source.py`: network
I/O lives here only, and news-service never imports stock-data-service's repository.
Unlike that module this one carries no pandas dependency — the scorer needs an ordered
(date, close) sequence and nothing more, and news-service's image has no pandas.

Adjusted vs raw close (EC-B5's sibling problem): a forward return computed on raw closes
reads a stock dividend as a loss — TPB's 15% stock dividend in the 23/9 mail would show
as roughly -13% with no economic event behind it. `adj_close` is therefore preferred,
with a fall back to `close` and a flag saying which was used, so a caller can qualify
what it reports. In this database `adj_close` is currently never written on ingest, so
the fallback is what runs today.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class PriceUnavailableError(RuntimeError):
    """No usable price history for a symbol over the requested window."""


@dataclass(frozen=True)
class PriceSeries:
    """Ascending daily closes. `dates[i]` pairs with `closes[i]`.

    The dates ARE the trading sessions, which is what makes positional horizon
    arithmetic ("20 sessions later") correct without a separate calendar.
    """

    symbol: str
    dates: tuple[date, ...]
    closes: tuple[float, ...]
    adjusted: bool          # True iff adj_close was available for every bar

    def __len__(self) -> int:
        return len(self.dates)

    def index_at_or_before(self, when: date) -> Optional[int]:
        """Position of the latest session on or before `when`; None if none exists.

        "At or before" rather than "at": the mail is published after the close of the
        session it describes, so the reference price is that session's close — and if
        the symbol did not trade that day, the last price actually known at publication
        is the honest reference.
        """
        found = None
        for i, d in enumerate(self.dates):
            if d <= when:
                found = i
            else:
                break
        return found


class PriceHistorySource:
    def __init__(
        self,
        base_url: str,
        *,
        api_prefix: str = "stock_helper",
        client: Optional[httpx.Client] = None,
        timeout: float = 30.0,
    ):
        self._base = base_url.rstrip("/")
        self._prefix = api_prefix
        self._client = client
        self._timeout = timeout

    def history(self, symbol: str, start: date, end: date) -> PriceSeries:
        """Daily closes for `symbol` over [start, end], ascending and de-duplicated."""
        url = f"{self._base}/{self._prefix}/api/v2/stocks/{symbol}/history"
        params = {"start_date": start.isoformat(), "end_date": end.isoformat()}

        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.get(url, params=params)
        except Exception as exc:  # noqa: BLE001
            raise PriceUnavailableError(f"stock-data-service unreachable for {symbol}: {exc}")
        finally:
            if self._client is None:
                client.close()

        if resp.status_code != 200:
            raise PriceUnavailableError(
                f"stock-data-service returned {resp.status_code} for {symbol}")
        rows = (resp.json() or {}).get("data") or []
        if not rows:
            raise PriceUnavailableError(f"no price history for {symbol} in {start}..{end}")

        # Latest row wins per date, then sort — the endpoint is not contractually unique.
        by_date: dict[date, dict] = {}
        for row in rows:
            raw_date = row.get("date")
            if not raw_date:
                continue
            try:
                d = date.fromisoformat(str(raw_date)[:10])
            except ValueError:
                continue
            by_date[d] = row

        dates: list[date] = []
        closes: list[float] = []
        adjusted = True
        for d in sorted(by_date):
            row = by_date[d]
            value = row.get("adj_close")
            if value is None:
                value = row.get("close")
                adjusted = False
            if value is None:
                continue
            dates.append(d)
            closes.append(float(value))

        if not dates:
            raise PriceUnavailableError(f"no usable closes for {symbol} in {start}..{end}")
        return PriceSeries(symbol=symbol.upper(), dates=tuple(dates),
                           closes=tuple(closes), adjusted=adjusted)
