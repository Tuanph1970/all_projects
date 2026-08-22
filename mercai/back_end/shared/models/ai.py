"""
AI feature models.

`ai_suggestions` is shared by every AI feature (listing optimizer, chat
copilot, review intelligence). It exists to answer the only rollout question
that matters: are sellers actually accepting these suggestions?

See docs/ai-features/02-listing-optimizer.md section 2.
"""
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Index, Integer, JSON, String
)
from sqlalchemy.sql import func

from shared.database import Base


# Feature identifiers
FEATURE_LISTING_OPTIMIZER = "listing_optimizer"
FEATURE_CHAT_COPILOT = "chat_copilot"
FEATURE_REVIEW_INTELLIGENCE = "review_intelligence"

# Suggestion lifecycle
STATUS_PROPOSED = "proposed"
STATUS_ACCEPTED = "accepted"
STATUS_PARTIALLY_ACCEPTED = "partially_accepted"
STATUS_REJECTED = "rejected"
STATUS_EXPIRED = "expired"

RESOLVED_STATUSES = (
    STATUS_ACCEPTED,
    STATUS_PARTIALLY_ACCEPTED,
    STATUS_REJECTED,
    STATUS_EXPIRED,
)


class AiSuggestion(Base):
    """
    One row per suggestion shown to a seller, plus what they did with it.

    Reliability class is split deliberately:
      - the initial 'proposed' insert is TELEMETRY (a failed write must never
        stop a suggestion being shown to the seller);
      - the transition to 'accepted' is LEDGER, because acceptance is the
        metric the rollout is judged on.
    See docs/ai-features/01-instrumentation.md for the distinction.

    `seller_id` carries no foreign key, matching the search_logs precedent:
    these rows are analytics that should outlive the account.
    """
    __tablename__ = "ai_suggestions"

    # SQLite only auto-increments INTEGER PRIMARY KEY, so the variant keeps
    # the model usable in the SQLite-backed test suite.
    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    seller_id = Column(Integer, nullable=False)
    feature = Column(String(40), nullable=False)
    entity_type = Column(String(40), nullable=False)   # 'product'|'chat_room'|'review'|'seller'
    entity_id = Column(Integer, nullable=True)

    # sha256 of the normalised input: doubles as cache key and dedupe key.
    input_hash = Column(String(64), nullable=False)
    # none_as_null so `WHERE accepted_fields IS NULL` stays meaningful.
    suggestion = Column(JSON(none_as_null=True), nullable=False)
    status = Column(String(20), nullable=False, default=STATUS_PROPOSED)
    accepted_fields = Column(JSON(none_as_null=True), nullable=True)

    model = Column(String(80), nullable=False)
    prompt_version = Column(String(20), nullable=False)
    latency_ms = Column(Integer, nullable=True)
    error = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_ai_sugg_seller_feature", "seller_id", "feature", "created_at"),
        Index("ix_ai_sugg_entity", "entity_type", "entity_id"),
        Index("ix_ai_sugg_hash", "input_hash"),
        Index("ix_ai_sugg_status", "feature", "status", "created_at"),
    )

    def __repr__(self):
        return (
            f"<AiSuggestion(id={self.id}, feature={self.feature!r}, "
            f"entity={self.entity_type}:{self.entity_id}, status={self.status!r})>"
        )
