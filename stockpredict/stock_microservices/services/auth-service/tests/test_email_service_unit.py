"""Tests for the SMTP/email helpers."""
from email.message import EmailMessage
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_settings
from app.services import email_service
from app.services.email_service import (
    _build_message,
    _send_sync,
    send_email,
    send_password_reset_email,
)


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
    assert "no-reply@stockhelper.local" in msg["From"]
    # Single-part message — no html alternative attached.
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
    # The walk should include both text and html parts.
    types = {part.get_content_type() for part in msg.iter_parts()}
    assert "text/html" in types


@pytest.mark.asyncio
async def test_send_email_returns_false_when_smtp_unconfigured(monkeypatch):
    """SMTP_HOST unset → log + return False."""
    monkeypatch.setattr(email_service.get_settings(), "SMTP_HOST", None)
    ok = await send_email(
        to_email="alice@example.com",
        subject="x",
        text_body="x",
    )
    assert ok is False


@pytest.mark.asyncio
async def test_send_email_invokes_send_sync_in_thread(monkeypatch):
    """SMTP_HOST set → message handed to _send_sync, returns True."""
    s = email_service.get_settings()
    monkeypatch.setattr(s, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(s, "SMTP_FROM_EMAIL", "no-reply@example.com")
    monkeypatch.setattr(s, "SMTP_FROM_NAME", "Test")

    with patch.object(email_service, "_send_sync") as send_mock:
        ok = await send_email(
            to_email="alice@example.com",
            subject="Hello",
            text_body="body",
            html_body="<p>html</p>",
        )
    assert ok is True
    send_mock.assert_called_once()
    sent_msg = send_mock.call_args.args[0]
    assert isinstance(sent_msg, EmailMessage)
    assert sent_msg["To"] == "alice@example.com"
    assert sent_msg["Subject"] == "Hello"


@pytest.mark.asyncio
async def test_send_email_returns_false_when_smtp_send_raises(monkeypatch):
    """SMTP I/O error is swallowed; caller gets a clean False."""
    s = email_service.get_settings()
    monkeypatch.setattr(s, "SMTP_HOST", "smtp.example.com")

    with patch.object(email_service, "_send_sync", side_effect=RuntimeError("smtp down")):
        ok = await send_email(
            to_email="alice@example.com",
            subject="Hello",
            text_body="body",
        )
    assert ok is False


@pytest.mark.asyncio
async def test_send_password_reset_email_routes_through_send_email(monkeypatch):
    """The reset email assembles a Vietnamese subject + body and delegates
    to send_email."""
    monkeypatch.setattr(email_service.get_settings(), "SMTP_HOST", None)
    # Capture the send_email call args.
    with patch("app.services.email_service.send_email", new=AsyncMock(return_value=True)) as send_mock:
        ok = await send_password_reset_email(
            to_email="alice@example.com",
            reset_link="https://app.stockhelper.local/reset?token=abc",
            expires_minutes=30,
        )
    assert ok is True
    kwargs = send_mock.call_args.kwargs
    assert kwargs["to_email"] == "alice@example.com"
    assert "Đặt lại mật khẩu" in kwargs["subject"]
    assert "abc" in kwargs["text_body"]
    assert "30 phút" in kwargs["text_body"]
    assert kwargs["html_body"] and "30 phút" in kwargs["html_body"]


# ---------------------------------------------------------------------------
# _send_sync — exercise the smtplib.SMTP path with a stub
# ---------------------------------------------------------------------------

def test_send_sync_with_tls_and_credentials(monkeypatch):
    """Configured TLS + credentials path calls starttls + login + send."""
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


def test_send_sync_without_tls_or_credentials_skips_them(monkeypatch):
    """If TLS is off and no credentials → just send_message."""
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
    smtp_instance.send_message.assert_called_once_with(msg)
