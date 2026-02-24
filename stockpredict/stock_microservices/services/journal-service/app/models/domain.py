"""Domain Models for Journal Service — 9 tables implementing Schwager's Trading Journal"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


# ============================================================================
# Enums
# ============================================================================

class TradeDirection(enum.Enum):
    LONG = "Long"
    SHORT = "Short"


class EntryType(enum.Enum):
    MARKET = "Market"
    LIMIT = "Limit"
    STOP = "Stop"


class TradeStatus(enum.Enum):
    OPEN = "Open"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"


class ChartPattern(enum.Enum):
    HEAD_AND_SHOULDERS = "Head and Shoulders"
    INVERSE_HEAD_AND_SHOULDERS = "Inverse Head and Shoulders"
    DOUBLE_TOP = "Double Top"
    DOUBLE_BOTTOM = "Double Bottom"
    TRIPLE_TOP = "Triple Top"
    TRIPLE_BOTTOM = "Triple Bottom"
    ASCENDING_TRIANGLE = "Ascending Triangle"
    DESCENDING_TRIANGLE = "Descending Triangle"
    SYMMETRICAL_TRIANGLE = "Symmetrical Triangle"
    BULL_FLAG = "Bull Flag"
    BEAR_FLAG = "Bear Flag"
    CUP_AND_HANDLE = "Cup and Handle"
    WEDGE_RISING = "Rising Wedge"
    WEDGE_FALLING = "Falling Wedge"
    CHANNEL_UP = "Channel Up"
    CHANNEL_DOWN = "Channel Down"
    BREAKOUT = "Breakout"
    BREAKDOWN = "Breakdown"
    CONSOLIDATION = "Consolidation"
    OTHER = "Other"


class EmotionalState(enum.Enum):
    CONFIDENT = "Confident"
    CALM = "Calm"
    EXCITED = "Excited"
    ANXIOUS = "Anxious"
    FEARFUL = "Fearful"
    GREEDY = "Greedy"
    FRUSTRATED = "Frustrated"
    REVENGE = "Revenge"
    BORED = "Bored"
    NEUTRAL = "Neutral"


class ChartType(enum.Enum):
    ENTRY = "Entry"
    EXIT = "Exit"
    DURING = "During"
    OVERVIEW = "Overview"


class RuleCategory(enum.Enum):
    RISK = "Risk"
    ENTRY = "Entry"
    EXIT = "Exit"
    PSYCHOLOGY = "Psychology"
    GENERAL = "General"


# ============================================================================
# Table 1: Accounts — Journal account settings
# ============================================================================

class Account(Base):
    __tablename__ = "journal_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    account_name = Column(String(255), nullable=False)
    starting_equity = Column(Float, nullable=False)
    current_equity = Column(Float, nullable=False)
    max_risk_per_trade = Column(Float, default=2.0)       # percentage
    max_cumulative_risk = Column(Float, default=25.0)      # percentage
    currency = Column(String(10), default="VND")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    trades = relationship("Trade", back_populates="account", cascade="all, delete-orphan")
    daily_plans = relationship("DailyPlan", back_populates="account", cascade="all, delete-orphan")
    weekly_reviews = relationship("WeeklyReview", back_populates="account", cascade="all, delete-orphan")
    equity_snapshots = relationship("EquitySnapshot", back_populates="account", cascade="all, delete-orphan")
    trading_rules = relationship("TradingRule", back_populates="account", cascade="all, delete-orphan")


# ============================================================================
# Table 2: Trades — Core trade log (Schwager's Notebook)
# ============================================================================

class Trade(Base):
    __tablename__ = "journal_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("journal_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    trade_number = Column(Integer, nullable=False)
    entry_date = Column(Date, nullable=False)
    market_ticker = Column(String(20), nullable=False, index=True)
    direction = Column(SQLEnum(TradeDirection), nullable=False)
    entry_price = Column(Float, nullable=False)
    entry_type = Column(SQLEnum(EntryType), nullable=False)
    initial_stop = Column(Float, nullable=False)
    revised_stop = Column(Float, nullable=True)
    position_size = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    objective_1 = Column(Float, nullable=True)
    objective_2 = Column(Float, nullable=True)
    exit_date = Column(Date, nullable=True)
    exit_price = Column(Float, nullable=True)
    status = Column(SQLEnum(TradeStatus), default=TradeStatus.OPEN)
    entry_reason = Column(Text, nullable=True)
    exit_reason = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="trades")
    stop_revisions = relationship("StopRevision", back_populates="trade", cascade="all, delete-orphan")
    diary = relationship("TradeDiary", back_populates="trade", uselist=False, cascade="all, delete-orphan")


# ============================================================================
# Table 3: Stop Revisions — Audit trail
# ============================================================================

class StopRevision(Base):
    __tablename__ = "journal_stop_revisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, ForeignKey("journal_trades.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_stop = Column(Float, nullable=False)
    new_stop = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    revised_at = Column(DateTime, default=datetime.utcnow)

    trade = relationship("Trade", back_populates="stop_revisions")


# ============================================================================
# Table 4: Trade Diary — Schwager's 3 pillars
# ============================================================================

class TradeDiary(Base):
    __tablename__ = "journal_trade_diary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, ForeignKey("journal_trades.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    reasons_for_trade = Column(Text, nullable=True)
    how_it_turned_out = Column(Text, nullable=True)
    lessons_and_mistakes = Column(Text, nullable=True)
    chart_pattern = Column(SQLEnum(ChartPattern), nullable=True)
    emotional_state_entry = Column(SQLEnum(EmotionalState), nullable=True)
    emotional_state_during = Column(SQLEnum(EmotionalState), nullable=True)
    emotional_state_exit = Column(SQLEnum(EmotionalState), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    trade = relationship("Trade", back_populates="diary")
    charts = relationship("DiaryChart", back_populates="diary", cascade="all, delete-orphan")


# ============================================================================
# Table 5: Diary Charts — Screenshot uploads
# ============================================================================

class DiaryChart(Base):
    __tablename__ = "journal_diary_charts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diary_id = Column(Integer, ForeignKey("journal_trade_diary.id", ondelete="CASCADE"), nullable=False, index=True)
    image_path = Column(String(500), nullable=False)
    caption = Column(String(500), nullable=True)
    chart_type = Column(SQLEnum(ChartType), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    diary = relationship("TradeDiary", back_populates="charts")


# ============================================================================
# Table 6: Daily Plans — Schwager's Step 4
# ============================================================================

class DailyPlan(Base):
    __tablename__ = "journal_daily_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("journal_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_date = Column(Date, nullable=False)
    market_review = Column(Text, nullable=True)
    new_trade_ideas = Column(Text, nullable=True)
    stop_objective_updates = Column(Text, nullable=True)
    emotional_checkin = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    account = relationship("Account", back_populates="daily_plans")


# ============================================================================
# Table 7: Weekly Reviews
# ============================================================================

class WeeklyReview(Base):
    __tablename__ = "journal_weekly_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("journal_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start = Column(Date, nullable=False)
    what_went_well = Column(Text, nullable=True)
    what_went_wrong = Column(Text, nullable=True)
    key_adjustments = Column(Text, nullable=True)
    trades_taken = Column(Integer, default=0)
    trades_won = Column(Integer, default=0)
    weekly_pnl = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    account = relationship("Account", back_populates="weekly_reviews")


# ============================================================================
# Table 8: Equity Snapshots
# ============================================================================

class EquitySnapshot(Base):
    __tablename__ = "journal_equity_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("journal_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False)
    equity_value = Column(Float, nullable=False)
    open_trade_equity = Column(Float, default=0.0)
    total_equity = Column(Float, nullable=False)

    account = relationship("Account", back_populates="equity_snapshots")


# ============================================================================
# Table 9: Trading Rules — Personal checklist
# ============================================================================

class TradingRule(Base):
    __tablename__ = "journal_trading_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("journal_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_text = Column(Text, nullable=False)
    category = Column(SQLEnum(RuleCategory), nullable=False)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    account = relationship("Account", back_populates="trading_rules")
