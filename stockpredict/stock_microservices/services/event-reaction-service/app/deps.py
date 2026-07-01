"""Dependency wiring — a container set at startup, overridable in tests."""
from __future__ import annotations

from typing import Optional

from app.services.event_reaction_service import EventReactionService


class _Container:
    service: Optional[EventReactionService] = None


container = _Container()


def get_service() -> EventReactionService:
    if container.service is None:
        raise RuntimeError("EventReactionService not initialised")
    return container.service
