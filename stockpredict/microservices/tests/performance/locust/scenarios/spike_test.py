"""
Spike test scenario for Stock Helper microservices.

Simulates sudden traffic surge to test system elasticity and recovery.

Run with:
    locust -f scenarios/spike_test.py --host=http://localhost --users=500 --spawn-rate=50
"""

import random
from datetime import datetime, timedelta
from typing import Optional

from locust import HttpUser, task, between, events, tag, LoadTestShape
from locust.runners import MasterRunner

import sys
sys.path.append('..')
from config import STOCK_SYMBOLS, TEST_USER


class SpikeUser(HttpUser):
    """User behavior during spike load test."""

    wait_time = between(0.5, 2)  # Faster interactions during spike

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token: Optional[str] = None

    def on_start(self):
        """Quick login for spike test."""
        self._quick_login()

    def _quick_login(self):
        """Fast authentication."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        username = f"spike_{timestamp}"

        # Try login first
        response = self.client.post(
            "/api/v2/auth/login",
            json={
                "username": TEST_USER["username"],
                "password": TEST_USER["password"]
            }
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")
        else:
            # Register and login
            self.client.post(
                "/api/v2/auth/register",
                json={
                    "username": username,
                    "email": f"{username}@test.com",
                    "password": TEST_USER["password"]
                }
            )
            response = self.client.post(
                "/api/v2/auth/login",
                json={"username": username, "password": TEST_USER["password"]}
            )
            if response.status_code == 200:
                self.token = response.json().get("access_token")

    @property
    def auth_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    # High-frequency read operations (80% of spike traffic)
    @task(20)
    @tag("spike", "read", "hot-path")
    def get_companies(self):
        """Most common operation during spike."""
        self.client.get(
            "/api/v2/companies",
            params={"page": 1, "page_size": 20},
            name="/api/v2/companies [spike]"
        )

    @task(15)
    @tag("spike", "read", "hot-path")
    def get_stock_quote(self):
        """Quick stock lookup."""
        symbol = random.choice(STOCK_SYMBOLS)
        self.client.get(
            f"/api/v2/stocks/{symbol}",
            name="/api/v2/stocks/[symbol] [spike]"
        )

    @task(10)
    @tag("spike", "read")
    def search_stocks(self):
        """Stock search during spike."""
        queries = ["bank", "tech", "VN", "food"]
        self.client.get(
            "/api/v2/stocks/search",
            params={"q": random.choice(queries)},
            name="/api/v2/stocks/search [spike]"
        )

    @task(8)
    @tag("spike", "read")
    def get_portfolio(self):
        """Portfolio check during spike."""
        self.client.get(
            "/api/v2/portfolio",
            headers=self.auth_headers,
            name="/api/v2/portfolio [spike]"
        )

    @task(5)
    @tag("spike", "read")
    def get_top_movers(self):
        """Check market movers."""
        endpoint = random.choice(["top-gainers", "top-losers", "top-actives"])
        self.client.get(
            f"/api/v2/companies/{endpoint}",
            name=f"/api/v2/companies/movers [spike]"
        )

    # Low-frequency write operations (20% of spike traffic)
    @task(2)
    @tag("spike", "write")
    def quick_transaction(self):
        """Transaction during spike."""
        symbol = random.choice(STOCK_SYMBOLS)
        self.client.post(
            "/api/v2/portfolio/transactions",
            headers=self.auth_headers,
            json={
                "symbol": symbol,
                "type": "buy",
                "quantity": random.randint(10, 50),
                "price": random.uniform(20000, 80000)
            },
            name="/api/v2/portfolio/transactions [spike]"
        )


class SpikeLoadShape(LoadTestShape):
    """
    Spike load shape: Sudden surge followed by gradual recovery.

    Timeline:
    - 0-60s: Ramp up to 50 users (normal load)
    - 60-90s: Spike to 500 users (10x surge)
    - 90-180s: Hold spike
    - 180-240s: Gradual recovery to 50 users
    - 240-300s: Stabilize at normal load
    """

    stages = [
        {"duration": 60, "users": 50, "spawn_rate": 5},      # Normal ramp-up
        {"duration": 90, "users": 500, "spawn_rate": 50},    # Spike!
        {"duration": 180, "users": 500, "spawn_rate": 10},   # Hold spike
        {"duration": 240, "users": 100, "spawn_rate": 10},   # Recovery
        {"duration": 300, "users": 50, "spawn_rate": 5},     # Stabilize
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data

        return None


# Event handlers
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("=" * 60)
    print("SPIKE TEST: Sudden Traffic Surge Simulation")
    print(f"Target host: {environment.host}")
    print("Timeline:")
    print("  0-60s:   Ramp to 50 users (baseline)")
    print("  60-90s:  SPIKE to 500 users (10x surge)")
    print("  90-180s: Hold spike load")
    print("  180-240s: Recovery phase")
    print("  240-300s: Stabilize")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("=" * 60)
    print("SPIKE TEST COMPLETE")
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Failure rate: {stats.total.fail_ratio * 100:.2f}%")
    if stats.total.num_requests > 0:
        print(f"Avg response time: {stats.total.avg_response_time:.2f}ms")
        print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print("=" * 60)
