"""Phase 3.5 performance SLA tests.

Target (PHASE3_IMPLEMENTATION_PLAN.md §3.5.2):
    p50 ≤  50ms, p95 ≤ 150ms, p99 ≤ 300ms  — Tier-2 core APIs
    health endpoints: p99 ≤ 100ms

All tests require a running stack (``./deploy.sh`` or docker-compose up).
Run via:  ./scripts/run-tests.sh --performance
Skipped automatically when services are unreachable.
"""
from __future__ import annotations

import asyncio
import time
from statistics import mean, median
from typing import List, Tuple

import httpx
import pytest

pytestmark = [pytest.mark.performance, pytest.mark.slow]

# ── Phase 3.5 SLA constants ───────────────────────────────────────────────────
# Primary gate — every core API endpoint must meet these.
P50_CORE_MS = 50
P95_CORE_MS = 150
P99_CORE_MS = 300        # THE Phase 3.5 p99 target

# Health probes are tighter.
P99_HEALTH_MS = 100

# Analysis/screener tier (heavier DB queries).
P99_ANALYSIS_MS = 1000

# Throughput targets (req/s under concurrent load).
THROUGHPUT_HEALTH_RPS = 200   # health probes
THROUGHPUT_API_RPS    = 50    # typical API read

N_SAMPLES = 100   # requests per endpoint for percentile stability


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _timed(
    client: httpx.AsyncClient, method: str, url: str, **kw
) -> Tuple[float, int]:
    t0 = time.perf_counter()
    try:
        r = await client.request(method, url, **kw)
        return (time.perf_counter() - t0) * 1000, r.status_code
    except Exception:
        return (time.perf_counter() - t0) * 1000, 0


def _percentile(times: List[float], pct: int) -> float:
    s = sorted(times)
    idx = max(0, int(len(s) * pct / 100) - 1)
    return s[idx]


async def _collect(
    client: httpx.AsyncClient, method: str, url: str,
    n: int = N_SAMPLES, **kw
) -> dict:
    tasks = [_timed(client, method, url, **kw) for _ in range(n)]
    results = await asyncio.gather(*tasks)
    times = [t for t, _ in results]
    codes = [c for _, c in results]
    success = sum(1 for c in codes if 200 <= c < 400)
    return {
        "p50":  _percentile(times, 50),
        "p95":  _percentile(times, 95),
        "p99":  _percentile(times, 99),
        "mean": mean(times),
        "min":  min(times),
        "max":  max(times),
        "success_rate": success / n * 100,
        "n": n,
    }


# ── Health endpoint SLA ───────────────────────────────────────────────────────

class TestHealthSLA:
    """T1: Health probes — p99 ≤ 100ms."""

    async def test_auth_health_p99(self, auth_client: httpx.AsyncClient):
        m = await _collect(auth_client, "GET", "/health/live", n=N_SAMPLES)
        print(f"\nauth /health/live — p50={m['p50']:.1f} p95={m['p95']:.1f} p99={m['p99']:.1f} ms")
        assert m["p99"] <= P99_HEALTH_MS, (
            f"auth /health p99={m['p99']:.1f}ms > SLA {P99_HEALTH_MS}ms"
        )
        assert m["success_rate"] >= 99.9

    async def test_stock_data_health_p99(self, stock_data_client: httpx.AsyncClient):
        m = await _collect(stock_data_client, "GET", "/health/live", n=N_SAMPLES)
        print(f"\nstock-data /health/live — p50={m['p50']:.1f} p95={m['p95']:.1f} p99={m['p99']:.1f} ms")
        assert m["p99"] <= P99_HEALTH_MS, (
            f"stock-data /health p99={m['p99']:.1f}ms > SLA {P99_HEALTH_MS}ms"
        )

    async def test_portfolio_health_p99(self, portfolio_client: httpx.AsyncClient):
        m = await _collect(portfolio_client, "GET", "/health/live", n=N_SAMPLES)
        print(f"\nportfolio /health/live — p50={m['p50']:.1f} p95={m['p95']:.1f} p99={m['p99']:.1f} ms")
        assert m["p99"] <= P99_HEALTH_MS


# ── Core API SLA (p99 ≤ 300ms) ───────────────────────────────────────────────

