"""
Resilient HTTP client combining all resilience patterns.

Provides:
- Circuit breaker for each target service
- Retry with exponential backoff
- Timeout enforcement
- Bulkhead for concurrent request limiting
"""

import logging
from typing import Any, Dict, Optional, Type, Tuple
from urllib.parse import urlparse

import httpx

from stock_common.config import ResilienceConfig
from stock_common.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from stock_common.resilience.bulkhead import Bulkhead, BulkheadFull
from stock_common.resilience.retry import retry_with_backoff
from stock_common.resilience.timeout import TimeoutError, with_timeout

logger = logging.getLogger(__name__)


class ResilientHTTPClient:
    """
    HTTP client with built-in resilience patterns.

    Combines:
    - Circuit breaker per service
    - Retry with exponential backoff
    - Request timeout
    - Bulkhead for concurrency limiting

    Example:
        client = ResilientHTTPClient(service_name="prediction-service")

        # GET request with resilience
        response = await client.get(
            "http://stock-data-service:8001/api/v1/stocks/VIC",
            timeout=5.0
        )

        # POST request with resilience
        response = await client.post(
            "http://prediction-service:8002/api/v1/predict",
            json={"ticker": "VIC", "days": 30}
        )
    """

    def __init__(
        self,
        service_name: str,
        config: Optional[ResilienceConfig] = None,
        base_headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize resilient HTTP client.

        Args:
            service_name: Name of the calling service (for tracing)
            config: Resilience configuration
            base_headers: Default headers for all requests
        """
        self.service_name = service_name
        self.config = config or ResilienceConfig()
        self.base_headers = base_headers or {}
        self.base_headers["X-Service-Name"] = service_name

        # Circuit breakers per target service
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Bulkhead for concurrent requests
        self._bulkhead = Bulkhead(
            name=f"{service_name}-http",
            max_concurrent=self.config.bulkhead_max_concurrent,
        )

        # HTTP client
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout_default),
            headers=self.base_headers,
        )

    def _get_circuit_breaker(self, url: str) -> CircuitBreaker:
        """Get or create circuit breaker for a target service."""
        parsed = urlparse(url)
        service_key = f"{parsed.scheme}://{parsed.netloc}"

        if service_key not in self._circuit_breakers:
            self._circuit_breakers[service_key] = CircuitBreaker(
                name=service_key,
                failure_threshold=self.config.circuit_breaker_failure_threshold,
                recovery_timeout=self.config.circuit_breaker_recovery_timeout,
            )

        return self._circuit_breakers[service_key]

    async def request(
        self,
        method: str,
        url: str,
        *,
        timeout: Optional[float] = None,
        retry_count: Optional[int] = None,
        retry_exceptions: Tuple[Type[Exception], ...] = (
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
        ),
        skip_circuit_breaker: bool = False,
        skip_retry: bool = False,
        skip_bulkhead: bool = False,
        **kwargs,
    ) -> httpx.Response:
        """
        Make an HTTP request with resilience patterns.

        Args:
            method: HTTP method
            url: Target URL
            timeout: Request timeout (overrides default)
            retry_count: Number of retries (overrides default)
            retry_exceptions: Exceptions to retry on
            skip_circuit_breaker: Disable circuit breaker
            skip_retry: Disable retry
            skip_bulkhead: Disable bulkhead
            **kwargs: Additional httpx request arguments

        Returns:
            HTTP response

        Raises:
            CircuitBreakerOpen: If circuit is open
            BulkheadFull: If bulkhead is full
            TimeoutError: If request times out
            httpx.HTTPError: On HTTP errors after retries
        """
        timeout = timeout or self.config.timeout_default
        retry_count = retry_count if retry_count is not None else self.config.retry_max_attempts

        circuit_breaker = self._get_circuit_breaker(url)

        async def make_request() -> httpx.Response:
            """Core request function."""
            return await self._client.request(
                method,
                url,
                timeout=httpx.Timeout(timeout),
                **kwargs,
            )

        async def request_with_circuit_breaker() -> httpx.Response:
            """Request with circuit breaker."""
            if skip_circuit_breaker:
                return await make_request()

            return await circuit_breaker.call(make_request)

        async def request_with_retry() -> httpx.Response:
            """Request with retry."""
            if skip_retry or retry_count == 0:
                return await request_with_circuit_breaker()

            return await retry_with_backoff(
                request_with_circuit_breaker,
                max_attempts=retry_count,
                min_wait=self.config.retry_min_wait,
                max_wait=self.config.retry_max_wait,
                retry_exceptions=retry_exceptions,
            )

        async def request_with_bulkhead() -> httpx.Response:
            """Request with bulkhead."""
            if skip_bulkhead:
                return await request_with_retry()

            return await self._bulkhead.execute(request_with_retry)

        # Execute with all patterns
        try:
            response = await request_with_bulkhead()

            # Check for server errors (may indicate service issues)
            if response.status_code >= 500:
                logger.warning(
                    f"Server error from {url}: {response.status_code}"
                )

            return response

        except CircuitBreakerOpen as e:
            logger.warning(f"Circuit breaker open for {url}: {e}")
            raise
        except BulkheadFull as e:
            logger.warning(f"Bulkhead full for {url}: {e}")
            raise
        except httpx.TimeoutException as e:
            logger.warning(f"Timeout for {url}: {e}")
            raise TimeoutError(url, timeout)
        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")
            raise

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make a GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make a POST request."""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        """Make a PUT request."""
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> httpx.Response:
        """Make a PATCH request."""
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """Make a DELETE request."""
        return await self.request("DELETE", url, **kwargs)

    def get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            service: {
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "is_open": cb.is_open,
            }
            for service, cb in self._circuit_breakers.items()
        }

    def get_bulkhead_status(self) -> Dict[str, int]:
        """Get bulkhead status."""
        return {
            "active": self._bulkhead.active_count,
            "queue": self._bulkhead.queue_count,
            "available": self._bulkhead.available_permits,
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "ResilientHTTPClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
