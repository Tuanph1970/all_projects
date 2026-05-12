"""Unit tests for email_service + portfolio_repository + dependencies.

Mirrors the auth-service unit-test pattern (in-memory mocks +
monkeypatched smtplib).
"""
from datetime import datetime, timedelta
from email.message import EmailMessage
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import (
    get_current_user,
    get_current_user_optional,
    validate_token_with_auth_service,
)
from app.config import get_settings
from app.services import email_service
from app.services.email_service import (
    _build_message,
    _send_sync,
    format_alert_email,
    send_email,
)


settings = get_settings()


# ---------------------------------------------------------------------------
# email_service: _build_message + _send_sync + send_email
# ---------------------------------------------------------------------------

def test_build_message_text_only_omits_html_alternative():
    msg = _build_message(
        to_email="alice@example.com",
        subject="Hello",
        text_body="plain body",
        html_body=None,
        from_email="no-reply@stockhelper.local",
        from_name="Stock Helper",
    )
    assert isinstance(msg, EmailMessage)
    assert msg["To"] == "alice@example.com"
    assert msg["Subject"] == "Hello"
    assert "Stock Helper" in msg["From"]
    assert not msg.is_multipart()


def test_build_message_adds_html_alternative_when_provided():
    msg = _build_message(
        to_email="alice@example.com",
        subject="Hello",
        text_body="plain",
        html_body="<p>html</p>",
        from_email="no-reply@stockhelper.local",
        from_name="Stock Helper",
    )
    assert msg.is_multipart()
    types = {part.get_content_type() for part in msg.iter_parts()}
    assert "text/html" in types


@pytest.mark.asyncio
async def test_send_email_returns_false_when_smtp_unconfigured(monkeypatch):
    monkeypatch.setattr(email_service.get_settings(), "SMTP_HOST", None)
    ok = await send_email(
        to_email="alice@example.com", subject="x", text_body="x",
    )
    assert ok is False


