"""Verify the slowapi rate limiter fires on the protected endpoints.

The base conftest disables the limiter at module import time so the
other tests aren't fighting the 5/minute budget. This file
re-enables it via a fresh in-process Limiter and confirms the
configured endpoints (/auth/login, /auth/register, /auth/reset-password)
respond with 429 once the budget is spent.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.api.dependencies import get_db
from app.api.rate_limit import limiter
from app.main import app
from app.models.domain import Base


PREFIX = "/stock_helper/api/v2/auth"
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def rate_limited_client():
    """Client with rate limiter forcibly enabled and budget reset.
    Uses a fresh in-memory DB so register/login work without interfering
    with the conftest's shared fixtures.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db

    # Force-enable the limiter for this test only, then reset its bucket
    # storage so we start from a known state.
    limiter.enabled = True
    limiter.reset()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test",
        ) as client:
            yield client
    finally:
        limiter.enabled = False
        limiter.reset()
        app.dependency_overrides.clear()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.mark.asyncio
async def test_login_returns_429_after_budget_spent(rate_limited_client: AsyncClient):
    """5/minute budget — the 6th attempt (any attempt, even with bad
    credentials) must return 429."""
    payload = {"email": "ghost@example.com", "password": "Wrong1234"}
    statuses = []
    for _ in range(6):
        r = await rate_limited_client.post(f"{PREFIX}/login", json=payload)
        statuses.append(r.status_code)

    # First 5 fail with 401 (bad creds), the 6th hits the limiter with 429.
    assert statuses[:5].count(401) == 5
    assert statuses[5] == 429


@pytest.mark.asyncio
async def test_register_returns_429_after_budget_spent(rate_limited_client: AsyncClient):
    statuses = []
    for i in range(6):
        # Different email each time so the validator doesn't 409 us first
        payload = {
            "email": f"user{i}@example.com",
            "username": f"user{i}",
            "password": "Strong1234",
        }
        r = await rate_limited_client.post(f"{PREFIX}/register", json=payload)
        statuses.append(r.status_code)

    assert statuses[:5].count(201) == 5
    assert statuses[5] == 429


@pytest.mark.asyncio
async def test_reset_password_returns_429_after_budget_spent(rate_limited_client: AsyncClient):
    """Important — reset-password is the enumeration vector; rate limiting
    here keeps an attacker from probing email-existence en masse."""
    statuses = []
    for _ in range(6):
        r = await rate_limited_client.post(
            f"{PREFIX}/reset-password",
            json={"email": "anyone@example.com"},
        )
        statuses.append(r.status_code)

    # First 5 return the generic 200 message, 6th is rate-limited.
    assert statuses[:5].count(200) == 5
    assert statuses[5] == 429


@pytest.mark.asyncio
async def test_refresh_endpoint_is_not_rate_limited(rate_limited_client: AsyncClient):
    """Sanity: only the brute-force-prone routes are gated. /refresh keeps
    the legitimate token-rotation flow working under load."""
    bad_refresh = {"refresh_token": "not-a-real-token"}
    for _ in range(10):
        r = await rate_limited_client.post(f"{PREFIX}/refresh", json=bad_refresh)
        # 401 is the expected rejection; 429 would mean we over-applied the limiter.
        assert r.status_code == 401, r.text
