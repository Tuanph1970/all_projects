"""
Bulkhead pattern implementation for resource isolation.

Provides:
- Concurrent request limiting per operation type
- Queue-based request handling
- Resource isolation to prevent cascade failures
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class BulkheadFull(Exception):
    """Exception raised when bulkhead is at capacity."""

    def __init__(self, bulkhead_name: str, max_concurrent: int, queue_size: int):
        self.bulkhead_name = bulkhead_name
        self.max_concurrent = max_concurrent
        self.queue_size = queue_size
        super().__init__(
            f"Bulkhead '{bulkhead_name}' is full. "
            f"Max concurrent: {max_concurrent}, Queue size: {queue_size}"
        )


class Bulkhead:
    """
    Bulkhead pattern for isolating concurrent operations.

    Limits the number of concurrent requests to a specific operation,
    preventing one slow or failing operation from consuming all resources.

    Example:
        # Create separate bulkheads for different operations
        prediction_bulkhead = Bulkhead("predictions", max_concurrent=5)
        data_sync_bulkhead = Bulkhead("data-sync", max_concurrent=10)

        async def predict(model_id: int):
            async with prediction_bulkhead:
                return await run_prediction(model_id)
    """

    def __init__(
        self,
        name: str,
        max_concurrent: int = 10,
        max_queue: int = 100,
        timeout: Optional[float] = None,
    ):
        """
        Initialize bulkhead.

        Args:
            name: Bulkhead name (for logging/metrics)
            max_concurrent: Maximum concurrent operations
            max_queue: Maximum waiting queue size (0 = no queue)
            timeout: Maximum time to wait in queue (None = no timeout)
        """
        self.name = name
        self.max_concurrent = max_concurrent
        self.max_queue = max_queue
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue_count = 0
        self._active_count = 0
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        """Number of currently active operations."""
        return self._active_count

    @property
    def queue_count(self) -> int:
        """Number of operations waiting in queue."""
        return self._queue_count

    @property
    def available_permits(self) -> int:
        """Number of available permits."""
        return self.max_concurrent - self._active_count

    async def acquire(self) -> bool:
        """
        Acquire a permit from the bulkhead.

        Returns:
            True if permit acquired

        Raises:
            BulkheadFull: If bulkhead and queue are full
            asyncio.TimeoutError: If timeout exceeded while waiting
        """
        async with self._lock:
            if self._active_count >= self.max_concurrent:
                if self._queue_count >= self.max_queue:
                    raise BulkheadFull(self.name, self.max_concurrent, self.max_queue)
                self._queue_count += 1

        try:
            if self.timeout:
                await asyncio.wait_for(self._semaphore.acquire(), timeout=self.timeout)
            else:
                await self._semaphore.acquire()
        finally:
            async with self._lock:
                if self._queue_count > 0:
                    self._queue_count -= 1

        async with self._lock:
            self._active_count += 1

        logger.debug(
            f"Bulkhead '{self.name}': acquired permit. "
            f"Active: {self._active_count}/{self.max_concurrent}"
        )
        return True

    def release(self) -> None:
        """Release a permit back to the bulkhead."""
        self._semaphore.release()
        self._active_count = max(0, self._active_count - 1)
        logger.debug(
            f"Bulkhead '{self.name}': released permit. "
            f"Active: {self._active_count}/{self.max_concurrent}"
        )

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function within the bulkhead.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from the function
        """
        await self.acquire()
        try:
            return await func(*args, **kwargs)
        finally:
            self.release()

    async def __aenter__(self) -> "Bulkhead":
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


class BulkheadManager:
    """
    Manager for multiple bulkheads.

    Provides a central registry for bulkheads across the application.

    Example:
        manager = BulkheadManager()
        manager.register("predictions", max_concurrent=5)
        manager.register("data-sync", max_concurrent=10)

        async with manager.get("predictions"):
            await run_prediction()
    """

    def __init__(self):
        self._bulkheads: Dict[str, Bulkhead] = {}

    def register(
        self,
        name: str,
        max_concurrent: int = 10,
        max_queue: int = 100,
        timeout: Optional[float] = None,
    ) -> Bulkhead:
        """Register a new bulkhead."""
        bulkhead = Bulkhead(name, max_concurrent, max_queue, timeout)
        self._bulkheads[name] = bulkhead
        return bulkhead

    def get(self, name: str) -> Bulkhead:
        """Get a bulkhead by name."""
        if name not in self._bulkheads:
            raise KeyError(f"Bulkhead '{name}' not registered")
        return self._bulkheads[name]

    def get_or_create(
        self,
        name: str,
        max_concurrent: int = 10,
        max_queue: int = 100,
        timeout: Optional[float] = None,
    ) -> Bulkhead:
        """Get existing bulkhead or create new one."""
        if name not in self._bulkheads:
            return self.register(name, max_concurrent, max_queue, timeout)
        return self._bulkheads[name]

    def stats(self) -> Dict[str, Dict[str, int]]:
        """Get stats for all bulkheads."""
        return {
            name: {
                "active": bh.active_count,
                "queue": bh.queue_count,
                "available": bh.available_permits,
                "max_concurrent": bh.max_concurrent,
            }
            for name, bh in self._bulkheads.items()
        }


def bulkhead(
    name: str,
    max_concurrent: int = 10,
    max_queue: int = 100,
    timeout: Optional[float] = None,
    fallback: Optional[Callable] = None,
):
    """
    Decorator for applying bulkhead pattern.

    Example:
        @bulkhead("predictions", max_concurrent=5, fallback=lambda: None)
        async def run_prediction(model_id: int):
            return await heavy_computation(model_id)
    """
    bh = Bulkhead(name, max_concurrent, max_queue, timeout)

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await bh.execute(func, *args, **kwargs)
            except BulkheadFull:
                if fallback is not None:
                    logger.warning(
                        f"Bulkhead '{name}' full, using fallback for {func.__name__}"
                    )
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(*args, **kwargs)
                    return fallback(*args, **kwargs)
                raise

        wrapper.bulkhead = bh
        return wrapper

    return decorator


# Global bulkhead manager
_bulkhead_manager = BulkheadManager()


def get_bulkhead_manager() -> BulkheadManager:
    """Get the global bulkhead manager."""
    return _bulkhead_manager
