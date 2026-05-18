"""Smoke tests for F-010 bootstrap — health probes and capability endpoint.

Uses httpx.AsyncClient with ASGITransport so no live DB is required.
The lifespan (which calls Base.metadata.create_all) is skipped via
app creation outside lifespan context.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch


@pytest.fixture()
def app():
    """Return the FastAPI app without running the lifespan."""
    from app.main import app as _app
    return _app


@pytest.mark.asyncio
async def test_liveness(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_health(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "decision" in data["service"]


@pytest.mark.asyncio
async def test_capabilities(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/stock_helper/api/v2/helper/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "decision-helper-service"
    assert isinstance(data["features"], list)


@pytest.mark.asyncio
async def test_metrics_endpoint(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert b"decision_helper_requests_total" in resp.content
