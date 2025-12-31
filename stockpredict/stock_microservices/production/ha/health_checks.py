"""
Health Check Configuration

Provides comprehensive health check configurations for service availability monitoring.
"""
import os
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckType(Enum):
    """Types of health checks"""
    LIVENESS = "liveness"      # Is the process running?
    READINESS = "readiness"    # Is the service ready for traffic?
    STARTUP = "startup"        # Has the service started correctly?


@dataclass
class HealthCheckConfig:
    """Health check configuration"""

    # Liveness probe settings
    liveness_path: str = "/health/live"
    liveness_initial_delay_seconds: int = 10
    liveness_period_seconds: int = 10
    liveness_timeout_seconds: int = 5
    liveness_failure_threshold: int = 3
    liveness_success_threshold: int = 1

    # Readiness probe settings
    readiness_path: str = "/health/ready"
    readiness_initial_delay_seconds: int = 5
    readiness_period_seconds: int = 5
    readiness_timeout_seconds: int = 3
    readiness_failure_threshold: int = 3
    readiness_success_threshold: int = 1

    # Startup probe settings
    startup_path: str = "/health/startup"
    startup_initial_delay_seconds: int = 0
    startup_period_seconds: int = 5
    startup_timeout_seconds: int = 5
    startup_failure_threshold: int = 30  # Allow 2.5 minutes for startup
    startup_success_threshold: int = 1

    # Response validation
    expected_status_codes: List[int] = field(default_factory=lambda: [200])

    # Dependency checks
    check_dependencies: bool = True
    dependency_timeout_seconds: int = 3


@dataclass
class ServiceHealth:
    """Service health status"""
    service_name: str
    status: HealthStatus
    timestamp: datetime
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    dependencies: Dict[str, HealthStatus] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service_name,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "latency_ms": self.latency_ms,
            "details": self.details,
            "dependencies": {k: v.value for k, v in self.dependencies.items()},
        }


@dataclass
class DependencyConfig:
    """Dependency health check configuration"""
    name: str
    check_url: str
    timeout_seconds: int = 3
    required: bool = True  # Is this dependency critical?
    check_interval_seconds: int = 30


# Service dependency definitions
SERVICE_DEPENDENCIES: Dict[str, List[DependencyConfig]] = {
    "auth": [
        DependencyConfig(
            name="database",
            check_url="postgresql://localhost:5432",
            required=True
        ),
        DependencyConfig(
            name="redis",
            check_url="redis://localhost:6379",
            required=True
        ),
    ],
    "stock-data": [
        DependencyConfig(
            name="database",
            check_url="postgresql://localhost:5432",
            required=True
        ),
        DependencyConfig(
            name="redis",
            check_url="redis://localhost:6379",
            required=True
        ),
        DependencyConfig(
            name="external-api",
            check_url=os.getenv("STOCK_API_HEALTH_URL", ""),
            required=False
        ),
    ],
    "portfolio": [
        DependencyConfig(
            name="database",
            check_url="postgresql://localhost:5432",
            required=True
        ),
        DependencyConfig(
            name="auth-service",
            check_url="http://auth-service:8001/health/ready",
            required=True
        ),
    ],
    "prediction": [
        DependencyConfig(
            name="database",
            check_url="postgresql://localhost:5432",
            required=True
        ),
        DependencyConfig(
            name="redis",
            check_url="redis://localhost:6379",
            required=True
        ),
        DependencyConfig(
            name="ml-model",
            check_url="file:///models/prediction_model.pkl",
            required=True
        ),
    ],
}


def get_health_check_config() -> HealthCheckConfig:
    """Get health check configuration"""
    return HealthCheckConfig()


async def check_http_health(
    url: str,
    timeout_seconds: int = 5,
    expected_status: List[int] = None
) -> tuple[HealthStatus, float, Dict]:
    """
    Check HTTP endpoint health

    Returns:
        Tuple of (status, latency_ms, details)
    """
    expected_status = expected_status or [200]
    start_time = datetime.now()

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            if response.status_code in expected_status:
                return HealthStatus.HEALTHY, latency_ms, {
                    "status_code": response.status_code,
                }
            else:
                return HealthStatus.UNHEALTHY, latency_ms, {
                    "status_code": response.status_code,
                    "reason": "Unexpected status code",
                }
    except httpx.TimeoutException:
        latency_ms = timeout_seconds * 1000
        return HealthStatus.UNHEALTHY, latency_ms, {
            "error": "Timeout",
        }
    except Exception as e:
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000
        return HealthStatus.UNHEALTHY, latency_ms, {
            "error": str(e),
        }


async def check_database_health(
    connection_string: str,
    timeout_seconds: int = 5
) -> tuple[HealthStatus, Dict]:
    """Check database connection health"""
    try:
        # Import here to avoid dependency issues
        from sqlalchemy.ext.asyncio import create_async_engine

        # Convert to async URL if needed
        if connection_string.startswith("postgresql://"):
            connection_string = connection_string.replace(
                "postgresql://",
                "postgresql+asyncpg://"
            )

        engine = create_async_engine(connection_string)

        async with engine.connect() as conn:
            result = await asyncio.wait_for(
                conn.execute("SELECT 1"),
                timeout=timeout_seconds
            )
            return HealthStatus.HEALTHY, {"connected": True}

    except asyncio.TimeoutError:
        return HealthStatus.UNHEALTHY, {"error": "Connection timeout"}
    except Exception as e:
        return HealthStatus.UNHEALTHY, {"error": str(e)}


