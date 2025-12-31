"""
Main Locust load testing file for Stock Helper microservices.

Run with:
    locust -f locustfile.py --host=http://localhost

Or for specific scenarios:
    locust -f locustfile.py --host=http://localhost --users=50 --spawn-rate=5 --run-time=5m
"""

import random
import json
from datetime import datetime, timedelta
from typing import Optional

from locust import HttpUser, task, between, events, tag
from locust.runners import MasterRunner, WorkerRunner

from config import SERVICES, STOCK_SYMBOLS, TEST_USER, THRESHOLDS


class BaseStockUser(HttpUser):
    """Base user class with common functionality."""

    abstract = True
    wait_time = between(1, 3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token: Optional[str] = None
        self.user_id: Optional[int] = None

    def on_start(self):
        """Called when user starts - login and setup."""
        self.login()

    def login(self):
        """Authenticate and get token."""
        with self.client.post(
            "/api/v2/auth/login",
            json={
                "username": TEST_USER["username"],
                "password": TEST_USER["password"]
            },
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
            elif response.status_code == 401:
                # User doesn't exist, try to register
                self.register_and_login()
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")

    def register_and_login(self):
        """Register a new user and login."""
        # Add timestamp to make unique
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        username = f"{TEST_USER['username']}_{timestamp}"

        # Register
        self.client.post(
            "/api/v2/auth/register",
            json={
                "username": username,
                "email": f"{username}@test.com",
                "password": TEST_USER["password"]
            }
        )

        # Login with new credentials
        response = self.client.post(
            "/api/v2/auth/login",
            json={
                "username": username,
                "password": TEST_USER["password"]
            }
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")

    @property
    def auth_headers(self):
        """Get authorization headers."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def random_symbol(self) -> str:
        """Get a random stock symbol."""
        return random.choice(STOCK_SYMBOLS)


class StockDataUser(BaseStockUser):
    """User simulating stock data browsing behavior."""

    weight = 5  # Most common user type

    @task(10)
    @tag("stock-data", "read")
    def list_companies(self):
        """Browse company listing."""
        page = random.randint(1, 10)
        self.client.get(
            "/api/v2/companies",
            params={"page": page, "page_size": 20},
            name="/api/v2/companies"
        )

    @task(8)
    @tag("stock-data", "read")
    def get_stock_detail(self):
        """View stock details."""
        symbol = self.random_symbol()
        self.client.get(
            f"/api/v2/stocks/{symbol}",
            name="/api/v2/stocks/[symbol]"
        )

    @task(5)
    @tag("stock-data", "read")
    def get_stock_history(self):
        """View historical data."""
        symbol = self.random_symbol()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=random.randint(7, 90))

        self.client.get(
            f"/api/v2/stocks/{symbol}/history",
            params={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            },
            name="/api/v2/stocks/[symbol]/history"
        )

    @task(6)
    @tag("stock-data", "read")
    def search_stocks(self):
        """Search for stocks."""
        queries = ["bank", "tech", "food", "real estate", "VN"]
        self.client.get(
            "/api/v2/stocks/search",
            params={"q": random.choice(queries)},
            name="/api/v2/stocks/search"
        )

    @task(4)
    @tag("stock-data", "read")
    def get_top_movers(self):
        """Check top gainers/losers."""
        endpoints = ["top-gainers", "top-losers", "top-actives"]
        endpoint = random.choice(endpoints)
        self.client.get(
            f"/api/v2/companies/{endpoint}",
            name=f"/api/v2/companies/{endpoint}"
        )

    @task(3)
    @tag("stock-data", "read")
    def get_market_indices(self):
        """Check market indices."""
        self.client.get("/api/v2/market/indices")

    @task(2)
    @tag("stock-data", "read")
    def list_industries(self):
        """Browse industries."""
        self.client.get("/api/v2/industries")


class PortfolioUser(BaseStockUser):
    """User simulating portfolio management behavior."""

    weight = 3

    @task(8)
    @tag("portfolio", "read")
    def get_portfolio(self):
        """View portfolio."""
        self.client.get(
            "/api/v2/portfolio",
            headers=self.auth_headers
        )

    @task(6)
    @tag("portfolio", "read")
    def get_portfolio_summary(self):
        """View portfolio summary."""
        self.client.get(
            "/api/v2/portfolio/summary",
            headers=self.auth_headers
        )

    @task(4)
    @tag("portfolio", "read")
    def get_holdings(self):
        """View holdings."""
        self.client.get(
            "/api/v2/portfolio/holdings",
            headers=self.auth_headers
        )

    @task(3)
    @tag("portfolio", "write")
    def add_transaction(self):
        """Add a transaction."""
        symbol = self.random_symbol()
        self.client.post(
            "/api/v2/portfolio/transactions",
            headers=self.auth_headers,
            json={
                "symbol": symbol,
                "type": random.choice(["buy", "sell"]),
                "quantity": random.randint(10, 100),
                "price": random.uniform(10000, 100000)
            },
            name="/api/v2/portfolio/transactions"
        )

    @task(2)
    @tag("portfolio", "read")
    def get_transaction_history(self):
        """View transaction history."""
        self.client.get(
            "/api/v2/portfolio/transactions",
            headers=self.auth_headers
        )

    @task(3)
    @tag("portfolio", "read")
    def get_alerts(self):
        """View price alerts."""
        self.client.get(
            "/api/v2/alerts",
            headers=self.auth_headers
        )

    @task(2)
    @tag("portfolio", "write")
    def create_alert(self):
        """Create price alert."""
        symbol = self.random_symbol()
        self.client.post(
            "/api/v2/alerts",
            headers=self.auth_headers,
            json={
                "symbol": symbol,
                "target_price": random.uniform(50000, 150000),
                "condition": random.choice(["above", "below"])
            },
            name="/api/v2/alerts"
        )

    @task(1)
    @tag("portfolio", "read")
    def get_performance(self):
        """View performance metrics."""
        self.client.get(
            "/api/v2/portfolio/performance",
            headers=self.auth_headers
        )


class AnalysisUser(BaseStockUser):
    """User simulating analysis behavior."""

    weight = 3

    @task(6)
    @tag("analysis", "read")
    def get_technical_analysis(self):
        """View technical analysis."""
        symbol = self.random_symbol()
        self.client.get(
            f"/api/v2/analysis/technical/{symbol}",
            name="/api/v2/analysis/technical/[symbol]"
        )

    @task(4)
    @tag("analysis", "read")
    def get_fundamental_analysis(self):
        """View fundamental analysis."""
        symbol = self.random_symbol()
        self.client.get(
            f"/api/v2/analysis/fundamental/{symbol}",
            name="/api/v2/analysis/fundamental/[symbol]"
        )

    @task(5)
    @tag("analysis", "read")
    def run_screener(self):
        """Run stock screener."""
        filters = random.choice([
            {"min_price": 20000, "max_price": 80000},
            {"min_pe": 5, "max_pe": 20},
            {"min_volume": 100000},
            {"industry": "Banking"},
        ])
        self.client.post(
            "/api/v2/screener",
            json={"filters": filters},
            name="/api/v2/screener"
        )

    @task(3)
    @tag("analysis", "read")
    def get_industry_analysis(self):
        """View industry analysis."""
        industries = ["banking", "real_estate", "technology", "consumer"]
        industry = random.choice(industries)
        self.client.get(
            f"/api/v2/industries/{industry}/stocks",
            name="/api/v2/industries/[code]/stocks"
        )


class PredictionUser(BaseStockUser):
    """User simulating prediction service usage."""

    weight = 1  # Less frequent due to computational cost

    @task(5)
    @tag("prediction", "read")
    def list_models(self):
        """List available models."""
        self.client.get(
            "/api/v2/models",
            headers=self.auth_headers
        )

    @task(4)
    @tag("prediction", "read")
    def get_prediction(self):
        """Get price prediction."""
        symbol = self.random_symbol()
        self.client.post(
            "/api/v2/predict",
            headers=self.auth_headers,
            json={
                "symbol": symbol,
                "days": random.randint(5, 14)
            },
            name="/api/v2/predict"
        )

    @task(2)
    @tag("prediction", "read")
    def get_supported_models(self):
        """Get supported model types."""
        self.client.get("/api/v2/supported-models")


class AIUser(BaseStockUser):
    """User simulating AI service usage."""

    weight = 1  # Less frequent due to LLM cost

    @task(4)
    @tag("ai", "read")
    def get_insight(self):
        """Get AI insight."""
        symbol = self.random_symbol()
        self.client.post(
            "/api/v2/ai/insight",
            headers=self.auth_headers,
            json={"symbol": symbol},
            name="/api/v2/ai/insight"
        )

    @task(3)
    @tag("ai", "read")
    def compare_stocks(self):
        """Compare stocks."""
        symbols = random.sample(STOCK_SYMBOLS, 3)
        self.client.post(
            "/api/v2/ai/compare",
            headers=self.auth_headers,
            json={"symbols": symbols},
            name="/api/v2/ai/compare"
        )

    @task(2)
    @tag("ai", "read")
    def chat_message(self):
        """Send chat message."""
        messages = [
            "What stocks should I look at today?",
            "Analyze VNM for me",
            "What is the current market trend?",
            "Compare VNM and FPT",
        ]
        self.client.post(
            "/api/v2/chat",
            headers=self.auth_headers,
            json={"message": random.choice(messages)},
            name="/api/v2/chat"
        )


class MixedUser(BaseStockUser):
    """User with mixed behavior across all services."""

    weight = 2

    @task(5)
    @tag("mixed", "browse")
    def browse_stocks(self):
        """Browse stock data."""
        self.client.get("/api/v2/companies", params={"page": 1, "page_size": 20})

    @task(4)
    @tag("mixed", "browse")
    def view_stock(self):
        """View a stock."""
        symbol = self.random_symbol()
        self.client.get(f"/api/v2/stocks/{symbol}", name="/api/v2/stocks/[symbol]")

    @task(3)
    @tag("mixed", "portfolio")
    def check_portfolio(self):
        """Check portfolio."""
        self.client.get("/api/v2/portfolio", headers=self.auth_headers)

    @task(2)
    @tag("mixed", "analysis")
    def quick_analysis(self):
        """Quick technical analysis."""
        symbol = self.random_symbol()
        self.client.get(
            f"/api/v2/analysis/technical/{symbol}",
            name="/api/v2/analysis/technical/[symbol]"
        )

    @task(1)
    @tag("mixed", "trade")
    def make_trade(self):
        """Make a trade."""
        symbol = self.random_symbol()
        self.client.post(
            "/api/v2/portfolio/transactions",
            headers=self.auth_headers,
            json={
                "symbol": symbol,
                "type": "buy",
                "quantity": random.randint(10, 50),
                "price": random.uniform(20000, 80000)
            },
            name="/api/v2/portfolio/transactions"
        )


class HealthCheckUser(HttpUser):
    """User for health check monitoring."""

    weight = 1
    wait_time = between(5, 10)

    @task
    @tag("health")
    def check_all_services(self):
        """Check health of all services."""
        services = [
            ("/api/v2/auth", 8007),
            ("/api/v2/stocks", 8001),
            ("/api/v2/portfolio", 8003),
            ("/api/v2/analysis", 8004),
        ]
        for path, port in services:
            self.client.get(
                "/health/live",
                name=f"health_{path}"
            )


# Event handlers for custom reporting
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Track request metrics for custom analysis."""
    if exception:
        print(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("=" * 60)
    print("Stock Helper Load Test Starting")
    print(f"Target host: {environment.host}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("=" * 60)
    print("Stock Helper Load Test Complete")
    print("=" * 60)
