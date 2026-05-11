"""Tests for FastAPI dependencies: get_current_user / get_optional_user /
get_client_info / get_repository / get_auth_service."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import (
    get_auth_service,
    get_client_info,
    get_current_user,
    get_optional_user,
    get_repository,
)
from app.config import get_settings
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


settings = get_settings()


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _user(id_=1, active=True):
    u = MagicMock()
    u.id = id_
    u.is_active = active
    return u


# ---------------------------------------------------------------------------
# Provider wiring — get_repository / get_auth_service
# ---------------------------------------------------------------------------

def test_get_repository_wraps_session():
    session = MagicMock()
    repo = get_repository(session)
    assert isinstance(repo, UserRepository)
    assert repo.session is session


def test_get_auth_service_wraps_repository():
    repo = MagicMock()
    svc = get_auth_service(repo)
    assert isinstance(svc, AuthService)
    assert svc.repository is repo


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_current_user_raises_401_without_credentials():
    repo = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=None, repository=repo)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_invalid_token():
    repo = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds("not.a.jwt"), repository=repo)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_user_not_in_db():
    repo = MagicMock()
    repo.get_user_by_id = AsyncMock(return_value=None)
    token = AuthService.create_access_token(7, "alice@example.com", "user")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds(token), repository=repo)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_403_when_user_inactive():
    repo = MagicMock()
    repo.get_user_by_id = AsyncMock(return_value=_user(active=False))
    token = AuthService.create_access_token(7, "alice@example.com", "user")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds(token), repository=repo)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_returns_user_on_valid_token():
    expected = _user(id_=7, active=True)
    repo = MagicMock()
    repo.get_user_by_id = AsyncMock(return_value=expected)
    token = AuthService.create_access_token(7, "alice@example.com", "user")
    out = await get_current_user(credentials=_creds(token), repository=repo)
    assert out is expected


# ---------------------------------------------------------------------------
# get_optional_user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_optional_user_returns_none_without_credentials():
    out = await get_optional_user(credentials=None, repository=MagicMock())
    assert out is None


@pytest.mark.asyncio
async def test_get_optional_user_returns_none_on_invalid_token():
    out = await get_optional_user(credentials=_creds("not.a.jwt"), repository=MagicMock())
    assert out is None


@pytest.mark.asyncio
async def test_get_optional_user_returns_user_on_valid_token():
    expected = _user(id_=7)
    repo = MagicMock()
    repo.get_user_by_id = AsyncMock(return_value=expected)
    token = AuthService.create_access_token(7, "alice@example.com", "user")
    out = await get_optional_user(credentials=_creds(token), repository=repo)
    assert out is expected


# ---------------------------------------------------------------------------
# get_client_info
# ---------------------------------------------------------------------------

def test_get_client_info_extracts_user_agent_and_ip():
    request = MagicMock()
    request.headers = {"user-agent": "pytest/0"}
    request.client = MagicMock()
    request.client.host = "10.0.0.1"
    out = get_client_info(request)
    assert out == {"user_agent": "pytest/0", "ip_address": "10.0.0.1"}


def test_get_client_info_handles_no_client():
    request = MagicMock()
    request.headers = {"user-agent": None}
    request.client = None
    out = get_client_info(request)
    assert out == {"user_agent": None, "ip_address": None}
