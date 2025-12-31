"""
Stock Common - Shared library for Stock Helper microservices.

This library provides common utilities for building microservices:
- Event bus (RabbitMQ integration)
- Resilience patterns (circuit breaker, retry, bulkhead)
- Authentication (JWT middleware)
- Observability (health checks, distributed tracing, metrics)
- Database utilities
"""

__version__ = "0.1.0"

from stock_common.config import ServiceConfig, get_config

__all__ = [
    "__version__",
    "ServiceConfig",
    "get_config",
]