@pytest.mark.asyncio
async def test_send_email_invokes_send_sync_in_thread(monkeypatch):
    s = email_service.get_settings()
    monkeypatch.setattr(s, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(s, "SMTP_FROM_EMAIL", "no-reply@example.com")
    monkeypatch.setattr(s, "SMTP_FROM_NAME", "Test")

    with patch.object(email_service, "_send_sync") as send_mock:
        ok = await send_email(
            to_email="alice@example.com", subject="Hello",
            text_body="body", html_body="<p>html</p>",
        )
    assert ok is True
    sent_msg = send_mock.call_args.args[0]
    assert isinstance(sent_msg, EmailMessage)
    assert sent_msg["Subject"] == "Hello"


@pytest.mark.asyncio
async def test_send_email_returns_false_when_smtp_send_raises(monkeypatch):
    s = email_service.get_settings()
    monkeypatch.setattr(s, "SMTP_HOST", "smtp.example.com")
    with patch.object(email_service, "_send_sync", side_effect=RuntimeError("smtp down")):
        ok = await send_email(
            to_email="alice@example.com", subject="x", text_body="x",
        )
    assert ok is False


def test_send_sync_with_tls_and_credentials(monkeypatch):
    s = email_service.get_settings()
    monkeypatch.setattr(s, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(s, "SMTP_PORT", 587)
    monkeypatch.setattr(s, "SMTP_USE_TLS", True)
    monkeypatch.setattr(s, "SMTP_USERNAME", "user")
    monkeypatch.setattr(s, "SMTP_PASSWORD", "pass")

    smtp_instance = MagicMock()
    smtp_ctx = MagicMock()
    smtp_ctx.__enter__ = MagicMock(return_value=smtp_instance)
    smtp_ctx.__exit__ = MagicMock(return_value=None)

    msg = _build_message(
        to_email="a@example.com", subject="s", text_body="b",
        html_body=None, from_email="from@x", from_name="Test",
    )
    with patch("app.services.email_service.smtplib.SMTP", return_value=smtp_ctx):
        _send_sync(msg)
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("user", "pass")
    smtp_instance.send_message.assert_called_once_with(msg)


def test_send_sync_without_tls_or_credentials(monkeypatch):
    s = email_service.get_settings()
    monkeypatch.setattr(s, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(s, "SMTP_PORT", 25)
    monkeypatch.setattr(s, "SMTP_USE_TLS", False)
    monkeypatch.setattr(s, "SMTP_USERNAME", None)
    monkeypatch.setattr(s, "SMTP_PASSWORD", None)

    smtp_instance = MagicMock()
    smtp_ctx = MagicMock()
    smtp_ctx.__enter__ = MagicMock(return_value=smtp_instance)
    smtp_ctx.__exit__ = MagicMock(return_value=None)

    msg = _build_message(
        to_email="a@example.com", subject="s", text_body="b",
        html_body=None, from_email="from@x", from_name="Test",
    )
    with patch("app.services.email_service.smtplib.SMTP", return_value=smtp_ctx):
        _send_sync(msg)
    smtp_instance.starttls.assert_not_called()
    smtp_instance.login.assert_not_called()


# ---------------------------------------------------------------------------
# format_alert_email — branch coverage per alert type
# ---------------------------------------------------------------------------

class TestFormatAlertEmail:
    def test_above_alert(self):
        subj, text, html = format_alert_email({
            "symbol": "FPT", "alert_type": "above",
            "target_price": 100.0, "trigger_price": 105.0,
        })
        assert "FPT" in subj and "above" in subj.lower()
        assert "105" in text
        assert "html" not in subj.lower()
        assert "<p>" in html

    def test_below_alert(self):
        subj, text, _ = format_alert_email({
            "symbol": "VNM", "alert_type": "below",
            "target_price": 50.0, "trigger_price": 45.0,
        })
        assert "VNM" in subj and "below" in subj.lower()
        assert "45" in text

    def test_change_percent_alert(self):
        subj, text, _ = format_alert_email({
            "symbol": "VCB", "alert_type": "change_percent",
            "target_percent": 5.0, "trigger_price": 90.0,
        })
        assert "VCB" in subj
        assert "5" in subj
        assert "90" in text

    def test_unknown_alert_type_falls_back(self):
        subj, text, _ = format_alert_email({
            "symbol": "HPG", "trigger_price": 25.0,
        })
        assert "HPG" in subj
        assert "25" in text


# ---------------------------------------------------------------------------
# dependencies: get_current_user / get_current_user_optional /
# validate_token_with_auth_service
# ---------------------------------------------------------------------------

def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _token(payload_overrides=None) -> str:
    payload = {
        "sub": "42",
        "email": "alice@example.com",
        "role": "user",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=10),
    }
    if payload_overrides:
        payload.update(payload_overrides)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.mark.asyncio
async def test_get_current_user_returns_dict_on_valid_token():
    user = await get_current_user(credentials=_creds(_token()))
    assert user == {"user_id": 42, "email": "alice@example.com", "role": "user"}


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_invalid_token():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds("not.a.jwt"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_expired_token():
    expired = jwt.encode(
        {
            "sub": "42", "email": "x@y.com",
            "iat": datetime.utcnow() - timedelta(minutes=20),
            "exp": datetime.utcnow() - timedelta(minutes=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds(expired))
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_sub_missing():
    """Token where sub is None → "Subject must be a string" or "missing"."""
    token = _token({"sub": None})
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_none_without_credentials():
    assert (await get_current_user_optional(credentials=None)) is None


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_none_on_invalid_token():
    assert (await get_current_user_optional(credentials=_creds("not.a.jwt"))) is None


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_user_on_valid_token():
    user = await get_current_user_optional(credentials=_creds(_token()))
    assert user is not None
    assert user["user_id"] == 42


# validate_token_with_auth_service — httpx mocked
class _FakeHttpxClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        c = MagicMock()
        c.get = AsyncMock(return_value=self._response)
        return c

    async def __aexit__(self, *_):
        return False


@pytest.mark.asyncio
async def test_validate_token_with_auth_service_returns_payload_on_200():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"user_id": 7, "email": "x@y.com"}
    with patch("app.api.dependencies.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await validate_token_with_auth_service("any.jwt")
    assert out == {"user_id": 7, "email": "x@y.com"}


@pytest.mark.asyncio
async def test_validate_token_with_auth_service_returns_none_on_non_200():
    resp = MagicMock()
    resp.status_code = 503
    with patch("app.api.dependencies.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await validate_token_with_auth_service("any.jwt")
    assert out is None


@pytest.mark.asyncio
async def test_validate_token_with_auth_service_returns_none_on_exception():
    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    with patch("app.api.dependencies.httpx.AsyncClient", return_value=Boom()):
        out = await validate_token_with_auth_service("any.jwt")
    assert out is None
