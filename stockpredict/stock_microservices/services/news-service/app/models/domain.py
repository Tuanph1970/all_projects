"""SQLAlchemy model for the shared news corpus (SRS §4.1, FR-NEWS-STORE).

One table, `news_events`, holds both streams. Raw fields (title/body/url/lang/raw_json)
are written once and never mutated (EC-N3); only classification + pipeline stamps change.
Portable across MySQL (prod) and sqlite (tests).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text, text
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# Large text on MySQL, plain TEXT elsewhere (sqlite in tests).
_LongText = Text().with_variant(MEDIUMTEXT, "mysql")


class NewsEvent(Base):
    """One ingested news/event item (company or macro)."""

    __tablename__ = "news_events"

    news_id: Mapped[str] = mapped_column(String(64), primary_key=True)  # dedupe key (FR-NEWS-DEDUP)
    source: Mapped[str] = mapped_column(String(64), index=True)         # "vnstock" | "fed" | ...
    stream: Mapped[str] = mapped_column(String(16), index=True)         # "company" | "macro"
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    ts_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)  # published (EC-N6)

    # Raw, immutable after insert (EC-N3).
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(_LongText, nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    lang: Mapped[str | None] = mapped_column(String(8), nullable=True)
    raw_json: Mapped[str | None] = mapped_column(_LongText, nullable=True)

    # Classification (added by the pipeline; nullable until classified).
    category: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    sentiment: Mapped[str | None] = mapped_column(String(8), nullable=True)  # good|bad|neutral
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # [-1, 1]
    # Backlog #112(d). How sentiment_score was obtained: 'model' (the LLM
    # returned a graded score), 'label_fallback' (direction only; magnitude is a
    # placeholder), 'keyword_fallback' (a keyword count over the prose), or
    # 'template' (no LLM answered — nothing was judged). NULL on rows written
    # before the field existed, which is honest: we do not know how they were
    # scored, and defaulting them to 'model' would assert something false.
    score_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Backlog #115. True when `ts_utc` is the INGESTION moment rather than the
    # publication moment. The upstream company feed returns
    # `"publishDate": null`, so a symbol's FIRST poll writes its entire backlog
    # under a single timestamp: measured 2026-11-03, 350 of 360 stored items sat
    # in seven such 50-item clusters, and the three symbols added to the
    # watchlist that day each produced one.
    #
    # These rows are real news whose DATE is unknown. They stay readable in the
    # API, but news_features excludes them from the decayed series — counting
    # them would invent 50 news events on a day when nothing was published, and
    # that series is a model covariate.
    bulk_ingest: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("0"), default=False)

    # Pipeline stamps.
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bridged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
