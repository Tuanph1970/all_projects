"""Event-driven price alert evaluation.

Subscribes to `stock.price.updated` events on the stock-common EventBus.
For each price tick, looks up active alerts for that symbol, evaluates the
trigger condition, and on match: marks the alert triggered and publishes
`portfolio.alert.triggered` so other services (notifications, etc.) can react.

This replaces the prior "evaluate alerts on every API request" polling model.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from stock_common.config import RabbitMQConfig
from stock_common.events import Event, EventBus
from stock_common.events.models import DomainEvents

from app.api.dependencies import async_session_factory, engine  # type: ignore
from app.models.domain import AlertType, PriceAlert

logger = logging.getLogger(__name__)


_event_bus: Optional[EventBus] = None


async def start_alert_consumer(service_name: str = "portfolio-service") -> Optional[EventBus]:
    """Connect to RabbitMQ and subscribe to stock price updates.

    Returns the EventBus instance, or None if RabbitMQ is unavailable —
    callers should treat None as "event-driven alerts disabled" and continue
    booting the service. The synchronous CRUD endpoints still work without
    this consumer.
    """
    global _event_bus
    try:
        config = RabbitMQConfig()
        bus = EventBus(config, service_name=service_name)
        await bus.connect()
        await bus.subscribe(
            event_pattern=DomainEvents.STOCK_PRICE_UPDATED,
            handler=_handle_price_update,
            queue_name=f"{service_name}.alerts.price_updated",
            durable=True,
        )
        _event_bus = bus
        logger.info("Alert consumer subscribed to %s", DomainEvents.STOCK_PRICE_UPDATED)
        return bus
    except Exception as e:
        logger.warning("Could not start alert consumer (RabbitMQ unavailable?): %s", e)
        _event_bus = None
        return None


async def stop_alert_consumer() -> None:
    global _event_bus
    if _event_bus is not None:
        try:
            await _event_bus.disconnect()
        except Exception as e:
            logger.warning("EventBus disconnect raised: %s", e)
        _event_bus = None


def _alert_should_fire(alert: PriceAlert, new_price: float, prev_price: Optional[float]) -> bool:
    """Match the alert's trigger semantics. Returns True iff this tick crosses."""
    if alert.alert_type == AlertType.ABOVE:
        return alert.target_price is not None and new_price >= alert.target_price
    if alert.alert_type == AlertType.BELOW:
        return alert.target_price is not None and new_price <= alert.target_price
    if alert.alert_type == AlertType.CHANGE_PERCENT:
        if alert.target_percent is None or prev_price in (None, 0):
            return False
        change_pct = (new_price - prev_price) / prev_price * 100.0
        return abs(change_pct) >= abs(alert.target_percent)
    return False


async def _handle_price_update(event: Event) -> None:
    """Process one stock.price.updated event.

    Expected payload: {symbol, price, prev_price?, change_percent?}.
    Anything missing → log + skip; never raise (would nack into DLQ).
    """
    payload = event.payload or {}
    symbol = payload.get("symbol")
    price = payload.get("price")
    prev_price = payload.get("prev_price") or payload.get("ref_price")

    if not symbol or price is None:
        logger.debug("Skipping malformed price event: %s", payload)
        return

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(PriceAlert).where(
                    PriceAlert.symbol == symbol.upper(),
                    PriceAlert.is_active.is_(True),
                    PriceAlert.is_triggered.is_(False),
                )
            )
            alerts = result.scalars().all()
            if not alerts:
                return

            triggered_ids: list[int] = []
            for alert in alerts:
                if _alert_should_fire(alert, float(price), prev_price):
                    triggered_ids.append(alert.id)

            if not triggered_ids:
                return

            from datetime import datetime
            await session.execute(
                update(PriceAlert)
                .where(PriceAlert.id.in_(triggered_ids))
                .values(is_triggered=True, triggered_at=datetime.utcnow())
            )
            await session.commit()
            logger.info("Triggered %d alert(s) on %s @ %s", len(triggered_ids), symbol, price)

            # Publish a portfolio.alert.triggered event per fired alert so
            # downstream services (notifications, journal, dashboards) can react.
            if _event_bus is None:
                return
            for alert in alerts:
                if alert.id in triggered_ids:
                    await _event_bus.publish(
                        Event(
                            event_type=DomainEvents.PORTFOLIO_ALERT_TRIGGERED,
                            payload={
                                "alert_id": alert.id,
                                "user_id": alert.user_id,
                                "symbol": alert.symbol,
                                "alert_type": alert.alert_type.value,
                                "target_price": alert.target_price,
                                "target_percent": alert.target_percent,
                                "trigger_price": float(price),
                            },
                        ).with_causation(event.metadata.event_id)
                    )
    except Exception as e:
        # Swallow — failing here shouldn't take the queue offline. The alert
        # remains untriggered and the next price tick will retry.
        logger.error("Error processing price update for %s: %s", symbol, e)
