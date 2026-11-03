"""Coverage for alert_event_handler — the event-driven price-alert path
shipped in Sprint B (stock.price.updated → trigger matching alerts →
publish portfolio.alert.triggered).

Tests focus on `_alert_should_fire()` (pure trigger logic) directly and
on `_handle_price_update()` with stubbed Redis/SQL plumbing. We don't
need a live RabbitMQ here — `_event_bus` is patched to None so the
publish branch is exercised as a no-op.
"""
from datetime import datetime, timedelta

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


# ---------------------------------------------------------------------------
# The binding, which is the half that was broken
# ---------------------------------------------------------------------------

def test_the_consumer_binds_the_pattern_the_publisher_actually_sends():
    """This handler had tests, a durable queue and a live consumer, and received
    nothing for its entire life: it bound `stock.price.updated` while
    stock-data-service publishes `stock.price.updated.<SYMBOL>`, which a topic
    exchange does not match. Both sides now take the convention from
    stock_common.events.routing; this asserts the consumer still uses it."""
    import inspect

    from stock_common.events.routing import (
        PRICE_UPDATED_PATTERN,
        price_updated_routing_key,
        topic_matches,
    )

    import app.services.alert_event_handler as mod

    src = inspect.getsource(mod.start_alert_consumer)
    assert "PRICE_UPDATED_PATTERN" in src, (
        "the consumer no longer binds the shared pattern; a bare event name here "
        "silently receives nothing"
    )
    # And the shared pattern really does match what the publisher sends.
    assert topic_matches(PRICE_UPDATED_PATTERN, price_updated_routing_key("ACB"))


# ---------------------------------------------------------------------------
# Backlog #117 — the unusual-volume alert
# ---------------------------------------------------------------------------

def _vol_alert(multiple=None, alert_id=1):
    from app.models.domain import AlertType, PriceAlert

    a = PriceAlert()
    a.id = alert_id
    a.alert_type = AlertType.VOLUME_UNUSUAL
    a.target_percent = multiple
    a.target_price = None
    return a


def test_a_volume_alert_fires_at_its_multiple():
    from app.services.alert_event_handler import _volume_alert_should_fire

    assert _volume_alert_should_fire(_vol_alert(3.0), 3.0) is True
    assert _volume_alert_should_fire(_vol_alert(3.0), 4.2) is True
    assert _volume_alert_should_fire(_vol_alert(3.0), 2.99) is False


def test_an_alert_without_a_multiple_uses_the_measured_default():
    """3.0x was measured, not picked: across 42,674 readings on 32 real symbols
    it fires on 4.55% of them — about eleven times per symbol per year. 1.5x
    would be eight a day across the watchlist, which is how alerting features
    get muted."""
    from app.services.alert_event_handler import (
        DEFAULT_VOLUME_MULTIPLE,
        _volume_alert_should_fire,
    )

    assert DEFAULT_VOLUME_MULTIPLE == 3.0
    assert _volume_alert_should_fire(_vol_alert(None), 3.1) is True
    assert _volume_alert_should_fire(_vol_alert(None), 2.5) is False


def test_an_ABSENT_reading_never_fires():
    """The reading is an explicit unknown when a symbol has too little history
    or a dormant window. Firing on an unknown would invent an event; and
    treating the absence as 'not unusual' is luck rather than logic, which is
    why the branch is explicit rather than falling out of a comparison."""
    from app.services.alert_event_handler import _volume_alert_should_fire

    assert _volume_alert_should_fire(_vol_alert(3.0), None) is False


@pytest.mark.parametrize("junk", ["lots", "", float("nan")])
def test_an_unusable_reading_never_fires(junk):
    from app.services.alert_event_handler import _volume_alert_should_fire

    assert _volume_alert_should_fire(_vol_alert(3.0), junk) is False


def test_a_volume_alert_is_not_judged_on_price():
    """The bug this dispatch avoids: _alert_should_fire takes no volume
    argument, so routing a VOLUME_UNUSUAL alert through it would always return
    False and the alert would silently never fire."""
    from app.services.alert_event_handler import _alert_should_fire

    assert _alert_should_fire(_vol_alert(3.0), 999_999.0, 1.0) is False


def test_the_handler_dispatches_volume_alerts_on_rel_volume():
    """Guards the wiring, which is where this feature would die quietly."""
    import inspect

    import app.services.alert_event_handler as mod

    src = inspect.getsource(mod._handle_price_update)
    assert "rel_volume" in src, "the handler never reads the event's rel_volume"
    assert "_volume_alert_should_fire" in src, "volume alerts are not dispatched"
    assert "VOLUME_UNUSUAL" in src