async def check_redis_health(
    redis_url: str,
    timeout_seconds: int = 3
) -> tuple[HealthStatus, Dict]:
    """Check Redis connection health"""
    try:
        import redis.asyncio as redis

        client = redis.from_url(redis_url, socket_timeout=timeout_seconds)
        await client.ping()
        info = await client.info("server")
        await client.close()

        return HealthStatus.HEALTHY, {
            "connected": True,
            "redis_version": info.get("redis_version"),
        }

    except Exception as e:
        return HealthStatus.UNHEALTHY, {"error": str(e)}


async def check_dependency_health(
    dependency: DependencyConfig
) -> tuple[str, HealthStatus, Dict]:
    """Check a single dependency health"""
    if dependency.check_url.startswith("http"):
        status, _, details = await check_http_health(
            dependency.check_url,
            dependency.timeout_seconds
        )
    elif dependency.check_url.startswith("postgresql"):
        status, details = await check_database_health(
            dependency.check_url,
            dependency.timeout_seconds
        )
    elif dependency.check_url.startswith("redis"):
        status, details = await check_redis_health(
            dependency.check_url,
            dependency.timeout_seconds
        )
    elif dependency.check_url.startswith("file://"):
        # File existence check
        import os
        path = dependency.check_url.replace("file://", "")
        if os.path.exists(path):
            status = HealthStatus.HEALTHY
            details = {"exists": True}
        else:
            status = HealthStatus.UNHEALTHY
            details = {"exists": False, "path": path}
    else:
        status = HealthStatus.UNKNOWN
        details = {"error": "Unknown check type"}

    return dependency.name, status, details


async def check_service_health(
    service_name: str,
    service_url: Optional[str] = None,
    check_dependencies: bool = True
) -> ServiceHealth:
    """
    Comprehensive service health check

    Args:
        service_name: Name of the service
        service_url: Optional URL to check (for readiness)
        check_dependencies: Whether to check dependencies

    Returns:
        ServiceHealth object with complete status
    """
    start_time = datetime.now()
    config = get_health_check_config()
    dependencies = {}
    details = {}

    # Check main service if URL provided
    if service_url:
        status, latency, check_details = await check_http_health(
            f"{service_url}{config.readiness_path}",
            config.readiness_timeout_seconds
        )
        details.update(check_details)
    else:
        status = HealthStatus.HEALTHY
        latency = 0

    # Check dependencies
    if check_dependencies and service_name in SERVICE_DEPENDENCIES:
        dep_configs = SERVICE_DEPENDENCIES[service_name]
        dep_tasks = [check_dependency_health(dep) for dep in dep_configs]
        dep_results = await asyncio.gather(*dep_tasks, return_exceptions=True)

        has_critical_failure = False
        for i, result in enumerate(dep_results):
            if isinstance(result, Exception):
                dep_name = dep_configs[i].name
                dependencies[dep_name] = HealthStatus.UNHEALTHY
                if dep_configs[i].required:
                    has_critical_failure = True
            else:
                dep_name, dep_status, dep_details = result
                dependencies[dep_name] = dep_status
                if dep_status == HealthStatus.UNHEALTHY and dep_configs[i].required:
                    has_critical_failure = True

        # Downgrade service status if critical dependency failed
        if has_critical_failure and status == HealthStatus.HEALTHY:
            status = HealthStatus.DEGRADED

    return ServiceHealth(
        service_name=service_name,
        status=status,
        timestamp=datetime.now(),
        latency_ms=latency,
        details=details,
        dependencies=dependencies
    )


# Kubernetes probe generators
def generate_liveness_probe(config: Optional[HealthCheckConfig] = None) -> Dict:
    """Generate Kubernetes liveness probe configuration"""
    config = config or get_health_check_config()

    return {
        "httpGet": {
            "path": config.liveness_path,
            "port": 8000,
        },
        "initialDelaySeconds": config.liveness_initial_delay_seconds,
        "periodSeconds": config.liveness_period_seconds,
        "timeoutSeconds": config.liveness_timeout_seconds,
        "failureThreshold": config.liveness_failure_threshold,
        "successThreshold": config.liveness_success_threshold,
    }


def generate_readiness_probe(config: Optional[HealthCheckConfig] = None) -> Dict:
    """Generate Kubernetes readiness probe configuration"""
    config = config or get_health_check_config()

    return {
        "httpGet": {
            "path": config.readiness_path,
            "port": 8000,
        },
        "initialDelaySeconds": config.readiness_initial_delay_seconds,
        "periodSeconds": config.readiness_period_seconds,
        "timeoutSeconds": config.readiness_timeout_seconds,
        "failureThreshold": config.readiness_failure_threshold,
        "successThreshold": config.readiness_success_threshold,
    }


def generate_startup_probe(config: Optional[HealthCheckConfig] = None) -> Dict:
    """Generate Kubernetes startup probe configuration"""
    config = config or get_health_check_config()

    return {
        "httpGet": {
            "path": config.startup_path,
            "port": 8000,
        },
        "initialDelaySeconds": config.startup_initial_delay_seconds,
        "periodSeconds": config.startup_period_seconds,
        "timeoutSeconds": config.startup_timeout_seconds,
        "failureThreshold": config.startup_failure_threshold,
        "successThreshold": config.startup_success_threshold,
    }
