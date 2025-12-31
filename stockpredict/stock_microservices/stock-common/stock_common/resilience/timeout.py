"""
Timeout pattern implementation.

Provides:
- Request deadline enforcement
- Configurable timeout per operation
- Timeout context manager and decorator
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Exception raised when operation times out."""

    def __init__(self, operation_name: str, timeout: float):
        self.operation_name = operation_name
        self.timeout = timeout
        super().__init__(
            f"Operation '{operation_name}' timed out after {timeout:.2f} seconds"
        )


class Timeout:
    """
    Timeout context manager for async operations.

    Example:
        async with Timeout("fetch-data", seconds=5.0):
            data = await fetch_data()
    """

    def __init__(
        self,
        name: str,
        seconds: float,
        on_timeout: Optional[Callable[[], Any]] = None,
    ):
        """
        Initialize timeout.

        Args:
            name: Operation name (for logging)
            seconds: Timeout in seconds
            on_timeout: Optional callback when timeout occurs
        """
        self.name = name
        self.seconds = seconds
        self.on_timeout = on_timeout
        self._task: Optional[asyncio.Task] = None

    async def __aenter__(self) -> "Timeout":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is asyncio.TimeoutError:
            logger.warning(f"Operation '{self.name}' timed out after {self.seconds}s")
            if self.on_timeout:
                if asyncio.iscoroutinefunction(self.on_timeout):
                    await self.on_timeout()
                else:
                    self.on_timeout()
            raise TimeoutError(self.name, self.seconds) from exc_val
        return False


async def with_timeout(
    func: Callable,
    *args,
    timeout_seconds: float,
    operation_name: str = "unknown",
    on_timeout: Optional[Callable[[], Any]] = None,
    **kwargs,
) -> Any:
    """
    Execute a function with a timeout.

    Args:
        func: Async function to execute
        *args: Positional arguments
        timeout_seconds: Timeout in seconds
        operation_name: Name for logging
        on_timeout: Callback when timeout occurs
        **kwargs: Keyword arguments

    Returns:
        Result from the function

    Raises:
        TimeoutError: If operation times out
    """
    try:
        return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning(f"Operation '{operation_name}' timed out after {timeout_seconds}s")
        if on_timeout:
            if asyncio.iscoroutinefunction(on_timeout):
                await on_timeout()
            else:
                on_timeout()
        raise TimeoutError(operation_name, timeout_seconds)


def timeout(
    seconds: float,
    operation_name: Optional[str] = None,
    on_timeout: Optional[Callable[[], Any]] = None,
    fallback: Optional[Callable] = None,
):
    """
    Decorator for applying timeout to async functions.

    Example:
        @timeout(seconds=5.0, fallback=lambda: None)
        async def slow_operation():
            await asyncio.sleep(10)
            return "done"
    """

    def decorator(func: Callable):
        name = operation_name or func.__name__

        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await with_timeout(
                    func,
                    *args,
                    timeout_seconds=seconds,
                    operation_name=name,
                    on_timeout=on_timeout,
                    **kwargs,
                )
            except TimeoutError:
                if fallback is not None:
                    logger.warning(f"Using fallback for timed-out operation '{name}'")
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(*args, **kwargs)
                    return fallback(*args, **kwargs)
                raise

        return wrapper

    return decorator


class DeadlineManager:
    """
    Manager for tracking request deadlines across service calls.

    Propagates remaining deadline time through service calls to ensure
    cascading timeouts respect the original request deadline.

    Example:
        deadline = DeadlineManager(total_seconds=30.0)

        # First call uses some time
        async with deadline.track("service-a"):
            await call_service_a()

        # Second call gets remaining time
        remaining = deadline.remaining
        async with deadline.track("service-b"):
            await call_service_b()
    """

    def __init__(self, total_seconds: float):
        """
        Initialize deadline manager.

        Args:
            total_seconds: Total deadline in seconds
        """
        self.total_seconds = total_seconds
        self._start_time: Optional[float] = None
        self._current_operation: Optional[str] = None

    @property
    def remaining(self) -> float:
        """Get remaining time until deadline."""
        if self._start_time is None:
            return self.total_seconds
        import time
        elapsed = time.time() - self._start_time
        return max(0, self.total_seconds - elapsed)

    @property
    def is_expired(self) -> bool:
        """Check if deadline has expired."""
        return self.remaining <= 0

    def start(self) -> None:
        """Start tracking the deadline."""
        import time
        self._start_time = time.time()

    def track(self, operation_name: str) -> "DeadlineContext":
        """Create a context for tracking an operation within the deadline."""
        if self._start_time is None:
            self.start()
        return DeadlineContext(self, operation_name)


class DeadlineContext:
    """Context manager for tracking operations within a deadline."""

    def __init__(self, manager: DeadlineManager, operation_name: str):
        self.manager = manager
        self.operation_name = operation_name

    async def __aenter__(self) -> "DeadlineContext":
        if self.manager.is_expired:
            raise TimeoutError(self.operation_name, 0)
        self.manager._current_operation = self.operation_name
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.manager._current_operation = None
        if exc_type is asyncio.TimeoutError:
            raise TimeoutError(self.operation_name, self.manager.remaining)
