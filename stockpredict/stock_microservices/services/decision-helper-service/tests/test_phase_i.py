"""Tests for Phase I — Real-time alerts (F-080..F-083)."""
from __future__ import annotations

import asyncio
import pytest

from app.services.alert_broker import AlertBroker
from app.models.schemas import AlertEvent, AlertsListResponse


# ---------------------------------------------------------------------------
# F-080 — AlertBroker
# ---------------------------------------------------------------------------

class TestAlertBroker:
    def setup_method(self):
        self.broker = AlertBroker()

    def test_subscribe_returns_queue(self):
        q = self.broker.subscribe(user_id=1)
        assert q is not None
        assert self.broker.subscriber_count == 1

    def test_unsubscribe_removes_queue(self):
        q = self.broker.subscribe(1)
        self.broker.unsubscribe(1, q)
        assert self.broker.subscriber_count == 0

    def test_multiple_subscribers_same_user(self):
        q1 = self.broker.subscribe(1)
        q2 = self.broker.subscribe(1)
        assert self.broker.subscriber_count == 2
        self.broker.unsubscribe(1, q1)
        assert self.broker.subscriber_count == 1

    def test_different_users_isolated(self):
        q1 = self.broker.subscribe(1)
        q2 = self.broker.subscribe(2)
        assert self.broker.subscriber_count == 2

    @pytest.mark.asyncio
    async def test_publish_reaches_subscriber(self):
        q = self.broker.subscribe(user_id=42)
        payload = {"ticker": "VIC", "action": "BUY", "bar_date": "2025-05-19"}
        await self.broker.publish(42, payload)
        result = await asyncio.wait_for(q.get(), timeout=1.0)
        assert result["ticker"] == "VIC"
        assert result["action"] == "BUY"

    @pytest.mark.asyncio
    async def test_publish_to_wrong_user_not_received(self):
        q = self.broker.subscribe(user_id=1)
        await self.broker.publish(user_id=2, payload={"ticker": "HPG"})
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(q.get(), timeout=0.05)

    @pytest.mark.asyncio
    async def test_publish_to_no_subscribers_is_noop(self):
        # Should not raise even with no subscribers
        await self.broker.publish(99, {"ticker": "VCB", "action": "BUY"})

    @pytest.mark.asyncio
    async def test_publish_broadcasts_to_all_subscribers(self):
        q1 = self.broker.subscribe(5)
        q2 = self.broker.subscribe(5)
        await self.broker.publish(5, {"ticker": "FPT"})
        r1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        r2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert r1["ticker"] == "FPT"
        assert r2["ticker"] == "FPT"

    @pytest.mark.asyncio
    async def test_full_queue_drops_gracefully(self):
        q = self.broker.subscribe(7)
        # Fill the queue (maxsize=100)
        for i in range(100):
            await self.broker.publish(7, {"n": i})
        # One more should not raise
        await self.broker.publish(7, {"n": 999})
        assert not q.empty()


# ---------------------------------------------------------------------------
# F-083 — Alert schemas
# ---------------------------------------------------------------------------

class TestAlertSchemas:
    def test_alert_event_fields(self):
        a = AlertEvent(
            ticker="VIC",
            action="BUY",
            bar_date="2025-05-19",
            regime="TREND_UP",
            confidence=0.82,
            stop_price=45.5,
            target_price=52.0,
        )
        assert a.ticker == "VIC"
        assert a.action == "BUY"

    def test_alert_event_optional_fields(self):
        a = AlertEvent(
            ticker="VCB",
            action="SELL_SHORT",
            bar_date="2025-05-19",
        )
        assert a.regime is None
        assert a.confidence is None
        assert a.stop_price is None

    def test_alerts_list_response(self):
        alerts = [
            AlertEvent(ticker="A", action="BUY", bar_date="2025-05-19"),
            AlertEvent(ticker="B", action="SELL_SHORT", bar_date="2025-05-19"),
        ]
        resp = AlertsListResponse(alerts=alerts, total=2)
        assert resp.total == 2
        assert len(resp.alerts) == 2

    def test_alerts_list_empty(self):
        resp = AlertsListResponse(alerts=[], total=0)
        assert resp.alerts == []
