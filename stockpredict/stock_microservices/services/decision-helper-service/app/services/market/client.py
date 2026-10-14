"""HTTP clients for upstream services consumed by the decision pipeline."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MarketClient:
    """Thin async HTTP façade over stock-data-service, analysis-service, and ai-insights-service."""

    def __init__(self) -> None:
        timeout = httpx.Timeout(
            connect=3.0,
            read=settings.MARKET_GATEWAY_TIMEOUT_MS / 1000,
            write=3.0,
            pool=3.0,
        )
        self._stock = httpx.AsyncClient(
            base_url=settings.STOCK_DATA_SERVICE_URL, timeout=timeout
        )
        self._analysis = httpx.AsyncClient(
            base_url=settings.ANALYSIS_SERVICE_URL, timeout=timeout
        )
        self._insights = httpx.AsyncClient(
            base_url=settings.AI_INSIGHTS_SERVICE_URL, timeout=timeout
        )

    async def aclose(self) -> None:
        await self._stock.aclose()
        await self._analysis.aclose()
        await self._insights.aclose()

    # ------------------------------------------------------------------
    # OHLCV
    # ------------------------------------------------------------------

    async def fetch_ohlcv(
        self,
        symbol: str,
        days: int = 300,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Return list of {date, open, high, low, close, volume} dicts sorted oldest-first."""
        end = end_date or date.today()
        start = end - timedelta(days=days)
        try:
            resp = await self._stock.get(
                f"/stock_helper/api/v2/stocks/{symbol}/history",
                params={"start_date": str(start), "end_date": str(end)},
            )
            resp.raise_for_status()
            payload = resp.json()
            bars = payload.get("data", [])
            # sort ascending by date
            bars.sort(key=lambda b: b["date"])
            return bars
        except httpx.HTTPError as exc:
            logger.warning("fetch_ohlcv %s failed: %s", symbol, exc)
            return []

    # ------------------------------------------------------------------
    # Regime
    # ------------------------------------------------------------------

    async def fetch_regime(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Return analysis-service regime response dict or None on error."""
        try:
            resp = await self._analysis.get(
                f"/stock_helper/api/v2/analysis/regime/{symbol}"
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("fetch_regime %s failed: %s", symbol, exc)
            return None

    # ------------------------------------------------------------------
    # S/R levels
    # ------------------------------------------------------------------

    async def fetch_sr_levels(
        self,
        symbol: str,
        window: int = 5,
        tolerance_pct: float = 1.5,
    ) -> Optional[Dict[str, Any]]:
        """Return analysis-service S/R response dict or None on error."""
        try:
            resp = await self._analysis.get(
                f"/stock_helper/api/v2/analysis/sr/{symbol}",
                params={"window": window, "tolerance_pct": tolerance_pct},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("fetch_sr_levels %s failed: %s", symbol, exc)
            return None

    # ------------------------------------------------------------------
    # ATR (needed by stop_module and sizing_module)
    # ------------------------------------------------------------------

    async def fetch_atr(
        self,
        symbol: str,
        period: int = 14,
        days: int = 100,
    ) -> Optional[Dict[str, Any]]:
        """Return analysis-service /analysis/atr/{symbol} dict or None on error."""
        try:
            resp = await self._analysis.get(
                f"/stock_helper/api/v2/analysis/atr/{symbol}",
                params={"period": period, "days": days},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("fetch_atr %s failed: %s", symbol, exc)
            return None

    # ------------------------------------------------------------------
    # Swing pivots (needed by stop_module)
    # ------------------------------------------------------------------

    async def fetch_swings(
        self,
        symbol: str,
        window: int = 3,
        days: int = 300,
    ) -> Optional[Dict[str, Any]]:
        """Return analysis-service /analysis/swings/{symbol} dict or None on error."""
        try:
            resp = await self._analysis.get(
                f"/stock_helper/api/v2/analysis/swings/{symbol}",
                params={"window": window, "days": days},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("fetch_swings %s failed: %s", symbol, exc)
            return None

    # ------------------------------------------------------------------
    # AI-insights patterns (needed by failed_signal detectors)
    # ------------------------------------------------------------------

    #: Bars of history the pattern scan runs over. The detectors need enough
    #: room for a formation plus the breakout that follows it; ai-insights
    #: caps the window itself.
    PATTERNS_LOOKBACK_BARS = 250

    async def fetch_patterns(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Return the ai-insights chart-pattern scan, or None on error.

        Best-effort: the failed_signal detectors degrade gracefully if absent.

        Backlog #73 — THE URL WAS WRONG. This used to call
        ``/ai/insight/{symbol}``, which is a different endpoint: an LLM
        narrative returning ``{symbol, insight_type, content, summary,
        key_points, sentiment, confidence, sources, generated_at}``. It answers
        200, so nothing failed and nothing was logged — but it carries no
        ``patterns`` key, so ``patterns.get("patterns", [])`` was always empty
        and all five pattern-based failed-signal detectors had nothing to
        iterate. That is the first of the two reasons they had never fired; the
        second was the vocabulary mismatch handled in
        ``failed_signal.adapt_ai_insights_patterns``.

        The scan lives at ``/ai/insights/patterns/{symbol}`` — plural, and
        under ``/patterns/``.
        """
        try:
            resp = await self._insights.get(
                f"/stock_helper/api/v2/ai/insights/patterns/{symbol}",
                params={"lookback_bars": self.PATTERNS_LOOKBACK_BARS},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            logger.debug("fetch_patterns %s failed: %s", symbol, exc)
            return None

    # ------------------------------------------------------------------
    # Technical indicators (RSI/MACD for confirmation oscillator rule)
    # ------------------------------------------------------------------

    async def fetch_technical(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Return analysis-service /technical/{symbol} dict or None on error."""
        try:
            resp = await self._analysis.get(
                f"/stock_helper/api/v2/analysis/technical/{symbol}"
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("fetch_technical %s failed: %s", symbol, exc)
            return None


_client: Optional[MarketClient] = None


def get_market_client() -> MarketClient:
    global _client
    if _client is None:
        _client = MarketClient()
    return _client
