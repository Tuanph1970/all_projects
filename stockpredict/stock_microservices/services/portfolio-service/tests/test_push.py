"""Tests for the web-push channel: service, consumer, and HTTP routes.

Mocks pywebpush + the DB layer so we can verify:
- push_service: dev-fallback when VAPID unset, success path, 410 from
  push service returns the status code so the consumer can prune
- push_consumer: payload skip, no-subscriptions skip, fan-out to many
  subs, expired subs pruned via DELETE, errors swallowed, lifecycle
- routes: subscribe (insert + refresh), unsubscribe, vapid-public-key
  503 when unconfigured / 200 when set
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import push_consumer as consumer
from app.services import push_service
from stock_common.events import Event
from stock_common.events.models import DomainEvents


# ---------------------------------------------------------------------------
# format_alert_push — pure formatter
# ---------------------------------------------------------------------------

class TestFormatter:
    def test_above_alert(self):
        out = push_service.format_alert_push(
            {
                "symbol": "FPT",
                "alert_type": "above",
                "target_price": 100.0,
                "trigger_price": 105.0,
                "alert_id": 7,
            }
        )
        assert "FPT" in out["title"] and "above" in out["title"].lower()
        assert "105" in out["body"]
        assert out["tag"] == "alert-7"
        assert out["data"]["alert_id"] == 7
        assert out["data"]["symbol"] == "FPT"

    def test_unknown_alert_type_falls_back(self):
        out = push_service.format_alert_push(
            {"symbol": "HPG", "trigger_price": 25.0}
        )
        assert "HPG" in out["title"]
        # alert_id missing → tag falls back to symbol
        assert out["tag"] == "alert-HPG"


# ---------------------------------------------------------------------------
# send_push_to_subscription
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_push_returns_false_when_vapid_unset(monkeypatch):
    """Dev fallback: no private key → log + return (False, None).
    Must NOT raise — same surface as the configured path."""
    monkeypatch.setattr(
        push_service,
        "get_settings",
        lambda: SimpleNamespace(VAPID_PRIVATE_KEY=None, VAPID_SUBJECT="mailto:x@y"),
    )
    delivered, status = await push_service.send_push_to_subscription(
        endpoint="https://example/push/abc",
        p256dh="p",
        auth="a",
        payload={"title": "t"},
    )
    assert delivered is False
    assert status is None


@pytest.mark.asyncio
async def test_send_push_success(monkeypatch):
    monkeypatch.setattr(
        push_service,
        "get_settings",
        lambda: SimpleNamespace(
            VAPID_PRIVATE_KEY="priv", VAPID_SUBJECT="mailto:x@y"
        ),
    )
    monkeypatch.setattr(push_service, "_send_sync", lambda *a, **kw: None)

    delivered, status = await push_service.send_push_to_subscription(
        endpoint="https://example/push/abc",
        p256dh="p",
        auth="a",
        payload={"title": "t"},
    )
    assert delivered is True
    assert status is None


@pytest.mark.asyncio
async def test_send_push_propagates_410_for_pruning(monkeypatch):
    """410 Gone means the subscription is dead — caller will prune it."""
    monkeypatch.setattr(
        push_service,
        "get_settings",
        lambda: SimpleNamespace(
            VAPID_PRIVATE_KEY="priv", VAPID_SUBJECT="mailto:x@y"
        ),
    )

    class FakeResponse:
        status_code = 410

    class FakeWebPushError(Exception):
        response = FakeResponse()

    def boom(*_a, **_kw):
        raise FakeWebPushError("gone")

    monkeypatch.setattr(push_service, "_send_sync", boom)

    delivered, status = await push_service.send_push_to_subscription(
        endpoint="https://example/push/dead",
        p256dh="p",
        auth="a",
        payload={"title": "t"},
    )
    assert delivered is False
    assert status == 410


# ---------------------------------------------------------------------------
# push_consumer._handle_alert_triggered
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


def _make_session_factory(subs: list):
    """Return (factory, session). subs is the list scalars().all() yields."""
    session = AsyncMock()

    list_result = MagicMock()
    list_scalars = MagicMock()
    list_scalars.all.return_value = subs
    list_result.scalars.return_value = list_scalars
    session.execute.return_value = list_result
    session.commit = AsyncMock()

    factory_cm = MagicMock()
    factory_cm.__aenter__ = AsyncMock(return_value=session)
    factory_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=factory_cm)
    return factory, session


def _fake_sub(id_, endpoint="https://push.example/s1"):
    return SimpleNamespace(
        id=id_,
        user_id=42,
        endpoint=endpoint,
        p256dh_key="p",
        auth_key="a",
    )


@pytest.mark.asyncio
async def test_handle_alert_skips_payload_without_user_id(monkeypatch):
    send_mock = AsyncMock()
    monkeypatch.setattr(consumer, "send_push_to_subscriptions", send_mock)

    bad = Event(
        event_type=DomainEvents.PORTFOLIO_ALERT_TRIGGERED,
        payload={"symbol": "FPT"},
    )
    await consumer._handle_alert_triggered(bad)
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_alert_skips_when_no_subscriptions(monkeypatch):
    factory, _ = _make_session_factory(subs=[])
    monkeypatch.setattr(consumer, "async_session_factory", factory)

    send_mock = AsyncMock()
    monkeypatch.setattr(consumer, "send_push_to_subscriptions", send_mock)

    await consumer._handle_alert_triggered(_alert_event())
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_alert_fans_out_to_subscriptions(monkeypatch):
    subs = [_fake_sub(1), _fake_sub(2, endpoint="https://push.example/s2")]
    factory, session = _make_session_factory(subs=subs)
    monkeypatch.setattr(consumer, "async_session_factory", factory)

    send_mock = AsyncMock(return_value=[(1, True, None), (2, True, None)])
    monkeypatch.setattr(consumer, "send_push_to_subscriptions", send_mock)

    await consumer._handle_alert_triggered(_alert_event())

    send_mock.assert_awaited_once()
    args, _ = send_mock.call_args
    passed_subs, payload = args
    assert list(passed_subs) == subs
    assert "FPT" in payload["title"]
    # No expired subs → no DELETE issued (only the initial SELECT).
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_handle_alert_prunes_expired_subscriptions(monkeypatch):
    """404/410 from the push service → DELETE the row."""
    subs = [_fake_sub(1), _fake_sub(2, endpoint="https://push.example/s2")]
    factory, session = _make_session_factory(subs=subs)
    monkeypatch.setattr(consumer, "async_session_factory", factory)

    send_mock = AsyncMock(return_value=[(1, True, None), (2, False, 410)])
    monkeypatch.setattr(consumer, "send_push_to_subscriptions", send_mock)

    await consumer._handle_alert_triggered(_alert_event())

    # SELECT + DELETE = 2 executes; commit() called once for the prune.
    assert session.execute.await_count == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_alert_swallows_db_errors(monkeypatch):
    factory_cm = MagicMock()
    factory_cm.__aenter__ = AsyncMock(side_effect=RuntimeError("DB down"))
    factory_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=factory_cm)
    monkeypatch.setattr(consumer, "async_session_factory", factory)

    # Must not raise
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
    bus = await consumer.start_push_consumer()
    assert bus is None


@pytest.mark.asyncio
async def test_stop_consumer_idempotent_when_not_started(monkeypatch):
    monkeypatch.setattr(consumer, "_event_bus", None)
    await consumer.stop_push_consumer()  # must not raise


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------

PREFIX = "/stock_helper/api/v2/portfolio/push"


@pytest.mark.asyncio
async def test_vapid_public_key_503_when_unconfigured(client, monkeypatch):
    from app.config import get_settings
    get_settings.cache_clear()

    monkeypatch.setenv("VAPID_PUBLIC_KEY", "")
    # Re-prime cache with cleared env
    get_settings.cache_clear()

    r = await client.get(f"{PREFIX}/vapid-public-key")
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_vapid_public_key_returns_key_when_set(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("VAPID_PUBLIC_KEY", "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM")
    get_settings.cache_clear()

    r = await client.get(f"{PREFIX}/vapid-public-key")
    assert r.status_code == 200
    assert r.json()["public_key"].startswith("BNcRdre")

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_subscribe_inserts_new_row(client, mock_db):
    """No existing endpoint → INSERT, refresh, return."""
    not_found = MagicMock()
    not_found.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = not_found

    # `add` is sync on AsyncSession — the AsyncMock default returns a
    # coroutine which trips a RuntimeWarning. Swap in a plain MagicMock.
    mock_db.add = MagicMock()

    # Make the post-commit refresh assign an id + created_at.
    from datetime import datetime as _dt

    async def fake_refresh(obj):
        obj.id = 11
        obj.created_at = _dt.utcnow()

    mock_db.refresh = fake_refresh

    body = {
        "endpoint": "https://push.example/new",
        "keys": {"p256dh": "p", "auth": "a"},
    }
    r = await client.post(f"{PREFIX}/subscribe", json=body)
    assert r.status_code == 201
    out = r.json()
    assert out["endpoint"] == "https://push.example/new"
    assert out["id"] == 11
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_subscribe_refreshes_existing_row(client, mock_db):
    """Endpoint already known → update user_id + keys, no new row."""
    from datetime import datetime as _dt

    existing = SimpleNamespace(
        id=5,
        user_id=2,
        endpoint="https://push.example/known",
        p256dh_key="old_p",
        auth_key="old_a",
        user_agent=None,
        created_at=_dt.utcnow(),
    )
    found = MagicMock()
    found.scalar_one_or_none.return_value = existing
    mock_db.execute.return_value = found
    mock_db.refresh = AsyncMock()

    body = {
        "endpoint": "https://push.example/known",
        "keys": {"p256dh": "new_p", "auth": "new_a"},
    }
    r = await client.post(f"{PREFIX}/subscribe", json=body)
    assert r.status_code == 201
    # Existing row mutated, no add() called.
    assert existing.p256dh_key == "new_p"
    assert existing.auth_key == "new_a"
    assert existing.user_id == 1  # mocked current user
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_unsubscribe_issues_delete(client, mock_db):
    mock_db.execute = AsyncMock()
    r = await client.delete(
        f"{PREFIX}/subscribe", params={"endpoint": "https://push.example/abc"}
    )
    assert r.status_code == 204
    mock_db.execute.assert_awaited_once()
    mock_db.commit.assert_awaited()
