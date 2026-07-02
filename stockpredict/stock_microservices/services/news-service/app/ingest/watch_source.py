"""ingest/ WatchSource — the union watched-ticker set over HTTP (FR-NEWS-WATCH).

Reads the distinct owned/watched tickers from portfolio-service and decision-helper via
small additive read endpoints, and returns their union. This module is deliberately
user-agnostic: only ticker strings cross the wire, never user identity (EC-N10). The
per-user fan-out happens later, in portfolio-service (N7).

Resilience (EC-N7): a failing/absent upstream contributes an empty set and is logged;
the other upstream still counts. Mirrors the injectable-client shape of HttpPriceSource
so tests run with a MockTransport and no real network.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


def _extract_symbols(payload) -> set[str]:
    """Accept a bare list or a {"symbols"|"tickers": [...]} wrapper."""
    if isinstance(payload, dict):
        payload = payload.get("symbols") or payload.get("tickers") or []
    if not isinstance(payload, list):
        return set()
    return {str(s).strip().upper() for s in payload if str(s).strip()}


class WatchSource:
    def __init__(
        self,
        portfolio_url: str,
        decision_helper_url: str,
        *,
        api_prefix: str = "stock_helper",
        client: Optional[httpx.Client] = None,
        timeout: float = 10.0,
    ):
        self._portfolio = portfolio_url.rstrip("/")
        self._helper = decision_helper_url.rstrip("/")
        self._prefix = api_prefix
        self._client = client
        self._timeout = timeout

    def resolve(self) -> list[str]:
        """Union of both upstreams' watched tickers: uppercased, de-duped, sorted."""
        symbols: set[str] = set()
        symbols |= self._fetch(
            f"{self._portfolio}/{self._prefix}/api/v2/portfolio/watched-symbols"
        )
        symbols |= self._fetch(
            f"{self._helper}/{self._prefix}/api/v2/helper/watched-tickers"
        )
        return sorted(symbols)

    def _fetch(self, url: str) -> set[str]:
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning("watch source %s returned %s", url, resp.status_code)
                return set()
            return _extract_symbols(resp.json())
        except Exception as exc:  # noqa: BLE001 — log-and-continue (EC-N7)
            logger.warning("watch source %s unavailable: %s", url, exc)
            return set()
        finally:
            if self._client is None:
                client.close()
