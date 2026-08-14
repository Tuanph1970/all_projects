#!/usr/bin/env python3
"""
Mercai - Microservices Health Check Utility

Usage:
    python scripts/health_check.py [options]

Options:
    --json          Output in JSON format
    --verbose       Show detailed output
    --service NAME  Check specific service
    --timeout SEC   Request timeout (default: 5)
    --help          Show help message
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import httpx
except ImportError:
    print("Installing required package: httpx")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    name: str
    status: HealthStatus
    latency_ms: float
    message: Optional[str] = None
    details: Optional[Dict] = None
    checked_at: str = ""

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.utcnow().isoformat()


@dataclass
class HealthCheckResult:
    timestamp: str
    overall_status: HealthStatus
    total_services: int
    healthy_count: int
    unhealthy_count: int
    services: List[ServiceHealth]

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "overall_status": self.overall_status.value,
            "summary": {
                "total": self.total_services,
                "healthy": self.healthy_count,
                "unhealthy": self.unhealthy_count
            },
            "services": [
                {
                    "name": s.name,
                    "status": s.status.value,
                    "latency_ms": s.latency_ms,
                    "message": s.message,
                    "details": s.details
                }
                for s in self.services
            ]
        }


# Service configuration
SERVICES = {
    "auth": {
        "url": "http://auth-service:8001/health",
        "gateway_path": "/api/v1/auth",
        "description": "Authentication & User Management"
    },
    "product": {
        "url": "http://product-service:8002/health",
        "gateway_path": "/api/v1/products",
        "description": "Product Catalog & Search"
    },
    "order": {
        "url": "http://order-service:8003/health",
        "gateway_path": "/api/v1/orders",
        "description": "Order & Cart Management"
    },
    "chat": {
        "url": "http://chat-service:8004/health",
        "gateway_path": "/api/v1/chat",
        "description": "Real-time Messaging"
    },
    "seller": {
        "url": "http://seller-service:8005/health",
        "gateway_path": "/api/v1/seller",
        "description": "Seller Dashboard & Analytics"
    }
}

INFRASTRUCTURE = {
    "traefik": {
        "url": "http://traefik:8080/api/overview",
        "description": "API Gateway"
    },
    "redis": {
        "url": "http://redis:6379",
        "check_type": "tcp",
        "description": "Cache Service"
    },
    "mysql": {
        "url": "http://db:3306",
        "check_type": "tcp",
        "description": "Database"
    }
}


class HealthChecker:
    def __init__(self, timeout: float = 5.0, gateway_host: str = "localhost"):
        self.timeout = timeout
        self.gateway_host = gateway_host
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    async def check_http_health(self, name: str, url: str) -> ServiceHealth:
        """Check health via HTTP endpoint."""
        start_time = datetime.now()
        try:
            response = await self.client.get(url)
            latency = (datetime.now() - start_time).total_seconds() * 1000

            if response.status_code == 200:
                try:
                    data = response.json()
                    status = HealthStatus.HEALTHY if data.get("status") == "healthy" else HealthStatus.DEGRADED
                    return ServiceHealth(
                        name=name,
                        status=status,
                        latency_ms=round(latency, 2),
                        message="OK",
                        details=data
                    )
                except json.JSONDecodeError:
                    return ServiceHealth(
                        name=name,
                        status=HealthStatus.HEALTHY,
                        latency_ms=round(latency, 2),
                        message="OK (non-JSON response)"
                    )
            else:
                return ServiceHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=round(latency, 2),
                    message=f"HTTP {response.status_code}"
                )
        except httpx.ConnectError as e:
            latency = (datetime.now() - start_time).total_seconds() * 1000
            return ServiceHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=round(latency, 2),
                message=f"Connection failed: {str(e)}"
            )
        except httpx.TimeoutException:
            return ServiceHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=self.timeout * 1000,
                message="Timeout"
            )
        except Exception as e:
            latency = (datetime.now() - start_time).total_seconds() * 1000
            return ServiceHealth(
                name=name,
                status=HealthStatus.UNKNOWN,
                latency_ms=round(latency, 2),
                message=str(e)
            )

    async def check_gateway_endpoint(self, name: str, path: str) -> ServiceHealth:
        """Check service via API gateway."""
        url = f"http://{self.gateway_host}:80{path}"
        start_time = datetime.now()
        try:
            response = await self.client.get(url)
            latency = (datetime.now() - start_time).total_seconds() * 1000

            # Any response (even 401/403) means the service is reachable
            if response.status_code < 500:
                return ServiceHealth(
                    name=f"{name}_gateway",
                    status=HealthStatus.HEALTHY,
                    latency_ms=round(latency, 2),
                    message=f"HTTP {response.status_code}"
                )
            else:
                return ServiceHealth(
                    name=f"{name}_gateway",
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=round(latency, 2),
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            latency = (datetime.now() - start_time).total_seconds() * 1000
            return ServiceHealth(
                name=f"{name}_gateway",
                status=HealthStatus.UNHEALTHY,
                latency_ms=round(latency, 2),
                message=str(e)
            )

    async def check_all_services(self, service_filter: Optional[str] = None) -> HealthCheckResult:
        """Check all services and return results."""
        results: List[ServiceHealth] = []

        # Check microservices
        tasks = []
        for name, config in SERVICES.items():
            if service_filter and service_filter != name:
                continue
            tasks.append(self.check_http_health(name, config["url"]))

        if tasks:
            service_results = await asyncio.gather(*tasks)
            results.extend(service_results)

        # Calculate summary
        healthy_count = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        unhealthy_count = sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)

        if unhealthy_count == 0:
            overall = HealthStatus.HEALTHY
        elif healthy_count > 0:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.UNHEALTHY

        return HealthCheckResult(
            timestamp=datetime.utcnow().isoformat(),
            overall_status=overall,
            total_services=len(results),
            healthy_count=healthy_count,
            unhealthy_count=unhealthy_count,
            services=results
        )


def print_colored(text: str, color: str = "reset"):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "reset": "\033[0m",
        "bold": "\033[1m"
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")


def print_result(result: HealthCheckResult, verbose: bool = False):
    """Print health check results in human-readable format."""
    print()
    print_colored("=" * 60, "blue")
    print_colored("  MERCAI - HEALTH CHECK REPORT", "bold")
    print_colored("=" * 60, "blue")
    print()
    print(f"Timestamp: {result.timestamp}")
    print()

    # Summary
    status_color = {
        HealthStatus.HEALTHY: "green",
        HealthStatus.DEGRADED: "yellow",
        HealthStatus.UNHEALTHY: "red"
    }
    print_colored(f"Overall Status: {result.overall_status.value.upper()}",
                  status_color.get(result.overall_status, "reset"))
    print(f"Services: {result.healthy_count}/{result.total_services} healthy")
    print()

    # Service details
    print_colored("Services:", "bold")
    print("-" * 60)

    for service in result.services:
        icon = "✓" if service.status == HealthStatus.HEALTHY else "✗"
        color = "green" if service.status == HealthStatus.HEALTHY else "red"
        print_colored(
            f"  {icon} {service.name:20} {service.status.value:12} {service.latency_ms:>8.1f}ms",
            color
        )
        if verbose and service.message:
            print(f"      Message: {service.message}")
        if verbose and service.details:
            print(f"      Details: {json.dumps(service.details, indent=8)}")

    print()


async def main():
    parser = argparse.ArgumentParser(description="Mercai Health Check")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--service", "-s", type=str, help="Check specific service")
    parser.add_argument("--timeout", "-t", type=float, default=5.0, help="Request timeout")
    parser.add_argument("--gateway", "-g", type=str, default="localhost", help="Gateway host")

    args = parser.parse_args()

    async with HealthChecker(timeout=args.timeout, gateway_host=args.gateway) as checker:
        result = await checker.check_all_services(service_filter=args.service)

        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print_result(result, verbose=args.verbose)

        # Exit with appropriate code
        if result.overall_status == HealthStatus.HEALTHY:
            sys.exit(0)
        elif result.overall_status == HealthStatus.DEGRADED:
            sys.exit(1)
        else:
            sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
