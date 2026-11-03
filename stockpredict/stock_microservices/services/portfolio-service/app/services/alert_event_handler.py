"""Event-driven price alert evaluation.

Subscribes to `stock.price.updated` events on the stock-common EventBus.
For each price tick, looks up active alerts for that symbol, evaluates the
trigger condition, and on match: marks the alert triggered and publishes
`portfolio.alert.triggered` so other services (notifications, etc.) can react.

This replaces the prior "evaluate alerts on every API request" polling model.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from stock_common.config import RabbitMQConfig
from stock_common.events.routing import PRICE_UPDATED_PATTERN
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
        # The pattern comes from stock_common.events.routing, the same module the
        # publisher takes its routing key from. It used to be
        # DomainEvents.STOCK_PRICE_UPDATED — the bare event name — while the
        # publisher sends `stock.price.updated.<SYMBOL>`. On a topic exchange the
        # extra word means NO MATCH, so this consumer received nothing for its
        # entire life: a live consumer on a healthy queue that never saw a
        # message. Measured against the broker 2026-11-02, the old binding took
        # 0 of 1 published messages.
        await bus.subscribe(
            event_pattern=PRICE_UPDATED_PATTERN,
            handler=_handle_price_update,
            queue_name=f"{service_name}.alerts.price_updated",
            durable=True,
        )
        _event_bus = bus
        logger.info("Alert consumer subscribed to %s", PRICE_UPDATED_PATTERN)
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


#: Backlog #117. Multiple of a symbol's own trailing median volume at which an
#: unusual-volume alert fires, when the alert itself does not name one.
#:
#: MEASURED, not chosen: across 42,674 readings on 32 real symbols the firing
#: rate is 23.95% at 1.5x, 12.74% at 2.0x, 4.55% at 3.0x, 2.11% at 4.0x and
#: 1.08% at 5.0x. 3.0x is about ELEVEN alerts per symbol per year — roughly
#: monthly — where 1.5x would be eight a day across a 32-symbol watchlist,
#: which is how an alerting feature gets muted. The median reading across the
#: whole sample is 0.986, which is the sanity check that the measure is centred.
#:
#: Note this is a FIRING RATE, not a false-positive rate: nothing here
#: establishes that a spike predicts anything. It bounds the noise, no more.
DEFAULT_VOLUME_MULTIPLE = 3.0


#: VN market clock. A session runs 09:00-15:00 ICT, so "today" for a daily
#: volume reading is an ICT date. Taking it from the server's UTC clock would be
#: right during the session and wrong for an after-hours refresh, so the offset
#: is stated rather than inherited.
MARKET_TZ_OFFSET = timedelta(hours=7)


def _market_now() -> datetime:
    """Naive market-local time, matching the naive UTC stored in triggered_at."""
    return datetime.utcnow() + MARKET_TZ_OFFSET


def _already_fired_today(alert: PriceAlert) -> bool:
    """Has this alert already fired during the current market day?

    Backlog #117. A volume alert RE-FIRES, unlike a price alert — unusual volume
    recurs, and a one-shot volume alert goes quiet after its first day and never
    speaks again. But it re-fires at most ONCE A DAY, because rel_volume is a
    daily aggregate: once a spike happens, the reading stays above the multiple
    for the rest of the session, and the priceboard refreshes many times. An
    unconditional re-arm would send two dozen notifications for one event.
    """
    fired_at = getattr(alert, "triggered_at", None)
    if fired_at is None:
        return False
    return (fired_at + MARKET_TZ_OFFSET).date() >= _market_now().date()


def _volume_alert_should_fire(
    alert: PriceAlert, rel_volume: Optional[float]
) -> bool:
    """True iff this tick's relative volume reaches the alert's multiple.

    An ABSENT `rel_volume` never fires. The upstream reading is an explicit
    unknown when a symbol has too little history or a dormant window, and
    reading that absence as "not unusual" would be luck rather than logic —
    but reading it as unusual would invent an event.
    """
    if rel_volume is None:
        return False
    if _already_fired_today(alert):
        return False
    multiple = alert.target_percent if alert.target_percent else DEFAULT_VOLUME_MULTIPLE
    try:
        return float(rel_volume) >= abs(float(multiple))
    except (TypeError, ValueError):
        return False


def _alert_should_fire(alert: PriceAlert, new_price: float, prev_price: Optional[float]) -> bool:
    """Match the alert's trigger semantics. Returns True iff this tick crosses.

    Unit contract: both `new_price` and `alert.target_price` are expected in
    actual VND. The `stock.price.updated` event carries `matchPrice` from the
    Vietcap priceboard, which is already in actual VND — do not multiply.
    (Note: the historical OHLC API stores `close` in thousands-quote; if you
    ever feed alerts from that path, multiply by 1000 at the boundary.)
    """
    if alert.alert_type == AlertType.ABOVE:
        return alert.target_price is not None and new_price >= alert.target_price
    if alert.alert_type == AlertType.BELOW:
        return alert.target_price is not None and new_price <= alert.target_price
    if alert.alert_type == AlertType.CHANGE_PERCENT:
        if alert.target_percent is None or prev_price in (None, 0):
            return False
        change_pct = (new_price - prev_price) / prev_price * 100.0
        return abs(change_pct) >= abs(alert.target_percent)
    # VOLUME_UNUSUAL is evaluated by _volume_alert_should_fire, which needs the
    # event's rel_volume rather than a price, so it is dispatched separately in
    # _handle_price_update. Reaching here for it means no price rule applied.
    return False


async def _handle_price_update(event: Event) -> None:
    """Process one stock.price.updated event.

    Expected payload: {symbol, price, prev_price?, change_percent?,
    volume?, rel_volume?}. `rel_volume` (Backlog #117) is today's volume over
    the median of this symbol's own trailing history, attached by
    stock-data-service, and may legitimately be absent.
    Anything missing → log + skip; never raise (would nack into DLQ).
    """
    payload = event.payload or {}
    symbol = payload.get("symbol")
    price = payload.get("price")
    prev_price = payload.get("prev_price") or payload.get("ref_price")
    rel_volume = payload.get("rel_volume")

    if not symbol or price is None:
        logger.debug("Skipping malformed price event: %s", payload)
        return

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(PriceAlert).where(
                    PriceAlert.symbol == symbol.upper(),
                    PriceAlert.is_active.is_(True),
                    # Backlog #117. A triggered PRICE alert stays done — "above
                    # 25,000" is a threshold crossed once. A triggered VOLUME
                    # alert must still be loaded, because unusual volume recurs
                    # and it re-arms on the next market day; the once-a-day gate
                    # lives in _already_fired_today. Without this clause the
                    # predicate could say "fire again" forever and the row would
                    # never be read.
                    or_(
                        PriceAlert.is_triggered.is_(False),
                        PriceAlert.alert_type == AlertType.VOLUME_UNUSUAL,
                    ),
                )
            )
            alerts = result.scalars().all()
            if not alerts:
                return

            triggered_ids: list[int] = []
            for alert in alerts:
                # Backlog #117: a volume alert is judged on rel_volume, not on
                # price, so it is dispatched here rather than inside
                # _alert_should_fire, which takes no volume argument.
                if alert.alert_type == AlertType.VOLUME_UNUSUAL:
                    fired = _volume_alert_should_fire(alert, rel_volume)
                else:
                    fired = _alert_should_fire(alert, float(price), prev_price)
                if fired:
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
                                # Backlog #117. Without this a volume alert's
                                # notification can only quote a PRICE, which says
                                # nothing about why it fired — the first live
                                # firing read "Your alert for POW fired at
                                # 20000.0", a true sentence about the wrong
                                # quantity.
                                "rel_volume": rel_volume,
                            },
                        ).with_causation(event.metadata.event_id)
                    )
    except Exception as e:
        # Swallow — failing here shouldn't take the queue offline. The alert
        # remains untriggered and the next price tick will retry.
        logger.error("Error processing price update for %s: %s", symbol, e)
