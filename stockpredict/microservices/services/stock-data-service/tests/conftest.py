"""
Test Configuration and Fixtures for Stock Data Service
"""
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date

# Mock vnstock3 before importing app modules
sys.modules['vnstock3'] = MagicMock()

from app.main import app
from app.api.dependencies import get_db, get_stock_service
from app.models.schemas import (
    CompanyResponse, CompanyDetailResponse, HistoricalDataResponse,
    TopMoverResponse, SearchResult, MarketIndexResponse, IndustryResponse,
    StockPriceResponse
)


@pytest_asyncio.fixture
async def mock_db():
    """Mock database session"""
    mock_session = AsyncMock()
    yield mock_session


@pytest.fixture
def mock_stock_service():
    """Mock stock service"""
    mock_service = MagicMock()
    mock_service.get_all_companies = AsyncMock(return_value=([], 0, 0))
    mock_service.get_company_by_symbol = AsyncMock(return_value=None)
    mock_service.get_company_detail = AsyncMock(return_value=None)
    mock_service.get_historical_data = AsyncMock(return_value=None)
    mock_service.get_top_gainers = AsyncMock(return_value=[])
    mock_service.get_top_losers = AsyncMock(return_value=[])
    mock_service.get_top_actives = AsyncMock(return_value=[])
    mock_service.search_companies = AsyncMock(return_value=[])
    mock_service.get_industries = AsyncMock(return_value=[])
    mock_service.get_market_indices = AsyncMock(return_value=[])
    mock_service.get_companies_by_industry = AsyncMock(return_value=[])
    return mock_service


@pytest_asyncio.fixture
async def client(mock_db, mock_stock_service):
    """Create test client with mocked dependencies"""

    async def override_get_db():
        yield mock_db

    def override_get_stock_service():
        return mock_stock_service

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_stock_service] = override_get_stock_service

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_company():
    """Mock company response"""
    return CompanyResponse(
        id=1,
        symbol="VNM",
        name="Vietnam Dairy Products JSC",
        exchange="HOSE",
        industry_id=1,
        industry_name="Food & Beverage",
        is_active=True,
        is_tradeable=True,
        market_cap=180000000000000
    )


@pytest.fixture
def mock_company_detail():
    """Mock company detail response"""
    return CompanyDetailResponse(
        id=1,
        symbol="VNM",
        name="Vietnam Dairy Products JSC",
        name_en="Vinamilk",
        exchange="HOSE",
        industry=IndustryResponse(
            id=1,
            code="FOOD",
            name="Food & Beverage",
            level=1
        ),
        current_price=75000.0,
        change=1500.0,
        change_percent=2.04,
        volume=1500000,
        market_cap=180000000000000,
        description="Leading dairy company in Vietnam",
        website="https://www.vinamilk.com.vn"
    )


@pytest.fixture
def mock_historical_data():
    """Mock historical data response"""
    return HistoricalDataResponse(
        symbol="VNM",
        name="Vietnam Dairy Products JSC",
        exchange="HOSE",
        data=[
            StockPriceResponse(
                date=date.today(),
                open=74000.0,
                high=76000.0,
                low=73500.0,
                close=75000.0,
                volume=1500000
            )
        ],
        count=1
    )


@pytest.fixture
def mock_top_mover():
    """Mock top mover response"""
    return TopMoverResponse(
        symbol="VNM",
        name="Vietnam Dairy Products JSC",
        exchange="HOSE",
        close=75000.0,
        change=1500.0,
        change_percent=2.04,
        volume=1500000
    )


@pytest.fixture
def mock_search_result():
    """Mock search result"""
    return SearchResult(
        symbol="VNM",
        name="Vietnam Dairy Products JSC",
        exchange="HOSE",
        industry_name="Food & Beverage"
    )


@pytest.fixture
def mock_market_index():
    """Mock market index response"""
    return MarketIndexResponse(
        code="VNINDEX",
        name="VN-Index",
        date=date.today(),
        close=1200.5,
        change=15.3,
        change_percent=1.29,
        volume=500000000
    )


@pytest.fixture
def mock_industry():
    """Mock industry response"""
    return IndustryResponse(
        id=1,
        code="FOOD",
        name="Food & Beverage",
        level=1,
        company_count=25
    )
