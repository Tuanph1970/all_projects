"""Domain Models for Portfolio Service"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text, Enum as SQLEnum, BigInteger
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class TransactionType(enum.Enum):
    BUY = "buy"
    SELL = "sell"


class AlertType(enum.Enum):
    ABOVE = "above"
    BELOW = "below"
    CHANGE_PERCENT = "change_percent"
    #: Backlog #117. Fires when a symbol's volume is a multiple of its own
    #: trailing MEDIAN volume — `target_percent` carries the multiple (3.0 =
    #: three times normal), reusing the existing column rather than adding one.
    #: Per-symbol by construction: E&M are explicit that "high" volume means
    #: high FOR THAT STOCK, so there is no absolute share-count threshold.
    VOLUME_UNUSUAL = "volume_unusual"


class FeedbackCategory(enum.Enum):
    """What kind of thing the user is telling us.

    The point of asking is TRIAGE: "the chart is wrong" and "please add X" need
    different responses, and a single free-text inbox makes that distinction
    the reader's problem. Kept deliberately short — a long list makes people
    pick "other".
    """
    IDEA = "idea"            # a feature or improvement they want
    PROBLEM = "problem"      # something is broken or wrong
    CONFUSING = "confusing"  # it works, but they could not tell how
    PRAISE = "praise"        # what to keep; the easiest signal to lose
    OTHER = "other"


class FeedbackStatus(enum.Enum):
    """The owner's triage state. Not shown to the submitter."""
    NEW = "new"
    TRIAGED = "triaged"
    DONE = "done"
    DECLINED = "declined"


class Portfolio(Base):
    """User portfolio model"""
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), default="Default Portfolio")
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioHolding(Base):
    """Stock holdings in a portfolio"""
    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Integer, default=0)
    average_price = Column(Float, nullable=True)
    total_cost = Column(Float, default=0)
    current_price = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    profit_loss = Column(Float, nullable=True)
    profit_loss_percent = Column(Float, nullable=True)
    is_watchlist_only = Column(Boolean, default=False)

    # Who proposed watching this symbol, and what they said.
    # Written by the TCB News screen when a "3. Khuyến nghị cổ phiếu" recommendation is
    # confirmed; a manual add takes the server default. `proposal_label` keeps the
    # desk's exact wording ("Chờ mua") beside the normalised action, so the
    # normalisation is never lossy.
    proposal_by = Column(String(32), nullable=True, server_default="TCB")
    proposal_action = Column(String(8), nullable=True)      # BUY | SELL | HOLD | WATCH
    proposal_label = Column(String(128), nullable=True)     # verbatim source phrase
    proposal_date = Column(Date, nullable=True)             # the session it was made on
    proposal_note = Column(Text, nullable=True)             # rationale excerpt

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="holdings")


class Transaction(Base):
    """Buy/Sell transactions"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    fees = Column(Float, default=0)
    notes = Column(Text, nullable=True)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="transactions")


class PriceAlert(Base):
    """Price alerts for stocks"""
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    target_price = Column(Float, nullable=True)
    target_percent = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    is_triggered = Column(Boolean, default=False)
    triggered_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationType(enum.Enum):
    ALERT_TRIGGERED = "alert.triggered"
    NEWS_COMPANY = "news.company"            # good/bad company news for owned/watched tickers
    JOURNAL_REMINDER = "journal.reminder"   # reserved for future
    TRAINING_DONE = "training.done"          # reserved for future
    SYSTEM = "system"


class Notification(Base):
    """User-facing notifications. Persisted from event-bus events
    (currently portfolio.alert.triggered) so the UI can render an
    inbox / bell-icon dropdown. New notifications are unread; the
    UI updates `read_at` when the user dismisses one.
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    # Free-form per-type metadata (symbol, alert_id, trigger_price, etc.)
    # — kept JSON-serialized in TEXT to avoid a new column per notif type.
    metadata_json = Column(Text, nullable=True)
    # The event_id of the source event that produced this notification.
    # Lets us dedupe if the same event is replayed (DLQ retry / restart).
    source_event_id = Column(String(64), nullable=True, index=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PushSubscription(Base):
    """Browser push-notification subscription registered from the frontend
    after the user grants notification permission.

    Each browser session produces one (endpoint, keys) tuple. Endpoint is
    unique per browser/profile and acts as the dedupe key — re-subscribing
    from the same browser refreshes the keys + updated_at rather than
    inserting a duplicate row.
    """
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    endpoint = Column(String(500), nullable=False, unique=True, index=True)
    # p256dh + auth are returned by PushSubscription.toJSON() in the browser.
    # Both are required by pywebpush to encrypt the payload.
    p256dh_key = Column(String(255), nullable=False)
    auth_key = Column(String(255), nullable=False)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserFeedback(Base):
    """One piece of feedback from a user (v0.9).

    WHY `page` AND `app_version` ARE COLUMNS AND NOT OPTIONAL EXTRAS. Feedback
    without context is nearly unusable: "the numbers look wrong" is a different
    report depending on whether it came from the Chart analyst, the Backtest
    Studio or the Risk Dashboard, and the submitter almost never says. The
    frontend fills `page` from the current route automatically, so the useful
    half costs the user nothing. `app_version` ties a report to a release, which
    is what makes "did 0.9 fix it?" answerable later.

    `user_agent` is kept for the same reason the push-subscription table keeps
    it: a rendering complaint is often a device complaint.

    NOT ANONYMOUS, deliberately. The endpoint requires a token, so every row
    carries user_id — that is what allows a follow-up question, and this is an
    invited-user application rather than a public site. `contact_ok` records
    whether the user actually wants that follow-up, so the permission is
    explicit rather than assumed from the fact that we know who they are.
    """
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    category = Column(SQLEnum(FeedbackCategory), nullable=False, index=True)
    message = Column(Text, nullable=False)
    #: Optional 1-5 overall rating. Separate from `category` on purpose: someone
    #: can love the app and still report a bug, and forcing one number to carry
    #: both would lose whichever they cared about less.
    rating = Column(Integer, nullable=True)
    #: The route the user was on when they opened the form, filled by the UI.
    page = Column(String(120), nullable=True, index=True)
    app_version = Column(String(32), nullable=True, index=True)
    user_agent = Column(String(255), nullable=True)
    contact_ok = Column(Boolean, nullable=False, default=False)
    status = Column(SQLEnum(FeedbackStatus), nullable=False,
                    default=FeedbackStatus.NEW, index=True)
    #: The owner's private note while triaging. Never returned to the submitter.
    owner_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
