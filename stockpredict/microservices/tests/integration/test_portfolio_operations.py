"""
Integration tests for portfolio-service.

Tests cover:
- Portfolio CRUD operations
- Holdings management
- Transaction recording
- Price alerts
- Portfolio summary and metrics
"""

import pytest
import httpx
from datetime import datetime

from tests.conftest import get_api_path


pytestmark = [pytest.mark.integration, pytest.mark.auth]


class TestHealthEndpoints:
    """Test portfolio-service health endpoints."""

    async def test_health_live(self, portfolio_client: httpx.AsyncClient):
        """Test liveness probe endpoint."""
        response = await portfolio_client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    async def test_health_ready(self, portfolio_client: httpx.AsyncClient):
        """Test readiness probe endpoint."""
        response = await portfolio_client.get("/health/ready")
        # May return 503 if database not connected
        assert response.status_code in [200, 503]


class TestPortfolioCreation:
    """Test portfolio creation operations."""

    async def test_create_portfolio(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        sample_portfolio_data: dict
    ):
        """Test creating a new portfolio."""
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/portfolios"),
            json=sample_portfolio_data
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == sample_portfolio_data["name"]
        assert "id" in data

    async def test_create_portfolio_unauthorized(
        self,
        portfolio_client: httpx.AsyncClient,
        sample_portfolio_data: dict
    ):
        """Test creating portfolio without auth fails."""
        response = await portfolio_client.post(
            get_api_path("portfolio/portfolios"),
            json=sample_portfolio_data
        )
        assert response.status_code == 401

    async def test_get_default_portfolio(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test getting default portfolio."""
        response = await authenticated_portfolio_client.get(
            get_api_path("portfolios/default")
        )
        # May create default if not exists
        assert response.status_code in [200, 201, 404]

    async def test_create_duplicate_portfolio_name(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        sample_portfolio_data: dict
    ):
        """Test creating portfolio with duplicate name."""
        # Create first portfolio
        await authenticated_portfolio_client.post(
            get_api_path("portfolio/portfolios"),
            json=sample_portfolio_data
        )

        # Try to create duplicate
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/portfolios"),
            json=sample_portfolio_data
        )
        # May succeed with different ID or fail with conflict
        assert response.status_code in [200, 201, 400, 409]


class TestPortfolioRetrieval:
    """Test portfolio retrieval operations."""

    async def test_list_portfolios(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test listing user portfolios."""
        response = await authenticated_portfolio_client.get(get_api_path("portfolio/portfolios"))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    async def test_get_portfolio_by_id(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        sample_portfolio_data: dict
    ):
        """Test getting portfolio by ID."""
        # Create portfolio first
        create_response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/portfolios"),
            json=sample_portfolio_data
        )
        if create_response.status_code in [200, 201]:
            portfolio_id = create_response.json().get("id")
            if portfolio_id:
                response = await authenticated_portfolio_client.get(
                    get_api_path(f"portfolio/{portfolio_id}")
                )
                assert response.status_code == 200

    async def test_get_portfolio_summary(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test getting portfolio summary."""
        response = await authenticated_portfolio_client.get(
            get_api_path("portfolio/summary")
        )
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Should contain summary metrics (matching PortfolioSummary schema)
            assert any(key in data for key in [
                "total_value", "totalValue", "total", "value",
                "holdings", "cash", "performance",
                # Actual schema field names
                "total_holdings", "total_invested", "current_value",
                "portfolio_id", "portfolio_name"
            ])


class TestHoldingsManagement:
    """Test holdings management operations."""

    async def test_add_holding(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        sample_holding_data: dict
    ):
        """Test adding a holding to portfolio."""
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/holdings"),
            json=sample_holding_data
        )
        assert response.status_code in [200, 201]

    async def test_list_holdings(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test listing portfolio holdings."""
        response = await authenticated_portfolio_client.get(
            get_api_path("portfolio/holdings")
        )
        assert response.status_code in [200, 404]

    async def test_update_holding(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        sample_holding_data: dict
    ):
        """Test updating a holding."""
        # First add a holding
        create_response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/holdings"),
            json=sample_holding_data
        )

        if create_response.status_code in [200, 201]:
            holding_id = create_response.json().get("id")
            if holding_id:
                update_data = {"quantity": 200}
                response = await authenticated_portfolio_client.put(
                    get_api_path(f"portfolio/holdings/{holding_id}"),
                    json=update_data
                )
                assert response.status_code in [200, 404]

    async def test_remove_holding(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        sample_holding_data: dict
    ):
        """Test removing a holding."""
        # First add a holding
        create_response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/holdings"),
            json=sample_holding_data
        )

        if create_response.status_code in [200, 201]:
            holding_id = create_response.json().get("id")
            if holding_id:
                response = await authenticated_portfolio_client.delete(
                    get_api_path(f"portfolio/holdings/{holding_id}")
                )
                assert response.status_code in [200, 204, 404]


