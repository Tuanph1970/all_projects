"""
Configuration for Locust load tests.

Contains service URLs, test parameters, and thresholds.
"""

import os
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ServiceConfig:
    """Configuration for a single service."""
    name: str
    base_url: str
    health_endpoint: str = "/health/live"
    weight: int = 1  # Relative weight for user distribution


# Service configurations
SERVICES = {
    "auth": ServiceConfig(
        name="auth-service",
        base_url=os.getenv("AUTH_SERVICE_URL", "http://localhost:8007"),
        weight=2
    ),
    "stock-data": ServiceConfig(
        name="stock-data-service",
        base_url=os.getenv("STOCK_DATA_SERVICE_URL", "http://localhost:8001"),
        weight=5
    ),
    "portfolio": ServiceConfig(
        name="portfolio-service",
        base_url=os.getenv("PORTFOLIO_SERVICE_URL", "http://localhost:8003"),
        weight=3
    ),
    "prediction": ServiceConfig(
        name="prediction-service",
        base_url=os.getenv("PREDICTION_SERVICE_URL", "http://localhost:8002"),
        weight=1
    ),
    "analysis": ServiceConfig(
        name="analysis-service",
        base_url=os.getenv("ANALYSIS_SERVICE_URL", "http://localhost:8004"),
        weight=3
    ),
    "ai-insights": ServiceConfig(
        name="ai-insights-service",
        base_url=os.getenv("AI_INSIGHTS_SERVICE_URL", "http://localhost:8005"),
        weight=1
    ),
    "chatbot": ServiceConfig(
        name="chatbot-service",
        base_url=os.getenv("CHATBOT_SERVICE_URL", "http://localhost:8006"),
        weight=1
    ),
}

# Test data
STOCK_SYMBOLS = [
    "VNM", "FPT", "VIC", "VHM", "HPG", "MWG", "TCB", "VCB", "BID", "CTG",
    "VPB", "MBB", "ACB", "STB", "SHB", "VRE", "NVL", "DIG", "KDH", "DXG"
]

# Performance thresholds (in milliseconds)
THRESHOLDS = {
    "health_check": {
        "p50": 50,
        "p95": 100,
        "p99": 200
    },
    "auth_login": {
        "p50": 200,
        "p95": 500,
        "p99": 1000
    },
    "stock_list": {
        "p50": 100,
        "p95": 300,
        "p99": 500
    },
    "stock_detail": {
        "p50": 100,
        "p95": 250,
        "p99": 500
    },
    "portfolio_summary": {
        "p50": 150,
        "p95": 400,
        "p99": 800
    },
    "analysis": {
        "p50": 300,
        "p95": 800,
        "p99": 1500
    },
    "prediction": {
        "p50": 500,
        "p95": 2000,
        "p99": 5000
    }
}

# Load test scenarios
@dataclass
class LoadScenario:
    """Load test scenario configuration."""
    name: str
    users: int
    spawn_rate: float
    run_time: str
    description: str


SCENARIOS = {
    "smoke": LoadScenario(
        name="smoke",
        users=5,
        spawn_rate=1,
        run_time="1m",
        description="Quick smoke test to verify basic functionality"
    ),
    "load": LoadScenario(
        name="load",
        users=50,
        spawn_rate=5,
        run_time="5m",
        description="Normal load test simulating typical usage"
    ),
    "stress": LoadScenario(
        name="stress",
        users=200,
        spawn_rate=10,
        run_time="10m",
        description="Stress test to find breaking points"
    ),
    "spike": LoadScenario(
        name="spike",
        users=500,
        spawn_rate=50,
        run_time="5m",
        description="Spike test simulating sudden traffic surge"
    ),
    "soak": LoadScenario(
        name="soak",
        users=30,
        spawn_rate=2,
        run_time="30m",
        description="Soak test for memory leaks and stability"
    ),
    "breakpoint": LoadScenario(
        name="breakpoint",
        users=1000,
        spawn_rate=20,
        run_time="15m",
        description="Find the system's breaking point"
    )
}

# Test user credentials
TEST_USER = {
    "username": os.getenv("LOAD_TEST_USER", "loadtest_user"),
    "email": os.getenv("LOAD_TEST_EMAIL", "loadtest@test.com"),
    "password": os.getenv("LOAD_TEST_PASSWORD", "LoadTest123!")
}
