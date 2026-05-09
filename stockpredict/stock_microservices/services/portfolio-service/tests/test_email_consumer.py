"""Tests for the email_consumer that sends alert.triggered events as
emails alongside the in-app notification consumer.

Mocks the RabbitMQ side, the user-email lookup, and the SMTP sender so
we can verify the consumer logic without standing up a real broker or
mail server.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import email_consumer as consumer
from stock_common.events import Event
from stock_common.events.models import DomainEvents


def _alert_event(user_id=42, symbol="FPT", price=105.0, alert_type="above"):
    return Event(
        event_type=DomainEvents.PORTFOLIO_ALERT_TRIGGERED,
        payload={
            "alert_id": 7,
            "user_id": user_id,
            "symbol": symbol,
            "alert_type": alert_type,
            "target_price": 100.0,
            "trigger_price": price,
        },
    )


# ---------------------------------------------------------------------------
# _handle_alert_triggered — the consumer logic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_alert_skips_payload_without_user_id(monkeypatch):
    """No user_id means we can't look up an email — should noop, not raise."""
    send_mock = AsyncMock()
    monkeypatch.setattr(consumer, "send_email", send_mock)

    bad = Event(
        event_type=DomainEvents.PORTFOLIO_ALERT_TRIGGERED,
        payload={"symbol": "FPT"},  # no user_id
    )
    await consumer._handle_alert_triggered(bad)

    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_alert_skips_when_user_has_no_email(monkeypatch):
    """User exists but has no email row — log + skip rather than send."""
    monkeypatch.setattr(consumer, "_lookup_user_email", AsyncMock(return_value=None))
    send_mock = AsyncMock()
    monkeypatch.setattr(consumer, "send_email", send_mock)

    await consumer._handle_alert_triggered(_alert_event())

    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_alert_sends_email_with_formatted_subject_and_body(monkeypatch):
    """Happy path: lookup returns an address, format_alert_email shapes
    subject+bodies, send_email is called with all three."""
    monkeypatch.setattr(
        consumer, "_lookup_user_email", AsyncMock(return_value="user@example.com")
    )
    send_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(consumer, "send_email", send_mock)

    await consumer._handle_alert_triggered(
        _alert_event(symbol="VNM", price=72.5, alert_type="above")
    )

    send_mock.assert_awaited_once()
    kwargs = send_mock.call_args.kwargs
    assert kwargs["to_email"] == "user@example.com"
    assert "VNM" in kwargs["subject"] and "above" in kwargs["subject"].lower()
    assert "VNM" in kwargs["text_body"]
    assert "72.5" in kwargs["text_body"]
    assert kwargs["html_body"]  # non-empty


@pytest.mark.asyncio
async def test_lookup_user_email_swallows_db_errors(monkeypatch):
    """If the SELECT raises (e.g. users table missing in this DB) we log
    + return None — must NOT propagate, otherwise the message would nack
    into DLQ on every redelivery."""
    factory_cm = MagicMock()
    factory_cm.__aenter__ = AsyncMock(side_effect=RuntimeError("table users not found"))
    factory_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=factory_cm)
    monkeypatch.setattr(consumer, "async_session_factory", factory)

    result = await consumer._lookup_user_email(42)
    assert result is None


@pytest.mark.asyncio
async def test_lookup_user_email_returns_email_from_row(monkeypatch):
    session = AsyncMock()
    row_result = MagicMock()
    row_result.scalar_one_or_none.return_value = "alice@example.com"
    session.execute.return_value = row_result

    factory_cm = MagicMock()
    factory_cm.__aenter__ = AsyncMock(return_value=session)
    factory_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=factory_cm)
    monkeypatch.setattr(consumer, "async_session_factory", factory)

    result = await consumer._lookup_user_email(42)
    assert result == "alice@example.com"


# ---------------------------------------------------------------------------
# Lifecycle — start/stop must be best-effort
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_consumer_returns_none_on_rabbit_failure(monkeypatch):
    """RabbitMQ unavailable at boot → service still starts; in-app
    notifications keep working if the broker recovers."""
    class BoomBus:
        def __init__(self, *a, **kw):
            pass

        async def connect(self):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(consumer, "EventBus", BoomBus)
    bus = await consumer.start_email_consumer()
    assert bus is None


@pytest.mark.asyncio
async def test_stop_consumer_idempotent_when_not_started(monkeypatch):
    monkeypatch.setattr(consumer, "_event_bus", None)
    await consumer.stop_email_consumer()  # must not raise
