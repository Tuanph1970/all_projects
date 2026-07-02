"""N7 — news.company consumer: fan-out to per-user notifications + optional email.

The fan-out/dedup logic is exercised against a REAL in-memory async sqlite DB (aiosqlite)
so the (user_id, news_id) dedup and the portfolios->holdings->users join are tested for
real, not mocked. Email delivery is patched.

Mandatory gates (SRS §5.3, EC-N2/N9/N10):
  - one notification per user owning/watching the symbol, type=news_company, source_event_id=news_id
  - redeliver same news_id -> no duplicate per user
  - email invoked per newly-notified user only when SMTP is configured
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from stock_common.events import Event

import app.services.news_event_handler as handler
from app.models.domain import (
    Base, Notification, NotificationType, Portfolio, PortfolioHolding,
)
from app.repositories.portfolio_repository import PortfolioRepository


@pytest_asyncio.fixture
async def sqlite_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    # Seed: user1 owns FPT, user2 watches FPT, user3 owns ACB.
    async with factory() as s:
        s.add_all([
            Portfolio(id=1, user_id=1, name="P1", is_default=True),
            Portfolio(id=2, user_id=2, name="P2", is_default=True),
            Portfolio(id=3, user_id=3, name="P3", is_default=True),
        ])
        await s.flush()
        s.add_all([
            PortfolioHolding(portfolio_id=1, symbol="FPT", quantity=10, is_watchlist_only=False),
            PortfolioHolding(portfolio_id=2, symbol="FPT", quantity=0, is_watchlist_only=True),
            PortfolioHolding(portfolio_id=3, symbol="ACB", quantity=5, is_watchlist_only=False),
        ])
        await s.commit()
    yield factory
    await engine.dispose()


def _event(news_id="n1", symbol="FPT", sentiment="good"):
    return Event(event_type="news.company", payload={
        "news_id": news_id, "symbol": symbol, "sentiment": sentiment,
        "category": "new_product", "title": "FPT launches AI product",
        "url": "https://x/fpt", "ts_utc": "2026-07-01T09:00:00+00:00",
        "sentiment_score": 0.8,
    })


async def _notifs(factory):
    async with factory() as s:
        return (await s.execute(select(Notification))).scalars().all()


@pytest.mark.asyncio
async def test_repo_resolves_users_owning_or_watching_symbol(sqlite_factory):
    async with sqlite_factory() as s:
        users = await PortfolioRepository(s).get_user_ids_for_symbol("fpt")
    assert sorted(users) == [1, 2]          # owner + watcher; not the ACB user


@pytest.mark.asyncio
async def test_fan_out_one_notification_per_watching_user(sqlite_factory, monkeypatch):
    monkeypatch.setattr(handler, "async_session_factory", sqlite_factory)
    monkeypatch.setattr(handler, "_email_enabled", lambda: False)

    await handler._handle_news_company(_event())

    rows = await _notifs(sqlite_factory)
    assert {r.user_id for r in rows} == {1, 2}          # EC-N10 fan-out
    assert all(r.type == NotificationType.NEWS_COMPANY for r in rows)
    assert all(r.source_event_id == "n1" for r in rows)
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_redelivery_does_not_duplicate_per_user(sqlite_factory, monkeypatch):
    monkeypatch.setattr(handler, "async_session_factory", sqlite_factory)
    monkeypatch.setattr(handler, "_email_enabled", lambda: False)

    await handler._handle_news_company(_event())
    await handler._handle_news_company(_event())          # same news_id again (EC-N2)

    rows = await _notifs(sqlite_factory)
    assert len(rows) == 2                                  # still 2, no dupes


@pytest.mark.asyncio
async def test_no_users_no_notifications(sqlite_factory, monkeypatch):
    monkeypatch.setattr(handler, "async_session_factory", sqlite_factory)
    monkeypatch.setattr(handler, "_email_enabled", lambda: False)

    await handler._handle_news_company(_event(symbol="VNM"))  # nobody holds VNM
    assert await _notifs(sqlite_factory) == []


@pytest.mark.asyncio
async def test_email_sent_per_new_user_only_when_enabled(sqlite_factory, monkeypatch):
    monkeypatch.setattr(handler, "async_session_factory", sqlite_factory)
    monkeypatch.setattr(handler, "_email_enabled", lambda: True)
    monkeypatch.setattr(handler, "_lookup_user_email", AsyncMock(return_value="u@x.io"))
    send = AsyncMock()
    monkeypatch.setattr(handler, "send_email", send)

    await handler._handle_news_company(_event())
    assert send.await_count == 2                           # one per newly-notified user

    send.reset_mock()
    await handler._handle_news_company(_event())           # redelivery -> no new users
    assert send.await_count == 0                           # so no re-email


@pytest.mark.asyncio
async def test_email_not_sent_when_disabled(sqlite_factory, monkeypatch):
    monkeypatch.setattr(handler, "async_session_factory", sqlite_factory)
    monkeypatch.setattr(handler, "_email_enabled", lambda: False)
    send = AsyncMock()
    monkeypatch.setattr(handler, "send_email", send)

    await handler._handle_news_company(_event())
    assert send.await_count == 0


@pytest.mark.asyncio
async def test_skips_event_without_symbol_or_news_id(sqlite_factory, monkeypatch):
    monkeypatch.setattr(handler, "async_session_factory", sqlite_factory)
    bad = Event(event_type="news.company", payload={"symbol": "FPT"})  # no news_id
    await handler._handle_news_company(bad)
    assert await _notifs(sqlite_factory) == []
