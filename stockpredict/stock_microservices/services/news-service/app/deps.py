"""Dependency wiring — a container set at startup, overridable in tests."""
from __future__ import annotations

from typing import Optional

from app.repositories.news_repository import NewsRepository
from app.repositories.tcb_repository import TcbRepository
from app.services.watchlist_push import WatchlistPusher


class _Container:
    repo: Optional[NewsRepository] = None
    tcb_repo: Optional[TcbRepository] = None
    watchlist_pusher: Optional[WatchlistPusher] = None
    call_scorer = None
    scoring_scheduler = None
    company_poller = None
    scheduler = None
    macro_poller = None
    macro_scheduler = None
    broker_mail_repo = None
    broker_mail_source = None
    broker_mail_scheduler = None
    bus = None


container = _Container()


def get_repo() -> NewsRepository:
    if container.repo is None:
        raise RuntimeError("NewsRepository not initialised")
    return container.repo


def get_tcb_repo() -> TcbRepository:
    if container.tcb_repo is None:
        raise RuntimeError("TcbRepository not initialised")
    return container.tcb_repo


def get_watchlist_pusher() -> WatchlistPusher:
    if container.watchlist_pusher is None:
        raise RuntimeError("WatchlistPusher not initialised")
    return container.watchlist_pusher


def get_call_scorer():
    if container.call_scorer is None:
        raise RuntimeError("CallScorer not initialised")
    return container.call_scorer


def get_broker_mail_repo():
    if container.broker_mail_repo is None:
        raise RuntimeError("BrokerMailRepository not initialised")
    return container.broker_mail_repo


def get_broker_mail_source():
    if container.broker_mail_source is None:
        raise RuntimeError("BrokerMailSource not initialised")
    return container.broker_mail_source
