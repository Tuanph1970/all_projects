"""
Prometheus metrics for microservices.

Provides:
- Request duration histogram
- Request counter by status
- Active requests gauge
- Custom business metrics
"""

import logging
import time
from functools import wraps
from typing import Callable, Dict, Optional

from fastapi import Request, Response
from fastapi.routing import APIRoute
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class MetricsManager:
    """
    Manager for Prometheus metrics.

    Provides common metrics for microservices:
    - HTTP request duration
    - HTTP request count
    - Active requests
    - Service info
    """

    def __init__(self, service_name: str, service_version: str = "0.1.0"):
        self.service_name = service_name
        self.service_version = service_version

        # Service info
        self.info = Info(
            "service",
            "Service information",
        )
        self.info.info({
            "name": service_name,
            "version": service_version,
        })

        # HTTP metrics
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_code"],
        )

        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        self.http_requests_in_progress = Gauge(
            "http_requests_in_progress",
            "Number of HTTP requests in progress",
            ["method", "endpoint"],
        )

        # Event bus metrics
        self.events_published_total = Counter(
            "events_published_total",
            "Total events published",
            ["event_type"],
        )

        self.events_consumed_total = Counter(
            "events_consumed_total",
            "Total events consumed",
            ["event_type", "status"],
        )

        self.event_processing_duration_seconds = Histogram(
            "event_processing_duration_seconds",
            "Event processing duration in seconds",
            ["event_type"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
        )

        # Database metrics
        self.db_queries_total = Counter(
            "db_queries_total",
            "Total database queries",
            ["operation", "table"],
        )

        self.db_query_duration_seconds = Histogram(
            "db_query_duration_seconds",
            "Database query duration in seconds",
            ["operation"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
        )

        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge(
            "circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half-open)",
            ["name"],
        )

        self.circuit_breaker_failures_total = Counter(
            "circuit_breaker_failures_total",
            "Total circuit breaker failures",
            ["name"],
        )

        # Custom metrics storage
        self._custom_counters: Dict[str, Counter] = {}
        self._custom_gauges: Dict[str, Gauge] = {}
        self._custom_histograms: Dict[str, Histogram] = {}

    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
    ) -> None:
        """Record HTTP request metrics."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).inc()

        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)

    def record_event_published(self, event_type: str) -> None:
        """Record event published metric."""
        self.events_published_total.labels(event_type=event_type).inc()

    def record_event_consumed(
        self,
        event_type: str,
        status: str = "success",
        duration: Optional[float] = None,
    ) -> None:
        """Record event consumed metric."""
        self.events_consumed_total.labels(
            event_type=event_type,
            status=status,
        ).inc()

        if duration is not None:
            self.event_processing_duration_seconds.labels(
                event_type=event_type,
            ).observe(duration)

    def record_db_query(
        self,
        operation: str,
        table: str,
        duration: float,
    ) -> None:
        """Record database query metric."""
        self.db_queries_total.labels(
            operation=operation,
            table=table,
        ).inc()

        self.db_query_duration_seconds.labels(
            operation=operation,
        ).observe(duration)

    def create_counter(
        self,
        name: str,
        description: str,
        labels: Optional[list] = None,
    ) -> Counter:
        """Create a custom counter."""
        if name not in self._custom_counters:
            self._custom_counters[name] = Counter(
                f"{self.service_name}_{name}",
                description,
                labels or [],
            )
        return self._custom_counters[name]

    def create_gauge(
        self,
        name: str,
        description: str,
        labels: Optional[list] = None,
    ) -> Gauge:
        """Create a custom gauge."""
        if name not in self._custom_gauges:
            self._custom_gauges[name] = Gauge(
                f"{self.service_name}_{name}",
                description,
                labels or [],
            )
        return self._custom_gauges[name]

    def create_histogram(
        self,
        name: str,
        description: str,
        labels: Optional[list] = None,
        buckets: Optional[tuple] = None,
    ) -> Histogram:
        """Create a custom histogram."""
        if name not in self._custom_histograms:
            self._custom_histograms[name] = Histogram(
                f"{self.service_name}_{name}",
                description,
                labels or [],
                buckets=buckets or Histogram.DEFAULT_BUCKETS,
            )
        return self._custom_histograms[name]


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic metrics collection.

    Tracks:
    - Request duration
    - Request count by status code
    - Active requests
    """

    def __init__(self, app, metrics: MetricsManager):
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(self, request: Request, call_next) -> Response:
        method = request.method
        endpoint = self._get_endpoint(request)

        # Track in-progress requests
        self.metrics.http_requests_in_progress.labels(
            method=method,
            endpoint=endpoint,
        ).inc()

        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            self.metrics.record_request(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration=duration,
            )

            return response

        except Exception as e:
            duration = time.time() - start_time

            self.metrics.record_request(
                method=method,
                endpoint=endpoint,
                status_code=500,
                duration=duration,
            )

            raise

        finally:
            self.metrics.http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint,
            ).dec()

    def _get_endpoint(self, request: Request) -> str:
        """Get the endpoint path template."""
        # Try to get the route path template
        if request.scope.get("route"):
            route = request.scope["route"]
            if isinstance(route, APIRoute):
                return route.path
        return request.url.path


def setup_metrics(service_name: str, service_version: str = "0.1.0") -> MetricsManager:
    """Set up metrics for a service."""
    return MetricsManager(service_name, service_version)


def create_metrics_endpoint(app) -> None:
    """
    Add Prometheus metrics endpoint to FastAPI app.

    Creates GET /metrics endpoint.
    """
    from fastapi import FastAPI
    from fastapi.responses import Response

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )


def timed(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """
    Decorator for timing function execution.

    Example:
        @timed("process_order", {"order_type": "buy"})
        async def process_order(order_id: str):
            # ... processing logic
            pass
    """

    def decorator(func: Callable) -> Callable:
        histogram = Histogram(
            metric_name,
            f"Duration of {func.__name__}",
            list(labels.keys()) if labels else [],
        )

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start
                if labels:
                    histogram.labels(**labels).observe(duration)
                else:
                    histogram.observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                if labels:
                    histogram.labels(**labels).observe(duration)
                else:
                    histogram.observe(duration)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
