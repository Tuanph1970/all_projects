"""SQLAlchemy model for captured broker mail (FR-BM-INTAKE, EC-B1, EC-B2).

One table, one row per email, in the existing `stock_news` database. This is phase E1 of
SRS_broker_mail: **capture only, no parsing**. The whole point of shipping it alone is
stated in Appendix E — *an email never captured is unrecoverable*, and the parser is far
easier to write against sixty stored samples than against two pasted ones.

`raw_mime` is the complete RFC 822 message exactly as the server handed it over, stored
on receipt and never mutated (EC-B2). Extraction (E2) is a separate, re-runnable pass
that reads this table and writes new rows, so a parser fix replays over the whole archive
without re-fetching mail — which also means it cannot be replayed over mail we declined
to store, hence capture is deliberately permissive.

Portable across MySQL (prod) and sqlite (tests), matching `domain.py` in this package.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.domain import Base, _LongText


class BrokerMailRaw(Base):
    """One captured broker email, immutable once written."""

    __tablename__ = "broker_mail_raw"
    __table_args__ = (
        Index("ix_broker_mail_raw_received", "received_utc"),
        Index("ix_broker_mail_raw_sender", "sender"),
        # E2 scans for un-extracted mail; a partial index is not portable, so the plain
        # column index serves both "what is pending" and "what did we extract when".
        Index("ix_broker_mail_raw_extracted", "extracted_at"),
    )

    # sha256(Message-ID), hex. The primary key IS the dedupe key (FR-BM-DEDUP): insert
    # if absent, and re-seeing a message is a no-op rather than an update.
    mail_id: Mapped[str] = mapped_column(String(64), primary_key=True)

    # The header verbatim, kept beside its hash so a human can trace a row back to the
    # message in the mailbox. 512 is RFC 5322's practical ceiling, not a guess.
    message_id: Mapped[str] = mapped_column(String(512), nullable=False)

    # Envelope From. For forwarded mail this is the FORWARDER, not the broker — which is
    # why Appendix B's allow-list carries the forwarding address as well as the domain.
    sender: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(998), nullable=True)

    # The mail's own Date header, normalised to UTC. Falls back to the capture time when
    # that header is absent or unparseable: a NULL here would break both ordering and
    # "backfill since <date>", and a message with a broken Date must still be captured.
    received_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # When WE stored it. Distinct from received_utc on every backfilled row, and the only
    # honest answer to "when did this archive learn about this mail?".
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Which Appendix B registry key matched. Carried so that adding a second broker is
    # "a new row here plus a golden set of its own — no new code path", and so E2 can
    # select the right extractor without re-deriving it from the sender.
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="tcbs.daily")

    # The message, byte-for-byte as received. Never mutated (EC-B2).
    raw_mime: Mapped[str] = mapped_column(_LongText, nullable=False)

    # Set by E2's extraction pass; NULL means "captured, not yet parsed". E1 only ever
    # writes NULL here — the column exists now so intake never needs a migration later.
    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (f"<BrokerMailRaw {self.mail_id[:12]}… {self.sender} "
                f"{self.received_utc:%Y-%m-%d} {(self.subject or '')[:40]!r}>")
