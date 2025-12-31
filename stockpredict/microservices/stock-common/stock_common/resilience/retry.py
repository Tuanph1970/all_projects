"""
Retry pattern implementation with exponential backoff.

Provides automatic retry for transient failures with:
- Configurable retry count
- Exponential backoff with jitter
- Specific exception filtering
"""

import asyncio
import logging
import random
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type

from tenacity import (
    AsyncRetrying,
    RetryError as TenacityRetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """Exception raised when all retry attempts fail."""

    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Failed after {attempts} attempts. Last error: {last_exception}"
        )


async def retry_with_backoff(
    func: Callable,
    *args,
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    **kwargs,
) -> Any:
    """
    Execute a function with retry and exponential backoff.

    Args:
        func: Async function to call
        *args: Positional arguments for the function
        max_attempts: Maximum number of attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        retry_exceptions: Tuple of exceptions to retry on
        on_retry: Callback function called on each retry (attempt_number, exception)
        **kwargs: Keyword arguments for the function

    Returns:
        Result from the function

    Raises:
        RetryError: If all retry attempts fail
    """
    attempt = 0
    last_exception: Optional[Exception] = None

    async for attempt_info in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=min_wait, max=max_wait, jitter=min_wait / 2),
        retry=retry_if_exception_type(retry_exceptions),
        reraise=True,
    ):
        with attempt_info:
            attempt = attempt_info.retry_state.attempt_number
            try:
                return await func(*args, **kwargs)
            except retry_exceptions as e:
                last_exception = e
                if attempt < max_attempts:
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed: {e}. Retrying..."
                    )
                    if on_retry:
                        on_retry(attempt, e)
                raise

    raise RetryError(attempt, last_exception)


def retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
):
    """
    Decorator for applying retry pattern with exponential backoff.

    Example:
        @retry(max_attempts=3, retry_exceptions=(ConnectionError, TimeoutError))
        async def fetch_data():
            return await httpx.get("https://api.example.com")
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(
                func,
                *args,
                max_attempts=max_attempts,
                min_wait=min_wait,
                max_wait=max_wait,
                retry_exceptions=retry_exceptions,
                on_retry=on_retry,
                **kwargs,
            )

        return wrapper

    return decorator


class RetryableOperation:
    """
    Context manager for retryable operations with state tracking.

    Example:
        async with RetryableOperation("fetch-prices", max_attempts=3) as op:
            result = await fetch_prices()
            if not result:
                op.mark_failed(ValueError("No data"))
    """

    def __init__(
        self,
        name: str,
        max_attempts: int = 3,
        min_wait: float = 1.0,
        max_wait: float = 10.0,
    ):
        self.name = name
        self.max_attempts = max_attempts
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.attempt = 0
        self._should_retry = False
        self._last_exception: Optional[Exception] = None

    def mark_failed(self, exception: Exception) -> None:
        """Mark the current attempt as failed."""
        self._last_exception = exception
        self._should_retry = self.attempt < self.max_attempts

    @property
    def should_retry(self) -> bool:
        """Check if operation should be retried."""
        return self._should_retry

    async def __aenter__(self) -> "RetryableOperation":
        self.attempt += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            self._last_exception = exc_val
            self._should_retry = self.attempt < self.max_attempts

            if self._should_retry:
                wait_time = min(
                    self.max_wait,
                    self.min_wait * (2 ** (self.attempt - 1)) + random.uniform(0, self.min_wait / 2),
                )
                logger.warning(
                    f"Operation '{self.name}' attempt {self.attempt}/{self.max_attempts} "
                    f"failed: {exc_val}. Retrying in {wait_time:.2f}s..."
                )
                await asyncio.sleep(wait_time)
                return True  # Suppress exception

        return False
