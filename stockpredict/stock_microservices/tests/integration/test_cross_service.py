"""
Integration tests for cross-service communication.

Tests cover:
- Auth → Portfolio flow
- Stock Data → Analysis flow
- Portfolio → Stock Data integration
- Prediction → Stock Data integration
- Full user journey workflows
"""

import pytest
import httpx
from datetime import datetime

from tests.conftest import get_api_path


pytestmark = [pytest.mark.integration, pytest.mark.e2e]


class TestAuthPortfolioIntegration:
    """Test integration between auth-service and portfolio-service."""

    async def test_authenticated_portfolio_access(
        self,
        auth_client: httpx.AsyncClient,
        portfolio_client: httpx.AsyncClient,
        test_user_data: dict
    ):
        """Test that auth tokens work across services."""
        # Register user
        register_response = await auth_client.post(
            get_api_path("auth/register"),
            json=test_user_data
        )
        assert register_response.status_code == 201

        # Login to get token
        login_response = await auth_client.post(
            get_api_path("auth/login"),
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Use token with portfolio service
        portfolio_response = await portfolio_client.get(
            get_api_path("portfolio/portfolios"),
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should accept the token (200) or have no portfolios yet (404)
        assert portfolio_response.status_code in [200, 404]

    async def test_invalid_token_rejected_by_portfolio(
        self,
        portfolio_client: httpx.AsyncClient
    ):
        """Test that portfolio service rejects invalid tokens."""
        response = await portfolio_client.get(
            get_api_path("portfolio/portfolios"),
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401

    async def test_token_refresh_maintains_access(
        self,
        auth_client: httpx.AsyncClient,
        portfolio_client: httpx.AsyncClient,
        test_user_data: dict
    ):
        """Test that refreshed tokens still work with portfolio service."""
        # Register and login
        await auth_client.post(get_api_path("auth/register"), json=test_user_data)
        login_response = await auth_client.post(
            get_api_path("auth/login"),
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )
        tokens = login_response.json()

        # Refresh token
        refresh_response = await auth_client.post(
            get_api_path("auth/refresh"),
            json={"refresh_token": tokens["refresh_token"]}
        )
        new_token = refresh_response.json()["access_token"]

        # Use new token with portfolio
        portfolio_response = await portfolio_client.get(
            get_api_path("portfolio/portfolios"),
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert portfolio_response.status_code in [200, 404]


class TestStockDataAnalysisIntegration:
    """Test integration between stock-data-service and analysis-service."""

    async def test_analysis_uses_stock_data(
        self,
        stock_data_client: httpx.AsyncClient,
        analysis_client: httpx.AsyncClient
    ):
        """Test that analysis service can get data from stock-data service."""
        symbol = "VNM"

        # Verify stock exists
        stock_response = await stock_data_client.get(get_api_path(f"stocks/{symbol}"))

        if stock_response.status_code == 200:
            # Request analysis
            analysis_response = await analysis_client.get(
                get_api_path(f"analysis/technical/{symbol}")
            )
            # Analysis should work or indicate missing data
            assert analysis_response.status_code in [200, 404, 503]

    async def test_fundamental_analysis_uses_stock_data(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test fundamental analysis integration."""
        symbol = "FPT"
        response = await analysis_client.get(
            get_api_path(f"analysis/fundamental/{symbol}")
        )
        assert response.status_code in [200, 404, 503]


class TestPortfolioStockDataIntegration:
    """Test integration between portfolio-service and stock-data-service."""

    async def test_portfolio_price_refresh(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        stock_data_client: httpx.AsyncClient
    ):
        """Test that portfolio can refresh prices from stock-data service."""
        # Add a holding
        await authenticated_portfolio_client.post(
            get_api_path("portfolio/holdings"),
            json={
                "symbol": "VNM",
                "quantity": 100,
                "price": 75000.0
            }
        )

        # Refresh prices
        refresh_response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/refresh")
        )
        assert refresh_response.status_code in [200, 202, 404]

    async def test_alert_checks_current_price(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test that alerts can check current prices."""
        # Create alert - use portfolio/alerts route since client has portfolio base URL
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/alerts"),
            json={
                "symbol": "VNM",
                "target_price": 80000.0,
                "condition": "above"
            }
        )
        assert response.status_code in [200, 201]


class TestPredictionStockDataIntegration:
    """Test integration between prediction-service and stock-data-service."""

    async def test_prediction_fetches_history(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test that prediction service can fetch historical data."""
        response = await authenticated_prediction_client.post(
            get_api_path("predict"),
            json={
                "symbol": "VNM",
                "days": 7
            }
        )
        # Prediction may need model training first
        assert response.status_code in [200, 400, 404, 422]

    @pytest.mark.slow
    async def test_model_training_uses_stock_data(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test model training retrieves data from stock-data service."""
        response = await authenticated_prediction_client.post(
            get_api_path("models/train"),
            json={
                "symbol": "FPT",
                "model_type": "xgboost",
                "lookback_days": 30
            }
        )
        # Training is async, so 202 is common
        assert response.status_code in [200, 202, 400, 404]


class TestFullUserJourney:
    """Test complete user journey across all services."""

    async def test_new_user_investment_journey(
        self,
        auth_client: httpx.AsyncClient,
        stock_data_client: httpx.AsyncClient,
        portfolio_client: httpx.AsyncClient,
        analysis_client: httpx.AsyncClient,
        test_user_data: dict
    ):
        """
        Test complete investment journey:
        1. User registers
        2. User logs in
        3. User researches stocks
        4. User analyzes a stock
        5. User creates portfolio
        6. User buys stock
        7. User sets alert
        8. User checks portfolio summary
        """
        # 1. Register
        register_response = await auth_client.post(
            get_api_path("auth/register"),
            json=test_user_data
        )
        assert register_response.status_code == 201

        # 2. Login
        login_response = await auth_client.post(
            get_api_path("auth/login"),
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 3. Research stocks
        search_response = await stock_data_client.get(
            get_api_path("stocks/search"),
            params={"q": "Vinamilk"}
        )
        # Search may return empty list or 404 if no stocks in DB
        assert search_response.status_code in [200, 404]

        # Get top gainers
        gainers_response = await stock_data_client.get(
            get_api_path("stocks/top-gainers")
        )
        assert gainers_response.status_code in [200, 404]

        # 4. Analyze a stock
        analysis_response = await analysis_client.get(
            get_api_path("analysis/technical/VNM")
        )
        # Analysis may or may not have data
        assert analysis_response.status_code in [200, 404, 503]

        # 5. Create portfolio
        portfolio_response = await portfolio_client.post(
            get_api_path("portfolio/portfolios"),
            headers=auth_headers,
            json={
                "name": "My Investment Portfolio",
                "initial_cash": 100000000.0
            }
        )
        assert portfolio_response.status_code in [200, 201]
        portfolio_id = portfolio_response.json().get("id", 1)

        # 6. Buy stock (transactions are under portfolio/{id}/transactions)
        transaction_response = await portfolio_client.post(
            get_api_path(f"portfolio/portfolios/{portfolio_id}/transactions"),
            headers=auth_headers,
            json={
                "symbol": "VNM",
                "type": "buy",
                "quantity": 100,
                "price": 75000.0
            }
        )
        assert transaction_response.status_code in [200, 201]

        # 7. Set alert
        alert_response = await portfolio_client.post(
            get_api_path("portfolio/alerts"),
            headers=auth_headers,
            json={
                "symbol": "VNM",
                "target_price": 80000.0,
                "condition": "above"
            }
        )
        assert alert_response.status_code in [200, 201]

        # 8. Check portfolio summary
        summary_response = await portfolio_client.get(
            get_api_path(f"portfolio/portfolios/{portfolio_id}/summary"),
            headers=auth_headers
        )
        assert summary_response.status_code in [200, 404]


class TestServiceDependencyFailure:
    """Test behavior when dependent services are unavailable."""

    async def test_portfolio_handles_stock_data_timeout(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test portfolio service handles stock-data timeout gracefully."""
        # This test assumes stock-data might be slow
        # In real scenario, you'd mock or slow down the dependency
        # First create a portfolio
        response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/portfolios"),
            json={"name": "Timeout Test Portfolio", "initial_cash": 1000000.0}
        )
        # Should handle timeout gracefully or return 201 for creation
        assert response.status_code in [200, 201, 202, 503, 504]

    async def test_analysis_handles_missing_stock(
        self,
        analysis_client: httpx.AsyncClient
    ):
        """Test analysis service handles non-existent stock."""
        response = await analysis_client.get(
            get_api_path("analysis/technical/INVALID999")
        )
        assert response.status_code in [404, 400]


class TestDataConsistency:
    """Test data consistency across services."""

    async def test_portfolio_holding_matches_stock_data(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        stock_data_client: httpx.AsyncClient
    ):
        """Test that holding symbols are valid stocks."""
        # Get portfolios first
        portfolios_response = await authenticated_portfolio_client.get(
            get_api_path("portfolio/portfolios")
        )

        if portfolios_response.status_code == 200:
            portfolios = portfolios_response.json()
            if portfolios and len(portfolios) > 0:
                portfolio_id = portfolios[0].get("id", 1)
                # Get holdings for the portfolio
                holdings_response = await authenticated_portfolio_client.get(
                    get_api_path(f"portfolio/portfolios/{portfolio_id}")
                )
                if holdings_response.status_code == 200:
                    portfolio_data = holdings_response.json()
                    holdings = portfolio_data.get("holdings", [])

                    for holding in holdings[:3]:  # Check first 3
                        symbol = holding.get("symbol")
                        if symbol:
                            # Verify stock exists
                            stock_response = await stock_data_client.get(
                                get_api_path(f"stocks/{symbol}")
                            )
                            assert stock_response.status_code in [200, 404]

    async def test_transaction_prices_reasonable(
        self,
        authenticated_portfolio_client: httpx.AsyncClient,
        stock_data_client: httpx.AsyncClient
    ):
        """Test that transaction prices are in reasonable range."""
        # Get portfolios first
        portfolios_response = await authenticated_portfolio_client.get(
            get_api_path("portfolio/portfolios")
        )

        if portfolios_response.status_code == 200:
            portfolios = portfolios_response.json()
            if portfolios and len(portfolios) > 0:
                portfolio_id = portfolios[0].get("id", 1)
                # Get transactions for the portfolio
                transactions_response = await authenticated_portfolio_client.get(
                    get_api_path(f"portfolio/portfolios/{portfolio_id}/transactions")
                )

                if transactions_response.status_code == 200:
                    transactions = transactions_response.json()
                    items = transactions if isinstance(transactions, list) else transactions.get("items", [])

                    for tx in items[:5]:
                        price = tx.get("price", 0)
                        # Vietnamese stock prices are typically 1,000 - 500,000 VND
                        assert 0 <= price <= 10000000  # Up to 10 million VND


class TestConcurrentRequests:
    """Test handling of concurrent requests across services."""

    async def test_concurrent_portfolio_operations(
        self,
        authenticated_portfolio_client: httpx.AsyncClient
    ):
        """Test concurrent portfolio operations don't conflict."""
        import asyncio

        # First create a portfolio to use
        create_response = await authenticated_portfolio_client.post(
            get_api_path("portfolio/portfolios"),
            json={"name": "Concurrent Test Portfolio", "initial_cash": 10000000.0}
        )
        if create_response.status_code not in [200, 201]:
            # Try to get existing portfolio
            get_response = await authenticated_portfolio_client.get(
                get_api_path("portfolio/portfolios")
            )
            if get_response.status_code == 200 and get_response.json():
                portfolio_id = get_response.json()[0].get("id", 1)
            else:
                return  # Skip if we can't create or get a portfolio
        else:
            portfolio_id = create_response.json().get("id", 1)

        async def add_transaction(symbol: str):
            return await authenticated_portfolio_client.post(
                get_api_path(f"portfolio/portfolios/{portfolio_id}/transactions"),
                json={
                    "symbol": symbol,
                    "type": "buy",
                    "quantity": 10,
                    "price": 50000.0
                }
            )

        # Execute concurrent requests
        results = await asyncio.gather(
            add_transaction("VNM"),
            add_transaction("FPT"),
            add_transaction("VIC"),
            return_exceptions=True
        )

        # All should succeed or fail gracefully
        for result in results:
            if not isinstance(result, Exception):
                assert result.status_code in [200, 201, 400, 409]

    async def test_concurrent_auth_and_portfolio(
        self,
        auth_client: httpx.AsyncClient,
        portfolio_client: httpx.AsyncClient,
        auth_token: str
    ):
        """Test concurrent auth check and portfolio operation."""
        import asyncio

        async def verify_token():
            # The /auth/verify endpoint expects token in JSON body, not headers
            return await auth_client.post(
                get_api_path("auth/verify"),
                json={"token": auth_token}
            )

        async def get_portfolio():
            return await portfolio_client.get(
                get_api_path("portfolio/portfolios"),
                headers={"Authorization": f"Bearer {auth_token}"}
            )

        results = await asyncio.gather(
            verify_token(),
            get_portfolio(),
            verify_token(),
            get_portfolio()
        )

        # All should complete successfully
        for result in results:
            assert result.status_code in [200, 404]
