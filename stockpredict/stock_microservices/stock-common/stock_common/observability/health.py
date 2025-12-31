"""
Health check implementation for Kubernetes probes.

Provides:
- Liveness probe: Is the service alive?
- Readiness probe: Is the service ready to accept traffic?
- Startup probe: Has the service started successfully?
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Response

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class HealthCheck:
    """
    Individual health check definition.

    Example:
        async def check_database():
            try:
                await db.execute("SELECT 1")
                return True, "Connected"
            except Exception as e:
                return False, str(e)

        db_check = HealthCheck(
            name="database",
            check_fn=check_database,
            critical=True,  # Service is not ready without this
        )
    """
    name: str
    check_fn: Callable[[], Any]
    critical: bool = True  # If True, failure means service is not ready
    timeout: float = 5.0  # Timeout for the check
    description: str = ""


class HealthCheckRegistry:
    """
    Registry for health checks.

    Manages liveness and readiness checks for the service.
    """

    def __init__(self, service_name: str, service_version: str = "0.1.0"):
        self.service_name = service_name
        self.service_version = service_version
        self._checks: Dict[str, HealthCheck] = {}
        self._is_ready = False
        self._startup_time: Optional[datetime] = None

    def register(self, check: HealthCheck) -> None:
        """Register a health check."""
        self._checks[check.name] = check
        logger.debug(f"Registered health check: {check.name}")

    def unregister(self, name: str) -> None:
        """Unregister a health check."""
        self._checks.pop(name, None)

    def mark_ready(self) -> None:
        """Mark the service as ready."""
        self._is_ready = True
        self._startup_time = datetime.now(timezone.utc)
        logger.info(f"Service {self.service_name} marked as ready")

    def mark_not_ready(self) -> None:
        """Mark the service as not ready."""
        self._is_ready = False
        logger.warning(f"Service {self.service_name} marked as not ready")

    async def run_check(self, check: HealthCheck) -> HealthCheckResult:
        """Run a single health check."""
        import time
        start = time.time()

        try:
            result = await asyncio.wait_for(
                check.check_fn() if asyncio.iscoroutinefunction(check.check_fn)
                else asyncio.to_thread(check.check_fn),
                timeout=check.timeout,
            )

            # Handle different return types
            if isinstance(result, tuple):
                is_healthy, message = result
            elif isinstance(result, bool):
                is_healthy = result
                message = "OK" if result else "Failed"
            elif isinstance(result, dict):
                is_healthy = result.get("healthy", True)
                message = result.get("message", "OK")
            else:
                is_healthy = bool(result)
                message = str(result) if result else "OK"

            duration = (time.time() - start) * 1000

            return HealthCheckResult(
                name=check.name,
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                message=message,
                duration_ms=duration,
            )

        except asyncio.TimeoutError:
            duration = (time.time() - start) * 1000
            return HealthCheckResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check timed out after {check.timeout}s",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"Health check {check.name} failed: {e}")
            return HealthCheckResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=duration,
            )

    async def check_liveness(self) -> Dict[str, Any]:
        """
        Check if the service is alive.

        Returns basic status - service is alive if it can respond.
        """
        return {
            "status": "alive",
            "service": self.service_name,
            "version": self.service_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def check_readiness(self) -> Dict[str, Any]:
        """
        Check if the service is ready to accept traffic.

        Runs all registered health checks and aggregates results.
        """
        if not self._is_ready:
            return {
                "status": "not_ready",
                "service": self.service_name,
                "message": "Service has not completed startup",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Run all checks in parallel
        check_tasks = [
            self.run_check(check)
            for check in self._checks.values()
        ]

        results = await asyncio.gather(*check_tasks, return_exceptions=True)

        # Process results
        check_results = {}
        all_healthy = True
        critical_failure = False

        for i, result in enumerate(results):
            check = list(self._checks.values())[i]

            if isinstance(result, Exception):
                check_results[check.name] = {
                    "status": "unhealthy",
                    "message": str(result),
                }
                all_healthy = False
                if check.critical:
                    critical_failure = True
            else:
                check_results[result.name] = {
                    "status": result.status.value,
                    "message": result.message,
                    "duration_ms": result.duration_ms,
                }
                if result.status != HealthStatus.HEALTHY:
                    all_healthy = False
                    if check.critical:
                        critical_failure = True

        # Determine overall status
        if critical_failure:
            overall_status = "not_ready"
        elif not all_healthy:
            overall_status = "degraded"
        else:
            overall_status = "ready"

        return {
            "status": overall_status,
            "service": self.service_name,
            "version": self.service_version,
            "checks": check_results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": (
                (datetime.now(timezone.utc) - self._startup_time).total_seconds()
                if self._startup_time else 0
            ),
        }

    async def check_startup(self) -> Dict[str, Any]:
        """
        Check if the service has started successfully.

        Used for Kubernetes startup probe.
        """
        return {
            "status": "started" if self._is_ready else "starting",
            "service": self.service_name,
            "version": self.service_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def create_health_router(registry: HealthCheckRegistry) -> APIRouter:
    """
    Create a FastAPI router with health check endpoints.

    Endpoints:
    - GET /health/live - Liveness probe
    - GET /health/ready - Readiness probe
    - GET /health/startup - Startup probe
    """
    router = APIRouter(prefix="/health", tags=["Health"])

    @router.get("/live")
    async def liveness():
        """Kubernetes liveness probe."""
        result = await registry.check_liveness()
        return result

    @router.get("/ready")
    async def readiness(response: Response):
        """Kubernetes readiness probe."""
        result = await registry.check_readiness()

        if result["status"] == "not_ready":
            response.status_code = 503
        elif result["status"] == "degraded":
            response.status_code = 200  # Still accept traffic, but degraded

        return result

    @router.get("/startup")
    async def startup(response: Response):
        """Kubernetes startup probe."""
        result = await registry.check_startup()

        if result["status"] != "started":
            response.status_code = 503

        return result

    return router
