"""
Test Configuration and Fixtures for Portfolio Service
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.main import app
from app.api.dependencies import get_db, get_current_user
from app.models.schemas import (
    PortfolioResponse, HoldingResponse, TransactionResponse, AlertResponse,
    TransactionType, AlertType
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
        return {"user_id": 1, "email": "test@example.com", "role": "user"}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthenticated_client(mock_db):
    """Create test client without authentication"""

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_portfolio():
    """Mock portfolio response"""
    return PortfolioResponse(
        id=1,
        user_id=1,
        name="Test Portfolio",
        description="Test description",
        is_default=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def mock_holding():
    """Mock holding response"""
    return HoldingResponse(
        id=1,
        portfolio_id=1,
        symbol="VNM",
        quantity=100,
        average_price=75000.0,
        total_cost=7500000.0,
        current_price=80000.0,
        current_value=8000000.0,
        profit_loss=500000.0,
        profit_loss_percent=6.67,
        is_watchlist_only=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def mock_transaction():
    """Mock transaction response"""
    return TransactionResponse(
        id=1,
        portfolio_id=1,
        symbol="VNM",
        transaction_type=TransactionType.BUY,
        quantity=100,
        price=75000.0,
        total_value=7500000.0,
        fees=15000.0,
        notes="Test transaction",
        transaction_date=datetime.utcnow(),
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_alert():
    """Mock alert response"""
    return AlertResponse(
        id=1,
        user_id=1,
        symbol="VNM",
        alert_type=AlertType.ABOVE,
        target_price=85000.0,
        target_percent=None,
        is_active=True,
        is_triggered=False,
        triggered_at=None,
        notes="Price target alert",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def create_portfolio_data():
    """Test data for creating portfolio"""
    return {
        "name": "My Portfolio",
        "description": "My investment portfolio",
        "is_default": False
    }


@pytest.fixture
def create_holding_data():
    """Test data for creating holding"""
    return {
        "symbol": "VNM",
        "quantity": 100,
        "average_price": 75000.0,
        "is_watchlist_only": False
    }


@pytest.fixture
def create_transaction_data():
    """Test data for creating transaction"""
    return {
        "symbol": "VNM",
        "transaction_type": "buy",
        "quantity": 100,
        "price": 75000.0,
        "fees": 15000.0,
        "notes": "Initial purchase"
    }


@pytest.fixture
def create_alert_data():
    """Test data for creating alert"""
    return {
        "symbol": "VNM",
        "alert_type": "above",
        "target_price": 85000.0,
        "notes": "Sell target"
    }
