"""Unit tests for app.services.market.client.MarketClient.

Every method is a thin httpx façade with the same shape:
- 200 → return parsed JSON (or transformed list)
- non-200 / network error → return None or [] and log

Tests mock httpx.AsyncClient.get on the three internal clients
(_stock, _analysis, _insights) directly so we never make a real call.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.market.client import MarketClient, get_market_client


def _resp(status_code: int, json_body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    if status_code >= 400:
        r.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("boom", request=MagicMock(), response=r)
        )
    else:
        r.raise_for_status = MagicMock()
    return r


@pytest.fixture
def client() -> MarketClient:
    c = MarketClient()
    # Replace the underlying httpx clients with mocks so we never reach the
    # network and so we don't have to close real connections at teardown.
    c._stock = MagicMock()
    c._analysis = MagicMock()
    c._insights = MagicMock()
    c._stock.get = AsyncMock()
    c._analysis.get = AsyncMock()
    c._insights.get = AsyncMock()
    c._stock.aclose = AsyncMock()
    c._analysis.aclose = AsyncMock()
    c._insights.aclose = AsyncMock()
    return c


# ---------------------------------------------------------------------------
# fetch_ohlcv
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_ohlcv_returns_sorted_bars(client: MarketClient):
    bars = [
        {"date": "2026-05-20", "open": 80, "high": 82, "low": 79, "close": 81, "volume": 100},
        {"date": "2026-05-18", "open": 79, "high": 80, "low": 78, "close": 79, "volume": 90},
        {"date": "2026-05-19", "open": 79, "high": 81, "low": 78, "close": 80, "volume": 95},
    ]
    client._stock.get.return_value = _resp(200, {"data": bars})
    out = await client.fetch_ohlcv("VCB", days=10)
    assert [b["date"] for b in out] == ["2026-05-18", "2026-05-19", "2026-05-20"]
    # Default end_date uses today; verify the URL we hit matches the helper.
    call_path = client._stock.get.await_args.args[0]
    assert "VCB/history" in call_path


@pytest.mark.asyncio
async def test_fetch_ohlcv_uses_explicit_end_date(client: MarketClient):
    client._stock.get.return_value = _resp(200, {"data": []})
    await client.fetch_ohlcv("VCB", days=30, end_date=date(2026, 1, 31))
    params = client._stock.get.await_args.kwargs["params"]
    assert params["end_date"] == "2026-01-31"
    assert params["start_date"] == "2026-01-01"


@pytest.mark.asyncio
async def test_fetch_ohlcv_returns_empty_on_http_error(client: MarketClient):
    client._stock.get.side_effect = httpx.ConnectError("down")
    assert await client.fetch_ohlcv("VCB") == []


@pytest.mark.asyncio
async def test_fetch_ohlcv_returns_empty_when_data_missing(client: MarketClient):
    """Upstream sent 200 with a payload that omits 'data'."""
    client._stock.get.return_value = _resp(200, {})
    assert await client.fetch_ohlcv("VCB") == []


# ---------------------------------------------------------------------------
# fetch_regime
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_regime_returns_payload(client: MarketClient):
    client._analysis.get.return_value = _resp(200, {"regime": "TREND_UP"})
    out = await client.fetch_regime("VCB")
    assert out == {"regime": "TREND_UP"}


@pytest.mark.asyncio
async def test_fetch_regime_returns_none_on_error(client: MarketClient):
    client._analysis.get.side_effect = httpx.ConnectError("down")
    assert await client.fetch_regime("VCB") is None


# ---------------------------------------------------------------------------
# fetch_sr_levels
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_sr_levels_returns_payload(client: MarketClient):
    client._analysis.get.return_value = _resp(200, {"levels": []})
    assert await client.fetch_sr_levels("VCB") == {"levels": []}


@pytest.mark.asyncio
async def test_fetch_sr_levels_passes_query_params(client: MarketClient):
    client._analysis.get.return_value = _resp(200, {})
    await client.fetch_sr_levels("VCB", window=10, tolerance_pct=2.5)
    params = client._analysis.get.await_args.kwargs["params"]
    assert params == {"window": 10, "tolerance_pct": 2.5}


@pytest.mark.asyncio
async def test_fetch_sr_levels_returns_none_on_error(client: MarketClient):
    client._analysis.get.side_effect = httpx.ConnectError("down")
    assert await client.fetch_sr_levels("VCB") is None


# ---------------------------------------------------------------------------
# fetch_atr / fetch_swings / fetch_patterns / fetch_technical
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_atr_returns_payload(client: MarketClient):
    client._analysis.get.return_value = _resp(200, {"latest": 1.25})
    assert await client.fetch_atr("VCB") == {"latest": 1.25}


@pytest.mark.asyncio
async def test_fetch_atr_returns_none_on_error(client: MarketClient):
    client._analysis.get.side_effect = httpx.ConnectError("down")
    assert await client.fetch_atr("VCB") is None


@pytest.mark.asyncio
async def test_fetch_swings_returns_payload(client: MarketClient):
    client._analysis.get.return_value = _resp(200, {"pivots": [{"date": "2026-05-01"}]})
    assert await client.fetch_swings("VCB", window=5, days=100) == {"pivots": [{"date": "2026-05-01"}]}


@pytest.mark.asyncio
async def test_fetch_swings_returns_none_on_error(client: MarketClient):
    client._analysis.get.side_effect = httpx.ConnectError("down")
    assert await client.fetch_swings("VCB") is None


@pytest.mark.asyncio
async def test_fetch_patterns_returns_payload(client: MarketClient):
    client._insights.get.return_value = _resp(200, {"patterns": []})
    assert await client.fetch_patterns("VCB") == {"patterns": []}


@pytest.mark.asyncio
async def test_fetch_patterns_returns_none_on_error(client: MarketClient):
    """Patterns are best-effort — error degrades to None, no log noise required."""
    client._insights.get.side_effect = httpx.ConnectError("down")
    assert await client.fetch_patterns("VCB") is None


@pytest.mark.asyncio
async def test_fetch_technical_returns_payload(client: MarketClient):
    client._analysis.get.return_value = _resp(200, {"indicators": []})
    assert await client.fetch_technical("VCB") == {"indicators": []}


@pytest.mark.asyncio
async def test_fetch_technical_returns_none_on_error(client: MarketClient):
    client._analysis.get.side_effect = httpx.ConnectError("down")
    assert await client.fetch_technical("VCB") is None


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aclose_closes_all_three_clients(client: MarketClient):
    await client.aclose()
    client._stock.aclose.assert_awaited()
    client._analysis.aclose.assert_awaited()
    client._insights.aclose.assert_awaited()


def test_get_market_client_is_singleton():
    """Two calls return the same instance; the module-level cache holds it."""
    a = get_market_client()
    b = get_market_client()
    assert a is b
