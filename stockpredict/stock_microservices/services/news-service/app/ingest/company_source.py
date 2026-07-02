"""ingest/ CompanyNewsSource — per-ticker company news over HTTP (FR-NEWS-COMPANY).

Calls stock-data-service GET /companies/{symbol}/news (which wraps vnstock) and
normalizes each record to a NewsItem. Does NOT import vnstock or stock-data-service code
(EC-N1) — network I/O lives here only. Timestamps become tz-aware UTC (EC-N6); the full
source record is preserved verbatim in raw_json (EC-N3).

The upstream returns a bare JSON list of standardized records. Observed keys:
title, description (short), content (full), source (== article URL), publishDate,
createdAt, symbol, id. Normalization is defensive about missing/renamed keys.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.exceptions import SourceUnavailableError
from app.models.news_item import NewsItem

logger = logging.getLogger(__name__)


def _parse_ts(value) -> Optional[datetime]:
    """Coerce a source timestamp to tz-aware UTC; return None if unusable (EC-N6)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)  # naive -> treat as UTC by contract
    return dt.astimezone(timezone.utc)


class CompanyNewsSource:
    def __init__(
        self,
        base_url: str,
        *,
        api_prefix: str = "stock_helper",
        client: Optional[httpx.Client] = None,
        timeout: float = 10.0,
    ):
        self._base = base_url.rstrip("/")
        self._prefix = api_prefix
        self._client = client
        self._timeout = timeout

    def fetch(self, symbol: str) -> list[NewsItem]:
        symbol = symbol.upper()
        url = f"{self._base}/{self._prefix}/api/v2/companies/{symbol}/news"
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.get(url)
        except Exception as exc:  # noqa: BLE001 — network failure is an unavailable source
            raise SourceUnavailableError(f"company news fetch failed for {symbol}: {exc}") from exc
        finally:
            if self._client is None:
                client.close()

        if resp.status_code != 200:
            raise SourceUnavailableError(
                f"stock-data-service returned {resp.status_code} for {symbol} news"
            )
        payload = resp.json()
        # An empty list is a normal "no news" state, not a failure. A non-list payload
        # (e.g. an error object) means the source is broken.
        if not isinstance(payload, list):
            raise SourceUnavailableError(f"unexpected news payload for {symbol}: {type(payload)}")

        items: list[NewsItem] = []
        for rec in payload:
            item = self._to_item(symbol, rec)
            if item is not None:
                items.append(item)
        return items

    def _to_item(self, symbol: str, rec: dict) -> Optional[NewsItem]:
        if not isinstance(rec, dict):
            return None
        ts = _parse_ts(rec.get("publishDate") or rec.get("createdAt") or rec.get("published_at"))
        title = (rec.get("title") or rec.get("news_title") or "").strip()
        if ts is None or not title:
            logger.debug("skipping company news record (missing title/date) for %s", symbol)
            return None
        body = rec.get("content") or rec.get("description") or rec.get("summary")
        return NewsItem(
            source="vnstock",
            stream="company",
            symbol=(rec.get("symbol") or symbol).upper(),
            ts_utc=ts,
            title=title,
            body=body,
            url=rec.get("url") or rec.get("source"),
            lang=rec.get("lang"),
            raw_json=json.dumps(rec, default=str, ensure_ascii=False),
            guid=rec.get("id") or rec.get("guid"),
        )