def test_price_alerts_still_work_unchanged():
    """The counterpart: adding a branch must not disturb the three existing
    alert kinds."""
    from app.models.domain import AlertType, PriceAlert
    from app.services.alert_event_handler import _alert_should_fire

    def mk(kind, price=None, pct=None):
        a = PriceAlert()
        a.alert_type = kind
        a.target_price = price
        a.target_percent = pct
        return a

    assert _alert_should_fire(mk(AlertType.ABOVE, price=100.0), 101.0, None) is True
    assert _alert_should_fire(mk(AlertType.ABOVE, price=100.0), 99.0, None) is False
    assert _alert_should_fire(mk(AlertType.BELOW, price=100.0), 99.0, None) is True
    assert _alert_should_fire(mk(AlertType.CHANGE_PERCENT, pct=5.0), 110.0, 100.0) is True
    assert _alert_should_fire(mk(AlertType.CHANGE_PERCENT, pct=5.0), 102.0, 100.0) is False


def test_the_api_enum_and_the_domain_enum_agree():
    """Two separate AlertType enums exist — the API-facing one in schemas.py and
    the persisted one in domain.py. A value present in only one is a boundary
    that silently cannot be used: the database would accept a volume alert the
    endpoint rejects, or vice versa. Backlog #117 added VOLUME_UNUSUAL and this
    is what stops the next addition landing in only one of them."""
    from app.models.domain import AlertType as DomainAlertType
    from app.models.schemas import AlertType as ApiAlertType

    assert {t.value for t in DomainAlertType} == {t.value for t in ApiAlertType}


def test_the_alert_type_enum_column_is_widened_at_startup():
    """Backlog #117. The Python enum gaining a member does nothing to the MySQL
    column: create_all() does not ALTER an existing table, so price_alerts
    kept enum('ABOVE','BELOW','CHANGE_PERCENT') and an insert failed with
    "Data truncated for column 'alert_type'".

    That failure appears ONLY against a real MySQL — every Python-side test in
    this file passes without it, which is exactly why this guard reads the
    startup SQL instead of trusting them.
    """
    import inspect

    import app.main as main_mod

    src = inspect.getsource(main_mod.lifespan)
    assert "price_alerts MODIFY COLUMN alert_type" in src, (
        "nothing widens the alert_type column, so VOLUME_UNUSUAL cannot be stored"
    )
    # Uppercase member NAMES, because SQLAlchemy Enum persists the name.
    assert "'VOLUME_UNUSUAL'" in src
    for existing in ("'ABOVE'", "'BELOW'", "'CHANGE_PERCENT'"):
        assert existing in src, f"{existing} dropped from the member set — MODIFY replaces it"


# ---------------------------------------------------------------------------
# Backlog #117 — what the notification SAYS
#
# The first live firing produced "Your alert for POW fired at 20000.0" — a true
# sentence about the wrong quantity. A volume alert must state the MULTIPLE, and
# must not state a verdict: volume is attention, not direction.
# ---------------------------------------------------------------------------

def _vol_payload(rel_volume=5.0, multiple=3.0):
    return {
        "alert_id": 1, "user_id": 1, "symbol": "POW",
        "alert_type": "volume_unusual",
        "target_price": None, "target_percent": multiple,
        "trigger_price": 20000.0, "rel_volume": rel_volume,
    }


def test_the_in_app_notification_states_the_multiple_not_the_price():
    from app.services.notification_consumer import _format_alert_triggered

    title, body, meta = _format_alert_triggered(_vol_payload())
    text = f"{title} {body}"
    assert "5.0x" in text
    assert "median volume" in text
    assert "20000" not in text, "the price leaked into a volume alert's message"


def test_the_email_states_the_multiple_and_refuses_a_verdict():
    from app.services.email_service import format_alert_email

    subject, text_body, html_body = format_alert_email(_vol_payload())
    assert "5.0x" in subject and "POW" in subject
    assert "median volume" in text_body
    assert "20000" not in text_body, "the price leaked into a volume alert's email"
    # It must not claim the news is good or bad — volume is attention only.
    lowered = text_body.lower()
    for forbidden in ("good news", "bad news", "bullish", "bearish", "buy", "sell"):
        assert forbidden not in lowered, forbidden
    assert "not direction" in lowered


def test_the_push_notification_states_the_multiple():
    from app.services.push_service import format_alert_push
    out = format_alert_push(_vol_payload())
    assert "5.0x" in out["title"] or "5.0x" in out["body"]
    assert "median volume" in out["body"]


def test_an_absent_reading_degrades_to_words_not_to_a_fake_number():
    from app.services.email_service import format_alert_email

    subject, text_body, _ = format_alert_email(_vol_payload(rel_volume=None))
    assert "unusually high" in subject or "unusually high" in text_body
    assert "None" not in text_body and "0.0x" not in text_body


