"""Health & metrics smoke tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["service"] == "journal-service"


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient):
    r = await client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_metrics_exposed(client: AsyncClient):
    r = await client.get("/metrics")
    assert r.status_code == 200
    assert b"journal_service_requests_total" in r.content


@pytest.mark.asyncio
async def test_service_info(client: AsyncClient):
    r = await client.get("/stock_helper/api/v2/journal/info")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "journal-service"
    assert "endpoints" in body
