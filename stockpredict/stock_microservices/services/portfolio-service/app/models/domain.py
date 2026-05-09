"""Domain Models for Portfolio Service"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, BigInteger
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
