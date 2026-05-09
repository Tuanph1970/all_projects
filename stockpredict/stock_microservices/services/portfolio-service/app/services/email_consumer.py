"""Email-channel consumer for portfolio.alert.triggered events.

Subscribes alongside the in-app notification_consumer and delivers the
same alert as an email so users hear about price moves when the tab
isn't open.

User email is looked up by user_id via raw SQL against the shared
`users` table. The lookup is lazy (only when an event arrives) so
boot doesn't depend on the auth-service schema.

Best-effort and idempotent at the consumer-bus layer:
- If SMTP isn't configured, send_email logs instead of sending.
- If user_id has no email row, we log + skip rather than nack.
- Network/SMTP failures are caught so one bad email doesn't DLQ
  the queue (and we'd retry on the next price tick anyway).
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import text

from stock_common.config import RabbitMQConfig
from stock_common.events import Event, EventBus
from stock_common.events.models import DomainEvents

from app.api.dependencies import async_session_factory  # type: ignore
from app.services.email_service import format_alert_email, send_email

logger = logging.getLogger(__name__)


_event_bus: Optional[EventBus] = None


async def start_email_consumer(
    service_name: str = "portfolio-service",
) -> Optional[EventBus]:
    """Subscribe to portfolio.alert.triggered for email delivery.

    Returns None on RabbitMQ failure rather than blocking service boot —
    the in-app notifications still work if RabbitMQ later recovers.
    """
    global _event_bus
    try:
        config = RabbitMQConfig()
        bus = EventBus(config, service_name=service_name)
        await bus.connect()
        await bus.subscribe(
            event_pattern=DomainEvents.PORTFOLIO_ALERT_TRIGGERED,
            handler=_handle_alert_triggered,
            # Distinct queue name from notification_consumer so each
            # consumer gets its own copy of every event.
            queue_name=f"{service_name}.email.alert_triggered",
            durable=True,
        )
        _event_bus = bus
        logger.info(
            "Email consumer subscribed to %s",
            DomainEvents.PORTFOLIO_ALERT_TRIGGERED,
        )
        return bus
    except Exception as e:
        logger.warning(
            "Could not start email consumer (RabbitMQ unavailable?): %s", e
        )
        _event_bus = None
        return None


async def stop_email_consumer() -> None:
    global _event_bus
    if _event_bus is not None:
        try:
            await _event_bus.disconnect()
        except Exception as e:
            logger.warning("Email consumer disconnect raised: %s", e)
        _event_bus = None


async def _lookup_user_email(user_id: int) -> Optional[str]:
    """Read the email for a given user_id from the shared users table.

    Returns None if the user has no row, no email, or if the query
    raises (logged). Used by the email consumer below.
    """
    try:
        async with async_session_factory() as session:
            row = await session.execute(
                text("SELECT email FROM users WHERE id = :uid LIMIT 1"),
                {"uid": user_id},
            )
            email = row.scalar_one_or_none()
            return email if email else None
    except Exception as e:
        # Includes "table users does not exist" if the auth schema isn't
        # provisioned in this DB — a deployment misconfig rather than a
        # transient error, but we still don't want it to nack messages.
        logger.warning("Email lookup failed for user_id=%s: %s", user_id, e)
        return None


async def _handle_alert_triggered(event: Event) -> None:
    """Send a single alert email for one portfolio.alert.triggered event."""
    payload = event.payload or {}
    user_id = payload.get("user_id")
    if user_id is None:
        logger.debug("Skipping alert email — no user_id in payload: %s", payload)
        return

    email = await _lookup_user_email(int(user_id))
    if not email:
        logger.info(
            "Skipping alert email — no email on file for user_id=%s", user_id
        )
        return

    subject, text_body, html_body = format_alert_email(payload)
    await send_email(
        to_email=email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
