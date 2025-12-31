"""
Test Configuration and Fixtures for Analysis Service
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.main import app
from app.api.dependencies import get_db, get_current_user, get_current_user_optional
from app.models.schemas import (
    TechnicalAnalysisResponse, FundamentalAnalysisResponse,
    TechnicalIndicator, FundamentalMetric, SignalType
)


@pytest_asyncio.fixture
async def mock_db():
    """Mock database session"""
    mock_session = AsyncMock()
    yield mock_session


@pytest_asyncio.fixture
async def client(mock_db):
    """Create test client with mocked dependencies"""

    async def override_get_db():
        yield mock_db

    def override_get_current_user():
        return {"user_id": 1, "username": "testuser"}

    def override_get_current_user_optional():
        return {"user_id": 1, "username": "testuser"}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_optional] = override_get_current_user_optional

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_technical_analysis():
    """Mock technical analysis response"""
    return TechnicalAnalysisResponse(
        symbol="VNM",
        current_price=75000.0,
        indicators=[
            TechnicalIndicator(name="RSI", value=45.0, signal="neutral"),
            TechnicalIndicator(name="MACD", value=0.5, signal="bullish"),
        ],
        overall_signal=SignalType.HOLD,
        signal_strength=0.6,
        technical_score=55.0,
        support_levels=[72000.0, 70000.0],
        resistance_levels=[78000.0, 80000.0],
        trend="sideways",
        volatility="medium",
        generated_at=datetime.utcnow()
    )


@pytest.fixture
def mock_fundamental_analysis():
    """Mock fundamental analysis response"""
    return FundamentalAnalysisResponse(
        symbol="VNM",
        company_name="Vietnam Dairy Products",
        valuation=[
            FundamentalMetric(name="P/E", value=15.5, industry_avg=18.0, rating="good"),
            FundamentalMetric(name="P/B", value=3.2, industry_avg=3.5, rating="fair"),
        ],
        profitability=[
            FundamentalMetric(name="ROE", value=25.0, industry_avg=20.0, rating="excellent"),
        ],
        growth=[
            FundamentalMetric(name="Revenue Growth", value=8.5, rating="good"),
        ],
        financial_health=[
            FundamentalMetric(name="Current Ratio", value=2.1, rating="good"),
        ],
        fundamental_score=72.0,
        overall_rating="good",
        generated_at=datetime.utcnow()
    )


@pytest.fixture
def comparison_request_data():
    """Test data for stock comparison"""
    return {
        "symbols": ["VNM", "VIC", "FPT"]
    }


@pytest.fixture
def screener_request_data():
    """Test data for screener"""
    return {
        "filters": [
            {"field": "rsi", "operator": "lt", "value": 30}
        ],
        "sort_by": "rsi",
        "sort_order": "asc",
        "limit": 10
    }
