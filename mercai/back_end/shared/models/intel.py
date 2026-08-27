"""
Price-intelligence models.

Two tables. `tracked_comparables` is what a seller asked us to watch;
`comparable_observations` is the append-only record of what we saw each time we
looked.

See docs/ai-features/05-price-intelligence.md section 7.
"""
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer,
    Numeric, SmallInteger, String, UniqueConstraint,
)
from sqlalchemy.sql import func

from shared.database import Base


class TrackedComparable(Base):
    """
    One competitor listing a seller wants compared against one of their own.

    `product_id` is the entire matching story in phase 1: the seller states
    which of their products this URL is a comparable for, so no fuzzy scoring
    is needed and none is done. That stage was the largest source of silent
    wrongness in the architecture this was ported from.
    """
    __tablename__ = "tracked_comparables"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    url = Column(String(1000), nullable=False)
    # sha256 of the NORMALISED url (host lowercased, fragment and tracking
    # params stripped), so the same listing pasted from two campaign links is
    # one row rather than two comparables that always agree.
    url_hash = Column(String(64), nullable=False)
    source_host = Column(String(255), nullable=False, index=True)
    label = Column(String(255), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    last_fetched_at = Column(DateTime(timezone=True), nullable=True)
    last_status = Column(String(30), nullable=True)
    # Five in a row deactivates the row and tells the seller, so a dead URL
    # stops consuming the host's politeness budget forever.
    consecutive_failures = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("product_id", "url_hash", name="uq_tc_product_url"),
        Index("ix_tc_product_active", "product_id", "is_active"),
    )

    def __repr__(self):
        return f"<TrackedComparable(id={self.id}, host={self.source_host!r})>"


class ComparableObservation(Base):
    """
    What we saw on one visit. Append-only, and it records FAILURES as rows.

    A failed fetch is a fact about the market -- "this competitor has been
    unreadable for two weeks" is information, and a table that only stores
    successes cannot express it. Grouping this table by (source_host, status)
    is also the evidence-based worklist of which adapter to write next.

    Reliability class: TELEMETRY (see 01-instrumentation.md). A failed insert
    must never fail the seller's request; unlike price_history this describes
    the outside world and is already approximate.
    """
    __tablename__ = "comparable_observations"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True, autoincrement=True,
    )
    comparable_id = Column(
        Integer, ForeignKey("tracked_comparables.id"), nullable=False, index=True
    )
    observed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    status = Column(String(30), nullable=False)
    price = Column(Numeric(12, 2), nullable=True)
    price_min = Column(Numeric(12, 2), nullable=True)
    price_max = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=True)
    is_range = Column(Boolean, nullable=False, default=False)
    availability = Column(String(20), nullable=True)
    title_seen = Column(String(500), nullable=True)

    extractor_tier = Column(String(20), nullable=True)
    confidence = Column(SmallInteger, nullable=True)
    # The literal substring that produced the number, plus the path or selector.
    # Against the model this was anti-hallucination; against a parser it is
    # diagnosis -- it says immediately whether we grabbed a shipping fee, a
    # strike-through, or the wrong variant.
    evidence = Column(String(500), nullable=True)

    http_status = Column(SmallInteger, nullable=True)
    # Lets a re-fetch returning byte-identical HTML skip re-parsing, and
    # distinguishes "the price did not change" from "we did not check".
    content_hash = Column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_co_comparable_time", "comparable_id", "observed_at"),
        Index("ix_co_status", "status", "observed_at"),
    )

    def __repr__(self):
        return (
            f"<ComparableObservation(id={self.id}, status={self.status!r}, "
            f"price={self.price})>"
        )


class CategoryBenchmark(Base):
    """
    A market-wide price benchmark for one external category.

    Deliberately NOT a set of comparables. It is an aggregate over a whole
    category on another marketplace, computed without matching anything to
    anything: no per-listing pairing means no per-listing pairing errors, and
    one bad row cannot move a median over a hundred items. That robustness is
    the entire reason this exists alongside the pasted-URL path.

    It is also never blended into the position statistics -- see
    services/benchmarks.py for why that would quietly mislead a seller.
    """
    __tablename__ = "category_benchmarks"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(30), nullable=False)              # 'tiki'
    external_category_id = Column(String(40), nullable=False)
    external_category_label = Column(String(255), nullable=True)
    # Which Mercai category this benchmarks, by NAME rather than id: category
    # ids differ between environments, names do not.
    mercai_category_name = Column(String(100), nullable=False, index=True)

    sample_size = Column(Integer, nullable=False, default=0)
    pages_sampled = Column(Integer, nullable=False, default=0)
    catalogue_total = Column(Integer, nullable=True)          # what the source claims

    p25 = Column(Numeric(12, 2), nullable=True)
    median = Column(Numeric(12, 2), nullable=True)
    p75 = Column(Numeric(12, 2), nullable=True)
    price_min = Column(Numeric(12, 2), nullable=True)
    price_max = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=False, default="VND")

    status = Column(String(30), nullable=False, default="ok")
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("source", "external_category_id", name="uq_cb_source_category"),
        Index("ix_cb_mercai_category", "mercai_category_name", "computed_at"),
    )

    def __repr__(self):
        return (
            f"<CategoryBenchmark({self.source}:{self.external_category_id} "
            f"n={self.sample_size} median={self.median})>"
        )
