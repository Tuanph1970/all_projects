"""SQLAlchemy ORM models — ADR-001 §3."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DECIMAL, JSON, Boolean, Column, Date, DateTime, Enum, Integer,
    String, UniqueConstraint, BigInteger, func,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class UserRiskPrefs(Base):
    """One row per user; created lazily on first preference write."""
    __tablename__ = "user_risk_prefs"

    user_id = Column(BigInteger, primary_key=True, comment="from JWT; no FK")
    account_equity = Column(DECIMAL(18, 2), nullable=False, default=0)
    risk_per_trade_pct = Column(DECIMAL(5, 3), nullable=False, default=1.0)
    max_concurrent_positions = Column(Integer, nullable=False, default=5)
    max_correlation = Column(DECIMAL(4, 3), nullable=False, default=0.7)
    loss_streak_size_cut = Column(DECIMAL(4, 3), nullable=False, default=0.5)
    loss_streak_threshold = Column(Integer, nullable=False, default=3)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class PositionState(Base):
    """One row per (user_id, ticker) — v1 single-leg limit."""
    __tablename__ = "position_states"
    __table_args__ = (UniqueConstraint("user_id", "ticker", name="uq_position_user_ticker"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    ticker = Column(String(16), nullable=False)
    state = Column(
        Enum("FLAT", "LONG", "SHORT", name="position_state_enum"),
        nullable=False,
        default="FLAT",
    )
    entry_bar_date = Column(Date, nullable=True)
    entry_price = Column(DECIMAL(18, 4), nullable=True)
    position_size = Column(Integer, nullable=False, default=0)
    current_stop = Column(DECIMAL(18, 4), nullable=True)
    current_target = Column(DECIMAL(18, 4), nullable=True)
    entry_signal_kind = Column(String(64), nullable=True)
    last_decision_run_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class SignalHistory(Base):
    """Append-only signal log for backtest replay."""
    __tablename__ = "signal_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(16), nullable=False, index=True)
    bar_date = Column(Date, nullable=False, index=True)
    signal_kind = Column(String(64), nullable=False)
    direction = Column(Enum("LONG", "SHORT", name="signal_direction_enum"), nullable=False)
    raw_confidence = Column(DECIMAL(4, 3), nullable=False)
    confirmed = Column(Boolean, nullable=False, default=False)
    confirmation_reason = Column(String(255), nullable=True)
    regime = Column(
        Enum("TREND_UP", "TREND_DOWN", "RANGE", "UNDEFINED", name="regime_enum"),
        nullable=False,
    )
    features_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class DecisionRun(Base):
    """One row per (user, ticker, bar, trigger) — persisted recommendation."""
    __tablename__ = "decision_runs"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "ticker", "bar_date", "trigger",
            name="uq_decision_run_key",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    ticker = Column(String(16), nullable=False, index=True)
    bar_date = Column(Date, nullable=False, index=True)
    trigger = Column(
        Enum("SCHEDULED", "ON_DEMAND", "BACKTEST", name="trigger_enum"),
        nullable=False,
    )
    regime = Column(
        Enum("TREND_UP", "TREND_DOWN", "RANGE", "UNDEFINED", name="regime_run_enum"),
        nullable=True,
    )
    signal_kind = Column(String(64), nullable=True)
    signal_confirmed = Column(Boolean, nullable=False, default=False)
    failed_signal_kind = Column(String(64), nullable=True)
    action = Column(
        Enum(
            "BUY", "SELL", "SELL_SHORT", "COVER", "HOLD", "WAIT", "REVERSE",
            name="action_enum",
        ),
        nullable=False,
    )
    state_before = Column(
        Enum("FLAT", "LONG", "SHORT", name="state_before_enum"), nullable=False
    )
    state_after = Column(
        Enum("FLAT", "LONG", "SHORT", name="state_after_enum"), nullable=False
    )
    entry_price = Column(DECIMAL(18, 4), nullable=True)
    stop_price = Column(DECIMAL(18, 4), nullable=True)
    target_price = Column(DECIMAL(18, 4), nullable=True)
    position_size = Column(Integer, nullable=True)
    reason_chain_json = Column(JSON, nullable=True)
    confidence = Column(DECIMAL(4, 3), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
