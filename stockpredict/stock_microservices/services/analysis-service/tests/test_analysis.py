"""
Analysis Service Tests - New Endpoints
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.models.schemas import (
    SignalType, ScreenerResponse, ScreenerStock,
    TechnicalAnalysisResponse, FundamentalAnalysisResponse,
    TechnicalIndicator, FundamentalMetric
)


# ============================================================================
# Health Check Tests
# ============================================================================

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


# ============================================================================
# Filter Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_available_filters(client: AsyncClient):
    """Test getting available filter options"""
    response = await client.get("/stock_helper/api/v2/analysis/filters")
    assert response.status_code == 200
    data = response.json()

    assert "technical" in data
    assert "fundamental" in data
    assert "market" in data

    # Check technical filters
    technical_fields = [f["field"] for f in data["technical"]]
    assert "rsi" in technical_fields
    assert "macd" in technical_fields


# ============================================================================
# Compare Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_compare_stocks_success(client: AsyncClient, mock_technical_analysis, mock_fundamental_analysis):
    """Test comparing multiple stocks"""
    with patch("app.api.routes.AnalysisService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_technical_analysis = AsyncMock(return_value=mock_technical_analysis)
        mock_instance.get_fundamental_analysis = AsyncMock(return_value=mock_fundamental_analysis)

        response = await client.post(
            "/stock_helper/api/v2/analysis/compare",
            json={"symbols": ["VNM", "FPT"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert "stocks" in data
        assert "best_technical" in data
        assert "best_fundamental" in data
        assert "recommendation" in data
        assert "generated_at" in data


@pytest.mark.asyncio
async def test_compare_stocks_minimum_symbols(client: AsyncClient):
    """Test comparison requires at least 2 symbols"""
    response = await client.post(
        "/stock_helper/api/v2/analysis/compare",
        json={"symbols": ["VNM"]}
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_compare_stocks_maximum_symbols(client: AsyncClient):
    """Test comparison accepts up to 10 symbols"""
    symbols = [f"SYM{i}" for i in range(11)]
    response = await client.post(
        "/stock_helper/api/v2/analysis/compare",
        json={"symbols": symbols}
    )
    assert response.status_code == 422  # Too many symbols


# ============================================================================
# Industry Analysis Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_industry_analysis_success(client: AsyncClient):
    """Test getting industry analysis"""
    mock_screener_result = ScreenerResponse(
        total=5,
        stocks=[
            ScreenerStock(
                symbol="VCB", name="Vietcombank", price=90000, change_percent=1.5,
                volume=1000000, market_cap=500000000000, pe_ratio=12.0, rsi=45.0, signal="hold"
            ),
            ScreenerStock(
                symbol="BID", name="BIDV", price=45000, change_percent=0.8,
                volume=800000, market_cap=300000000000, pe_ratio=10.0, rsi=50.0, signal="hold"
            ),
        ],
        generated_at=datetime.utcnow()
    )

    with patch("app.api.routes.AnalysisService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.run_screener = AsyncMock(return_value=mock_screener_result)

        response = await client.get("/stock_helper/api/v2/analysis/industry/BANK")

        assert response.status_code == 200
        data = response.json()
        assert data["industry_code"] == "BANK"
        assert "stock_count" in data
        assert "top_performers" in data
        assert "worst_performers" in data
        assert "avg_pe_ratio" in data


@pytest.mark.asyncio
async def test_get_industry_analysis_with_limit(client: AsyncClient):
    """Test industry analysis respects limit parameter"""
    mock_screener_result = ScreenerResponse(
        total=20,
        stocks=[
            ScreenerStock(
                symbol=f"STK{i}", name=f"Stock {i}", price=50000, change_percent=0.5,
                volume=500000, market_cap=100000000000, pe_ratio=15.0, rsi=50.0, signal="hold"
            )
            for i in range(20)
        ],
        generated_at=datetime.utcnow()
    )

    with patch("app.api.routes.AnalysisService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.run_screener = AsyncMock(return_value=mock_screener_result)

        response = await client.get("/stock_helper/api/v2/analysis/industry/TECH?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["top_performers"]) <= 5


# ============================================================================
# Combined Analysis Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_combined_analysis_success(client: AsyncClient, mock_technical_analysis, mock_fundamental_analysis):
    """Test getting combined technical and fundamental analysis"""
    with patch("app.api.routes.AnalysisService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_technical_analysis = AsyncMock(return_value=mock_technical_analysis)
        mock_instance.get_fundamental_analysis = AsyncMock(return_value=mock_fundamental_analysis)

        response = await client.get("/stock_helper/api/v2/analysis/combined/VNM")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "VNM"
        assert "technical" in data
        assert "fundamental" in data
        assert "combined_score" in data
        assert "recommendation" in data
        assert "confidence" in data
        assert "key_insights" in data


@pytest.mark.asyncio
async def test_get_combined_analysis_not_found(client: AsyncClient):
    """Test combined analysis for non-existent symbol"""
    with patch("app.api.routes.AnalysisService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_technical_analysis = AsyncMock(return_value=None)
        mock_instance.get_fundamental_analysis = AsyncMock(return_value=None)

        response = await client.get("/stock_helper/api/v2/analysis/combined/INVALID")

        assert response.status_code == 404


# ============================================================================
# Top Signals Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_top_signals_success(client: AsyncClient):
    """Test getting top buy/sell signals"""
    # Create mock with oversold stocks (RSI < 35)
    buy_stocks = [
        ScreenerStock(
            symbol="STK1", name="Stock 1", price=50000, change_percent=-2.0,
            volume=500000, market_cap=100000000000, pe_ratio=15.0, rsi=25.0, signal="buy"
        ),
        ScreenerStock(
            symbol="STK2", name="Stock 2", price=60000, change_percent=-1.5,
            volume=600000, market_cap=120000000000, pe_ratio=12.0, rsi=30.0, signal="buy"
        ),
    ]

    # Create mock with overbought stocks (RSI > 65)
    sell_stocks = [
        ScreenerStock(
            symbol="STK3", name="Stock 3", price=70000, change_percent=3.0,
            volume=700000, market_cap=150000000000, pe_ratio=20.0, rsi=75.0, signal="sell"
        ),
        ScreenerStock(
            symbol="STK4", name="Stock 4", price=80000, change_percent=2.5,
            volume=800000, market_cap=180000000000, pe_ratio=22.0, rsi=70.0, signal="sell"
        ),
    ]

    with patch("app.api.routes.AnalysisService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.run_screener = AsyncMock(
            side_effect=[
                ScreenerResponse(total=2, stocks=buy_stocks, generated_at=datetime.utcnow()),
                ScreenerResponse(total=2, stocks=sell_stocks, generated_at=datetime.utcnow()),
            ]
        )

        response = await client.get("/stock_helper/api/v2/analysis/signals")

        assert response.status_code == 200
        data = response.json()
        assert "buy_signals" in data
        assert "sell_signals" in data
        assert "generated_at" in data


@pytest.mark.asyncio
async def test_get_top_signals_with_limit(client: AsyncClient):
    """Test top signals respects limit parameter"""
    with patch("app.api.routes.AnalysisService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.run_screener = AsyncMock(
            return_value=ScreenerResponse(total=0, stocks=[], generated_at=datetime.utcnow())
        )

        response = await client.get("/stock_helper/api/v2/analysis/signals?limit=5")

        assert response.status_code == 200


# ============================================================================
# Quick Summary Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_quick_summary_success(client: AsyncClient, mock_technical_analysis, mock_fundamental_analysis):
    """Test getting quick summary for a stock"""
    with patch("app.api.routes.AnalysisService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_technical_analysis = AsyncMock(return_value=mock_technical_analysis)
        mock_instance.get_fundamental_analysis = AsyncMock(return_value=mock_fundamental_analysis)

        response = await client.get("/stock_helper/api/v2/analysis/summary/VNM")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "VNM"
        assert "price" in data
        assert "technical_signal" in data
        assert "technical_score" in data
        assert "fundamental_rating" in data
        assert "fundamental_score" in data
        assert "key_levels" in data
        assert "one_liner" in data


@pytest.mark.asyncio
async def test_get_quick_summary_not_found(client: AsyncClient):
    """Test quick summary for non-existent symbol"""
    with patch("app.api.routes.AnalysisService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_technical_analysis = AsyncMock(return_value=None)
        mock_instance.get_fundamental_analysis = AsyncMock(return_value=None)

        response = await client.get("/stock_helper/api/v2/analysis/summary/INVALID")

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_quick_summary_technical_only(client: AsyncClient, mock_technical_analysis):
    """Test quick summary works with only technical data"""
    with patch("app.api.routes.AnalysisService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_technical_analysis = AsyncMock(return_value=mock_technical_analysis)
        mock_instance.get_fundamental_analysis = AsyncMock(return_value=None)

        response = await client.get("/stock_helper/api/v2/analysis/summary/VNM")

        assert response.status_code == 200
        data = response.json()
        assert data["fundamental_rating"] == "N/A"
        assert data["fundamental_score"] == 0.0


# ============================================================================
# Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_compare_invalid_json(client: AsyncClient):
    """Test comparison with invalid JSON"""
    response = await client.post(
        "/stock_helper/api/v2/analysis/compare",
        content="invalid json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_industry_limit_validation(client: AsyncClient):
    """Test industry analysis limit parameter validation"""
    response = await client.get("/stock_helper/api/v2/analysis/industry/BANK?limit=100")
    assert response.status_code == 422  # Exceeds max limit of 50


@pytest.mark.asyncio
async def test_signals_limit_validation(client: AsyncClient):
    """Test signals limit parameter validation"""
    response = await client.get("/stock_helper/api/v2/analysis/signals?limit=100")
    assert response.status_code == 422  # Exceeds max limit of 50
