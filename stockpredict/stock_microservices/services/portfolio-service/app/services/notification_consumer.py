"""Persist portfolio.alert.triggered events as notifications.

Subscribes to the same EventBus as alert_event_handler.py but for the
downstream "alert fired → user should see this in their inbox" path.
The producer is the alert handler itself (it publishes the triggered
event after marking the alert), so this module is a pure consumer.

Idempotent: events are deduped by `metadata.event_id` so a DLQ retry
doesn't double-insert. Best-effort: connection failures during boot
log and continue rather than blocking service startup.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from stock_common.config import RabbitMQConfig
from stock_common.events import Event, EventBus
from stock_common.events.models import DomainEvents

from app.api.dependencies import async_session_factory  # type: ignore
from app.models.domain import Notification, NotificationType

logger = logging.getLogger(__name__)


_event_bus: Optional[EventBus] = None


async def start_notification_consumer(
    service_name: str = "portfolio-service",
) -> Optional[EventBus]:
    """Subscribe to alert.triggered. Returns None on RabbitMQ failure
    rather than blocking service boot."""
    global _event_bus
    try:
        config = RabbitMQConfig()
        bus = EventBus(config, service_name=service_name)
        await bus.connect()
        await bus.subscribe(
            event_pattern=DomainEvents.PORTFOLIO_ALERT_TRIGGERED,
            handler=_handle_alert_triggered,
            queue_name=f"{service_name}.notifications.alert_triggered",
            durable=True,
        )
        _event_bus = bus
        logger.info(
            "Notification consumer subscribed to %s",
            DomainEvents.PORTFOLIO_ALERT_TRIGGERED,
        )
        return bus
    except Exception as e:
        logger.warning(
            "Could not start notification consumer (RabbitMQ unavailable?): %s", e
        )
        _event_bus = None
        return None


async def stop_notification_consumer() -> None:
    global _event_bus
    if _event_bus is not None:
        try:
            await _event_bus.disconnect()
        except Exception as e:
            logger.warning("Notification consumer disconnect raised: %s", e)
        _event_bus = None


def _format_alert_triggered(payload: dict) -> tuple[str, str, dict]:
    """Build (title, body, metadata) for an alert-triggered notification."""
    symbol = payload.get("symbol", "?")
    alert_type = payload.get("alert_type", "")
    target_price = payload.get("target_price")
    target_percent = payload.get("target_percent")
    trigger_price = payload.get("trigger_price")

    if alert_type == "above":
        title = f"{symbol} crossed above {target_price}"
        body = (
            f"Price reached {trigger_price}, hitting your above-{target_price} alert."
        )
    elif alert_type == "below":
        title = f"{symbol} crossed below {target_price}"
        body = (
            f"Price dropped to {trigger_price}, hitting your below-{target_price} alert."
        )
    elif alert_type == "change_percent":
        title = f"{symbol} moved {target_percent}%+"
        body = f"Price hit {trigger_price} — change exceeded {target_percent}%."
    else:
        title = f"Alert triggered for {symbol}"
        body = f"Price hit {trigger_price}."

    metadata = {
        "alert_id": payload.get("alert_id"),
        "symbol": symbol,
        "alert_type": alert_type,
        "trigger_price": trigger_price,
        "target_price": target_price,
        "target_percent": target_percent,
    }
    return title, body, metadata


async def _handle_alert_triggered(event: Event) -> None:
    """Persist a Notification row for each alert.triggered event.

    Dedupes on event.metadata.event_id so retries don't double-insert.
    Swallows DB errors (logged) — losing one notification is better than
    nacking into the DLQ and re-firing.
    """
    payload = event.payload or {}
    user_id = payload.get("user_id")
    if user_id is None:
        logger.debug("Skipping alert event with no user_id: %s", payload)
        return

    event_id = event.metadata.event_id

    try:
        async with async_session_factory() as session:
            # Dedupe: same source_event_id already inserted?
            existing = await session.execute(
                select(Notification.id).where(
                    Notification.source_event_id == event_id
                )
            )
            if existing.scalar_one_or_none() is not None:
                logger.debug("Notification for event %s already persisted", event_id)
                return

            title, body, meta = _format_alert_triggered(payload)
            session.add(
                Notification(
                    user_id=int(user_id),
                    type=NotificationType.ALERT_TRIGGERED,
                    title=title,
                    body=body,
                    metadata_json=json.dumps(meta),
                    source_event_id=event_id,
                    created_at=datetime.utcnow(),
                )
            )
            await session.commit()
            logger.info(
                "Persisted notification for user %s (event %s)", user_id, event_id
            )
    except Exception as e:
        logger.error("Error persisting notification for event %s: %s", event_id, e)
