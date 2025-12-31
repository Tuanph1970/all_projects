"""
Stress test scenario for Stock Helper microservices.

Progressively increases load to find system breaking points.

Run with:
    locust -f scenarios/stress_test.py --host=http://localhost
"""

import random
from datetime import datetime, timedelta
from typing import Optional

from locust import HttpUser, task, between, events, tag, LoadTestShape
from locust.runners import MasterRunner

import sys
sys.path.append('..')
from config import STOCK_SYMBOLS, TEST_USER, THRESHOLDS


class StressUser(HttpUser):
    """User behavior during stress test - aggressive interactions."""

    wait_time = between(0.1, 1)  # Very fast to stress the system

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token: Optional[str] = None
        self.request_count = 0

    def on_start(self):
        """Initialize user session."""
        self._authenticate()

    def _authenticate(self):
        """Quick authentication."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        username = f"stress_{timestamp}_{random.randint(1000, 9999)}"

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

    # CPU-intensive operations
    @task(10)
    @tag("stress", "cpu-intensive")
    def list_companies_large(self):
        """Large pagination request."""
        self.client.get(
            "/api/v2/companies",
            params={"page": 1, "page_size": 100},
            name="/api/v2/companies [large]"
        )

    @task(8)
    @tag("stress", "cpu-intensive")
    def search_complex(self):
        """Complex search queries."""
        queries = [
            "technology company with high growth",
            "banking sector",
            "real estate investment",
            "consumer goods manufacturing"
        ]
        self.client.get(
            "/api/v2/stocks/search",
            params={"q": random.choice(queries)},
            name="/api/v2/stocks/search [complex]"
        )

    @task(6)
    @tag("stress", "cpu-intensive")
    def technical_analysis(self):
        """Compute-heavy technical analysis."""
        symbol = random.choice(STOCK_SYMBOLS)
        self.client.get(
            f"/api/v2/analysis/technical/{symbol}",
            name="/api/v2/analysis/technical [stress]"
        )

    @task(5)
    @tag("stress", "cpu-intensive")
    def run_screener(self):
        """Resource-intensive stock screening."""
        filters = random.choice([
            {"min_price": 10000, "max_price": 100000, "min_volume": 50000},
            {"min_pe": 5, "max_pe": 30, "min_market_cap": 1000000000},
            {"industry": "Banking", "min_dividend_yield": 3},
        ])
        self.client.post(
            "/api/v2/screener",
            json={"filters": filters},
            name="/api/v2/screener [stress]"
        )

    # Memory-intensive operations
    @task(4)
    @tag("stress", "memory-intensive")
    def get_stock_history_long(self):
        """Long historical data request."""
        symbol = random.choice(STOCK_SYMBOLS)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # Full year

        self.client.get(
            f"/api/v2/stocks/{symbol}/history",
            params={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            },
            name="/api/v2/stocks/history [1yr]"
        )

    @task(3)
    @tag("stress", "memory-intensive")
    def portfolio_full_report(self):
        """Full portfolio report."""
        self.client.get(
            "/api/v2/portfolio/summary",
            headers=self.auth_headers,
            name="/api/v2/portfolio/summary [stress]"
        )
        self.client.get(
            "/api/v2/portfolio/performance",
            headers=self.auth_headers,
            name="/api/v2/portfolio/performance [stress]"
        )

    # IO-intensive operations
    @task(5)
    @tag("stress", "io-intensive")
    def rapid_transactions(self):
        """Rapid transaction creation."""
        symbol = random.choice(STOCK_SYMBOLS)
        self.client.post(
            "/api/v2/portfolio/transactions",
            headers=self.auth_headers,
            json={
                "symbol": symbol,
                "type": random.choice(["buy", "sell"]),
                "quantity": random.randint(1, 100),
                "price": random.uniform(10000, 100000)
            },
            name="/api/v2/portfolio/transactions [stress]"
        )

    @task(3)
    @tag("stress", "io-intensive")
    def create_alerts_batch(self):
        """Create multiple alerts."""
        for _ in range(3):
            symbol = random.choice(STOCK_SYMBOLS)
            self.client.post(
                "/api/v2/alerts",
                headers=self.auth_headers,
                json={
                    "symbol": symbol,
                    "target_price": random.uniform(30000, 120000),
                    "condition": random.choice(["above", "below"])
                },
                name="/api/v2/alerts [batch]"
            )

    # External service simulation
    @task(2)
    @tag("stress", "external")
    def prediction_request(self):
        """ML prediction request (expensive)."""
        symbol = random.choice(STOCK_SYMBOLS)
        self.client.post(
            "/api/v2/predict",
            headers=self.auth_headers,
            json={
                "symbol": symbol,
                "days": random.randint(7, 30)
            },
            name="/api/v2/predict [stress]"
        )

    @task(1)
    @tag("stress", "external")
    def ai_insight(self):
        """AI insight request (expensive)."""
        symbol = random.choice(STOCK_SYMBOLS)
        self.client.post(
            "/api/v2/ai/insight",
            headers=self.auth_headers,
            json={"symbol": symbol},
            name="/api/v2/ai/insight [stress]"
        )


class StressLoadShape(LoadTestShape):
    """
    Stress load shape: Progressive increase until breaking point.

    Timeline:
    - Phase 1: 0-120s - Baseline (50 users)
    - Phase 2: 120-240s - Moderate load (200 users)
    - Phase 3: 240-360s - High load (500 users)
    - Phase 4: 360-480s - Extreme load (1000 users)
    - Phase 5: 480-600s - Breaking point (2000 users)
    - Phase 6: 600-720s - Recovery observation (500 users)
    """

    stages = [
        {"duration": 120, "users": 50, "spawn_rate": 5},
        {"duration": 240, "users": 200, "spawn_rate": 10},
        {"duration": 360, "users": 500, "spawn_rate": 20},
        {"duration": 480, "users": 1000, "spawn_rate": 30},
        {"duration": 600, "users": 2000, "spawn_rate": 50},
        {"duration": 720, "users": 500, "spawn_rate": 20},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        return None


class BreakingPointTracker:
    """Track when system starts failing."""

    def __init__(self):
        self.breaking_point_users = None
        self.breaking_point_time = None
        self.error_threshold = 0.05  # 5% error rate
        self.latency_threshold = 5000  # 5 seconds

    def check_breaking_point(self, environment):
        stats = environment.stats
        if stats.total.num_requests == 0:
            return

        error_rate = stats.total.fail_ratio
        avg_response = stats.total.avg_response_time

        if self.breaking_point_users is None:
            if error_rate > self.error_threshold or avg_response > self.latency_threshold:
                self.breaking_point_users = environment.runner.user_count
                self.breaking_point_time = datetime.now()
                print(f"\n{'='*60}")
                print(f"BREAKING POINT DETECTED!")
                print(f"Users: {self.breaking_point_users}")
                print(f"Error rate: {error_rate*100:.2f}%")
                print(f"Avg response time: {avg_response:.2f}ms")
                print(f"{'='*60}\n")


tracker = BreakingPointTracker()


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Track metrics per request."""
    if exception:
        print(f"[STRESS] Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("=" * 60)
    print("STRESS TEST: Finding System Breaking Points")
    print(f"Target host: {environment.host}")
    print("Phases:")
    print("  Phase 1 (0-2min):   Baseline - 50 users")
    print("  Phase 2 (2-4min):   Moderate - 200 users")
    print("  Phase 3 (4-6min):   High - 500 users")
    print("  Phase 4 (6-8min):   Extreme - 1000 users")
    print("  Phase 5 (8-10min):  Breaking point - 2000 users")
    print("  Phase 6 (10-12min): Recovery - 500 users")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("=" * 60)
    print("STRESS TEST COMPLETE")
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Failure rate: {stats.total.fail_ratio * 100:.2f}%")
    if stats.total.num_requests > 0:
        print(f"Avg response time: {stats.total.avg_response_time:.2f}ms")
        print(f"Max response time: {stats.total.max_response_time:.2f}ms")
        print(f"50th percentile: {stats.total.get_response_time_percentile(0.50):.2f}ms")
        print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
        print(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")

    if tracker.breaking_point_users:
        print(f"\nBREAKING POINT: {tracker.breaking_point_users} users")
    else:
        print("\nNo breaking point detected - system handled full load!")
    print("=" * 60)
