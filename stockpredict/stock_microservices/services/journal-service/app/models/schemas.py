"""Pydantic Schemas for Journal Service"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# Enums (mirror domain enums for API)
# ============================================================================

class TradeDirection(str, Enum):
    LONG = "Long"
    SHORT = "Short"


class EntryType(str, Enum):
    MARKET = "Market"
    LIMIT = "Limit"
    STOP = "Stop"


class TradeStatus(str, Enum):
    OPEN = "Open"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"


class ChartPattern(str, Enum):
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


class EmotionalState(str, Enum):
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


class ChartType(str, Enum):
    ENTRY = "Entry"
    EXIT = "Exit"
    DURING = "During"
    OVERVIEW = "Overview"


class RuleCategory(str, Enum):
    RISK = "Risk"
    ENTRY = "Entry"
    EXIT = "Exit"
    PSYCHOLOGY = "Psychology"
    GENERAL = "General"


# ============================================================================
# Account Schemas
# ============================================================================

class AccountCreate(BaseModel):
    account_name: str = Field(..., max_length=255)
    starting_equity: float = Field(..., gt=0)
    currency: str = Field(default="VND", max_length=10)
    max_risk_per_trade: float = Field(default=2.0, ge=0.1, le=100.0)
    max_cumulative_risk: float = Field(default=25.0, ge=1.0, le=100.0)


class AccountUpdate(BaseModel):
    account_name: Optional[str] = Field(default=None, max_length=255)
    current_equity: Optional[float] = Field(default=None, gt=0)
    max_risk_per_trade: Optional[float] = Field(default=None, ge=0.1, le=100.0)
    max_cumulative_risk: Optional[float] = Field(default=None, ge=1.0, le=100.0)
    currency: Optional[str] = Field(default=None, max_length=10)


class AccountResponse(BaseModel):
    id: int
    user_id: int
    account_name: str
    starting_equity: float
    current_equity: float
    max_risk_per_trade: float
    max_cumulative_risk: float
    currency: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Trade Schemas (Phase 2 — defined here for completeness)
# ============================================================================

class TradeCreate(BaseModel):
    entry_date: date
    market_ticker: str = Field(..., max_length=20)
    direction: TradeDirection
    entry_price: float = Field(..., gt=0)
    entry_type: EntryType
    initial_stop: float = Field(..., gt=0)
    position_size: float = Field(..., gt=0)
    commission: float = Field(default=0.0, ge=0)
    objective_1: Optional[float] = Field(default=None, gt=0)
    objective_2: Optional[float] = Field(default=None, gt=0)
    entry_reason: Optional[str] = None


class TradeUpdate(BaseModel):
    exit_date: Optional[date] = None
    exit_price: Optional[float] = Field(default=None, gt=0)
    status: Optional[TradeStatus] = None
    exit_reason: Optional[str] = None
    lessons_learned: Optional[str] = None
    objective_1: Optional[float] = Field(default=None, gt=0)
    objective_2: Optional[float] = Field(default=None, gt=0)


class TradeResponse(BaseModel):
    id: int
    account_id: int
    trade_number: int
    entry_date: date
    market_ticker: str
    direction: TradeDirection
    entry_price: float
    entry_type: EntryType
    initial_stop: float
    revised_stop: Optional[float]
    position_size: float
    commission: float
    objective_1: Optional[float]
    objective_2: Optional[float]
    exit_date: Optional[date]
    exit_price: Optional[float]
    status: TradeStatus
    entry_reason: Optional[str]
    exit_reason: Optional[str]
    lessons_learned: Optional[str]
    # Computed fields
    risk_amount: Optional[float] = None
    risk_percent: Optional[float] = None
    net_pnl: Optional[float] = None
    r_multiple: Optional[float] = None
    duration_days: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Stop Revision Schemas
# ============================================================================

class StopRevisionCreate(BaseModel):
    new_stop: float = Field(..., gt=0)
    reason: Optional[str] = None


class StopRevisionResponse(BaseModel):
    id: int
    trade_id: int
    previous_stop: float
    new_stop: float
    reason: Optional[str]
    revised_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Trade Diary Schemas (Phase 3)
# ============================================================================

class TradeDiaryCreate(BaseModel):
    reasons_for_trade: Optional[str] = None
    chart_pattern: Optional[ChartPattern] = None
    emotional_state_entry: Optional[EmotionalState] = None


class TradeDiaryUpdate(BaseModel):
    how_it_turned_out: Optional[str] = None
    lessons_and_mistakes: Optional[str] = None
    chart_pattern: Optional[ChartPattern] = None
    emotional_state_during: Optional[EmotionalState] = None
    emotional_state_exit: Optional[EmotionalState] = None


class TradeDiaryResponse(BaseModel):
    id: int
    trade_id: int
    reasons_for_trade: Optional[str]
    how_it_turned_out: Optional[str]
    lessons_and_mistakes: Optional[str]
    chart_pattern: Optional[ChartPattern]
    emotional_state_entry: Optional[EmotionalState]
    emotional_state_during: Optional[EmotionalState]
    emotional_state_exit: Optional[EmotionalState]
    diary_complete: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Diary Chart Schemas
# ============================================================================

class DiaryChartResponse(BaseModel):
    id: int
    diary_id: int
    image_path: str
    caption: Optional[str]
    chart_type: Optional[ChartType]
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Daily Plan Schemas (Phase 5)
# ============================================================================

class DailyPlanCreate(BaseModel):
    plan_date: date
    market_review: Optional[str] = None
    new_trade_ideas: Optional[str] = None
    stop_objective_updates: Optional[str] = None
    emotional_checkin: Optional[str] = None


class DailyPlanUpdate(BaseModel):
    market_review: Optional[str] = None
    new_trade_ideas: Optional[str] = None
    stop_objective_updates: Optional[str] = None
    emotional_checkin: Optional[str] = None


class DailyPlanResponse(BaseModel):
    id: int
    account_id: int
    plan_date: date
    market_review: Optional[str]
    new_trade_ideas: Optional[str]
    stop_objective_updates: Optional[str]
    emotional_checkin: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Weekly Review Schemas (Phase 5)
# ============================================================================

class WeeklyReviewCreate(BaseModel):
    week_start: date
    what_went_well: Optional[str] = None
    what_went_wrong: Optional[str] = None
    key_adjustments: Optional[str] = None


class WeeklyReviewUpdate(BaseModel):
    what_went_well: Optional[str] = None
    what_went_wrong: Optional[str] = None
    key_adjustments: Optional[str] = None


class WeeklyReviewResponse(BaseModel):
    id: int
    account_id: int
    week_start: date
    what_went_well: Optional[str]
    what_went_wrong: Optional[str]
    key_adjustments: Optional[str]
    trades_taken: int
    trades_won: int
    weekly_pnl: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Trading Rule Schemas
# ============================================================================

class TradingRuleCreate(BaseModel):
    rule_text: str
    category: RuleCategory
    sort_order: int = Field(default=0, ge=0)


class TradingRuleUpdate(BaseModel):
    rule_text: Optional[str] = None
    category: Optional[RuleCategory] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(default=None, ge=0)


class TradingRuleResponse(BaseModel):
    id: int
    account_id: int
    rule_text: str
    category: RuleCategory
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


# ============================================================================
# Equity Snapshot Schemas
# ============================================================================

class EquitySnapshotResponse(BaseModel):
    id: int
    account_id: int
    snapshot_date: date
    equity_value: float
    open_trade_equity: float
    total_equity: float

    class Config:
        from_attributes = True
