"""SQLAlchemy model for the owned event store (gap map §4)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EventRecord(Base):
    """One discrete, timestamped event (the events contract, persisted)."""

    __tablename__ = "event_reaction_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ts_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    actual: Mapped[float] = mapped_column(Float)
    consensus: Mapped[float | None] = mapped_column(Float, nullable=True)
    asset_scope: Mapped[str | None] = mapped_column(String(128), nullable=True)
