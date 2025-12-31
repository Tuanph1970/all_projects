"""
Prometheus Metrics Module for Ceramic Marketplace Microservices

This module provides standardized metrics collection for all microservices.
"""

import time
from functools import wraps
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        Info,
        generate_latest,
        CONTENT_TYPE_LATEST,
        REGISTRY,
        CollectorRegistry
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("prometheus_client not installed. Metrics will be disabled.")


# =============================================================================
# Metrics Definitions
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # Request metrics
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"]
    )

    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
        buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
    )

    REQUEST_IN_PROGRESS = Gauge(
        "http_requests_in_progress",
        "Number of HTTP requests in progress",
        ["method", "endpoint"]
    )

    # Database metrics
    DB_QUERY_COUNT = Counter(
        "db_queries_total",
        "Total database queries",
        ["operation", "table"]
    )

    DB_QUERY_LATENCY = Histogram(
        "db_query_duration_seconds",
        "Database query latency in seconds",
        ["operation"],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
    )

    DB_CONNECTION_POOL = Gauge(
        "db_connection_pool_size",
        "Database connection pool size",
        ["state"]
    )

    # Cache metrics
    CACHE_HIT_COUNT = Counter(
        "cache_hits_total",
        "Total cache hits",
        ["cache_type"]
    )

    CACHE_MISS_COUNT = Counter(
        "cache_misses_total",
        "Total cache misses",
        ["cache_type"]
    )

    CACHE_LATENCY = Histogram(
        "cache_operation_duration_seconds",
        "Cache operation latency",
        ["operation"],
        buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1)
    )

    # Business metrics
    ACTIVE_USERS = Gauge(
        "active_users_total",
        "Number of active users",
        ["role"]
    )

    ORDER_COUNT = Counter(
        "orders_total",
        "Total orders",
        ["status"]
    )

    ORDER_VALUE = Histogram(
        "order_value_dollars",
        "Order value distribution",
        buckets=(10, 25, 50, 100, 250, 500, 1000, 2500, 5000)
    )

    # Service info
    SERVICE_INFO = Info(
        "service",
        "Service information"
    )


# =============================================================================
# Middleware
# =============================================================================

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics for Prometheus."""

    def __init__(self, app: FastAPI, service_name: str = "unknown"):
        super().__init__(app)
        self.service_name = service_name
        if PROMETHEUS_AVAILABLE:
            SERVICE_INFO.info({
                "name": service_name,
                "version": "1.0.0"
            })

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not PROMETHEUS_AVAILABLE:
            return await call_next(request)

        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = self._get_path_template(request)

        # Track in-progress requests
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).inc()

        # Time the request
        start_time = time.time()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            status_code = 500
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status=status_code
            ).inc()
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=path
            ).observe(duration)
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).dec()

    def _get_path_template(self, request: Request) -> str:
        """Get the path template instead of actual path to avoid high cardinality."""
        for route in request.app.routes:
            match, scope = route.matches(request.scope)
            if match == Match.FULL:
                return route.path
        return request.url.path


# =============================================================================
# Metrics Endpoint
# =============================================================================

def create_metrics_endpoint(app: FastAPI):
    """Add /metrics endpoint to FastAPI app."""

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        if not PROMETHEUS_AVAILABLE:
            return Response(
                content="Prometheus client not available",
                status_code=503
            )
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST
        )


# =============================================================================
# Helper Functions
# =============================================================================

def setup_metrics(app: FastAPI, service_name: str):
    """
    Setup Prometheus metrics for a FastAPI application.

    Args:
        app: FastAPI application instance
        service_name: Name of the service for labeling
    """
    if not PROMETHEUS_AVAILABLE:
        print(f"Metrics disabled for {service_name} - prometheus_client not installed")
        return

    # Add middleware
    app.add_middleware(PrometheusMiddleware, service_name=service_name)

    # Add metrics endpoint
    create_metrics_endpoint(app)

    print(f"Prometheus metrics enabled for {service_name}")


def track_db_query(operation: str, table: str = "unknown"):
    """Decorator to track database query metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return await func(*args, **kwargs)

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                DB_QUERY_COUNT.labels(operation=operation, table=table).inc()
                return result
            finally:
                duration = time.time() - start_time
                DB_QUERY_LATENCY.labels(operation=operation).observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return func(*args, **kwargs)

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                DB_QUERY_COUNT.labels(operation=operation, table=table).inc()
                return result
            finally:
                duration = time.time() - start_time
                DB_QUERY_LATENCY.labels(operation=operation).observe(duration)

        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def track_cache_operation(operation: str):
    """Decorator to track cache operation metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return await func(*args, **kwargs)

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                CACHE_LATENCY.labels(operation=operation).observe(duration)

        return wrapper
    return decorator


def record_cache_hit(cache_type: str = "redis"):
    """Record a cache hit."""
    if PROMETHEUS_AVAILABLE:
        CACHE_HIT_COUNT.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str = "redis"):
    """Record a cache miss."""
    if PROMETHEUS_AVAILABLE:
        CACHE_MISS_COUNT.labels(cache_type=cache_type).inc()


def record_order(status: str, value: float):
    """Record an order."""
    if PROMETHEUS_AVAILABLE:
        ORDER_COUNT.labels(status=status).inc()
        ORDER_VALUE.observe(value)


def set_active_users(count: int, role: str = "all"):
    """Set the number of active users."""
    if PROMETHEUS_AVAILABLE:
        ACTIVE_USERS.labels(role=role).set(count)


def set_db_pool_size(active: int, idle: int):
    """Set database connection pool metrics."""
    if PROMETHEUS_AVAILABLE:
        DB_CONNECTION_POOL.labels(state="active").set(active)
        DB_CONNECTION_POOL.labels(state="idle").set(idle)


# Helper for checking if function is coroutine
def asyncio_iscoroutinefunction(func):
    """Check if function is a coroutine function."""
    import asyncio
    return asyncio.iscoroutinefunction(func)
