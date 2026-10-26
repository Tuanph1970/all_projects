"""BrokerMailRepository — the only writer of `broker_mail_raw` (FR-BM-INTAKE/DEDUP).

Insert-if-absent on `mail_id`, mirroring NewsRepository (EC-N2) and TcbRepository: a
message seen twice is the row that already exists, never a second row and never an
update. EC-B2 makes that stronger than a convenience — raw MIME is immutable, so there
is no legitimate reason to ever write over a captured message.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models.broker_mail import BrokerMailRaw
from app.models.domain import Base

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BrokerMailRepository:
    def __init__(self, engine: Engine):
        self._engine = engine
        self._Session = sessionmaker(bind=engine, expire_on_commit=False)

    def ensure_schema(self) -> None:
        """Create `broker_mail_raw` if absent.

        Shares `Base` with news_events and the tcb_news* tables, so NewsRepository's
        `_ensure_database()` has already created the database itself. No column
        migration helper here on purpose: E1 writes the full table from the start, and
        `extracted_at` is already present so E2 adds no column either.
        """
        Base.metadata.create_all(self._engine)

    # -- writes --------------------------------------------------------------

    def insert_if_absent(
        self,
        *,
        mail_id: str,
        message_id: str,
        sender: str,
        subject: Optional[str],
        received_utc: datetime,
        raw_mime: str,
        source: str = "tcbs.daily",
    ) -> bool:
        """Store one captured message. Returns True if it was new, False if already held.

        The caller counts the return value rather than re-querying, which is what makes
        "zero duplicates" (the E1 gate) an observable number instead of a hope.
        """
        with self._Session() as s:
            if s.get(BrokerMailRaw, mail_id) is not None:
                return False
            s.add(BrokerMailRaw(
                mail_id=mail_id,
                message_id=message_id[:512],
                sender=sender[:320],
                subject=(subject or None) and subject[:998],
                received_utc=received_utc,
                fetched_at=_utcnow(),
                source=source,
                raw_mime=raw_mime,
            ))
            try:
                s.commit()
            except IntegrityError:
                # A backfill running beside a scheduled tick can reach the same message
                # concurrently. The primary key is the arbiter; losing the race is a
                # no-op, which is exactly the FR-BM-DEDUP contract.
                s.rollback()
                return False
            return True

    def mark_extracted(self, mail_id: str, *, when: Optional[datetime] = None) -> bool:
        """E2's hook: record that this message has been through extraction.

        The only column on this table that may ever change — `raw_mime` and the headers
        are immutable (EC-B2). Present now so intake needs no migration when E2 lands.
        """
        with self._Session() as s:
            row = s.get(BrokerMailRaw, mail_id)
            if row is None:
                return False
            row.extracted_at = when or _utcnow()
            s.commit()
            return True

    # -- reads ---------------------------------------------------------------

    def get(self, mail_id: str) -> Optional[BrokerMailRaw]:
        with self._Session() as s:
            return s.get(BrokerMailRaw, mail_id)

    def list_recent(self, *, limit: int = 50) -> list[BrokerMailRaw]:
        """Newest first — what an operator wants to see after a poll."""
        with self._Session() as s:
            return list(s.execute(
                select(BrokerMailRaw)
                .order_by(BrokerMailRaw.received_utc.desc())
                .limit(limit)
            ).scalars().all())

    def list_unextracted(self, *, limit: int = 500) -> list[BrokerMailRaw]:
        """Oldest first — the E2 work queue, in the order the sessions happened."""
        with self._Session() as s:
            return list(s.execute(
                select(BrokerMailRaw)
                .where(BrokerMailRaw.extracted_at.is_(None))
                .order_by(BrokerMailRaw.received_utc.asc())
                .limit(limit)
            ).scalars().all())

    def stats(self) -> dict:
        """The E1 gate as a number: how much is captured, over what span, how much is
        still unparsed. `distinct_message_ids == stored` is the zero-duplicates check —
        it would only diverge if two different Message-IDs ever hashed to one mail_id."""
        with self._Session() as s:
            stored = s.execute(select(func.count(BrokerMailRaw.mail_id))).scalar() or 0
            distinct = s.execute(
                select(func.count(func.distinct(BrokerMailRaw.message_id)))).scalar() or 0
            earliest = s.execute(select(func.min(BrokerMailRaw.received_utc))).scalar()
            latest = s.execute(select(func.max(BrokerMailRaw.received_utc))).scalar()
            unextracted = s.execute(
                select(func.count(BrokerMailRaw.mail_id))
                .where(BrokerMailRaw.extracted_at.is_(None))).scalar() or 0
            return {
                "stored": stored,
                "distinct_message_ids": distinct,
                "earliest_received": earliest,
                "latest_received": latest,
                "unextracted": unextracted,
            }
