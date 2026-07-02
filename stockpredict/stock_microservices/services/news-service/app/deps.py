"""Dependency wiring — a container set at startup, overridable in tests."""
from __future__ import annotations

from typing import Optional

from app.repositories.news_repository import NewsRepository


class _Container:
    repo: Optional[NewsRepository] = None
    company_poller = None
    scheduler = None
    macro_poller = None
    macro_scheduler = None
    bus = None


container = _Container()


def get_repo() -> NewsRepository:
    if container.repo is None:
        raise RuntimeError("NewsRepository not initialised")
    return container.repo
