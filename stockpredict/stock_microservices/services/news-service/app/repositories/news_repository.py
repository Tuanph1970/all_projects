"""NewsRepository — the only writer of the news_events corpus (FR-NEWS-STORE).

Insert-if-absent semantics: `upsert` is a no-op on an already-seen news_id (EC-N2), so
re-polls never duplicate rows, re-classify, or re-notify — and never overwrite the raw,
immutable corpus (EC-N3). Only `mark_*` mutate classification/pipeline-stamp columns.
Works with any SQLAlchemy engine (MySQL in prod, sqlite in tests).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.domain import Base, NewsEvent
from app.models.news_item import NewsItem

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Coerce to tz-aware UTC. Neither MySQL nor sqlite persist tzinfo, so we treat
    stored naive datetimes as UTC by contract (EC-N6)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


_STAMP_FIELDS = ("ts_utc", "ingested_at", "classified_at", "notified_at", "bridged_at")


def _normalize(obj: Optional[NewsEvent]) -> Optional[NewsEvent]:
    """Re-attach UTC tzinfo to a detached row's datetime columns on read (EC-N6)."""
    if obj is None:
        return None
    for f in _STAMP_FIELDS:
        setattr(obj, f, _to_utc(getattr(obj, f)))
    return obj


class NewsRepository:
    def __init__(self, engine: Engine):
        self._engine = engine
        self._Session = sessionmaker(bind=engine, expire_on_commit=False)

    def ensure_schema(self) -> None:
        """Auto-provision on deploy: create the database if missing, then the tables.

        MySQL create_all() creates tables but not the database, and the mysql/init seed
        only runs on a fresh volume — so a Docker deploy against an existing MySQL would
        otherwise fail with 'Unknown database'. We create it here (no-op for sqlite)."""
        self._ensure_database()
        Base.metadata.create_all(self._engine)

    def _ensure_database(self) -> None:
        url = self._engine.url
        if url.get_backend_name().startswith("sqlite"):
            return  # sqlite has no separate CREATE DATABASE step
        dbname = url.database
        if not dbname:
            return
        server_url = url.set(database="")  # connect to the server, no DB selected
        # (URL.set(database=None) is a no-op in SQLAlchemy; "" actually clears it)
        tmp = create_engine(server_url)
        try:
            with tmp.connect() as conn:
                conn.execute(text(
                    f"CREATE DATABASE IF NOT EXISTS `{dbname}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                ))
                conn.commit()
            logger.info("ensured database %s exists", dbname)
        finally:
            tmp.dispose()

    def exists(self, news_id: str) -> bool:
        with self._Session() as s:  # type: Session
            return s.get(NewsEvent, news_id) is not None

    def get(self, news_id: str) -> Optional[NewsEvent]:
        with self._Session() as s:
            return _normalize(s.get(NewsEvent, news_id))

    def upsert(self, item: NewsItem) -> bool:
        """Insert if new; no-op if already seen. Returns True iff newly inserted (EC-N2)."""
        news_id = item.news_id()
        with self._Session() as s:
            if s.get(NewsEvent, news_id) is not None:
                return False  # already seen — raw corpus is immutable (EC-N3)
            s.add(
                NewsEvent(
                    news_id=news_id,
                    source=item.source,
                    stream=item.stream,
                    symbol=item.symbol,
                    ts_utc=_to_utc(item.ts_utc),
                    title=item.title,
                    body=item.body,
                    url=item.url,
                    lang=item.lang,
                    raw_json=item.raw_json,
                    ingested_at=_utcnow(),
                )
            )
            s.commit()
            return True

    def mark_classified(
        self, news_id: str, *, sentiment: str | None, category: str | None, score: float | None
    ) -> None:
        with self._Session() as s:
            obj = s.get(NewsEvent, news_id)
            if obj is None:
                return
            obj.sentiment = sentiment
            obj.category = category
            obj.sentiment_score = score
            obj.classified_at = _utcnow()
            s.commit()

    def mark_notified(self, news_id: str) -> None:
        self._stamp(news_id, "notified_at")

    def mark_bridged(self, news_id: str) -> None:
        self._stamp(news_id, "bridged_at")

    def _stamp(self, news_id: str, field: str) -> None:
        with self._Session() as s:
            obj = s.get(NewsEvent, news_id)
            if obj is None:
                return
            setattr(obj, field, _utcnow())
            s.commit()

    def list_new(self, *, limit: Optional[int] = None) -> list[NewsEvent]:
        """Rows still needing classification (classified_at IS NULL)."""
        stmt = (
            select(NewsEvent)
            .where(NewsEvent.classified_at.is_(None))
            .order_by(NewsEvent.ingested_at)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        with self._Session() as s:
            return [_normalize(r) for r in s.scalars(stmt).all()]

    def query(
        self,
        *,
        stream: Optional[str] = None,
        symbol: Optional[str] = None,
        category: Optional[str] = None,
        sentiment: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NewsEvent]:
        stmt = select(NewsEvent)
        if stream is not None:
            stmt = stmt.where(NewsEvent.stream == stream)
        if symbol is not None:
            stmt = stmt.where(NewsEvent.symbol == symbol)
        if category is not None:
            stmt = stmt.where(NewsEvent.category == category)
        if sentiment is not None:
            stmt = stmt.where(NewsEvent.sentiment == sentiment)
        if since is not None:
            stmt = stmt.where(NewsEvent.ts_utc >= since)
        if until is not None:
            stmt = stmt.where(NewsEvent.ts_utc <= until)
        stmt = stmt.order_by(NewsEvent.ts_utc.desc()).limit(limit).offset(offset)
        with self._Session() as s:
            return [_normalize(r) for r in s.scalars(stmt).all()]
