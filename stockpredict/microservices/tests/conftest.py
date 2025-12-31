"""
Shared pytest fixtures for integration testing.

This module provides reusable fixtures for:
- HTTP clients for each microservice
- Database connections and cleanup
- Authentication tokens
- Test data factories
- Docker service management
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text


# =============================================================================
# Environment Configuration
# =============================================================================

# API prefix used by all microservices (must match service config)
API_PREFIX = os.getenv("API_PREFIX", "stock_helper")


def get_api_path(endpoint: str) -> str:
    """Get full API path with prefix. E.g., '/auth/register' -> '/stock_helper/api/v2/auth/register'"""
    # Remove leading slash if present
    endpoint = endpoint.lstrip("/")
    return f"/{API_PREFIX}/api/v2/{endpoint}"


def get_service_url(service: str) -> str:
    """Get service URL from environment or use defaults."""
    urls = {
        "auth": os.getenv("AUTH_SERVICE_URL", "http://localhost:8007"),
        "stock-data": os.getenv("STOCK_DATA_SERVICE_URL", "http://localhost:8001"),
        "portfolio": os.getenv("PORTFOLIO_SERVICE_URL", "http://localhost:8003"),
        "prediction": os.getenv("PREDICTION_SERVICE_URL", "http://localhost:8002"),
        "analysis": os.getenv("ANALYSIS_SERVICE_URL", "http://localhost:8004"),
        "ai-insights": os.getenv("AI_INSIGHTS_SERVICE_URL", "http://localhost:8005"),
        "chatbot": os.getenv("CHATBOT_SERVICE_URL", "http://localhost:8006"),
    }
    return urls.get(service, "http://localhost:8000")


def get_database_url(db_name: str) -> str:
    """Get database URL for a specific database."""
    host = os.getenv("DATABASE_HOST", "localhost")
    port = os.getenv("DATABASE_PORT", "3306")
    user = os.getenv("DATABASE_USER", "root")
    password = os.getenv("DATABASE_PASSWORD", "Mysql_2025")
    return f"mysql+asyncmy://{user}:{password}@{host}:{port}/{db_name}"


# =============================================================================
# Event Loop
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# HTTP Clients
# =============================================================================

@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Generic HTTP client."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def auth_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client configured for auth-service."""
    base_url = get_service_url("auth")
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def stock_data_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client configured for stock-data-service."""
    base_url = get_service_url("stock-data")
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def portfolio_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client configured for portfolio-service."""
    base_url = get_service_url("portfolio")
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def prediction_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client configured for prediction-service."""
    base_url = get_service_url("prediction")
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def analysis_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client configured for analysis-service."""
    base_url = get_service_url("analysis")
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def ai_insights_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client configured for ai-insights-service."""
    base_url = get_service_url("ai-insights")
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def chatbot_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client configured for chatbot-service."""
    base_url = get_service_url("chatbot")
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        yield client


# =============================================================================
# Database Sessions
# =============================================================================

@pytest_asyncio.fixture
async def auth_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Database session for auth_db."""
    engine = create_async_engine(get_database_url("auth_db"), echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def stockdata_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Database session for stockdata_db."""
    engine = create_async_engine(get_database_url("stockdata_db"), echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def portfolio_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Database session for portfolio_db."""
    engine = create_async_engine(get_database_url("portfolio_db"), echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


# =============================================================================
# Test User & Authentication
# =============================================================================

@pytest.fixture
def test_user_data() -> dict:
    """Generate unique test user data."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return {
        "username": f"testuser_{timestamp}",
        "email": f"testuser_{timestamp}@test.com",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User"
    }


@pytest_asyncio.fixture
async def registered_user(auth_client: httpx.AsyncClient, test_user_data: dict) -> dict:
    """Create and return a registered test user."""
    response = await auth_client.post(get_api_path("auth/register"), json=test_user_data)
    assert response.status_code == 201, f"Failed to register user: {response.text}"
    return {**test_user_data, **response.json()}


