"""Web-push channel consumer for portfolio.alert.triggered events.

Third subscriber alongside the in-app notification_consumer and the
email_consumer. Looks up every active push subscription for the user
and delivers the alert via the browser Push API.

Best-effort: missing user_id / no subscriptions / RabbitMQ down all log
and return rather than nack. On 404/410 from the push service the
subscription row is deleted (the browser is gone).
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import delete, select

from stock_common.config import RabbitMQConfig
from stock_common.events import Event, EventBus
from stock_common.events.models import DomainEvents

from app.api.dependencies import async_session_factory  # type: ignore
from app.models.domain import PushSubscription
from app.services.push_service import (
    EXPIRED_STATUS_CODES,
    format_alert_push,
    send_push_to_subscriptions,
)

logger = logging.getLogger(__name__)


_event_bus: Optional[EventBus] = None


async def start_push_consumer(
    service_name: str = "portfolio-service",
) -> Optional[EventBus]:
    """Subscribe to portfolio.alert.triggered for browser push delivery.

    Returns None on RabbitMQ failure rather than blocking service boot.
    """
    global _event_bus
    try:
        config = RabbitMQConfig()
        bus = EventBus(config, service_name=service_name)
        await bus.connect()
        await bus.subscribe(
            event_pattern=DomainEvents.PORTFOLIO_ALERT_TRIGGERED,
            handler=_handle_alert_triggered,
            # Distinct queue name from notification_consumer + email_consumer
            # so each gets its own copy of every event.
            queue_name=f"{service_name}.push.alert_triggered",
            durable=True,
        )
        _event_bus = bus
        logger.info(
            "Push consumer subscribed to %s",
            DomainEvents.PORTFOLIO_ALERT_TRIGGERED,
        )
        return bus
    except Exception as e:
        logger.warning(
            "Could not start push consumer (RabbitMQ unavailable?): %s", e
        )
        _event_bus = None
        return None


async def stop_push_consumer() -> None:
    global _event_bus
    if _event_bus is not None:
        try:
            await _event_bus.disconnect()
        except Exception as e:
            logger.warning("Push consumer disconnect raised: %s", e)
        _event_bus = None


async def _handle_alert_triggered(event: Event) -> None:
    """Send a push to every active browser subscription for the user.

    Prunes subscriptions that come back 404/410 — those endpoints are
    permanently gone (browser uninstalled, permission revoked).
    """
    payload = event.payload or {}
    user_id = payload.get("user_id")
    if user_id is None:
        logger.debug("Skipping push — no user_id in payload: %s", payload)
        return

    try:
        async with async_session_factory() as session:
            subs_result = await session.execute(
                select(PushSubscription).where(
                    PushSubscription.user_id == int(user_id)
                )
            )
            subs = list(subs_result.scalars().all())

            if not subs:
                logger.debug(
                    "No push subscriptions for user_id=%s; skipping push.",
                    user_id,
                )
                return

            push_payload = format_alert_push(payload)
            results = await send_push_to_subscriptions(subs, push_payload)

            expired_ids = [
                sub_id
                for sub_id, delivered, status in results
                if not delivered and status in EXPIRED_STATUS_CODES
            ]
            if expired_ids:
                await session.execute(
                    delete(PushSubscription).where(
                        PushSubscription.id.in_(expired_ids)
                    )
                )
                await session.commit()
                logger.info(
                    "Pruned %d expired push subscription(s) for user_id=%s",
                    len(expired_ids),
                    user_id,
                )
    except Exception as e:
        # Don't nack — losing one push is better than DLQ thrash, and the
        # alert is already in the user's bell-icon inbox.
        logger.error("Error in push consumer for user_id=%s: %s", user_id, e)
