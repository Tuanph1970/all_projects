"""
Failover and Circuit Breaker Configuration

Provides failover, circuit breaker, and retry configurations for resilient services.
"""
import os
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, TypeVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
import random

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""

    # Failure thresholds
    failure_threshold: int = 5           # Failures before opening
    success_threshold: int = 3           # Successes in half-open to close
    failure_rate_threshold: float = 0.5  # 50% failure rate threshold

    # Timing
    timeout_seconds: int = 30            # Time to wait before half-open
    half_open_max_requests: int = 3      # Requests to allow in half-open

    # Monitoring window
    window_size_seconds: int = 60        # Window for failure rate calculation
    min_requests_in_window: int = 10     # Minimum requests before evaluating

    # Exclusions
    excluded_exceptions: tuple = field(default_factory=lambda: (
        ValueError,
        TypeError,
    ))


@dataclass
class RetryConfig:
    """Retry configuration"""

    # Retry limits
    max_attempts: int = 3
    max_delay_seconds: float = 30.0

    # Backoff settings
    initial_delay_seconds: float = 0.1
    backoff_multiplier: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd

    # Retry conditions
    retryable_status_codes: tuple = field(default_factory=lambda: (
        408,  # Request Timeout
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    ))

    retryable_exceptions: tuple = field(default_factory=lambda: (
        ConnectionError,
        TimeoutError,
    ))


@dataclass
class FailoverConfig:
    """Failover configuration"""

    # Primary/secondary settings
    failover_enabled: bool = True
    failback_enabled: bool = True

    # Failover timing
    failover_timeout_seconds: int = 10
    failback_delay_seconds: int = 300  # Wait before trying primary again

    # Health check for failback
    health_check_interval_seconds: int = 30
    health_check_consecutive_successes: int = 3

    # Components
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)


class CircuitBreaker:
    """
    Circuit breaker implementation

    Prevents cascading failures by stopping requests to failing services.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: datetime = datetime.now()
        self.request_count_in_window = 0
        self.failure_count_in_window = 0
        self.half_open_requests = 0

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        return self.state == CircuitState.HALF_OPEN

    def should_allow_request(self) -> bool:
        """Check if request should be allowed"""
        if self.is_closed:
            return True

        if self.is_open:
            # Check if timeout has passed
            if self.last_state_change:
                elapsed = (datetime.now() - self.last_state_change).total_seconds()
                if elapsed >= self.config.timeout_seconds:
                    self._transition_to_half_open()
                    return True
            return False

        if self.is_half_open:
            # Allow limited requests in half-open
            if self.half_open_requests < self.config.half_open_max_requests:
                self.half_open_requests += 1
                return True
            return False

        return False

    def record_success(self):
        """Record a successful request"""
        self.request_count_in_window += 1

        if self.is_half_open:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        else:
            self.failure_count = 0  # Reset consecutive failures

    def record_failure(self, exception: Exception = None):
        """Record a failed request"""
        # Check if exception should be excluded
        if exception and isinstance(exception, self.config.excluded_exceptions):
            return

        self.failure_count += 1
        self.failure_count_in_window += 1
        self.request_count_in_window += 1
        self.last_failure_time = datetime.now()

        if self.is_half_open:
            self._transition_to_open()
        elif self.is_closed:
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()
            elif self._check_failure_rate():
                self._transition_to_open()

    def _check_failure_rate(self) -> bool:
        """Check if failure rate exceeds threshold"""
        if self.request_count_in_window < self.config.min_requests_in_window:
            return False

        failure_rate = self.failure_count_in_window / self.request_count_in_window
        return failure_rate >= self.config.failure_rate_threshold

    def _transition_to_open(self):
        """Transition to open state"""
        logger.warning(f"Circuit {self.name} transitioning to OPEN")
        self.state = CircuitState.OPEN
        self.last_state_change = datetime.now()
        self.success_count = 0

    def _transition_to_half_open(self):
        """Transition to half-open state"""
        logger.info(f"Circuit {self.name} transitioning to HALF_OPEN")
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = datetime.now()
        self.half_open_requests = 0
        self.success_count = 0

    def _transition_to_closed(self):
        """Transition to closed state"""
        logger.info(f"Circuit {self.name} transitioning to CLOSED")
        self.state = CircuitState.CLOSED
        self.last_state_change = datetime.now()
        self.failure_count = 0
        self.failure_count_in_window = 0
        self.request_count_in_window = 0

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.last_state_change.isoformat(),
        }


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open"""
    pass


