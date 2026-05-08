"""Coverage for stock-data-service's EventBus publisher (Sprint B).

publish_price_updates() is the producer for stock.price.updated events
that portfolio-service consumes. We exercise the success path, the
malformed-record skip, and the RabbitMQ-down degrade path without
touching real RabbitMQ.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.services import event_publisher


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Force a clean module-level _event_bus between tests so init/shutdown
    state from one test doesn't bleed into the next."""
    event_publisher._event_bus = None
    yield
    event_publisher._event_bus = None


# ---------------------------------------------------------------------------
# init / shutdown lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_init_event_publisher_returns_none_on_rabbit_unavailable(
    monkeypatch,
):
    """If RabbitMQ is unreachable, init logs a warning and returns None.
    The service is still expected to boot — the publisher just becomes
    a silent no-op for the rest of its lifetime."""
    class BoomBus:
        def __init__(self, *a, **kw):
            pass

        async def connect(self):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(event_publisher, "EventBus", BoomBus)
    bus = await event_publisher.init_event_publisher()
    assert bus is None
    assert event_publisher._event_bus is None


@pytest.mark.asyncio
async def test_init_event_publisher_is_idempotent(monkeypatch):
    """Calling init twice should not reconnect — the second call returns
    the cached bus."""
    fake_bus = AsyncMock()

    class FakeEventBus:
        def __new__(cls, *a, **kw):
            return fake_bus

    monkeypatch.setattr(event_publisher, "EventBus", FakeEventBus)

    first = await event_publisher.init_event_publisher()
    second = await event_publisher.init_event_publisher()
    assert first is second is fake_bus
    # connect should only have happened once
    fake_bus.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_event_publisher_when_not_initialized():
    """Calling shutdown without prior init should be a no-op."""
    # Should not raise
    await event_publisher.shutdown_event_publisher()


@pytest.mark.asyncio
async def test_shutdown_event_publisher_calls_disconnect():
    fake_bus = AsyncMock()
    event_publisher._event_bus = fake_bus

    await event_publisher.shutdown_event_publisher()

    fake_bus.disconnect.assert_awaited_once()
    assert event_publisher._event_bus is None


@pytest.mark.asyncio
async def test_shutdown_swallows_disconnect_error():
    """A flaky disconnect should not raise — the service is shutting down
    anyway."""
    fake_bus = AsyncMock()
    fake_bus.disconnect = AsyncMock(side_effect=RuntimeError("kaboom"))
    event_publisher._event_bus = fake_bus

    # Should not raise
    await event_publisher.shutdown_event_publisher()
    assert event_publisher._event_bus is None


# ---------------------------------------------------------------------------
# publish_price_updates — fans out per record
# ---------------------------------------------------------------------------

def _record(symbol="FPT", match_price=125.5, ref_price=120.0,
            change_percent=4.58, exchange="HOSE"):
    return {
        "symbol": symbol,
        "matchPrice": match_price,
        "refPrice": ref_price,
        "changePercent": change_percent,
        "exchange": exchange,
    }


@pytest.mark.asyncio
async def test_publish_price_updates_no_op_when_publisher_uninitialized():
    """Service started without EventBus available → publish should be a
    silent no-op rather than raising."""
    event_publisher._event_bus = None

    # Should not raise
    await event_publisher.publish_price_updates([_record()])


@pytest.mark.asyncio
async def test_publish_price_updates_no_op_on_empty_list():
    """No records → no events. Don't even touch the bus."""
    fake_bus = AsyncMock()
    event_publisher._event_bus = fake_bus

    await event_publisher.publish_price_updates([])

    fake_bus.publish.assert_not_called()


@pytest.mark.asyncio
async def test_publish_price_updates_publishes_one_event_per_record():
    fake_bus = AsyncMock()
    event_publisher._event_bus = fake_bus

    records = [
        _record(symbol="FPT", match_price=125.5),
        _record(symbol="VNM", match_price=72.0),
        _record(symbol="VCB", match_price=89.0),
    ]
    await event_publisher.publish_price_updates(records)

    assert fake_bus.publish.await_count == 3


@pytest.mark.asyncio
async def test_publish_price_updates_uses_per_symbol_routing_key():
    """Routing key should suffix the symbol so consumers can subscribe
    per-symbol if they want to."""
    fake_bus = AsyncMock()
    event_publisher._event_bus = fake_bus

    await event_publisher.publish_price_updates([_record(symbol="FPT")])

    call = fake_bus.publish.await_args
    routing_key = call.kwargs.get("routing_key") or (call.args[1] if len(call.args) > 1 else None)
    assert routing_key == "stock.price.updated.FPT"


@pytest.mark.asyncio
async def test_publish_price_updates_event_payload_has_required_fields():
    fake_bus = AsyncMock()
    event_publisher._event_bus = fake_bus

    await event_publisher.publish_price_updates([_record(symbol="FPT", match_price=125.5)])

    event = fake_bus.publish.await_args.args[0]
    assert event.event_type == "stock.price.updated"
    assert event.payload["symbol"] == "FPT"
    assert event.payload["price"] == 125.5
    assert event.payload["ref_price"] == 120.0
    assert event.payload["exchange"] == "HOSE"


@pytest.mark.asyncio
async def test_publish_price_updates_skips_records_missing_symbol():
    """Defensive: bad record shape → log & skip, don't crash the publish loop."""
    fake_bus = AsyncMock()
    event_publisher._event_bus = fake_bus

    bad = {"matchPrice": 100.0}  # no symbol
    good = _record(symbol="FPT")

    await event_publisher.publish_price_updates([bad, good])

    # Only the good record published.
    assert fake_bus.publish.await_count == 1
    event = fake_bus.publish.await_args.args[0]
    assert event.payload["symbol"] == "FPT"


@pytest.mark.asyncio
async def test_publish_price_updates_skips_records_missing_price():
    fake_bus = AsyncMock()
    event_publisher._event_bus = fake_bus

    no_price = {"symbol": "FPT"}  # no matchPrice
    await event_publisher.publish_price_updates([no_price])

    fake_bus.publish.assert_not_called()


@pytest.mark.asyncio
async def test_publish_price_updates_swallows_per_record_failure():
    """One bad publish shouldn't take down the whole batch."""
    fake_bus = AsyncMock()
    fake_bus.publish.side_effect = [
        RuntimeError("transient"),       # first record fails
        None,                              # second succeeds
    ]
    event_publisher._event_bus = fake_bus

    # Should not raise
    await event_publisher.publish_price_updates([
        _record(symbol="FPT"),
        _record(symbol="VNM"),
    ])

    # Both attempted
    assert fake_bus.publish.await_count == 2


@pytest.mark.asyncio
async def test_publish_price_updates_handles_missing_optional_fields():
    """ref_price absent → payload still publishes with ref_price=None."""
    fake_bus = AsyncMock()
    event_publisher._event_bus = fake_bus

    minimal = {"symbol": "FPT", "matchPrice": 100.0}  # no refPrice
    await event_publisher.publish_price_updates([minimal])

    event = fake_bus.publish.await_args.args[0]
    assert event.payload["ref_price"] is None
