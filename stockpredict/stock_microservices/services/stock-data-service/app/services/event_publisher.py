"""Event publishing for stock-data-service.

Singleton EventBus connection used to fan out `stock.price.updated` events
when refresh_price_board() pulls fresh quotes. Other services (portfolio
alerts, dashboards) subscribe and react.
"""
from __future__ import annotations

import logging
from typing import Optional

from stock_common.config import RabbitMQConfig
from stock_common.events import Event, EventBus
from stock_common.events.models import DomainEvents

logger = logging.getLogger(__name__)


_event_bus: Optional[EventBus] = None


async def init_event_publisher(service_name: str = "stock-data-service") -> Optional[EventBus]:
    """Open the shared EventBus connection. Returns the bus, or None if
    RabbitMQ is unavailable (service still works without events).
    """
    global _event_bus
    if _event_bus is not None:
        return _event_bus
    try:
        config = RabbitMQConfig()
        bus = EventBus(config, service_name=service_name)
        await bus.connect()
        _event_bus = bus
        logger.info("Event publisher connected to RabbitMQ")
        return bus
    except Exception as e:
        logger.warning("Event publisher disabled (RabbitMQ unavailable?): %s", e)
        _event_bus = None
        return None


async def shutdown_event_publisher() -> None:
    global _event_bus
    if _event_bus is not None:
        try:
            await _event_bus.disconnect()
        except Exception as e:
            logger.warning("Event publisher disconnect raised: %s", e)
        _event_bus = None


async def publish_price_updates(records: list[dict]) -> None:
    """Publish one stock.price.updated event per priceboard record.

    Best-effort — never raises. A failed publish is logged but does not
    abort the upstream priceboard refresh.

    Routing key includes the symbol so consumers can subscribe per-symbol
    (`stock.price.updated.FPT`) if they need finer-grained filtering than
    the default `stock.price.updated`.
    """
    if _event_bus is None or not records:
        return

    for rec in records:
        symbol = rec.get("symbol")
        match_price = rec.get("matchPrice")
        ref_price = rec.get("refPrice")
        if not symbol or match_price is None:
            continue
        try:
            await _event_bus.publish(
                Event(
                    event_type=DomainEvents.STOCK_PRICE_UPDATED,
                    payload={
                        "symbol": symbol,
                        "price": float(match_price),
                        "ref_price": float(ref_price) if ref_price is not None else None,
                        "change_percent": rec.get("changePercent"),
                        "exchange": rec.get("exchange"),
                    },
                ),
                routing_key=f"{DomainEvents.STOCK_PRICE_UPDATED}.{symbol}",
            )
        except Exception as e:
            logger.error("Failed to publish price update for %s: %s", symbol, e)
