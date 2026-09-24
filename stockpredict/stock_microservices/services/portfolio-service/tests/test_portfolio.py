"""
Portfolio Service Tests
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "portfolio-service"


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient):
    """Test liveness probe"""
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_service_info(client: AsyncClient):
    """Test service info endpoint"""
    response = await client.get("/stock_helper/api/v2/portfolio/info")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "portfolio-service"
    assert "version" in data
    assert "endpoints" in data


# Portfolio CRUD Tests
@pytest.mark.asyncio
async def test_create_portfolio(client: AsyncClient, create_portfolio_data, mock_portfolio):
    """Test portfolio creation"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.create_portfolio = AsyncMock(return_value=mock_portfolio)
        MockService.return_value = mock_service

        response = await client.post(
            "/stock_helper/api/v2/portfolio/portfolios",
            json=create_portfolio_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Portfolio"


@pytest.mark.asyncio
async def test_get_portfolios(client: AsyncClient, mock_portfolio):
    """Test getting all portfolios"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.get_user_portfolios = AsyncMock(return_value=[mock_portfolio])
        MockService.return_value = mock_service

        response = await client.get("/stock_helper/api/v2/portfolio/portfolios")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Portfolio"


@pytest.mark.asyncio
async def test_get_portfolio_by_id(client: AsyncClient, mock_portfolio):
    """Test getting a specific portfolio"""
    # Create a mock portfolio with holdings
    mock_portfolio_with_holdings = MagicMock()
    mock_portfolio_with_holdings.id = 1
    mock_portfolio_with_holdings.user_id = 1
    mock_portfolio_with_holdings.name = "Test Portfolio"
    mock_portfolio_with_holdings.description = "Test"
    mock_portfolio_with_holdings.is_default = True
    mock_portfolio_with_holdings.created_at = datetime.utcnow()
    mock_portfolio_with_holdings.updated_at = datetime.utcnow()
    mock_portfolio_with_holdings.holdings = []
    mock_portfolio_with_holdings.transactions = []

    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.get_portfolio = AsyncMock(return_value=mock_portfolio_with_holdings)
        MockService.return_value = mock_service

        response = await client.get("/stock_helper/api/v2/portfolio/portfolios/1")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_portfolio_not_found(client: AsyncClient):
    """Test getting non-existent portfolio"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.get_portfolio = AsyncMock(return_value=None)
        MockService.return_value = mock_service

        response = await client.get("/stock_helper/api/v2/portfolio/portfolios/999")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_portfolio(client: AsyncClient, mock_portfolio):
    """Test portfolio update"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.update_portfolio = AsyncMock(return_value=mock_portfolio)
        MockService.return_value = mock_service

        response = await client.put(
            "/stock_helper/api/v2/portfolio/portfolios/1",
            json={"name": "Updated Portfolio"}
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_portfolio(client: AsyncClient):
    """Test portfolio deletion"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.delete_portfolio = AsyncMock(return_value=True)
        MockService.return_value = mock_service

        response = await client.delete("/stock_helper/api/v2/portfolio/portfolios/1")
        assert response.status_code == 204


# Holding Tests
@pytest.mark.asyncio
async def test_add_holding(client: AsyncClient, create_holding_data, mock_holding):
    """Test adding holding to portfolio"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.add_holding = AsyncMock(return_value=mock_holding)
        MockService.return_value = mock_service

        response = await client.post(
            "/stock_helper/api/v2/portfolio/portfolios/1/holdings",
            json=create_holding_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == "VNM"


@pytest.mark.asyncio
async def test_get_holdings(client: AsyncClient, mock_holding):
    """Test getting holdings"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.get_holdings = AsyncMock(return_value=[mock_holding])
        MockService.return_value = mock_service

        response = await client.get("/stock_helper/api/v2/portfolio/portfolios/1/holdings")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


@pytest.mark.asyncio
async def test_remove_holding(client: AsyncClient):
    """Test removing holding"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.remove_holding = AsyncMock(return_value=True)
        MockService.return_value = mock_service

        response = await client.delete(
            "/stock_helper/api/v2/portfolio/portfolios/1/holdings/VNM"
        )
        assert response.status_code == 204


# Transaction Tests
@pytest.mark.asyncio
async def test_record_transaction(client: AsyncClient, create_transaction_data, mock_transaction):
    """Test recording transaction"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.record_transaction = AsyncMock(return_value=mock_transaction)
        MockService.return_value = mock_service

        response = await client.post(
            "/stock_helper/api/v2/portfolio/portfolios/1/transactions",
            json=create_transaction_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == "VNM"
        assert data["transaction_type"] == "buy"


@pytest.mark.asyncio
async def test_get_transactions(client: AsyncClient, mock_transaction):
    """Test getting transactions"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.get_transactions = AsyncMock(return_value=[mock_transaction])
        MockService.return_value = mock_service

        response = await client.get(
            "/stock_helper/api/v2/portfolio/portfolios/1/transactions"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


# Alert Tests
@pytest.mark.asyncio
async def test_create_alert(client: AsyncClient, create_alert_data, mock_alert):
    """Test creating price alert"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.create_alert = AsyncMock(return_value=mock_alert)
        MockService.return_value = mock_service

        response = await client.post(
            "/stock_helper/api/v2/portfolio/alerts",
            json=create_alert_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == "VNM"


@pytest.mark.asyncio
async def test_get_alerts(client: AsyncClient, mock_alert):
    """Test getting alerts"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.get_alerts = AsyncMock(return_value=[mock_alert])
        MockService.return_value = mock_service

        response = await client.get("/stock_helper/api/v2/portfolio/alerts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


@pytest.mark.asyncio
async def test_delete_alert(client: AsyncClient):
    """Test deleting alert"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.delete_alert = AsyncMock(return_value=True)
        MockService.return_value = mock_service

        response = await client.delete("/stock_helper/api/v2/portfolio/alerts/1")
        assert response.status_code == 204


# Watchlist Tests
@pytest.mark.asyncio
async def test_add_to_watchlist(client: AsyncClient, mock_portfolio, mock_holding):
    """Test adding to watchlist"""
    watchlist_holding = mock_holding.model_copy()
    watchlist_holding.is_watchlist_only = True

    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.get_or_create_default_portfolio = AsyncMock(return_value=mock_portfolio)
        mock_service.add_to_watchlist = AsyncMock(return_value=watchlist_holding)
        MockService.return_value = mock_service

        response = await client.post("/stock_helper/api/v2/portfolio/watchlist/VNM")
        assert response.status_code == 201


@pytest.mark.asyncio
async def test_get_watchlist(client: AsyncClient, mock_portfolio, mock_holding):
    """Test getting watchlist"""
    watchlist_holding = mock_holding.model_copy()
    watchlist_holding.is_watchlist_only = True

    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.get_or_create_default_portfolio = AsyncMock(return_value=mock_portfolio)
        mock_service.get_holdings = AsyncMock(return_value=[watchlist_holding])
        MockService.return_value = mock_service

        response = await client.get("/stock_helper/api/v2/portfolio/watchlist")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_remove_from_watchlist(client: AsyncClient, mock_portfolio):
    """Test removing from watchlist"""
    with patch("app.api.routes.PortfolioService") as MockService:
        mock_service = MagicMock()
        mock_service.get_or_create_default_portfolio = AsyncMock(return_value=mock_portfolio)
        mock_service.remove_holding = AsyncMock(return_value=True)
        MockService.return_value = mock_service

        response = await client.delete("/stock_helper/api/v2/portfolio/watchlist/VNM")
        assert response.status_code == 204


# Authentication Tests
@pytest.mark.asyncio
async def test_unauthenticated_access(unauthenticated_client: AsyncClient):
    """Test that protected endpoints require authentication"""
    response = await unauthenticated_client.get(
        "/stock_helper/api/v2/portfolio/portfolios"
    )
    assert response.status_code == 403  # Forbidden without Bearer token
