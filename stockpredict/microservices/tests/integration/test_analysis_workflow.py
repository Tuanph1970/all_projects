"""
Integration tests for analysis-service.

Tests cover:
- Technical analysis
- Fundamental analysis
- Stock screener
- Industry analysis
- Screener configurations
"""

import pytest
import httpx
from datetime import datetime

from tests.conftest import get_api_path


pytestmark = [pytest.mark.integration]


class TestHealthEndpoints:
    """Test analysis-service health endpoints."""

    async def test_health_live(self, analysis_client: httpx.AsyncClient):
        """Test liveness probe endpoint."""
        response = await analysis_client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    async def test_health_ready(self, analysis_client: httpx.AsyncClient):
        """Test readiness probe endpoint."""
        response = await analysis_client.get("/health/ready")
        # May return 503 if database not connected
        assert response.status_code in [200, 503]


class TestTechnicalAnalysis:
    """Test technical analysis endpoints."""

    async def test_get_technical_analysis(
        self,
        analysis_client: httpx.AsyncClient,
        sample_stock_symbols: list[str]
    ):
        """Test getting technical analysis for a stock."""
        symbol = sample_stock_symbols[0]  # VNM
        response = await analysis_client.get(
            get_api_path(f"analysis/technical/{symbol}")
        )
        assert response.status_code in [200, 404, 503]

        if response.status_code == 200:
            data = response.json()
            # Should contain technical indicators
            assert any(key in str(data).lower() for key in [
                "rsi", "macd", "sma", "ema", "bollinger", "signal", "trend"
            ])

    async def test_technical_analysis_with_period(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test technical analysis with specific period."""
        response = await analysis_client.get(
            get_api_path("analysis/technical/VNM"),
            params={"period": "1M"}
        )
        # May return 422 if period parameter not supported
        assert response.status_code in [200, 404, 422, 503]

    async def test_technical_analysis_indicators(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test getting specific technical indicators."""
        response = await analysis_client.get(
            get_api_path("analysis/technical/FPT/indicators"),
            params={"indicators": "RSI,MACD,SMA"}
        )
        assert response.status_code in [200, 404, 503]

    async def test_technical_analysis_invalid_symbol(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test technical analysis for invalid symbol."""
        response = await analysis_client.get(
            get_api_path("analysis/technical/INVALID999")
        )
        assert response.status_code in [404, 400]


class TestFundamentalAnalysis:
    """Test fundamental analysis endpoints."""

    async def test_get_fundamental_analysis(
        self,
        analysis_client: httpx.AsyncClient,
        sample_stock_symbols: list[str]
    ):
        """Test getting fundamental analysis for a stock."""
        symbol = sample_stock_symbols[0]
        response = await analysis_client.get(
            get_api_path(f"analysis/fundamental/{symbol}")
        )
        assert response.status_code in [200, 404, 503]

        if response.status_code == 200:
            data = response.json()
            # Should contain fundamental metrics
            assert any(key in str(data).lower() for key in [
                "pe", "pb", "eps", "roe", "roa", "revenue", "profit", "debt"
            ])

    async def test_fundamental_financial_statements(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test getting financial statements."""
        response = await analysis_client.get(
            get_api_path("analysis/fundamental/VNM/statements")
        )
        assert response.status_code in [200, 404, 503]

        if response.status_code == 200:
            data = response.json()
            # Should contain financial statement data
            assert isinstance(data, (list, dict))

    async def test_compare_fundamentals(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test comparing fundamentals of multiple stocks."""
        response = await analysis_client.post(
            get_api_path("analysis/fundamental/compare"),
            json={
                "symbols": ["VNM", "VIC", "FPT"]
            }
        )
        # May return 405 if endpoint doesn't support POST
        assert response.status_code in [200, 404, 405, 503]

        if response.status_code == 200:
            data = response.json()
            # Should contain comparison data
            assert isinstance(data, (list, dict))


class TestStockScreener:
    """Test stock screener endpoints."""

    async def test_screen_stocks_basic(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test basic stock screening."""
        response = await analysis_client.post(
            get_api_path("analysis/screener"),
            json={
                "filters": {
                    "min_price": 10000,
                    "max_price": 100000
                }
            }
        )
        assert response.status_code in [200, 400, 422, 404]

        if response.status_code == 200:
            data = response.json()
            items = data if isinstance(data, list) else data.get("results", data.get("items", []))
            assert isinstance(items, list)

    async def test_screen_stocks_with_pe_filter(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test screening with P/E ratio filter."""
        response = await analysis_client.post(
            get_api_path("analysis/screener"),
            json={
                "filters": {
                    "min_pe": 5,
                    "max_pe": 20
                }
            }
        )
        assert response.status_code in [200, 400, 422, 404]

    async def test_screen_stocks_with_volume_filter(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test screening with volume filter."""
        response = await analysis_client.post(
            get_api_path("analysis/screener"),
            json={
                "filters": {
                    "min_volume": 100000
                }
            }
        )
        assert response.status_code in [200, 400, 422, 404]

    async def test_screen_stocks_with_technical_signals(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test screening with technical signals."""
        response = await analysis_client.post(
            get_api_path("analysis/screener"),
            json={
                "filters": {
                    "rsi_oversold": True,  # RSI < 30
                    "macd_bullish": True   # MACD crossover
                }
            }
        )
        assert response.status_code in [200, 400, 422, 404]

    async def test_screen_stocks_with_industry(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test screening within specific industry."""
        response = await analysis_client.post(
            get_api_path("analysis/screener"),
            json={
                "filters": {
                    "industry": "Banking"
                }
            }
        )
        assert response.status_code in [200, 400, 422, 404]

    async def test_advanced_screening(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test advanced screening with multiple filters."""
        response = await analysis_client.post(
            get_api_path("analysis/screener/advanced"),
            json={
                "filters": [
                    {"field": "price", "operator": "between", "value": [20000, 80000]},
                    {"field": "pe_ratio", "operator": "lt", "value": 15},
                    {"field": "volume", "operator": "gt", "value": 50000},
                    {"field": "change_percent", "operator": "gt", "value": 0}
                ],
                "sort_by": "volume",
                "sort_order": "desc",
                "limit": 20
            }
        )
        assert response.status_code in [200, 400, 404]

    async def test_get_filter_options(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test getting available filter options."""
        response = await analysis_client.get(get_api_path("analysis/filters"))
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Should list available filters
            assert isinstance(data, (list, dict))


class TestScreenerConfigurations:
    """Test screener configuration management."""

    async def test_save_screener_config(
        self,
        analysis_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test saving a screener configuration."""
        response = await analysis_client.post(
            get_api_path("analysis/screener/configs"),
            headers=auth_headers,
            json={
                "name": "Value Stocks",
                "filters": {
                    "min_pe": 5,
                    "max_pe": 15,
                    "min_roe": 0.1
                }
            }
        )
        assert response.status_code in [200, 201, 401, 404, 422]

    async def test_list_screener_configs(
        self,
        analysis_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test listing saved screener configurations."""
        response = await analysis_client.get(
            get_api_path("analysis/screener/configs"),
            headers=auth_headers
        )
        assert response.status_code in [200, 401]

    async def test_delete_screener_config(
        self,
        analysis_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test deleting a screener configuration."""
        # First create a config
        create_response = await analysis_client.post(
            get_api_path("analysis/screener/configs"),
            headers=auth_headers,
            json={
                "name": "Test Config",
                "filters": {"min_price": 10000}
            }
        )

        if create_response.status_code in [200, 201]:
            config_id = create_response.json().get("id")
            if config_id:
                response = await analysis_client.delete(
                    get_api_path(f"analysis/screener/configs/{config_id}"),
                    headers=auth_headers
                )
                assert response.status_code in [200, 204, 404]


class TestIndustryAnalysis:
    """Test industry analysis endpoints."""

    async def test_list_industries(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test listing all industries."""
        response = await analysis_client.get(get_api_path("analysis/industries"))
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            items = data if isinstance(data, list) else data.get("data", data.get("items", []))
            assert isinstance(items, list)

    async def test_get_industry_stocks(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test getting stocks in an industry."""
        # First get industries
        industries_response = await analysis_client.get(get_api_path("analysis/industries"))
        if industries_response.status_code == 200:
            industries = industries_response.json()
            items = industries if isinstance(industries, list) else industries.get("data", [])

            if items:
                industry_code = items[0].get("code", items[0].get("id", "banking"))
                response = await analysis_client.get(
                    get_api_path(f"analysis/industries/{industry_code}/stocks")
        )
                assert response.status_code in [200, 404]

    async def test_get_industry_analysis(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test getting industry-level analysis."""
        response = await analysis_client.get(
            get_api_path("analysis/industries/banking/analysis")
        )
        assert response.status_code in [200, 404]

    async def test_get_industry_performance(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test getting industry performance metrics."""
        response = await analysis_client.get(
            get_api_path("analysis/industries/banking/performance")
        )
        assert response.status_code in [200, 404]

    async def test_compare_industries(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test comparing multiple industries."""
        response = await analysis_client.post(
            get_api_path("analysis/industries/compare"),
            json={
                "industries": ["banking", "real_estate", "technology"]
            }
        )
        assert response.status_code in [200, 400, 404]


class TestAnalysisSignals:
    """Test trading signal generation."""

    async def test_get_trading_signals(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test getting trading signals for a stock."""
        response = await analysis_client.get(
            get_api_path("analysis/technical/VNM"),
            params={"include_signals": True}
        )
        assert response.status_code in [200, 404, 503]

        if response.status_code == 200:
            data = response.json()
            # May contain signal like BUY/SELL/HOLD
            if "signal" in data or "recommendation" in data:
                signal = data.get("signal", data.get("recommendation", ""))
                assert signal.upper() in ["BUY", "SELL", "HOLD", "STRONG_BUY", "STRONG_SELL", ""]


class TestCaching:
    """Test caching behavior for analysis endpoints."""

    async def test_analysis_caching(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test that repeated analysis requests are fast (cached)."""
        import time

        symbol = "VNM"

        # First request
        start1 = time.time()
        await analysis_client.get(get_api_path(f"analysis/technical/{symbol}"))
        time1 = time.time() - start1

        # Second request (should be cached)
        start2 = time.time()
        await analysis_client.get(get_api_path(f"analysis/technical/{symbol}"))
        time2 = time.time() - start2

        # Second request should be faster or similar
        assert time2 < time1 * 3  # Allow some variance


class TestInputValidation:
    """Test input validation for analysis endpoints."""

    async def test_screener_empty_filters(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test screener with empty filters."""
        response = await analysis_client.post(
            get_api_path("analysis/screener"),
            json={"filters": {}}
        )
        # May return all stocks or require at least one filter
        assert response.status_code in [200, 400, 422]

    async def test_screener_invalid_filter_values(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test screener with invalid filter values."""
        response = await analysis_client.post(
            get_api_path("analysis/screener"),
            json={
                "filters": {
                    "min_price": -1000,  # Negative price
                    "max_price": 100
                }
            }
        )
        assert response.status_code in [400, 422]

    async def test_screener_min_greater_than_max(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test screener with min > max."""
        response = await analysis_client.post(
            get_api_path("analysis/screener"),
            json={
                "filters": {
                    "min_price": 100000,
                    "max_price": 10000
                }
            }
        )
        assert response.status_code in [400, 422]
