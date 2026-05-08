"""Coverage for alert_event_handler — the event-driven price-alert path
shipped in Sprint B (stock.price.updated → trigger matching alerts →
publish portfolio.alert.triggered).

Tests focus on `_alert_should_fire()` (pure trigger logic) directly and
on `_handle_price_update()` with stubbed Redis/SQL plumbing. We don't
need a live RabbitMQ here — `_event_bus` is patched to None so the
publish branch is exercised as a no-op.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.domain import AlertType, PriceAlert
from app.services import alert_event_handler as handler
from stock_common.events import Event
from stock_common.events.models import DomainEvents


def _make_alert(
    alert_type=AlertType.ABOVE,
    target_price=None,
    target_percent=None,
    is_active=True,
    is_triggered=False,
    symbol="FPT",
    user_id=1,
    alert_id=42,
) -> PriceAlert:
    a = PriceAlert(
        symbol=symbol,
        alert_type=alert_type,
        target_price=target_price,
        target_percent=target_percent,
        is_active=is_active,
        is_triggered=is_triggered,
        user_id=user_id,
    )
    # PK is normally set by the DB; we want a stable id for assertions.
    a.id = alert_id
    return a


# ---------------------------------------------------------------------------
# _alert_should_fire — pure trigger logic, no async needed
# ---------------------------------------------------------------------------

class TestAlertShouldFire:
    def test_above_fires_when_price_at_or_over_target(self):
        a = _make_alert(alert_type=AlertType.ABOVE, target_price=100.0)
        assert handler._alert_should_fire(a, 100.0, None) is True
        assert handler._alert_should_fire(a, 105.0, None) is True

    def test_above_does_not_fire_below_target(self):
        a = _make_alert(alert_type=AlertType.ABOVE, target_price=100.0)
        assert handler._alert_should_fire(a, 99.99, None) is False

    def test_below_fires_when_price_at_or_under_target(self):
        a = _make_alert(alert_type=AlertType.BELOW, target_price=50.0)
        assert handler._alert_should_fire(a, 50.0, None) is True
        assert handler._alert_should_fire(a, 49.0, None) is True

    def test_below_does_not_fire_above_target(self):
        a = _make_alert(alert_type=AlertType.BELOW, target_price=50.0)
        assert handler._alert_should_fire(a, 50.01, None) is False

    def test_change_percent_fires_when_threshold_crossed(self):
        a = _make_alert(
            alert_type=AlertType.CHANGE_PERCENT, target_percent=5.0,
        )
        # 100 → 106 is +6%, exceeds 5%
        assert handler._alert_should_fire(a, 106.0, 100.0) is True
        # 100 → 94 is -6%, abs() exceeds 5% — fires symmetrically
        assert handler._alert_should_fire(a, 94.0, 100.0) is True

    def test_change_percent_does_not_fire_below_threshold(self):
        a = _make_alert(
            alert_type=AlertType.CHANGE_PERCENT, target_percent=5.0,
        )
        # 100 → 104 is +4%, below threshold
        assert handler._alert_should_fire(a, 104.0, 100.0) is False

    def test_change_percent_returns_false_on_missing_prev_price(self):
        a = _make_alert(
            alert_type=AlertType.CHANGE_PERCENT, target_percent=5.0,
        )
        assert handler._alert_should_fire(a, 105.0, None) is False
        assert handler._alert_should_fire(a, 105.0, 0) is False

    def test_above_returns_false_on_missing_target(self):
        a = _make_alert(alert_type=AlertType.ABOVE, target_price=None)
        assert handler._alert_should_fire(a, 100.0, None) is False


# ---------------------------------------------------------------------------
# _handle_price_update — drives the alert sweep with stubbed plumbing
# ---------------------------------------------------------------------------

def _price_event(symbol="FPT", price=100.0, prev_price=95.0):
    return Event(
        event_type=DomainEvents.STOCK_PRICE_UPDATED,
        payload={"symbol": symbol, "price": price, "prev_price": prev_price},
    )


@pytest.mark.asyncio
async def test_handle_price_update_skips_malformed_payload():
    """Missing symbol / price → no-op, no exception."""
    bad_event = Event(
        event_type=DomainEvents.STOCK_PRICE_UPDATED,
        payload={"price": 100.0},  # missing symbol
    )
    # Should return cleanly without touching the DB
    await handler._handle_price_update(bad_event)


def _make_session_with_alerts(alerts: list) -> AsyncMock:
    """Build an AsyncMock session whose execute() returns scalars().all() == alerts."""
    session = AsyncMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = alerts
    result.scalars.return_value = scalars
    session.execute.return_value = result
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_handle_price_update_triggers_matching_alert(monkeypatch):
    """ABOVE alert at 100; price ticks to 105 → alert flips to triggered."""
    alert = _make_alert(alert_type=AlertType.ABOVE, target_price=100.0)
    session = _make_session_with_alerts([alert])

    # Patch the session factory so the handler picks up our stubbed session.
    factory_cm = MagicMock()
    factory_cm.__aenter__ = AsyncMock(return_value=session)
    factory_cm.__aexit__ = AsyncMock(return_value=None)

    factory = MagicMock(return_value=factory_cm)
    monkeypatch.setattr(handler, "async_session_factory", factory)
    monkeypatch.setattr(handler, "_event_bus", None)  # don't actually publish

    await handler._handle_price_update(_price_event(price=105.0))

    # We expect one SELECT (for the alert sweep) + one UPDATE (mark triggered).
    assert session.execute.await_count == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_price_update_no_op_when_no_alerts(monkeypatch):
    """No alerts for the symbol → handler returns without committing."""
    session = _make_session_with_alerts([])

    factory_cm = MagicMock()
    factory_cm.__aenter__ = AsyncMock(return_value=session)
    factory_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=factory_cm)
    monkeypatch.setattr(handler, "async_session_factory", factory)
    monkeypatch.setattr(handler, "_event_bus", None)

    await handler._handle_price_update(_price_event())

    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_price_update_no_op_when_threshold_not_crossed(monkeypatch):
    """Alert exists but condition not met → no UPDATE, no commit."""
    alert = _make_alert(alert_type=AlertType.ABOVE, target_price=200.0)
    session = _make_session_with_alerts([alert])

    factory_cm = MagicMock()
    factory_cm.__aenter__ = AsyncMock(return_value=session)
    factory_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=factory_cm)
    monkeypatch.setattr(handler, "async_session_factory", factory)
    monkeypatch.setattr(handler, "_event_bus", None)

    await handler._handle_price_update(_price_event(price=100.0))

    # Only the SELECT — no UPDATE / commit when nothing crosses.
    assert session.execute.await_count == 1
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_price_update_publishes_triggered_event(monkeypatch):
    """When an alert fires AND _event_bus is configured, publish
    portfolio.alert.triggered with the right payload + causation linkage."""
    alert = _make_alert(alert_type=AlertType.BELOW, target_price=50.0,
                        alert_id=7, symbol="VNM", user_id=99)
    session = _make_session_with_alerts([alert])

    factory_cm = MagicMock()
    factory_cm.__aenter__ = AsyncMock(return_value=session)
    factory_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=factory_cm)

    fake_bus = AsyncMock()
    monkeypatch.setattr(handler, "async_session_factory", factory)
    monkeypatch.setattr(handler, "_event_bus", fake_bus)

    incoming = _price_event(symbol="VNM", price=45.0)
    await handler._handle_price_update(incoming)

    fake_bus.publish.assert_awaited_once()
    published = fake_bus.publish.await_args.args[0]
    assert published.event_type == DomainEvents.PORTFOLIO_ALERT_TRIGGERED
    assert published.payload["alert_id"] == 7
    assert published.payload["user_id"] == 99
    assert published.payload["symbol"] == "VNM"
    assert published.payload["trigger_price"] == 45.0
    # Causation linkage: triggered event references the price event's id
    assert published.metadata.causation_id == incoming.metadata.event_id


@pytest.mark.asyncio
async def test_handle_price_update_swallows_db_errors(monkeypatch, caplog):
    """A failure inside the DB block is logged, never propagated.
    Otherwise the consumer would nack into the DLQ on every transient blip."""
    factory_cm = MagicMock()
    factory_cm.__aenter__ = AsyncMock(side_effect=RuntimeError("DB down"))
    factory_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=factory_cm)
    monkeypatch.setattr(handler, "async_session_factory", factory)
    monkeypatch.setattr(handler, "_event_bus", None)

    # Should not raise
    await handler._handle_price_update(_price_event())


# ---------------------------------------------------------------------------
# Lifecycle — start / stop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_alert_consumer_returns_none_on_rabbit_unavailable(
    monkeypatch,
):
    """RabbitMQ down → start_alert_consumer logs and returns None rather
    than failing the service boot."""
    class BoomBus:
        def __init__(self, *a, **kw):
            pass
        async def connect(self):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(handler, "EventBus", BoomBus)
    bus = await handler.start_alert_consumer()
    assert bus is None


@pytest.mark.asyncio
async def test_stop_alert_consumer_is_idempotent_when_not_started(monkeypatch):
    """Calling stop without a prior start should not raise."""
    monkeypatch.setattr(handler, "_event_bus", None)
    await handler.stop_alert_consumer()
