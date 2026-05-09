"""Tests for the notifications scaffold (consumer + CRUD routes).

Mocks the RabbitMQ side and the SQL session so we can verify both
halves of the flow:
- consumer: alert.triggered event → Notification row inserted, dedup
  on source_event_id, malformed payload skipped, db errors swallowed
- routes: list/mark-read/mark-all/delete operate per-user with
  proper isolation
"""
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.domain import Notification, NotificationType
from app.services import notification_consumer as consumer
from stock_common.events import Event
from stock_common.events.models import DomainEvents


# ---------------------------------------------------------------------------
# _format_alert_triggered — pure formatter, easy to verify
# ---------------------------------------------------------------------------

class TestFormatter:
    def test_above_alert(self):
        title, body, meta = consumer._format_alert_triggered(
            {
                "symbol": "FPT",
                "alert_type": "above",
                "target_price": 100.0,
                "trigger_price": 105.0,
                "alert_id": 7,
                "user_id": 1,
            }
        )
        assert "FPT" in title and "100" in title and "above" in title.lower()
        assert "105" in body
        assert meta["alert_id"] == 7
        assert meta["alert_type"] == "above"

    def test_below_alert(self):
        title, _, _ = consumer._format_alert_triggered(
            {"symbol": "VNM", "alert_type": "below", "target_price": 50.0}
        )
        assert "VNM" in title and "below" in title.lower()

    def test_change_percent_alert(self):
        title, body, _ = consumer._format_alert_triggered(
            {
                "symbol": "VCB",
                "alert_type": "change_percent",
                "target_percent": 5.0,
                "trigger_price": 90.0,
            }
        )
        assert "VCB" in title
        assert "5" in title  # formatter renders "5.0%+"
        assert "90" in body

    def test_unknown_alert_type_falls_back(self):
        title, body, _ = consumer._format_alert_triggered(
            {"symbol": "HPG", "trigger_price": 25.0}
        )
        assert "HPG" in title  # generic fallback still names the symbol


# ---------------------------------------------------------------------------
# _handle_alert_triggered — the consumer logic
# ---------------------------------------------------------------------------

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


def _make_session_factory(existing_event_id: str | None = None) -> tuple[MagicMock, MagicMock]:
    """Build an async session-factory mock + the session it yields.
    `existing_event_id` simulates the dedup query finding (or not finding)
    a prior notification with that source_event_id.
    """
    session = AsyncMock()

    dedup_result = MagicMock()
    dedup_result.scalar_one_or_none.return_value = existing_event_id
    session.execute.return_value = dedup_result
    session.commit = AsyncMock()
    session.add = MagicMock()

    factory_cm = MagicMock()
    factory_cm.__aenter__ = AsyncMock(return_value=session)
    factory_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=factory_cm)
    return factory, session


@pytest.mark.asyncio
async def test_handle_alert_skips_payload_without_user_id(monkeypatch):
    factory, session = _make_session_factory()
    monkeypatch.setattr(consumer, "async_session_factory", factory)

    bad = Event(
        event_type=DomainEvents.PORTFOLIO_ALERT_TRIGGERED,
        payload={"symbol": "FPT"},  # no user_id
    )
    await consumer._handle_alert_triggered(bad)

    factory.assert_not_called()  # never even opened a session


@pytest.mark.asyncio
async def test_handle_alert_persists_notification(monkeypatch):
    factory, session = _make_session_factory(existing_event_id=None)
    monkeypatch.setattr(consumer, "async_session_factory", factory)

    event = _alert_event(user_id=42, symbol="VNM", price=72.5, alert_type="above")
    await consumer._handle_alert_triggered(event)

    session.add.assert_called_once()
    notif = session.add.call_args.args[0]
    assert isinstance(notif, Notification)
    assert notif.user_id == 42
    assert notif.type == NotificationType.ALERT_TRIGGERED
    assert "VNM" in notif.title
    assert notif.source_event_id == event.metadata.event_id

    # Metadata should be JSON-serialized and contain the trigger price.
    meta = json.loads(notif.metadata_json)
    assert meta["symbol"] == "VNM"
    assert meta["trigger_price"] == 72.5

    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_alert_dedupes_on_source_event_id(monkeypatch):
    """Same event replayed (DLQ retry / reconnect) → second insert skipped."""
    factory, session = _make_session_factory(existing_event_id=99)
    monkeypatch.setattr(consumer, "async_session_factory", factory)

    await consumer._handle_alert_triggered(_alert_event())

    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_alert_swallows_db_errors(monkeypatch):
    """A failure in the DB block must NOT raise — would nack into DLQ."""
    factory_cm = MagicMock()
    factory_cm.__aenter__ = AsyncMock(side_effect=RuntimeError("DB down"))
    factory_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=factory_cm)
    monkeypatch.setattr(consumer, "async_session_factory", factory)

    # Should not raise
    await consumer._handle_alert_triggered(_alert_event())


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_consumer_returns_none_on_rabbit_failure(monkeypatch):
    class BoomBus:
        def __init__(self, *a, **kw):
            pass

        async def connect(self):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(consumer, "EventBus", BoomBus)
    bus = await consumer.start_notification_consumer()
    assert bus is None


