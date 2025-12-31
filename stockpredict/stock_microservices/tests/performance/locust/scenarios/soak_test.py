"""
Soak test scenario for Stock Helper microservices.

Long-running test to detect memory leaks, resource exhaustion, and stability issues.

Run with:
    locust -f scenarios/soak_test.py --host=http://localhost --run-time=30m
"""

import random
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass, field

from locust import HttpUser, task, between, events, tag, LoadTestShape
from locust.runners import MasterRunner

import sys
sys.path.append('..')
from config import STOCK_SYMBOLS, TEST_USER


@dataclass
class SoakMetrics:
    """Track soak test metrics over time."""

    start_time: datetime = field(default_factory=datetime.now)
    samples: List[Dict] = field(default_factory=list)
    memory_warnings: int = 0
    performance_degradation_points: List[datetime] = field(default_factory=list)

    def add_sample(self, environment):
        stats = environment.stats
        if stats.total.num_requests == 0:
            return

        sample = {
            "timestamp": datetime.now(),
            "elapsed_minutes": (datetime.now() - self.start_time).total_seconds() / 60,
            "requests": stats.total.num_requests,
            "failures": stats.total.num_failures,
            "avg_response_time": stats.total.avg_response_time,
            "p95_response_time": stats.total.get_response_time_percentile(0.95),
            "user_count": environment.runner.user_count if environment.runner else 0,
        }
        self.samples.append(sample)

        # Check for degradation
        if len(self.samples) > 10:
            recent_avg = sum(s["avg_response_time"] for s in self.samples[-5:]) / 5
            earlier_avg = sum(s["avg_response_time"] for s in self.samples[:5]) / 5

            if recent_avg > earlier_avg * 1.5:  # 50% degradation
                self.performance_degradation_points.append(datetime.now())

    def report(self):
        if not self.samples:
            return "No samples collected"

        duration = (datetime.now() - self.start_time).total_seconds() / 60

        report_lines = [
            "=" * 60,
            "SOAK TEST METRICS REPORT",
            "=" * 60,
            f"Duration: {duration:.1f} minutes",
            f"Samples collected: {len(self.samples)}",
            "",
            "Response Time Trend:",
        ]

        # Show response time trend
        for i in range(0, len(self.samples), max(1, len(self.samples) // 10)):
            sample = self.samples[i]
            report_lines.append(
                f"  {sample['elapsed_minutes']:.1f}min: "
                f"avg={sample['avg_response_time']:.0f}ms, "
                f"p95={sample['p95_response_time']:.0f}ms"
            )

        if self.performance_degradation_points:
            report_lines.append("")
            report_lines.append(f"Degradation detected at: {len(self.performance_degradation_points)} points")

        report_lines.append("=" * 60)
        return "\n".join(report_lines)


soak_metrics = SoakMetrics()


class SoakUser(HttpUser):
    """User behavior for soak testing - realistic, sustained load."""

    wait_time = between(2, 5)  # Realistic wait times

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token: Optional[str] = None
        self.session_start = datetime.now()
        self.actions_performed = 0

    def on_start(self):
        """Initialize long-running user session."""
        self._authenticate()

    def _authenticate(self):
        """Establish session."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        username = f"soak_{timestamp}"

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

    def _maybe_refresh_token(self):
        """Periodically refresh token to test token management."""
        session_age = (datetime.now() - self.session_start).total_seconds()
        if session_age > 600 and self.actions_performed % 50 == 0:  # Every 50 actions after 10 min
            self.client.post(
                "/api/v2/auth/refresh",
                headers=self.auth_headers,
                name="/api/v2/auth/refresh [soak]"
            )

    # Realistic user journey tasks
    @task(10)
    @tag("soak", "browse")
    def browse_companies(self):
        """Normal browsing behavior."""
        self.actions_performed += 1
        self._maybe_refresh_token()

        page = random.randint(1, 20)
        self.client.get(
            "/api/v2/companies",
            params={"page": page, "page_size": 20},
            name="/api/v2/companies [soak]"
        )

    @task(8)
    @tag("soak", "browse")
    def view_stock_detail(self):
        """View individual stock."""
        self.actions_performed += 1
        symbol = random.choice(STOCK_SYMBOLS)

        # Typical user flow: view stock then check history
        self.client.get(
            f"/api/v2/stocks/{symbol}",
            name="/api/v2/stocks/[symbol] [soak]"
        )

        if random.random() < 0.3:  # 30% also check history
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            self.client.get(
                f"/api/v2/stocks/{symbol}/history",
                params={
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                },
                name="/api/v2/stocks/history [soak]"
            )

    @task(6)
    @tag("soak", "search")
    def search_and_explore(self):
        """Search and explore results."""
        self.actions_performed += 1
        queries = ["bank", "tech", "food", "real estate", "manufacturing"]

        self.client.get(
            "/api/v2/stocks/search",
            params={"q": random.choice(queries)},
            name="/api/v2/stocks/search [soak]"
        )

    @task(5)
    @tag("soak", "portfolio")
    def check_portfolio(self):
        """Regular portfolio check."""
        self.actions_performed += 1

        self.client.get(
            "/api/v2/portfolio",
            headers=self.auth_headers,
            name="/api/v2/portfolio [soak]"
        )

        if random.random() < 0.5:
            self.client.get(
                "/api/v2/portfolio/summary",
                headers=self.auth_headers,
                name="/api/v2/portfolio/summary [soak]"
            )

    @task(3)
    @tag("soak", "analysis")
    def run_analysis(self):
        """Technical analysis."""
        self.actions_performed += 1
        symbol = random.choice(STOCK_SYMBOLS)

        self.client.get(
            f"/api/v2/analysis/technical/{symbol}",
            name="/api/v2/analysis/technical [soak]"
        )

    @task(2)
    @tag("soak", "trade")
    def make_transaction(self):
        """Occasional trade."""
        self.actions_performed += 1
        symbol = random.choice(STOCK_SYMBOLS)

        self.client.post(
            "/api/v2/portfolio/transactions",
            headers=self.auth_headers,
            json={
                "symbol": symbol,
                "type": random.choice(["buy", "sell"]),
                "quantity": random.randint(10, 100),
                "price": random.uniform(20000, 80000)
            },
            name="/api/v2/portfolio/transactions [soak]"
        )

    @task(2)
    @tag("soak", "market")
    def check_market(self):
        """Market overview."""
        self.actions_performed += 1

        self.client.get("/api/v2/market/indices", name="/api/v2/market/indices [soak]")

        endpoint = random.choice(["top-gainers", "top-losers", "top-actives"])
        self.client.get(
            f"/api/v2/companies/{endpoint}",
            name=f"/api/v2/companies/movers [soak]"
        )

    @task(1)
    @tag("soak", "alerts")
    def manage_alerts(self):
        """Alert management."""
        self.actions_performed += 1

        self.client.get(
            "/api/v2/alerts",
            headers=self.auth_headers,
            name="/api/v2/alerts [soak]"
        )

        if random.random() < 0.3:
            symbol = random.choice(STOCK_SYMBOLS)
            self.client.post(
                "/api/v2/alerts",
                headers=self.auth_headers,
                json={
                    "symbol": symbol,
                    "target_price": random.uniform(40000, 100000),
                    "condition": random.choice(["above", "below"])
                },
                name="/api/v2/alerts/create [soak]"
            )


class SoakLoadShape(LoadTestShape):
    """
    Soak load shape: Sustained moderate load for extended period.

    Timeline (30 minutes):
    - 0-2min: Gradual ramp up to 30 users
    - 2-28min: Sustained load at 30 users
    - 28-30min: Gradual ramp down
    """

    def tick(self):
        run_time = self.get_run_time()

        if run_time < 120:  # First 2 minutes - ramp up
            user_count = int(30 * (run_time / 120))
            return (max(1, user_count), 1)
        elif run_time < 1680:  # Minutes 2-28 - sustained
            return (30, 1)
        elif run_time < 1800:  # Last 2 minutes - ramp down
            remaining = 1800 - run_time
            user_count = int(30 * (remaining / 120))
            return (max(1, user_count), 1)

        return None


# Periodic metrics collection
last_sample_time = 0


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    global last_sample_time

    current_time = time.time()
    if current_time - last_sample_time > 60:  # Sample every minute
        if hasattr(context, 'environment'):
            soak_metrics.add_sample(context.environment)
        last_sample_time = current_time


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    global soak_metrics
    soak_metrics = SoakMetrics()

    print("=" * 60)
    print("SOAK TEST: Long-Running Stability Test")
    print(f"Target host: {environment.host}")
    print("Purpose: Detect memory leaks, resource exhaustion, stability issues")
    print("Recommended duration: 30+ minutes")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    # Final sample
    soak_metrics.add_sample(environment)

    print(soak_metrics.report())

    stats = environment.stats
    print(f"\nFinal Statistics:")
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Failure rate: {stats.total.fail_ratio * 100:.2f}%")
    if stats.total.num_requests > 0:
        print(f"Avg response time: {stats.total.avg_response_time:.2f}ms")
        print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print("=" * 60)
