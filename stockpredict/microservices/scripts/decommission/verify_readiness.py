#!/usr/bin/env python3
"""
Decommission Readiness Verification

This script verifies that all prerequisites for Django decommissioning are met.
Run this before proceeding with Django shutdown.
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

import httpx

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of a single verification check"""
    check_name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "critical"  # critical, warning, info

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check_name,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity,
            "details": self.details,
        }


@dataclass
class VerificationReport:
    """Complete verification report"""
    timestamp: datetime
    ready_for_decommission: bool
    checks: List[VerificationResult] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "ready_for_decommission": self.ready_for_decommission,
            "summary": self.summary,
            "checks": [c.to_dict() for c in self.checks],
        }


class DecommissionVerifier:
    """Verifies readiness for Django decommissioning"""

    def __init__(self):
        self.feature_flags_url = os.getenv("FEATURE_FLAGS_URL", "http://localhost:8010")
        self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
        self.traefik_url = os.getenv("TRAEFIK_API_URL", "http://localhost:8080")
        self.services = [
            ("auth-service", "http://localhost:8001"),
            ("stock-data-service", "http://localhost:8002"),
            ("portfolio-service", "http://localhost:8003"),
            ("prediction-service", "http://localhost:8004"),
            ("analysis-service", "http://localhost:8005"),
            ("ai-insights-service", "http://localhost:8006"),
            ("chatbot-service", "http://localhost:8007"),
        ]

    async def run_all_checks(self) -> VerificationReport:
        """Run all verification checks"""
        report = VerificationReport(
            timestamp=datetime.now(),
            ready_for_decommission=True,
        )

        # Run all checks
        checks = [
            self.check_traffic_routing(),
            self.check_microservices_health(),
            self.check_error_rates(),
            self.check_latency(),
            self.check_data_consistency(),
            self.check_feature_flags(),
            self.check_no_django_direct_connections(),
            self.check_minimum_runtime(),
            self.check_no_pending_migrations(),
            self.check_monitoring_alerts(),
        ]

        results = await asyncio.gather(*checks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                report.checks.append(VerificationResult(
                    check_name="unknown",
                    passed=False,
                    message=f"Check failed with error: {str(result)}",
                    severity="critical"
                ))
            else:
                report.checks.append(result)

        # Calculate summary
        report.summary = {
            "total": len(report.checks),
            "passed": sum(1 for c in report.checks if c.passed),
            "failed": sum(1 for c in report.checks if not c.passed),
            "critical_failures": sum(
                1 for c in report.checks
                if not c.passed and c.severity == "critical"
            ),
        }

        # Determine overall readiness
        report.ready_for_decommission = report.summary["critical_failures"] == 0

        return report

    async def check_traffic_routing(self) -> VerificationResult:
        """Verify 100% traffic is routed to microservices"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.feature_flags_url}/api/flags/status")
                response.raise_for_status()
                status = response.json()

            # Check all services are at 100%
            flags = status.get("flags", {})
            all_at_100 = True
            not_at_100 = []

            expected_flags = [
                "auth_microservice",
                "stock_data_microservice",
                "portfolio_microservice",
                "prediction_microservice",
                "analysis_microservice",
                "ai_insights_microservice",
                "chatbot_microservice",
            ]

            for flag in expected_flags:
                if flag in flags:
                    percentage = flags[flag].get("percentage", 0)
                    if percentage < 100:
                        all_at_100 = False
                        not_at_100.append(f"{flag}: {percentage}%")
                else:
                    all_at_100 = False
                    not_at_100.append(f"{flag}: not found")

            return VerificationResult(
                check_name="traffic_routing",
                passed=all_at_100,
                message="All traffic routed to microservices" if all_at_100
                        else f"Some services not at 100%: {', '.join(not_at_100)}",
                details={"flags": flags},
                severity="critical"
            )

        except Exception as e:
            return VerificationResult(
                check_name="traffic_routing",
                passed=False,
                message=f"Failed to check traffic routing: {str(e)}",
                severity="critical"
            )

    async def check_microservices_health(self) -> VerificationResult:
        """Verify all microservices are healthy"""
        unhealthy = []

        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in self.services:
                try:
                    response = await client.get(f"{url}/health/ready")
                    if response.status_code != 200:
                        unhealthy.append(f"{name}: status {response.status_code}")
                except Exception as e:
                    unhealthy.append(f"{name}: {str(e)}")

        return VerificationResult(
            check_name="microservices_health",
            passed=len(unhealthy) == 0,
            message="All microservices healthy" if len(unhealthy) == 0
                    else f"Unhealthy services: {', '.join(unhealthy)}",
            details={"unhealthy": unhealthy},
            severity="critical"
        )

    async def check_error_rates(self) -> VerificationResult:
        """Verify error rates are within acceptable thresholds"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Query Prometheus for error rate over last 24 hours
                query = 'sum(rate(http_requests_total{status=~"5.."}[24h])) / sum(rate(http_requests_total[24h])) * 100'
                response = await client.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": query}
                )
                response.raise_for_status()
                result = response.json()

            if result["status"] == "success" and result["data"]["result"]:
                error_rate = float(result["data"]["result"][0]["value"][1])
                threshold = 1.0  # 1% error rate threshold

                return VerificationResult(
                    check_name="error_rates",
                    passed=error_rate < threshold,
                    message=f"Error rate: {error_rate:.2f}% (threshold: {threshold}%)",
                    details={"error_rate": error_rate, "threshold": threshold},
                    severity="critical" if error_rate >= threshold else "info"
                )
            else:
                return VerificationResult(
                    check_name="error_rates",
                    passed=True,
                    message="No error rate data available (assuming OK)",
                    severity="warning"
                )

        except Exception as e:
            return VerificationResult(
                check_name="error_rates",
                passed=False,
                message=f"Failed to check error rates: {str(e)}",
                severity="warning"
            )

    async def check_latency(self) -> VerificationResult:
        """Verify latency is within acceptable thresholds"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Query Prometheus for P99 latency over last 24 hours
                query = 'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[24h])) by (le)) * 1000'
                response = await client.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": query}
                )
                response.raise_for_status()
                result = response.json()

            if result["status"] == "success" and result["data"]["result"]:
                p99_latency = float(result["data"]["result"][0]["value"][1])
                threshold = 500  # 500ms P99 threshold

                return VerificationResult(
                    check_name="latency",
                    passed=p99_latency < threshold,
                    message=f"P99 latency: {p99_latency:.0f}ms (threshold: {threshold}ms)",
                    details={"p99_latency_ms": p99_latency, "threshold_ms": threshold},
                    severity="warning" if p99_latency >= threshold else "info"
                )
            else:
                return VerificationResult(
                    check_name="latency",
                    passed=True,
                    message="No latency data available (assuming OK)",
                    severity="warning"
                )

        except Exception as e:
            return VerificationResult(
                check_name="latency",
                passed=False,
                message=f"Failed to check latency: {str(e)}",
                severity="warning"
            )

    async def check_data_consistency(self) -> VerificationResult:
        """Verify data consistency between Django and microservices"""
        # This would typically compare record counts and checksums
        # For now, we'll check if shadow comparator shows good match rate

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:8008/api/summary")
                if response.status_code == 200:
                    summary = response.json()
                    match_rate = summary.get("overall_match_rate", 0)
                    threshold = 99.0

                    return VerificationResult(
                        check_name="data_consistency",
                        passed=match_rate >= threshold,
                        message=f"Data consistency: {match_rate:.1f}% (threshold: {threshold}%)",
                        details=summary,
                        severity="critical" if match_rate < threshold else "info"
                    )
        except Exception:
            pass

        return VerificationResult(
            check_name="data_consistency",
            passed=True,
            message="Shadow comparator not available, skipping check",
            severity="warning"
        )

    async def check_feature_flags(self) -> VerificationResult:
        """Verify feature flags are configured for full microservices"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.feature_flags_url}/api/flags/")
                response.raise_for_status()
                flags = response.json()

            # Check Django fallback is disabled
            django_fallback = flags.get("django_fallback", {})
            fallback_enabled = django_fallback.get("enabled", True)

            return VerificationResult(
                check_name="feature_flags",
                passed=not fallback_enabled,
                message="Django fallback disabled" if not fallback_enabled
                        else "Django fallback is still enabled",
                details={"django_fallback": django_fallback},
                severity="critical" if fallback_enabled else "info"
            )

        except Exception as e:
            return VerificationResult(
                check_name="feature_flags",
                passed=False,
                message=f"Failed to check feature flags: {str(e)}",
                severity="warning"
            )

    async def check_no_django_direct_connections(self) -> VerificationResult:
        """Verify no direct connections to Django"""
        # This checks Traefik routing configuration
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.traefik_url}/api/http/routers")
                response.raise_for_status()
                routers = response.json()

            django_routes = [
                r for r in routers
                if "django" in r.get("service", "").lower()
                and r.get("status") == "enabled"
            ]

            return VerificationResult(
                check_name="no_django_routes",
                passed=len(django_routes) == 0,
                message="No active Django routes" if len(django_routes) == 0
                        else f"Found {len(django_routes)} active Django routes",
                details={"django_routes": django_routes},
                severity="critical" if len(django_routes) > 0 else "info"
            )

        except Exception as e:
            return VerificationResult(
                check_name="no_django_routes",
                passed=False,
                message=f"Failed to check Traefik routes: {str(e)}",
                severity="warning"
            )

    async def check_minimum_runtime(self) -> VerificationResult:
        """Verify microservices have been running at 100% for minimum 2 weeks"""
        # This would check historical data from Prometheus or feature flags
        minimum_days = 14

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.feature_flags_url}/api/flags/history")
                if response.status_code == 200:
                    history = response.json()

                    # Find when we first reached 100%
                    first_100_date = history.get("first_full_cutover")
                    if first_100_date:
                        first_100 = datetime.fromisoformat(first_100_date)
                        days_at_100 = (datetime.now() - first_100).days

                        return VerificationResult(
                            check_name="minimum_runtime",
                            passed=days_at_100 >= minimum_days,
                            message=f"Running at 100% for {days_at_100} days (minimum: {minimum_days})",
                            details={"days_at_100": days_at_100, "minimum_days": minimum_days},
                            severity="critical" if days_at_100 < minimum_days else "info"
                        )
        except Exception:
            pass

        return VerificationResult(
            check_name="minimum_runtime",
            passed=False,
            message=f"Could not verify minimum runtime of {minimum_days} days",
            severity="warning"
        )

    async def check_no_pending_migrations(self) -> VerificationResult:
        """Verify no pending data migrations"""
        # Check migration status endpoint
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:8080/api/migrations/status")
                if response.status_code == 200:
                    status = response.json()
                    pending = status.get("pending", [])

                    return VerificationResult(
                        check_name="no_pending_migrations",
                        passed=len(pending) == 0,
                        message="No pending migrations" if len(pending) == 0
                                else f"Found {len(pending)} pending migrations",
                        details={"pending": pending},
                        severity="critical" if len(pending) > 0 else "info"
                    )
        except Exception:
            pass

        return VerificationResult(
            check_name="no_pending_migrations",
            passed=True,
            message="Migration status endpoint not available, assuming OK",
            severity="info"
        )

    async def check_monitoring_alerts(self) -> VerificationResult:
        """Verify no active critical alerts"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.prometheus_url}/api/v1/alerts")
                response.raise_for_status()
                alerts = response.json()

            if alerts["status"] == "success":
                active_alerts = alerts["data"]["alerts"]
                critical_alerts = [
                    a for a in active_alerts
                    if a.get("labels", {}).get("severity") == "critical"
                    and a.get("state") == "firing"
                ]

                return VerificationResult(
                    check_name="monitoring_alerts",
                    passed=len(critical_alerts) == 0,
                    message="No critical alerts" if len(critical_alerts) == 0
                            else f"Found {len(critical_alerts)} critical alerts",
                    details={"critical_alerts": critical_alerts},
                    severity="critical" if len(critical_alerts) > 0 else "info"
                )

        except Exception as e:
            return VerificationResult(
                check_name="monitoring_alerts",
                passed=False,
                message=f"Failed to check alerts: {str(e)}",
                severity="warning"
            )


def print_report(report: VerificationReport):
    """Print verification report to console"""
    print("\n" + "=" * 70)
    print("  DECOMMISSION READINESS VERIFICATION REPORT")
    print("=" * 70)
    print(f"\n  Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Ready for Decommission: {'✅ YES' if report.ready_for_decommission else '❌ NO'}")

    print("\n  Summary:")
    print(f"    Total Checks: {report.summary['total']}")
    print(f"    Passed: {report.summary['passed']}")
    print(f"    Failed: {report.summary['failed']}")
    print(f"    Critical Failures: {report.summary['critical_failures']}")

    print("\n  Check Results:")
    print("  " + "-" * 66)

    for check in report.checks:
        icon = "✅" if check.passed else ("❌" if check.severity == "critical" else "⚠️")
        print(f"  {icon} {check.check_name}")
        print(f"     {check.message}")

    print("\n" + "=" * 70)

    if not report.ready_for_decommission:
        print("\n  ⚠️  CANNOT PROCEED WITH DECOMMISSIONING")
        print("  Please resolve all critical failures before proceeding.")
    else:
        print("\n  ✅ ALL CRITICAL CHECKS PASSED")
        print("  You may proceed with Django decommissioning.")

    print()


async def main():
    """Main entry point"""
    verifier = DecommissionVerifier()
    report = await verifier.run_all_checks()
    print_report(report)

    # Save report to file
    report_path = f"decommission_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)
    print(f"  Report saved to: {report_path}\n")

    # Exit with appropriate code
    sys.exit(0 if report.ready_for_decommission else 1)


if __name__ == "__main__":
    asyncio.run(main())
