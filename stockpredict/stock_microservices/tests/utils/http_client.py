"""
HTTP client utilities for testing.

Provides a wrapper around httpx with common functionality:
- Automatic token handling
- Response logging
- Performance metrics
- Retry logic
"""

import time
from typing import Optional, Any
from dataclasses import dataclass, field

import httpx


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    url: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


class TestClient:
    """Enhanced HTTP client for testing microservices."""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        timeout: float = 30.0
    ):
        self.base_url = base_url
        self.token = token
        self.timeout = timeout
        self.metrics: list[RequestMetrics] = []
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "TestClient":
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    def set_token(self, token: str):
        """Set or update the authentication token."""
        self.token = token
        if self._client:
            self._client.headers["Authorization"] = f"Bearer {token}"

    def clear_token(self):
        """Clear the authentication token."""
        self.token = None
        if self._client:
            self._client.headers.pop("Authorization", None)

    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make a request and record metrics."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with context.")

        start_time = time.perf_counter()
        response = await self._client.request(method, url, **kwargs)
        duration = (time.perf_counter() - start_time) * 1000  # Convert to ms

        self.metrics.append(RequestMetrics(
            url=url,
            method=method,
            status_code=response.status_code,
            duration_ms=duration
        ))

        return response

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

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary of all request metrics."""
        if not self.metrics:
            return {"total_requests": 0}

        durations = [m.duration_ms for m in self.metrics]
        status_codes = [m.status_code for m in self.metrics]

        return {
            "total_requests": len(self.metrics),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "success_rate": len([s for s in status_codes if 200 <= s < 400]) / len(status_codes),
            "error_count": len([s for s in status_codes if s >= 400]),
        }

    def clear_metrics(self):
        """Clear collected metrics."""
        self.metrics = []


class RetryClient(TestClient):
    """HTTP client with automatic retry logic."""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        super().__init__(base_url, token, timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make a request with automatic retry on failure."""
        import asyncio

        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = await super().request(method, url, **kwargs)
                # Retry on server errors
                if response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                return response
            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise

        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry loop exit")
