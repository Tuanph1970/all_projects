"""
Circuit Breaker pattern implementation.

Prevents cascade failures by:
1. Monitoring failure rates
2. Opening the circuit when failures exceed threshold
3. Rejecting requests while circuit is open
4. Half-opening to test recovery
5. Closing when service recovers
"""

import asyncio
import logging
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Type, Tuple

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit is open."""

    def __init__(self, circuit_name: str, time_remaining: float):
        self.circuit_name = circuit_name
        self.time_remaining = time_remaining
        super().__init__(
            f"Circuit '{circuit_name}' is open. Retry after {time_remaining:.1f} seconds."
        )


class CircuitBreaker:
    """
    Circuit Breaker implementation.

    States:
    - CLOSED: Normal operation, tracking failures
    - OPEN: Rejecting all requests, waiting for recovery timeout
    - HALF_OPEN: Allowing a test request to check if service recovered

    Example:
        breaker = CircuitBreaker("external-api", failure_threshold=5, recovery_timeout=30)

        try:
            result = await breaker.call(external_api_call, arg1, arg2)
        except CircuitBreakerOpen as e:
            # Handle circuit open (use fallback)
            result = fallback_value
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 1,
        excluded_exceptions: Tuple[Type[Exception], ...] = (),
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker name (for logging)
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before half-opening
            success_threshold: Successes needed in half-open to close
            excluded_exceptions: Exceptions that don't count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.excluded_exceptions = excluded_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self._state == CircuitState.OPEN

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from the function

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Any exception from the function
        """
        async with self._lock:
            self._check_state()

            if self._state == CircuitState.OPEN:
                time_remaining = self.recovery_timeout - (time.time() - self._last_failure_time)
                raise CircuitBreakerOpen(self.name, time_remaining)

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.excluded_exceptions:
            # Don't count excluded exceptions as failures
            raise
        except Exception as e:
            await self._on_failure()
            raise

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._close()
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._open()
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._open()

    def _check_state(self) -> None:
        """Check and potentially transition state."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time is not None:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    self._half_open()

    def _open(self) -> None:
        """Open the circuit."""
        self._state = CircuitState.OPEN
        logger.warning(
            f"Circuit '{self.name}' opened after {self._failure_count} failures"
        )

    def _half_open(self) -> None:
        """Half-open the circuit for testing."""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        logger.info(f"Circuit '{self.name}' half-opened, testing recovery")

    def _close(self) -> None:
        """Close the circuit."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info(f"Circuit '{self.name}' closed, service recovered")

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        logger.info(f"Circuit '{self.name}' manually reset")


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    fallback: Optional[Callable] = None,
):
    """
    Decorator for applying circuit breaker pattern.

    Example:
        @circuit_breaker("external-api", failure_threshold=5, fallback=lambda: None)
        async def call_external_api():
            return await httpx.get("https://api.example.com")
    """
    breaker = CircuitBreaker(name, failure_threshold, recovery_timeout)

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpen:
                if fallback is not None:
                    logger.warning(
                        f"Circuit '{name}' open, using fallback for {func.__name__}"
                    )
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(*args, **kwargs)
                    return fallback(*args, **kwargs)
                raise

        wrapper.circuit_breaker = breaker
        return wrapper

    return decorator
