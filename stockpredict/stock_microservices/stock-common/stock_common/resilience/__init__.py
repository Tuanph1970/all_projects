"""
Resilience patterns for microservices.

Provides:
- Circuit Breaker: Prevent cascade failures
- Retry: Automatic retry with exponential backoff
- Bulkhead: Resource isolation
- Timeout: Request deadline enforcement
"""

from stock_common.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    circuit_breaker,
)
from stock_common.resilience.retry import retry_with_backoff, RetryError
from stock_common.resilience.bulkhead import Bulkhead, BulkheadFull
from stock_common.resilience.timeout import timeout, TimeoutError
from stock_common.resilience.resilient_client import ResilientHTTPClient

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "circuit_breaker",
    "retry_with_backoff",
    "RetryError",
    "Bulkhead",
    "BulkheadFull",
    "timeout",
    "TimeoutError",
    "ResilientHTTPClient",
]
