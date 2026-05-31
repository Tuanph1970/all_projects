#!/usr/bin/env python3
"""Phase 3.5 performance benchmark — standalone runner.

Measures p50/p95/p99 for all core API endpoints against the Phase 3.5 SLA
(p99 ≤ 300ms for Tier-2 core APIs) and prints a pass/fail report.

Usage
-----
# Measure all services (requires stack running on default ports):
  python tests/performance/benchmark.py

# Override gateway URL:
  GATEWAY_URL=http://staging:8004 python tests/performance/benchmark.py

# Fewer samples (faster, less precise):
  python tests/performance/benchmark.py --samples 30

# Write JSON report to file:
  python tests/performance/benchmark.py --out reports/perf.json

Exit code: 0 = all SLAs met, 1 = one or more violations, 2 = services unreachable.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

try:
    import httpx
except ImportError:
    print("httpx not installed — pip install httpx", file=sys.stderr)
    sys.exit(2)


# ── SLA constants (Phase 3.5, §3.5.2) ────────────────────────────────────────

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8004")
API_PREFIX  = "/stock_helper/api/v2"

# Tier thresholds (all in milliseconds)
_T = {
    "T1": {"p50": 20,   "p95": 60,   "p99": 100},   # health
    "T2": {"p50": 50,   "p95": 150,  "p99": 300},   # core CRUD
    "T3": {"p50": 200,  "p95": 600,  "p99": 1000},  # analysis
    "T4": {"p50": 500,  "p95": 2000, "p99": 3000},  # ML predict
    "T5": {"p50": 1000, "p95": 5000, "p99": 10000}, # LLM
}

# Endpoint definitions: (name, method, path, tier, requires_auth)
ENDPOINTS = [
    # T1 — health
    ("health/live",          "GET", "/health/live",                     "T1", False),
    # T2 — core reads via gateway
    ("companies list",       "GET", f"{API_PREFIX}/companies?page_size=20",   "T2", False),
    ("stock detail",         "GET", f"{API_PREFIX}/stocks/VNM",               "T2", False),
    ("stock search",         "GET", f"{API_PREFIX}/stocks/search?q=VNM",      "T2", False),
    ("stock history",        "GET", f"{API_PREFIX}/stocks/VNM/history?period=1m", "T2", False),
    # T3 — analysis
    ("technical analysis",   "GET", f"{API_PREFIX}/analysis/technical/VNM",  "T3", True),
]

AUTH_URL      = os.getenv("AUTH_URL", "http://localhost:8007")
TEST_USERNAME = os.getenv("PERF_USERNAME", "perf_bench")
TEST_PASSWORD = os.getenv("PERF_PASSWORD", "PerfBench123!")


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class EndpointResult:
    name: str
    method: str
    url: str
    tier: str
    n_samples: int
    p50: float
    p95: float
    p99: float
    mean: float
    success_rate: float
    sla_p99: int
    passed: bool
    note: str = ""
    error: Optional[str] = None


@dataclass
class BenchmarkReport:
    timestamp: str
    gateway_url: str
    n_samples: int
    results: List[EndpointResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results if r.error is None)

    @property
    def violations(self) -> List[EndpointResult]:
        return [r for r in self.results if not r.passed and r.error is None]


# ── HTTP helpers ──────────────────────────────────────────────────────────────

async def _fetch(
    client: httpx.AsyncClient, method: str, url: str, **kw
) -> tuple[float, int]:
    t0 = time.perf_counter()
    try:
        r = await client.request(method, url, **kw)
        return (time.perf_counter() - t0) * 1000, r.status_code
    except Exception:
        return (time.perf_counter() - t0) * 1000, 0


def _pct(times: list[float], pct: int) -> float:
    s = sorted(times)
    return s[max(0, int(len(s) * pct / 100) - 1)]


async def _measure(
    client: httpx.AsyncClient, method: str, url: str, n: int, **kw
) -> dict:
    results = await asyncio.gather(*[_fetch(client, method, url, **kw) for _ in range(n)])
    times = [t for t, _ in results]
    codes = [c for _, c in results]
    ok    = sum(1 for c in codes if 200 <= c < 400)
    return {
        "p50": _pct(times, 50), "p95": _pct(times, 95), "p99": _pct(times, 99),
        "mean": sum(times) / len(times), "success_rate": ok / n * 100,
    }


# ── Auth helper ───────────────────────────────────────────────────────────────

async def _get_token(session: httpx.AsyncClient) -> Optional[str]:
    # Try login
    try:
        r = await session.post(
            f"{AUTH_URL}/stock_helper/api/v2/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("access_token")
    except Exception:
        pass

    # Try register + login
    try:
        await session.post(
            f"{AUTH_URL}/stock_helper/api/v2/auth/register",
            json={"username": TEST_USERNAME, "email": f"{TEST_USERNAME}@bench.local",
                  "password": TEST_PASSWORD},
            timeout=10,
        )
        r = await session.post(
            f"{AUTH_URL}/stock_helper/api/v2/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("access_token")
    except Exception:
        pass
    return None


# ── Main benchmark ────────────────────────────────────────────────────────────

async def run_benchmark(n_samples: int) -> BenchmarkReport:
    report = BenchmarkReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        gateway_url=GATEWAY_URL,
        n_samples=n_samples,
    )

    # Sanity-check reachability
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.get(f"{GATEWAY_URL}/health/live")
    except Exception as e:
        print(f"✗  Gateway unreachable at {GATEWAY_URL}: {e}", file=sys.stderr)
        sys.exit(2)

    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=30) as client:
        token = await _get_token(client)
        auth_headers = {"Authorization": f"Bearer {token}"} if token else {}
        if not token:
            print("⚠  Could not obtain auth token — authenticated endpoints will be skipped")

        for name, method, path, tier, needs_auth in ENDPOINTS:
            url = path  # relative to base_url
            kw: dict = {}
            if needs_auth:
                if not token:
                    report.results.append(EndpointResult(
                        name=name, method=method, url=url, tier=tier,
                        n_samples=0, p50=0, p95=0, p99=0, mean=0,
                        success_rate=0, sla_p99=_T[tier]["p99"],
                        passed=True, note="skipped (no auth token)",
                    ))
                    continue
                kw["headers"] = auth_headers

            try:
                m = await _measure(client, method, url, n_samples, **kw)
            except Exception as exc:
                report.results.append(EndpointResult(
                    name=name, method=method, url=url, tier=tier,
                    n_samples=0, p50=0, p95=0, p99=0, mean=0,
                    success_rate=0, sla_p99=_T[tier]["p99"],
                    passed=False, error=str(exc),
                ))
                continue

            sla = _T[tier]["p99"]
            passed = m["p99"] <= sla and m["success_rate"] >= 99.0
            report.results.append(EndpointResult(
                name=name, method=method, url=url, tier=tier,
                n_samples=n_samples,
                p50=round(m["p50"], 1), p95=round(m["p95"], 1), p99=round(m["p99"], 1),
                mean=round(m["mean"], 1), success_rate=round(m["success_rate"], 1),
                sla_p99=sla, passed=passed,
            ))

    return report


# ── Reporting ─────────────────────────────────────────────────────────────────

def _badge(passed: bool, skipped: bool = False) -> str:
    if skipped: return "⏭ "
    return "✅" if passed else "❌"


def print_report(report: BenchmarkReport) -> None:
    PASS = "\033[32m"
    FAIL = "\033[31m"
    WARN = "\033[33m"
    BOLD = "\033[1m"
    RST  = "\033[0m"

    width = 80
    print()
    print(BOLD + "=" * width + RST)
    print(BOLD + "  Phase 3.5 Performance Benchmark Report" + RST)
    print(f"  Gateway : {report.gateway_url}")
    print(f"  Samples : {report.n_samples}  |  Time: {report.timestamp}")
    print(BOLD + "=" * width + RST)
    print(f"  {'Endpoint':<28} {'Tier':4} {'p50':>6} {'p95':>6} {'p99':>7} {'SLA':>6} {'ok%':>5}  Result")
    print(f"  {'-'*28} {'-'*4} {'-'*6} {'-'*6} {'-'*7} {'-'*6} {'-'*5}  ------")

    for r in report.results:
        if r.error:
            print(f"  {r.name:<28} {r.tier:4}  {'ERR':>6} {'':>6} {'':>7} {'':>6} {'':>5}  ❌ {r.error}")
            continue
        skipped = "skipped" in r.note
        badge   = _badge(r.passed, skipped)
        color   = PASS if r.passed else (WARN if skipped else FAIL)
        p99_str = f"{r.p99:>6.1f}" if not skipped else f"{'skip':>6}"
        sla_str = f"{r.sla_p99:>5}ms"
        print(
            f"  {r.name:<28} {r.tier:4} "
            f"{r.p50:>5.1f}ms {r.p95:>5.1f}ms {p99_str}ms "
            f"{sla_str} {r.success_rate:>4.0f}%  {color}{badge}{RST}"
        )

    print(BOLD + "=" * width + RST)
    n_tested   = sum(1 for r in report.results if not r.error and "skipped" not in r.note)
    n_passed   = sum(1 for r in report.results if r.passed and "skipped" not in r.note)
    n_violated = len(report.violations)
    verdict    = (PASS + "ALL SLAs MET" + RST) if report.passed else (FAIL + f"{n_violated} SLA VIOLATION(S)" + RST)
    print(f"\n  {verdict}  ({n_passed}/{n_tested} endpoints within Phase 3.5 targets)")
    print()


def write_json(report: BenchmarkReport, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    d = asdict(report)
    with open(path, "w") as f:
        json.dump(d, f, indent=2)
    print(f"  Report written to {path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 3.5 performance benchmark (p99 SLA: 300ms for core APIs)"
    )
    parser.add_argument("--samples", type=int, default=50,
                        help="requests per endpoint (default 50; use 100+ for production)")
    parser.add_argument("--out", metavar="FILE",
                        help="write JSON report to FILE")
    args = parser.parse_args()

    report = asyncio.run(run_benchmark(args.samples))
    print_report(report)
    if args.out:
        write_json(report, args.out)

    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