class TestCoreAPISLA:
    """T2: Core read APIs — p99 ≤ 300ms (Phase 3.5 primary target)."""

    async def test_companies_list_p99(self, stock_data_client: httpx.AsyncClient):
        m = await _collect(
            stock_data_client, "GET",
            "/stock_helper/api/v2/companies",
            n=N_SAMPLES, params={"page": 1, "page_size": 20},
        )
        print(f"\nGET /companies — p50={m['p50']:.1f} p95={m['p95']:.1f} p99={m['p99']:.1f} ms")
        assert m["p99"] <= P99_CORE_MS, (
            f"/companies p99={m['p99']:.1f}ms > Phase 3.5 SLA {P99_CORE_MS}ms"
        )

    async def test_stock_detail_p99(self, stock_data_client: httpx.AsyncClient):
        m = await _collect(
            stock_data_client, "GET",
            "/stock_helper/api/v2/stocks/VNM",
            n=N_SAMPLES,
        )
        print(f"\nGET /stocks/VNM — p50={m['p50']:.1f} p95={m['p95']:.1f} p99={m['p99']:.1f} ms")
        assert m["p99"] <= P99_CORE_MS, (
            f"/stocks/{{symbol}} p99={m['p99']:.1f}ms > Phase 3.5 SLA {P99_CORE_MS}ms"
        )

    async def test_auth_login_p99(
        self,
        auth_client: httpx.AsyncClient,
        registered_user: dict,
    ):
        m = await _collect(
            auth_client, "POST",
            "/stock_helper/api/v2/auth/login",
            n=20,   # fewer — auth is stateful
            json={"username": registered_user["username"],
                  "password": registered_user["password"]},
        )
        print(f"\nPOST /auth/login — p50={m['p50']:.1f} p95={m['p95']:.1f} p99={m['p99']:.1f} ms")
        assert m["p99"] <= P99_CORE_MS, (
            f"/auth/login p99={m['p99']:.1f}ms > Phase 3.5 SLA {P99_CORE_MS}ms"
        )


# ── Concurrent load (p99 ≤ 300ms under 50 concurrent users) ──────────────────

class TestConcurrentSLA:
    """T2 under concurrency: p99 still ≤ 300ms with 50 simultaneous requests."""

    async def test_companies_concurrent_p99(self, stock_data_client: httpx.AsyncClient):
        tasks = [
            _timed(
                stock_data_client, "GET",
                "/stock_helper/api/v2/companies",
                params={"page": 1, "page_size": 10},
            )
            for _ in range(50)
        ]
        results = await asyncio.gather(*tasks)
        times = [t for t, _ in results]
        codes = [c for _, c in results]

        p99 = _percentile(times, 99)
        success_rate = sum(1 for c in codes if 200 <= c < 400) / len(codes) * 100
        print(f"\n50-concurrent /companies — p99={p99:.1f}ms  success={success_rate:.1f}%")

        assert p99 <= P99_CORE_MS, (
            f"p99={p99:.1f}ms under 50-user concurrency > SLA {P99_CORE_MS}ms"
        )
        assert success_rate >= 99.0


# ── Throughput targets ────────────────────────────────────────────────────────

class TestThroughput:
    """Throughput targets from Phase 3.5: stock-data ≥ 50 req/s for typical reads."""

    async def test_stock_data_throughput(self, stock_data_client: httpx.AsyncClient):
        n = 100
        t0 = time.perf_counter()
        tasks = [
            _timed(
                stock_data_client, "GET",
                "/stock_helper/api/v2/companies",
                params={"page": 1, "page_size": 10},
            )
            for _ in range(n)
        ]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - t0
        rps = n / elapsed
        success = sum(1 for _, c in results if 200 <= c < 400)

        print(f"\nThroughput /companies: {rps:.1f} req/s  ({success}/{n} successful)")
        assert rps >= THROUGHPUT_API_RPS, (
            f"stock-data throughput {rps:.1f} req/s < target {THROUGHPUT_API_RPS} req/s"
        )

    async def test_health_throughput(self, auth_client: httpx.AsyncClient):
        n = 200
        t0 = time.perf_counter()
        tasks = [_timed(auth_client, "GET", "/health/live") for _ in range(n)]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - t0
        rps = n / elapsed

        print(f"\nThroughput /health/live: {rps:.1f} req/s")
        assert rps >= THROUGHPUT_HEALTH_RPS, (
            f"health throughput {rps:.1f} req/s < target {THROUGHPUT_HEALTH_RPS} req/s"
        )


# ── Analysis tier (p99 ≤ 1000ms) ─────────────────────────────────────────────

class TestAnalysisSLA:
    """T3: Analysis endpoints — heavier DB queries, p99 ≤ 1000ms."""

    async def test_technical_analysis_p99(
        self,
        analysis_client: httpx.AsyncClient,
        auth_token: str,
    ):
        m = await _collect(
            analysis_client, "GET",
            "/stock_helper/api/v2/analysis/technical/VNM",
            n=30,
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        print(f"\nGET /analysis/technical/VNM — p99={m['p99']:.1f}ms")
        assert m["p99"] <= P99_ANALYSIS_MS, (
            f"technical analysis p99={m['p99']:.1f}ms > SLA {P99_ANALYSIS_MS}ms"
        )
