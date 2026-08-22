"""
Behavioural telemetry models for Mercai.

These tables capture signal that is otherwise irrecoverable: a search that was
not logged when it happened cannot be reconstructed later from any other table.

Reliability class: TELEMETRY. Writes are best-effort and must never fail the
request that triggered them -- see
services/product/app/services/search_logging.py for the write path.
"""
from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, JSON, String
from sqlalchemy.sql import func

from shared.database import Base


class SearchLog(Base):
    """
    One row per product search executed by a buyer.

    Written by the product service on both the basic (`GET /products/?search=`)
    and advanced (`GET /products/search/advanced`) endpoints.

    `user_id` deliberately carries no foreign key to `users`. Telemetry should
    outlive the account that generated it, and a FK would put these
    high-volume inserts in contention with the users table.
    """
    __tablename__ = "search_logs"

    # BIGINT on MySQL; SQLite only auto-increments INTEGER PRIMARY KEY, so the
    # variant keeps the model usable in SQLite-backed tests.
    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    # What was searched
    query_text = Column(String(500), nullable=True)   # raw, as the buyer typed it
    query_norm = Column(String(500), nullable=True)   # lowercased + whitespace-collapsed, for GROUP BY
    # none_as_null: store a real SQL NULL rather than JSON 'null', so that
    # `WHERE filters IS NULL` finds unfiltered searches.
    filters = Column(JSON(none_as_null=True), nullable=True)

    # What came back. 0 is the assortment-gap signal: a buyer looked for
    # something this marketplace does not sell.
    result_count = Column(Integer, nullable=False)

    source = Column(String(20), nullable=False)       # 'basic' | 'advanced'

    # Who searched. Both may be NULL: anonymous buyers who predate the client
    # sending an X-Anon-Id header.
    user_id = Column(Integer, nullable=True)
    anon_id = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # Aggregate queries group on the normalised form.
        Index("ix_search_logs_norm", "query_norm"),
        # "what did buyers search for and find nothing?" over a time window.
        Index("ix_search_logs_zero", "result_count", "created_at"),
        # Time-range scans and the retention purge.
        Index("ix_search_logs_created", "created_at"),
        Index("ix_search_logs_user", "user_id"),
    )

    def __repr__(self):
        return (
            f"<SearchLog(id={self.id}, query_norm={self.query_norm!r}, "
            f"result_count={self.result_count}, source={self.source!r})>"
        )