def test_price_alert_wording_is_unchanged():
    """Adding a branch must not disturb the three existing kinds."""
    from app.services.email_service import format_alert_email

    for kind, expect in (("above", "above"), ("below", "below"), ("change_percent", "%")):
        payload = dict(_vol_payload(), alert_type=kind, target_price=25000.0, target_percent=5.0)
        subject, body, _ = format_alert_email(payload)
        assert "POW" in subject
        assert expect in (subject + body).lower() or expect in (subject + body)


def test_the_triggered_event_carries_the_reading():
    """Without rel_volume on the event the consumers can only quote a price."""
    import inspect

    import app.services.alert_event_handler as mod

    src = inspect.getsource(mod._handle_price_update)
    assert '"rel_volume": rel_volume' in src


# ---------------------------------------------------------------------------
# Backlog #117 — a volume alert RE-FIRES, but at most once per market day
#
# A price alert is rightly one-shot: "above 25,000" is a threshold crossed once.
# Unusual volume RECURS, so a one-shot volume alert goes quiet after its first
# day and never speaks again — which is why the owner asked for this.
#
# But an unconditional re-arm is the opposite mistake. rel_volume is a DAILY
# aggregate: today's cumulative volume over the median of daily bars. The
# priceboard refreshes repeatedly through a session, so an always-armed alert
# would fire on every refresh while volume stayed above the multiple — roughly
# two dozen notifications for ONE event. "POW traded unusually today" happens
# once a day.
# ---------------------------------------------------------------------------

def _vol_alert_at(triggered_at, multiple=3.0):
    from app.models.domain import AlertType, PriceAlert

    a = PriceAlert()
    a.id = 1
    a.alert_type = AlertType.VOLUME_UNUSUAL
    a.target_percent = multiple
    a.target_price = None
    a.is_triggered = triggered_at is not None
    a.triggered_at = triggered_at
    return a


def test_a_volume_alert_that_never_fired_can_fire():
    from app.services.alert_event_handler import _volume_alert_should_fire

    assert _volume_alert_should_fire(_vol_alert_at(None), 5.0) is True


def test_a_volume_alert_refires_on_a_LATER_day():
    """The whole point: unusual volume recurs, so yesterday's firing must not
    silence the alert forever."""
    from app.services.alert_event_handler import _market_now, _volume_alert_should_fire

    yesterday = _market_now() - timedelta(days=1)
    assert _volume_alert_should_fire(_vol_alert_at(yesterday), 5.0) is True


def test_a_volume_alert_does_NOT_refire_the_same_day():
    """The counterpart, and the reason this is not an unconditional re-arm: the
    priceboard refreshes many times a session, and rel_volume stays above the
    multiple for the rest of the day once a spike happens."""
    from app.services.alert_event_handler import _market_now, _volume_alert_should_fire

    earlier_today = _market_now() - timedelta(minutes=30)
    assert _volume_alert_should_fire(_vol_alert_at(earlier_today), 5.0) is False


def test_the_day_boundary_is_the_MARKET_day_not_utc():
    """A VN session is 09:00-15:00 ICT. Defining the day in UTC would be right
    during the session and wrong for an after-hours refresh, so the boundary is
    stated in market time rather than inherited from the server clock."""
    from app.services.alert_event_handler import MARKET_TZ_OFFSET, _market_now

    assert MARKET_TZ_OFFSET == timedelta(hours=7)
    # _market_now is ahead of naive UTC by exactly the offset.
    delta = _market_now() - datetime.utcnow()
    assert timedelta(hours=6, minutes=59) < delta < timedelta(hours=7, minutes=1)


def test_a_price_alert_is_still_one_shot():
    """Re-firing is deliberately scoped to volume. "Above 25,000" is a threshold
    crossed once; re-arming it daily would change a shipped behaviour nobody
    asked to change."""
    import inspect

    import app.services.alert_event_handler as mod

    src = inspect.getsource(mod._handle_price_update)
    # The query must still exclude triggered alerts EXCEPT volume ones.
    assert "is_triggered.is_(False)" in src
    assert "VOLUME_UNUSUAL" in src
    assert "or_" in src, "triggered volume alerts are never re-read from the DB"


def test_the_query_re_reads_triggered_volume_alerts():
    """Guards the half that is easy to miss: the predicate can say "fire again"
    all it likes, but if the SELECT still filters is_triggered=False the alert
    is never even loaded."""
    import inspect

    import app.services.alert_event_handler as mod

    src = inspect.getsource(mod._handle_price_update)
    where = src[src.index("select(PriceAlert)"):src.index("alerts = result")]
    assert "or_" in where and "VOLUME_UNUSUAL" in where, where
