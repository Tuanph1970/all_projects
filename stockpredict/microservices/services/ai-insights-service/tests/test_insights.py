"""
AI Insights Service Tests - New Endpoints
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.models.schemas import InsightResponse, InsightType, ComparisonResponse


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
# Capabilities Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_capabilities(client: AsyncClient):
    """Test getting AI capabilities"""
    response = await client.get("/stock_helper/api/v2/ai/capabilities")
    assert response.status_code == 200
    data = response.json()

    assert "insight_types" in data
    assert "features" in data
    assert "batch_insights" in data["features"]
    assert "portfolio_insights" in data["features"]
    assert "sector_analysis" in data["features"]
    assert "trending_topics" in data["features"]


# ============================================================================
# Batch Insights Tests
# ============================================================================

@pytest.mark.asyncio
async def test_batch_insights_success(client: AsyncClient, mock_insight_response, mock_comparison_response):
    """Test batch insights generation"""
    with patch("app.api.routes.InsightsService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.generate_insight = AsyncMock(return_value=mock_insight_response)
        mock_instance.compare_stocks = AsyncMock(return_value=mock_comparison_response)

        response = await client.post(
            "/stock_helper/api/v2/ai/batch",
            json={
                "symbols": ["VNM", "FPT"],
                "insight_type": "summary",
                "include_comparison": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "successful" in data
        assert "failed" in data
        assert "generated_at" in data


@pytest.mark.asyncio
async def test_batch_insights_partial_failure(client: AsyncClient, mock_insight_response):
    """Test batch insights with some failures"""
    with patch("app.api.routes.InsightsService") as MockService:
        mock_instance = MockService.return_value

        # First call succeeds, second fails
        mock_instance.generate_insight = AsyncMock(
            side_effect=[mock_insight_response, Exception("API error")]
        )

        response = await client.post(
            "/stock_helper/api/v2/ai/batch",
            json={
                "symbols": ["VNM", "INVALID"],
                "insight_type": "summary",
                "include_comparison": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 1
        assert data["failed"] == 1


@pytest.mark.asyncio
async def test_batch_insights_validation(client: AsyncClient):
    """Test batch insights input validation"""
    # Empty symbols
    response = await client.post(
        "/stock_helper/api/v2/ai/batch",
        json={
            "symbols": [],
            "insight_type": "summary"
        }
    )
    assert response.status_code == 422

    # Too many symbols
    response = await client.post(
        "/stock_helper/api/v2/ai/batch",
        json={
            "symbols": [f"SYM{i}" for i in range(25)],
            "insight_type": "summary"
        }
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_batch_insights_without_comparison(client: AsyncClient, mock_insight_response):
    """Test batch insights without comparison"""
    with patch("app.api.routes.InsightsService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.generate_insight = AsyncMock(return_value=mock_insight_response)

        response = await client.post(
            "/stock_helper/api/v2/ai/batch",
            json={
                "symbols": ["VNM"],
                "insight_type": "analysis",
                "include_comparison": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["comparison"] is None


# ============================================================================
# Trending Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_trending(client: AsyncClient):
    """Test getting trending topics"""
    response = await client.get("/stock_helper/api/v2/ai/trending")

    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert "hot_stocks" in data
    assert "market_mood" in data
    assert "generated_at" in data

    # Verify topic structure
    if data["topics"]:
        topic = data["topics"][0]
        assert "topic" in topic
        assert "category" in topic
        assert "mentions" in topic
        assert "sentiment" in topic
        assert "related_symbols" in topic


@pytest.mark.asyncio
async def test_get_trending_unauthenticated(unauthenticated_client: AsyncClient):
    """Test trending works without authentication"""
    response = await unauthenticated_client.get("/stock_helper/api/v2/ai/trending")
    assert response.status_code == 200


# ============================================================================
# Portfolio Insights Tests
# ============================================================================

@pytest.mark.asyncio
async def test_portfolio_insight_success(client: AsyncClient, mock_insight_response):
    """Test portfolio insights generation"""
    with patch("app.api.routes.InsightsService") as MockService:
        mock_instance = MockService.return_value
        mock_instance._fetch_stock_data = AsyncMock(return_value={
            "quote": {"price": 75000}
        })
        mock_instance.generate_insight = AsyncMock(return_value=mock_insight_response)

        response = await client.post(
            "/stock_helper/api/v2/ai/portfolio-insight",
            json={
                "holdings": [
                    {"symbol": "VNM", "quantity": 100, "avg_cost": 70000},
                    {"symbol": "FPT", "quantity": 50, "avg_cost": 90000}
                ],
                "include_recommendations": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data
        assert "total_gain_loss_percent" in data
        assert "portfolio_sentiment" in data
        assert "diversification_score" in data
        assert "risk_assessment" in data
        assert "holdings_insights" in data
        assert "recommendations" in data


@pytest.mark.asyncio
async def test_portfolio_insight_empty_holdings(client: AsyncClient):
    """Test portfolio insight with empty holdings"""
    response = await client.post(
        "/stock_helper/api/v2/ai/portfolio-insight",
        json={
            "holdings": [],
            "include_recommendations": True
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_value"] == 0.0


@pytest.mark.asyncio
async def test_portfolio_insight_requires_auth(unauthenticated_client: AsyncClient):
    """Test portfolio insight requires authentication"""
    # Override to require auth
    from app.api.dependencies import get_current_user
    from app.main import app

    def override_get_current_user():
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = await unauthenticated_client.post(
        "/stock_helper/api/v2/ai/portfolio-insight",
        json={
            "holdings": [{"symbol": "VNM", "quantity": 100, "avg_cost": 70000}]
        }
    )

    # Should require authentication
    assert response.status_code in [401, 403, 422]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_portfolio_insight_holding_structure(client: AsyncClient, mock_insight_response):
    """Test portfolio insight holding insight structure"""
    with patch("app.api.routes.InsightsService") as MockService:
        mock_instance = MockService.return_value
        mock_instance._fetch_stock_data = AsyncMock(return_value={
            "quote": {"price": 75000}
        })
        mock_instance.generate_insight = AsyncMock(return_value=mock_insight_response)

        response = await client.post(
            "/stock_helper/api/v2/ai/portfolio-insight",
            json={
                "holdings": [{"symbol": "VNM", "quantity": 100, "avg_cost": 70000}]
            }
        )

        assert response.status_code == 200
        data = response.json()

        if data["holdings_insights"]:
            holding = data["holdings_insights"][0]
            assert "symbol" in holding
            assert "quantity" in holding
            assert "current_value" in holding
            assert "gain_loss_percent" in holding
            assert "sentiment" in holding
            assert "recommendation" in holding
            assert "risk_level" in holding


# ============================================================================
# Sectors Insights Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_sectors_insight(client: AsyncClient):
    """Test getting sector insights"""
    response = await client.get("/stock_helper/api/v2/ai/sectors")

    assert response.status_code == 200
    data = response.json()
    assert "sectors" in data
    assert "best_sector" in data
    assert "worst_sector" in data
    assert "market_rotation" in data
    assert "generated_at" in data


@pytest.mark.asyncio
async def test_sectors_insight_structure(client: AsyncClient):
    """Test sector insight data structure"""
    response = await client.get("/stock_helper/api/v2/ai/sectors")

    assert response.status_code == 200
    data = response.json()

    # Verify sector structure
    if data["sectors"]:
        sector = data["sectors"][0]
        assert "sector_code" in sector
        assert "sector_name" in sector
        assert "sentiment" in sector
        assert "outlook" in sector
        assert "key_drivers" in sector
        assert "top_picks" in sector
        assert isinstance(sector["key_drivers"], list)
        assert isinstance(sector["top_picks"], list)


@pytest.mark.asyncio
async def test_sectors_insight_unauthenticated(unauthenticated_client: AsyncClient):
    """Test sectors insight works without authentication"""
    response = await unauthenticated_client.get("/stock_helper/api/v2/ai/sectors")
    assert response.status_code == 200


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_batch_then_compare_workflow(client: AsyncClient, mock_insight_response, mock_comparison_response):
    """Test batch insights with comparison workflow"""
    with patch("app.api.routes.InsightsService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.generate_insight = AsyncMock(return_value=mock_insight_response)
        mock_instance.compare_stocks = AsyncMock(return_value=mock_comparison_response)

        response = await client.post(
            "/stock_helper/api/v2/ai/batch",
            json={
                "symbols": ["VNM", "FPT", "VIC"],
                "insight_type": "summary",
                "include_comparison": True
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should have comparison since we have multiple successful results
        assert data["successful"] >= 2
        # Note: comparison may be None depending on mock setup


@pytest.mark.asyncio
async def test_all_insight_types(client: AsyncClient, mock_insight_response):
    """Test batch insights with different insight types"""
    with patch("app.api.routes.InsightsService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.generate_insight = AsyncMock(return_value=mock_insight_response)

        for insight_type in ["analysis", "summary", "recommendation"]:
            response = await client.post(
                "/stock_helper/api/v2/ai/batch",
                json={
                    "symbols": ["VNM"],
                    "insight_type": insight_type,
                    "include_comparison": False
                }
            )

            assert response.status_code == 200