@pytest.mark.asyncio
async def test_stop_consumer_idempotent_when_not_started(monkeypatch):
    monkeypatch.setattr(consumer, "_event_bus", None)
    await consumer.stop_notification_consumer()  # must not raise


# ---------------------------------------------------------------------------
# Routes — list / mark-read / mark-all / delete
# ---------------------------------------------------------------------------

PREFIX = "/stock_helper/api/v2/portfolio/notifications"


def _make_notif(id_: int, user_id: int = 1, read: bool = False, title: str = "FPT crossed above 100") -> Notification:
    n = Notification(
        user_id=user_id,
        type=NotificationType.ALERT_TRIGGERED,
        title=title,
        body="Body",
        metadata_json=json.dumps({"symbol": "FPT", "trigger_price": 105.0}),
        source_event_id=f"evt-{id_}",
        created_at=datetime.utcnow(),
    )
    n.id = id_
    if read:
        n.read_at = datetime.utcnow()
    return n


def _wire_list_results(mock_db, notifs, total: int, unread: int):
    """Configure a mock_db so that:
      1st execute() → list query (returns notifs.scalars().all())
      2nd execute() → total count
      3rd execute() → unread count
    """
    list_result = MagicMock()
    list_scalars = MagicMock()
    list_scalars.all.return_value = notifs
    list_result.scalars.return_value = list_scalars

    total_result = MagicMock()
    total_result.scalar_one.return_value = total

    unread_result = MagicMock()
    unread_result.scalar_one.return_value = unread

    mock_db.execute.side_effect = [list_result, total_result, unread_result]


@pytest.mark.asyncio
async def test_list_notifications_returns_items_and_counts(client, mock_db):
    notifs = [_make_notif(2, read=False), _make_notif(1, read=True)]
    _wire_list_results(mock_db, notifs, total=2, unread=1)

    r = await client.get(PREFIX)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["unread"] == 1
    assert len(body["items"]) == 2
    # Read flag flows from read_at presence
    assert body["items"][0]["read"] is False
    assert body["items"][1]["read"] is True
    # Metadata JSON parsed back into a dict
    assert body["items"][0]["metadata"]["symbol"] == "FPT"


@pytest.mark.asyncio
async def test_list_notifications_empty(client, mock_db):
    _wire_list_results(mock_db, [], total=0, unread=0)
    r = await client.get(PREFIX)
    assert r.status_code == 200
    body = r.json()
    assert body == {"items": [], "total": 0, "unread": 0}


@pytest.mark.asyncio
async def test_mark_read_404_when_missing(client, mock_db):
    """Other users / nonexistent IDs return 404, not 500."""
    not_found = MagicMock()
    not_found.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = not_found

    r = await client.post(f"{PREFIX}/9999/read")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_mark_read_sets_read_at(client, mock_db):
    notif = _make_notif(7, read=False)
    found = MagicMock()
    found.scalar_one_or_none.return_value = notif
    mock_db.execute.return_value = found

    r = await client.post(f"{PREFIX}/7/read")
    assert r.status_code == 200
    assert r.json()["read"] is True
    assert notif.read_at is not None
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_mark_read_idempotent_when_already_read(client, mock_db):
    """Calling mark-read on an already-read notif does not bump read_at
    or commit again — it just returns the current state."""
    notif = _make_notif(7, read=True)
    original_read_at = notif.read_at
    found = MagicMock()
    found.scalar_one_or_none.return_value = notif
    mock_db.execute.return_value = found

    r = await client.post(f"{PREFIX}/7/read")
    assert r.status_code == 200
    assert notif.read_at == original_read_at
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_mark_all_read_returns_updated_count(client, mock_db):
    """update().rowcount flows through to MarkReadResponse.updated."""
    update_result = MagicMock()
    update_result.rowcount = 5
    mock_db.execute.return_value = update_result

    r = await client.post(f"{PREFIX}/read-all")
    assert r.status_code == 200
    assert r.json() == {"updated": 5}
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_notification_404_when_missing(client, mock_db):
    not_found = MagicMock()
    not_found.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = not_found

    r = await client.delete(f"{PREFIX}/9999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_notification_succeeds(client, mock_db):
    notif = _make_notif(3, read=False)
    found = MagicMock()
    found.scalar_one_or_none.return_value = notif
    mock_db.execute.return_value = found
    mock_db.delete = AsyncMock()

    r = await client.delete(f"{PREFIX}/3")
    assert r.status_code == 204
    mock_db.delete.assert_awaited_once_with(notif)
    mock_db.commit.assert_awaited()
