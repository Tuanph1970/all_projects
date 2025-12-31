"""
Test Configuration and Fixtures for AI Insights Service
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.main import app
from app.api.dependencies import get_current_user, get_current_user_optional
from app.models.schemas import (
    InsightResponse, InsightType, ComparisonResponse
)


@pytest_asyncio.fixture
async def client():
    """Create test client with mocked dependencies"""

    def override_get_current_user():
        return {"user_id": 1, "username": "testuser"}

    def override_get_current_user_optional():
        return {"user_id": 1, "username": "testuser"}

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_optional] = override_get_current_user_optional

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthenticated_client():
    """Create test client without authentication"""
    def override_get_current_user_optional():
        return None

    app.dependency_overrides[get_current_user_optional] = override_get_current_user_optional

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_insight_response():
    """Mock insight response"""
    return InsightResponse(
        symbol="VNM",
        insight_type=InsightType.ANALYSIS,
        content="VNM shows positive momentum with strong fundamentals.",
        summary="Positive outlook for VNM",
        key_points=["Strong revenue growth", "Good market position"],
        sentiment="bullish",
        confidence=0.8,
        sources=["technical_analysis", "fundamental_data"],
        generated_at=datetime.now()
    )


@pytest.fixture
def mock_comparison_response():
    """Mock comparison response"""
    return ComparisonResponse(
        symbols=["VNM", "VIC"],
        analysis="VNM shows stronger fundamentals while VIC has better growth potential.",
        rankings={"VNM": 1, "VIC": 2},
        recommendation="VNM",
        generated_at=datetime.now()
    )


@pytest.fixture
def batch_request_data():
    """Test data for batch insights"""
    return {
        "symbols": ["VNM", "FPT", "VIC"],
        "insight_type": "summary",
        "include_comparison": True
    }


@pytest.fixture
def portfolio_request_data():
    """Test data for portfolio insights"""
    return {
        "holdings": [
            {"symbol": "VNM", "quantity": 100, "avg_cost": 70000},
            {"symbol": "FPT", "quantity": 50, "avg_cost": 90000}
        ],
        "include_recommendations": True
    }
