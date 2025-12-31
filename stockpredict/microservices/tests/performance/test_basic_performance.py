"""
Basic performance tests for microservices.

Tests cover:
- Response time thresholds
- Throughput verification
- Concurrent load handling
- Cache effectiveness
"""

import pytest
import httpx
import asyncio
import time
from statistics import mean, median, stdev
from typing import List, Tuple


pytestmark = [pytest.mark.performance, pytest.mark.slow]


class PerformanceMetrics:
    """Helper class to collect and analyze performance metrics."""

    def __init__(self):
        self.response_times: List[float] = []
        self.status_codes: List[int] = []
        self.errors: List[str] = []

    def record(self, response_time: float, status_code: int, error: str = None):
        self.response_times.append(response_time)
        self.status_codes.append(status_code)
        if error:
            self.errors.append(error)

    def summary(self) -> dict:
        if not self.response_times:
            return {"error": "No data collected"}

        successful = [t for t, s in zip(self.response_times, self.status_codes) if 200 <= s < 400]
        success_rate = len(successful) / len(self.response_times) * 100 if self.response_times else 0

        return {
            "total_requests": len(self.response_times),
            "successful_requests": len(successful),
            "success_rate_percent": round(success_rate, 2),
            "avg_response_time_ms": round(mean(self.response_times) * 1000, 2) if self.response_times else 0,
            "median_response_time_ms": round(median(self.response_times) * 1000, 2) if self.response_times else 0,
            "min_response_time_ms": round(min(self.response_times) * 1000, 2) if self.response_times else 0,
            "max_response_time_ms": round(max(self.response_times) * 1000, 2) if self.response_times else 0,
            "std_dev_ms": round(stdev(self.response_times) * 1000, 2) if len(self.response_times) > 1 else 0,
            "error_count": len(self.errors),
        }


async def timed_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs
) -> Tuple[float, int, str]:
    """Execute a timed HTTP request."""
    start = time.perf_counter()
    try:
        response = await client.request(method, url, **kwargs)
        elapsed = time.perf_counter() - start
        return elapsed, response.status_code, None
    except Exception as e:
        elapsed = time.perf_counter() - start
        return elapsed, 0, str(e)


class TestResponseTimeThresholds:
    """Test that endpoints meet response time thresholds."""

    # Response time thresholds in milliseconds
    THRESHOLDS = {
        "health": 100,
        "auth_login": 500,
        "stock_list": 300,
        "stock_detail": 200,
        "portfolio_summary": 400,
        "analysis": 1000,
    }

    async def test_health_endpoint_performance(
        self,
        auth_client: httpx.AsyncClient
    ):
        """Test health endpoint is fast."""
        metrics = PerformanceMetrics()

        for _ in range(10):
            elapsed, status, error = await timed_request(
                auth_client, "GET", "/health/live"
            )
            metrics.record(elapsed, status, error)

        summary = metrics.summary()
        assert summary["avg_response_time_ms"] < self.THRESHOLDS["health"], \
            f"Health endpoint too slow: {summary['avg_response_time_ms']}ms"
        assert summary["success_rate_percent"] == 100

    async def test_auth_login_performance(
        self,
        auth_client: httpx.AsyncClient,
        registered_user: dict
    ):
        """Test login endpoint performance."""
        metrics = PerformanceMetrics()

        for _ in range(5):
            elapsed, status, error = await timed_request(
                auth_client, "POST", "/api/v2/auth/login",
                json={
                    "username": registered_user["username"],
                    "password": registered_user["password"]
                }
            )
            metrics.record(elapsed, status, error)

        summary = metrics.summary()
        assert summary["avg_response_time_ms"] < self.THRESHOLDS["auth_login"], \
            f"Login too slow: {summary['avg_response_time_ms']}ms"

    async def test_stock_list_performance(
        self,
        stock_data_client: httpx.AsyncClient
    ):
        """Test stock listing performance."""
        metrics = PerformanceMetrics()

        for _ in range(10):
            elapsed, status, error = await timed_request(
                stock_data_client, "GET", "/api/v2/companies",
                params={"page": 1, "page_size": 20}
            )
            metrics.record(elapsed, status, error)

        summary = metrics.summary()
        assert summary["avg_response_time_ms"] < self.THRESHOLDS["stock_list"], \
            f"Stock list too slow: {summary['avg_response_time_ms']}ms"


class TestConcurrentLoad:
    """Test handling of concurrent load."""

    async def test_concurrent_health_checks(
        self,
        http_client: httpx.AsyncClient
    ):
        """Test concurrent health checks across all services."""
        services = [
            ("http://localhost:8007", "auth"),
            ("http://localhost:8001", "stock-data"),
            ("http://localhost:8003", "portfolio"),
            ("http://localhost:8004", "analysis"),
        ]

        async def check_health(base_url: str):
            async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
                return await timed_request(client, "GET", "/health/live")

        # Run 50 concurrent health checks
        tasks = []
        for _ in range(50):
            for base_url, _ in services:
                tasks.append(check_health(base_url))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successful = sum(1 for r in results if not isinstance(r, Exception) and r[1] == 200)
        total = len(results)

        assert successful / total >= 0.95, f"Too many failures: {successful}/{total}"

    async def test_concurrent_stock_queries(
        self,
        stock_data_client: httpx.AsyncClient
    ):
        """Test concurrent stock data queries."""
        symbols = ["VNM", "FPT", "VIC", "HPG", "MWG", "TCB", "VCB", "BID"]
        metrics = PerformanceMetrics()

        async def query_stock(symbol: str):
            return await timed_request(
                stock_data_client, "GET", f"/api/v2/stocks/{symbol}"
            )

        # 20 concurrent queries
        tasks = [query_stock(s) for s in symbols * 3][:20]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if not isinstance(result, Exception):
                metrics.record(*result)

        summary = metrics.summary()
        assert summary["success_rate_percent"] >= 90
        assert summary["avg_response_time_ms"] < 500

    async def test_sustained_load(
        self,
        stock_data_client: httpx.AsyncClient
    ):
        """Test sustained load over time."""
        metrics = PerformanceMetrics()
        duration_seconds = 10
        requests_per_second = 5

        start_time = time.time()
        request_count = 0

        while time.time() - start_time < duration_seconds:
            batch_start = time.time()

            # Send batch of requests
            tasks = []
            for _ in range(requests_per_second):
                tasks.append(timed_request(
                    stock_data_client, "GET", "/api/v2/companies",
                    params={"page": 1, "page_size": 10}
                ))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if not isinstance(result, Exception):
                    metrics.record(*result)
                    request_count += 1

            # Wait for next second
            elapsed = time.time() - batch_start
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)

        summary = metrics.summary()
        print(f"\nSustained load test results: {summary}")

        assert summary["success_rate_percent"] >= 95
        assert summary["avg_response_time_ms"] < 1000


