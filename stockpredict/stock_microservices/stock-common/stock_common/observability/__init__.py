"""
Observability module for microservices.

Provides:
- Health checks (liveness, readiness)
- Distributed tracing (OpenTelemetry + Jaeger)
- Metrics (Prometheus)
- Structured logging
"""

from stock_common.observability.health import (
    HealthCheck,
    HealthCheckRegistry,
    HealthStatus,
    create_health_router,
)
from stock_common.observability.tracing import (
    setup_tracing,
    get_tracer,
    trace_span,
    inject_trace_context,
    extract_trace_context,
)
from stock_common.observability.metrics import (
    MetricsManager,
    setup_metrics,
    create_metrics_endpoint,
)
from stock_common.observability.logging import (
    setup_logging,
    get_logger,
    LogContext,
)

__all__ = [
    # Health
    "HealthCheck",
    "HealthCheckRegistry",
    "HealthStatus",
    "create_health_router",
    # Tracing
    "setup_tracing",
    "get_tracer",
    "trace_span",
    "inject_trace_context",
    "extract_trace_context",
    # Metrics
    "MetricsManager",
    "setup_metrics",
    "create_metrics_endpoint",
    # Logging
    "setup_logging",
    "get_logger",
    "LogContext",
]
