"""Shared test fixtures for journal-service.

Pattern mirrors auth-service: in-memory SQLite (aiosqlite), one fresh schema
per test, FastAPI app with the get_db dependency overridden, and a JWT helper
that signs with the same secret the service validates against.
"""
import os
from datetime import datetime, timedelta

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure the service settings are loaded with a deterministic JWT secret BEFORE
# `app.main` imports run — get_settings() is lru_cached so we set the env early.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-only-for-tests")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

# Patch SQLAlchemy.Enum so that on SQLite (used in tests) storage and read-back
# both go through enum *values* instead of member names. The journal-service
# enums (e.g. TradeDirection.LONG = "Long") have name != value, and SQLAlchemy
# 2.0's default writes values but reads names — that mismatch raises
# `LookupError: 'Long' is not among the defined enum values` on first refresh.
# Production MySQL uses native enums and is unaffected; this is test-only.
from sqlalchemy import Enum as _SQLEnum  # noqa: E402

_orig_enum_init = _SQLEnum.__init__


def _patched_enum_init(self, *enums, **kw):
    if "values_callable" not in kw and enums and hasattr(enums[0], "__members__"):
        kw["values_callable"] = lambda obj: [e.value for e in obj]
    _orig_enum_init(self, *enums, **kw)


_SQLEnum.__init__ = _patched_enum_init

from app.api.dependencies import get_db  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.models.domain import Base  # noqa: E402

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
API_PREFIX = f"/{get_settings().API_PREFIX}/api/v2/journal"

TEST_USER_ID = 4242
OTHER_USER_ID = 9999


def make_token(user_id: int = TEST_USER_ID, email: str = "trader@example.com",
               role: str = "user", expires_minutes: int = 30) -> str:
    """Issue a JWT the journal-service will accept."""
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def auth_headers(token: str | None = None) -> dict:
    return {"Authorization": f"Bearer {token or make_token()}"}


@pytest_asyncio.fixture
async def test_db():
    """Fresh SQLite schema per test — keeps cases independent."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db):
    """Test client with get_db overridden to the in-memory session."""

    async def _override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def headers() -> dict:
    return auth_headers()


@pytest.fixture
def other_user_headers() -> dict:
    return auth_headers(make_token(user_id=OTHER_USER_ID, email="other@example.com"))


@pytest.fixture
def account_payload() -> dict:
    return {
        "account_name": "Schwager Test Account",
        "starting_equity": 100_000_000,
        "currency": "VND",
        "max_risk_per_trade": 2.0,
        "max_cumulative_risk": 25.0,
    }


@pytest.fixture
def trade_payload() -> dict:
    """A long position with a 5% stop, well within risk limits."""
    return {
        "entry_date": "2026-01-15",
        "market_ticker": "FPT",
        "direction": "Long",
        "entry_price": 100.0,
        "entry_type": "Market",
        "initial_stop": 95.0,
        "position_size": 1000,
        "commission": 50.0,
        "objective_1": 110.0,
        "objective_2": 120.0,
        "entry_reason": "Bullish breakout above 50-day MA",
    }


@pytest_asyncio.fixture
async def account(client, headers, account_payload):
    """Create one account and return its dict — used by trade/diary/plan tests."""
    response = await client.post(
        f"{API_PREFIX}/accounts", json=account_payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest_asyncio.fixture
async def trade(client, headers, account, trade_payload):
    """Create one trade against the fixture account."""
    response = await client.post(
        f"{API_PREFIX}/accounts/{account['id']}/trades",
        json=trade_payload,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()