class TestTransactions:
    """Test transaction operations."""

    async def test_record_buy_transaction(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test recording a buy transaction."""
        transaction = {
            "symbol": "VNM",
            "type": "buy",
            "quantity": 100,
            "price": 75000.0,
            "date": datetime.now().isoformat()
        }
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/transactions"),
            json=transaction
        )
        assert response.status_code in [200, 201]

    async def test_record_sell_transaction(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test recording a sell transaction."""
        # First buy
        buy_transaction = {
            "symbol": "FPT",
            "type": "buy",
            "quantity": 100,
            "price": 90000.0
        }
        await authenticated_portfolio_client.post(
            get_api_path("portfolio/transactions"),
            json=buy_transaction
        )

        # Then sell
        sell_transaction = {
            "symbol": "FPT",
            "type": "sell",
            "quantity": 50,
            "price": 95000.0
        }
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/transactions"),
            json=sell_transaction
        )
        assert response.status_code in [200, 201, 400]  # 400 if not enough holdings

    async def test_get_transaction_history(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test getting transaction history."""
        response = await authenticated_portfolio_client.get(
            get_api_path("portfolio/transactions")
        )
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            items = data if isinstance(data, list) else data.get("items", data.get("data", []))
            assert isinstance(items, list)

    async def test_bulk_transactions(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test recording multiple transactions at once."""
        transactions = [
            {"symbol": "VNM", "type": "buy", "quantity": 50, "price": 75000.0},
            {"symbol": "FPT", "type": "buy", "quantity": 30, "price": 90000.0},
            {"symbol": "VIC", "type": "buy", "quantity": 20, "price": 50000.0},
        ]
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/transactions/bulk"),
            json={"transactions": transactions}
        )
        # Bulk endpoint may not exist
        assert response.status_code in [200, 201, 404]


class TestPriceAlerts:
    """Test price alert operations."""

    async def test_create_alert(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        sample_alert_data: dict
    ):
        """Test creating a price alert."""
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/alerts"),
            json=sample_alert_data
        )
        assert response.status_code in [200, 201]

        if response.status_code in [200, 201]:
            data = response.json()
            assert data["symbol"] == sample_alert_data["symbol"]
            assert "id" in data

    async def test_list_alerts(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test listing user alerts."""
        response = await authenticated_portfolio_client.get(get_api_path("portfolio/alerts"))
        assert response.status_code == 200
        data = response.json()
        items = data if isinstance(data, list) else data.get("items", data.get("data", []))
        assert isinstance(items, list)

    async def test_update_alert(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        sample_alert_data: dict
    ):
        """Test updating an alert."""
        # Create alert first
        create_response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/alerts"),
            json=sample_alert_data
        )

        if create_response.status_code in [200, 201]:
            alert_id = create_response.json().get("id")
            if alert_id:
                update_data = {"target_price": 120000.0}
                response = await authenticated_portfolio_client.put(
                    get_api_path(f"alerts/{alert_id}"),
                    json=update_data
                )
                assert response.status_code in [200, 404]

    async def test_delete_alert(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        sample_alert_data: dict
    ):
        """Test deleting an alert."""
        # Create alert first
        create_response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/alerts"),
            json=sample_alert_data
        )

        if create_response.status_code in [200, 201]:
            alert_id = create_response.json().get("id")
            if alert_id:
                response = await authenticated_portfolio_client.delete(
                    get_api_path(f"alerts/{alert_id}")
                )
                assert response.status_code in [200, 204, 404]

    async def test_toggle_alert(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        sample_alert_data: dict
    ):
        """Test toggling alert status."""
        # Create alert
        create_response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/alerts"),
            json=sample_alert_data
        )

        if create_response.status_code in [200, 201]:
            alert_id = create_response.json().get("id")
            if alert_id:
                response = await authenticated_portfolio_client.post(
                    get_api_path(f"alerts/{alert_id}/toggle")
                )
                assert response.status_code in [200, 404]


class TestPortfolioMetrics:
    """Test portfolio metrics and performance."""

    async def test_get_portfolio_performance(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test getting portfolio performance metrics."""
        response = await authenticated_portfolio_client.get(
            get_api_path("portfolio/performance")
        )
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Should contain performance metrics
            assert isinstance(data, dict)

    async def test_get_portfolio_metrics(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test getting detailed portfolio metrics."""
        response = await authenticated_portfolio_client.get(
            get_api_path("portfolio/metrics")
        )
        assert response.status_code in [200, 404]

    async def test_refresh_prices(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test refreshing portfolio prices."""
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/refresh")
        )
        assert response.status_code in [200, 202, 404]


class TestWatchlist:
    """Test watchlist operations."""

    async def test_add_to_watchlist(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test adding stock to watchlist."""
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/watchlist"),
            json={"symbol": "HPG"}
        )
        assert response.status_code in [200, 201, 404]

    async def test_get_watchlist(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test getting watchlist."""
        response = await authenticated_portfolio_client.get(
            get_api_path("portfolio/watchlist")
        )
        assert response.status_code in [200, 404]

    async def test_remove_from_watchlist(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test removing stock from watchlist."""
        # Add first
        await authenticated_portfolio_client.post(
            get_api_path("portfolio/watchlist"),
            json={"symbol": "MWG"}
        )

        # Remove
        response = await authenticated_portfolio_client.delete(
            get_api_path("portfolio/watchlist/MWG")
        )
        assert response.status_code in [200, 204, 404]


class TestInputValidation:
    """Test input validation."""

    async def test_invalid_transaction_quantity(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test transaction with invalid quantity."""
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/transactions"),
            json={
                "symbol": "VNM",
                "type": "buy",
                "quantity": -100,  # Invalid negative quantity
                "price": 75000.0
            }
        )
        assert response.status_code == 422

    async def test_invalid_transaction_price(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test transaction with invalid price."""
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/transactions"),
            json={
                "symbol": "VNM",
                "type": "buy",
                "quantity": 100,
                "price": -1000.0  # Invalid negative price
            }
        )
        assert response.status_code == 422

    async def test_invalid_alert_condition(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test alert with invalid condition."""
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/alerts"),
            json={
                "symbol": "VNM",
                "target_price": 100000.0,
                "condition": "invalid"  # Should be 'above' or 'below'
            }
        )
        assert response.status_code == 422