def with_circuit_breaker(circuit: CircuitBreaker):
    """Decorator to wrap function with circuit breaker"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not circuit.should_allow_request():
                raise CircuitBreakerOpen(f"Circuit {circuit.name} is open")
            try:
                result = await func(*args, **kwargs)
                circuit.record_success()
                return result
            except Exception as e:
                circuit.record_failure(e)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not circuit.should_allow_request():
                raise CircuitBreakerOpen(f"Circuit {circuit.name} is open")
            try:
                result = func(*args, **kwargs)
                circuit.record_success()
                return result
            except Exception as e:
                circuit.record_failure(e)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


async def retry_with_backoff(
    func: Callable,
    config: Optional[RetryConfig] = None,
    *args,
    **kwargs
) -> T:
    """
    Execute function with retry and exponential backoff

    Args:
        func: Async function to execute
        config: Retry configuration
        *args, **kwargs: Arguments to pass to function

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    config = config or RetryConfig()
    last_exception = None
    delay = config.initial_delay_seconds

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1} failed: {e}")

            if attempt < config.max_attempts - 1:
                # Calculate delay with optional jitter
                actual_delay = delay
                if config.jitter:
                    actual_delay *= (0.5 + random.random())

                actual_delay = min(actual_delay, config.max_delay_seconds)
                await asyncio.sleep(actual_delay)

                # Increase delay for next attempt
                delay *= config.backoff_multiplier
        except Exception as e:
            # Non-retryable exception
            raise

    raise last_exception


def with_retry(config: Optional[RetryConfig] = None):
    """Decorator to wrap function with retry logic"""
    config = config or RetryConfig()

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_with_backoff(func, config, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, use a simple retry loop
            last_exception = None
            delay = config.initial_delay_seconds

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_attempts - 1:
                        import time
                        actual_delay = delay
                        if config.jitter:
                            actual_delay *= (0.5 + random.random())
                        actual_delay = min(actual_delay, config.max_delay_seconds)
                        time.sleep(actual_delay)
                        delay *= config.backoff_multiplier

            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


class FailoverManager:
    """
    Manages failover between primary and secondary services

    Automatically routes traffic to secondary when primary fails,
    and fails back when primary recovers.
    """

    def __init__(
        self,
        primary_url: str,
        secondary_url: str,
        config: Optional[FailoverConfig] = None
    ):
        self.primary_url = primary_url
        self.secondary_url = secondary_url
        self.config = config or FailoverConfig()
        self.using_primary = True
        self.primary_circuit = CircuitBreaker("primary", self.config.circuit_breaker)
        self.secondary_circuit = CircuitBreaker("secondary", self.config.circuit_breaker)
        self.failback_check_count = 0
        self.last_failback_check: Optional[datetime] = None

    @property
    def current_url(self) -> str:
        """Get currently active service URL"""
        return self.primary_url if self.using_primary else self.secondary_url

    @property
    def current_circuit(self) -> CircuitBreaker:
        """Get circuit breaker for current service"""
        return self.primary_circuit if self.using_primary else self.secondary_circuit

    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> T:
        """
        Execute function with failover support

        Args:
            func: Async function that takes URL as first argument
            *args, **kwargs: Additional arguments

        Returns:
            Function result
        """
        # Try primary first (if using it)
        if self.using_primary:
            if self.primary_circuit.should_allow_request():
                try:
                    result = await retry_with_backoff(
                        func,
                        self.config.retry,
                        self.primary_url,
                        *args,
                        **kwargs
                    )
                    self.primary_circuit.record_success()
                    return result
                except Exception as e:
                    self.primary_circuit.record_failure(e)
                    if self.config.failover_enabled:
                        self._failover_to_secondary()
                    else:
                        raise

        # Try secondary
        if self.secondary_circuit.should_allow_request():
            try:
                result = await retry_with_backoff(
                    func,
                    self.config.retry,
                    self.secondary_url,
                    *args,
                    **kwargs
                )
                self.secondary_circuit.record_success()

                # Check if we should failback
                if not self.using_primary and self.config.failback_enabled:
                    await self._check_failback()

                return result
            except Exception as e:
                self.secondary_circuit.record_failure(e)
                raise

        raise CircuitBreakerOpen("Both primary and secondary circuits are open")

    def _failover_to_secondary(self):
        """Switch to secondary service"""
        if self.using_primary:
            logger.warning("Failing over to secondary service")
            self.using_primary = False
            self.failback_check_count = 0

    async def _check_failback(self):
        """Check if primary has recovered and failback"""
        now = datetime.now()

        # Rate limit failback checks
        if self.last_failback_check:
            elapsed = (now - self.last_failback_check).total_seconds()
            if elapsed < self.config.health_check_interval_seconds:
                return

        self.last_failback_check = now

        # Check primary health
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.primary_url}/health/ready")
                if response.status_code == 200:
                    self.failback_check_count += 1
                    if self.failback_check_count >= self.config.health_check_consecutive_successes:
                        logger.info("Failing back to primary service")
                        self.using_primary = True
                        self.primary_circuit._transition_to_closed()
                else:
                    self.failback_check_count = 0
        except Exception:
            self.failback_check_count = 0

    def get_status(self) -> Dict[str, Any]:
        """Get failover manager status"""
        return {
            "using_primary": self.using_primary,
            "current_url": self.current_url,
            "primary_circuit": self.primary_circuit.get_status(),
            "secondary_circuit": self.secondary_circuit.get_status(),
            "failback_check_count": self.failback_check_count,
        }


# Pre-configured failover managers for services
_failover_managers: Dict[str, FailoverManager] = {}


def get_failover_manager(
    service_name: str,
    primary_url: str,
    secondary_url: str
) -> FailoverManager:
    """Get or create failover manager for a service"""
    if service_name not in _failover_managers:
        _failover_managers[service_name] = FailoverManager(
            primary_url,
            secondary_url,
            FailoverConfig()
        )
    return _failover_managers[service_name]