@pytest_asyncio.fixture
async def auth_token(auth_client: httpx.AsyncClient, registered_user: dict) -> str:
    """Get an authentication token for the test user."""
    response = await auth_client.post(get_api_path("auth/login"), json={
        "email": registered_user["email"],
        "password": registered_user["password"]
    })
    assert response.status_code == 200, f"Failed to login: {response.text}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict:
    """Get authorization headers with the test user's token."""
    return {"Authorization": f"Bearer {auth_token}"}


# =============================================================================
# Authenticated Clients
# =============================================================================

@pytest_asyncio.fixture
async def authenticated_portfolio_client(
    auth_headers: dict
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Portfolio client with authentication headers."""
    base_url = get_service_url("portfolio")
    async with httpx.AsyncClient(
        base_url=base_url,
        headers=auth_headers,
        timeout=30.0
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_prediction_client(
    auth_headers: dict
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Prediction client with authentication headers."""
    base_url = get_service_url("prediction")
    async with httpx.AsyncClient(
        base_url=base_url,
        headers=auth_headers,
        timeout=30.0
    ) as client:
        yield client


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_stock_symbols() -> list[str]:
    """Sample Vietnamese stock symbols for testing."""
    return ["VNM", "FPT", "VIC", "VHM", "HPG", "MWG", "TCB", "VCB", "BID", "CTG"]


@pytest.fixture
def sample_portfolio_data() -> dict:
    """Sample portfolio creation data."""
    return {
        "name": "Test Portfolio",
        "description": "Portfolio for integration testing",
        "initial_cash": 100000000.0  # 100 million VND
    }


@pytest.fixture
def sample_holding_data() -> dict:
    """Sample holding/transaction data."""
    return {
        "symbol": "VNM",
        "quantity": 100,
        "price": 75000.0,
        "transaction_type": "buy"
    }


@pytest.fixture
def sample_alert_data() -> dict:
    """Sample price alert data."""
    return {
        "symbol": "FPT",
        "target_price": 100000.0,
        "condition": "above",
        "is_active": True
    }


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def cleanup_test_users(auth_db_session: AsyncSession):
    """Clean up test users after tests."""
    yield
    # Cleanup users created during tests
    await auth_db_session.execute(
        text("DELETE FROM users WHERE username LIKE 'testuser_%'")
    )
    await auth_db_session.commit()


@pytest_asyncio.fixture
async def cleanup_test_portfolios(portfolio_db_session: AsyncSession):
    """Clean up test portfolios after tests."""
    yield
    # Cleanup portfolios created during tests
    await portfolio_db_session.execute(
        text("DELETE FROM portfolios WHERE name LIKE 'Test%'")
    )
    await portfolio_db_session.commit()


# =============================================================================
# Health Check Utilities
# =============================================================================

@pytest_asyncio.fixture
async def wait_for_services(http_client: httpx.AsyncClient):
    """Wait for all services to be healthy before running tests."""
    services = [
        ("auth", get_service_url("auth")),
        ("stock-data", get_service_url("stock-data")),
        ("portfolio", get_service_url("portfolio")),
        ("prediction", get_service_url("prediction")),
        ("analysis", get_service_url("analysis")),
    ]

    for name, url in services:
        max_retries = 30
        for attempt in range(max_retries):
            try:
                response = await http_client.get(f"{url}/health/live")
                if response.status_code == 200:
                    break
            except httpx.RequestError:
                pass

            if attempt == max_retries - 1:
                pytest.fail(f"Service {name} not healthy after {max_retries} attempts")

            await asyncio.sleep(1)


# =============================================================================
# Performance Metrics
# =============================================================================

@pytest.fixture
def performance_thresholds() -> dict:
    """Performance thresholds for API endpoints."""
    return {
        "auth_login": 500,  # ms
        "auth_register": 1000,
        "stock_list": 200,
        "stock_history": 500,
        "portfolio_summary": 300,
        "prediction_run": 5000,
        "analysis_technical": 1000,
    }


# =============================================================================
# Markers
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "auth: marks tests requiring authentication")
    config.addinivalue_line("markers", "database: marks tests requiring database")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "e2e: marks end-to-end tests")
    config.addinivalue_line("markers", "performance: marks performance tests")