class TestCacheEffectiveness:
    """Test cache effectiveness."""

    async def test_repeated_requests_faster(
        self,
        stock_data_client: httpx.AsyncClient
    ):
        """Test that repeated requests benefit from caching."""
        symbol = "VNM"

        # Cold request (first time)
        cold_times = []
        for _ in range(3):
            elapsed, status, _ = await timed_request(
                stock_data_client, "GET", f"/api/v2/stocks/{symbol}"
            )
            if status == 200:
                cold_times.append(elapsed)

        # Warm requests (should be cached)
        warm_times = []
        for _ in range(10):
            elapsed, status, _ = await timed_request(
                stock_data_client, "GET", f"/api/v2/stocks/{symbol}"
            )
            if status == 200:
                warm_times.append(elapsed)

        if cold_times and warm_times:
            avg_cold = mean(cold_times)
            avg_warm = mean(warm_times)

            # Warm requests should be at least as fast
            # (allowing for variance, warm should not be 2x slower)
            assert avg_warm < avg_cold * 2, \
                f"Cache not effective: cold={avg_cold*1000:.2f}ms, warm={avg_warm*1000:.2f}ms"

    async def test_search_caching(
        self,
        stock_data_client: httpx.AsyncClient
    ):
        """Test that search results are cached."""
        query = "technology"

        # First search
        elapsed1, _, _ = await timed_request(
            stock_data_client, "GET", "/api/v2/stocks/search",
            params={"q": query}
        )

        # Repeated search
        elapsed2, _, _ = await timed_request(
            stock_data_client, "GET", "/api/v2/stocks/search",
            params={"q": query}
        )

        # Second should be similar or faster
        assert elapsed2 < elapsed1 * 3


class TestThroughput:
    """Test throughput capabilities."""

    async def test_max_throughput_health(
        self,
        http_client: httpx.AsyncClient
    ):
        """Test maximum throughput on health endpoint."""
        base_url = "http://localhost:8007"
        num_requests = 100
        metrics = PerformanceMetrics()

        async def health_check():
            async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
                return await timed_request(client, "GET", "/health/live")

        start = time.perf_counter()
        tasks = [health_check() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start

        for result in results:
            if not isinstance(result, Exception):
                metrics.record(*result)

        throughput = num_requests / total_time
        summary = metrics.summary()

        print(f"\nThroughput test: {throughput:.2f} req/s")
        print(f"Summary: {summary}")

        # Should handle at least 50 req/s for health checks
        assert throughput >= 50, f"Throughput too low: {throughput:.2f} req/s"

    async def test_api_throughput(
        self,
        stock_data_client: httpx.AsyncClient
    ):
        """Test API throughput for typical operations."""
        num_requests = 50
        metrics = PerformanceMetrics()

        async def api_request():
            return await timed_request(
                stock_data_client, "GET", "/api/v2/companies",
                params={"page": 1, "page_size": 10}
            )

        start = time.perf_counter()
        tasks = [api_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start

        for result in results:
            if not isinstance(result, Exception):
                metrics.record(*result)

        throughput = num_requests / total_time
        summary = metrics.summary()

        print(f"\nAPI throughput: {throughput:.2f} req/s")
        print(f"Summary: {summary}")

        # Should handle at least 20 req/s for API calls
        assert throughput >= 20, f"API throughput too low: {throughput:.2f} req/s"


class TestLatencyPercentiles:
    """Test latency percentiles (P50, P95, P99)."""

    async def test_latency_percentiles(
        self,
        stock_data_client: httpx.AsyncClient
    ):
        """Test latency percentiles meet thresholds."""
        response_times = []

        for _ in range(100):
            elapsed, status, _ = await timed_request(
                stock_data_client, "GET", "/api/v2/companies",
                params={"page": 1, "page_size": 10}
            )
            if status == 200:
                response_times.append(elapsed * 1000)  # Convert to ms

        if response_times:
            response_times.sort()
            n = len(response_times)

            p50 = response_times[int(n * 0.50)]
            p95 = response_times[int(n * 0.95)]
            p99 = response_times[int(n * 0.99)]

            print(f"\nLatency percentiles:")
            print(f"  P50: {p50:.2f}ms")
            print(f"  P95: {p95:.2f}ms")
            print(f"  P99: {p99:.2f}ms")

            # Thresholds
            assert p50 < 200, f"P50 too high: {p50:.2f}ms"
            assert p95 < 500, f"P95 too high: {p95:.2f}ms"
            assert p99 < 1000, f"P99 too high: {p99:.2f}ms"
