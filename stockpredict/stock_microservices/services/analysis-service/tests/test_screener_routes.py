"""Coverage for the /technical, /fundamental, /screener routes.

Mocks AnalysisService at the route boundary so we can verify route
plumbing (dependency injection, query-param forwarding, 404 handling)
without exercising the heavy stats / SQL paths.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


PREFIX = "/stock_helper/api/v2/analysis"


# ---------------------------------------------------------------------------
# /technical/{symbol}
#
# Happy-path body assertions are hard to mock cleanly because
# TechnicalAnalysisResponse references several nested schemas
# (CurrentPriceData, MovingAverages, etc.). We focus on route plumbing:
# query-param validation + 404 on service-returns-None. Service-layer
# tests should live alongside service code, not at the route boundary.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_technical_analysis_validates_period_lower_bound(client: AsyncClient):
    """period < 20 must 422 from FastAPI's Query validator."""
    r = await client.get(f"{PREFIX}/technical/FPT?period=10")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_technical_analysis_validates_period_upper_bound(client: AsyncClient):
    r = await client.get(f"{PREFIX}/technical/FPT?period=600")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_technical_analysis_404_when_service_returns_none(client: AsyncClient):
    """No data for symbol → 404 with helpful detail string."""
    with patch("app.api.routes.AnalysisService") as service_class:
        instance = MagicMock()
        instance.get_technical_analysis = AsyncMock(return_value=None)
        service_class.return_value = instance

        r = await client.get(f"{PREFIX}/technical/UNKNOWN")

    assert r.status_code == 404
    assert "UNKNOWN" in r.json()["detail"]


# ---------------------------------------------------------------------------
# /fundamental/{symbol}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fundamental_analysis_404(client: AsyncClient):
    with patch("app.api.routes.AnalysisService") as service_class:
        instance = MagicMock()
        instance.get_fundamental_analysis = AsyncMock(return_value=None)
        service_class.return_value = instance

        r = await client.get(f"{PREFIX}/fundamental/NOPE")

    assert r.status_code == 404


# ---------------------------------------------------------------------------
# /screener — POST + GET variants
# ---------------------------------------------------------------------------

def _screener_response(stock_count=2):
    return {
        "total": stock_count,
        "stocks": [
            {
                "symbol": f"S{i}",
                "name": f"Stock {i}",
                "exchange": "HOSE",
                "price": 100.0 + i,
                "change_percent": 1.5,
                "volume": 1000000 + i,
                "market_cap": 10_000_000_000.0,
                "pe_ratio": 15.0,
                "rsi": 55.0,
                "signal": "BUY",
            }
            for i in range(stock_count)
        ],
        "generated_at": datetime.now().isoformat(),
    }


@pytest.mark.asyncio
async def test_post_screener_forwards_filters_to_service(client: AsyncClient):
    with patch("app.api.routes.AnalysisService") as service_class:
        instance = MagicMock()
        instance.run_screener = AsyncMock(return_value=_screener_response(2))
        service_class.return_value = instance

        body = {
            "filters": [
                {"field": "pe_ratio", "operator": "lt", "value": 20},
                {"field": "change_percent", "operator": "gt", "value": 0},
            ],
            "sort_by": "change_percent",
            "sort_order": "desc",
            "limit": 10,
            "offset": 0,
        }
        r = await client.post(f"{PREFIX}/screener", json=body)

    assert r.status_code == 200, r.text
    assert r.json()["total"] == 2
    # Inspect the call: filters list arrived intact, sort_by/sort_order/limit
    # forwarded from the request body.
    call_kwargs = instance.run_screener.call_args.kwargs
    assert call_kwargs["sort_by"] == "change_percent"
    assert call_kwargs["sort_order"] == "desc"
    assert call_kwargs["limit"] == 10
    assert len(call_kwargs["filters"]) == 2


@pytest.mark.asyncio
async def test_post_screener_validates_limit_upper_bound(client: AsyncClient):
    """limit > 500 should 422 from the schema's Field constraint."""
    body = {"filters": [], "limit": 9999}
    r = await client.post(f"{PREFIX}/screener", json=body)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_screener_builds_filters_from_query_params(client: AsyncClient):
    with patch("app.api.routes.AnalysisService") as service_class:
        instance = MagicMock()
        instance.run_screener = AsyncMock(return_value=_screener_response(0))
        service_class.return_value = instance

        await client.get(
            f"{PREFIX}/screener?exchange=HOSE&min_price=50&max_price=200"
            "&min_volume=100000&min_market_cap=1000000000"
        )

    filters = instance.run_screener.call_args.kwargs["filters"]
    fields = {f.field for f in filters}
    # All five query params should produce a corresponding ScreenerFilter
    assert fields == {"exchange", "price", "volume", "market_cap"}
    # min_price and max_price both build "price" filters
    price_filters = [f for f in filters if f.field == "price"]
    assert len(price_filters) == 2


@pytest.mark.asyncio
async def test_get_screener_skips_exchange_when_all(client: AsyncClient):
    """exchange=ALL is a wildcard sentinel; should NOT add a filter."""
    with patch("app.api.routes.AnalysisService") as service_class:
        instance = MagicMock()
        instance.run_screener = AsyncMock(return_value=_screener_response(0))
        service_class.return_value = instance

        await client.get(f"{PREFIX}/screener?exchange=ALL")

    filters = instance.run_screener.call_args.kwargs["filters"]
    assert filters == []  # ALL means no filter


@pytest.mark.asyncio
async def test_get_screener_no_filters_when_no_query_params(client: AsyncClient):
    """Bare GET /screener returns up to `limit` rows with no filtering."""
    with patch("app.api.routes.AnalysisService") as service_class:
        instance = MagicMock()
        instance.run_screener = AsyncMock(return_value=_screener_response(2))
        service_class.return_value = instance

        r = await client.get(f"{PREFIX}/screener")

    assert r.status_code == 200
    filters = instance.run_screener.call_args.kwargs["filters"]
    assert filters == []


@pytest.mark.asyncio
async def test_get_screener_pagination_passes_through(client: AsyncClient):
    with patch("app.api.routes.AnalysisService") as service_class:
        instance = MagicMock()
        instance.run_screener = AsyncMock(return_value=_screener_response(0))
        service_class.return_value = instance

        await client.get(f"{PREFIX}/screener?limit=25&offset=50&sort_by=price&sort_order=desc")

    kwargs = instance.run_screener.call_args.kwargs
    assert kwargs["limit"] == 25
    assert kwargs["offset"] == 50
    assert kwargs["sort_by"] == "price"
    assert kwargs["sort_order"] == "desc"
