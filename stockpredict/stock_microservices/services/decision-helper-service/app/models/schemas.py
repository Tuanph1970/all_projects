"""Pydantic request/response schemas for the decision-helper-service."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums (as plain strings — mirrored from domain.py)
# ---------------------------------------------------------------------------

class RegimeKind:
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    UNDEFINED = "UNDEFINED"


class ActionKind:
    BUY = "BUY"
    SELL = "SELL"
    SELL_SHORT = "SELL_SHORT"
    COVER = "COVER"
    HOLD = "HOLD"
    WAIT = "WAIT"
    REVERSE = "REVERSE"


# ---------------------------------------------------------------------------
# Shared value objects
# ---------------------------------------------------------------------------

class ReasonStep(BaseModel):
    stage: str
    message: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Recommendation (the in-flight response object)
# ---------------------------------------------------------------------------

class RecommendationResponse(BaseModel):
    """Result of one decision run — returned from POST /helper/recommend."""
    user_id: int
    ticker: str
    bar_date: date
    trigger: str                       # SCHEDULED | ON_DEMAND | BACKTEST

    regime: str
    action: str
    state_before: str
    state_after: str

    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    position_size: Optional[int] = None

    signal_kind: Optional[str] = None
    signal_confirmed: bool = False
    failed_signal_kind: Optional[str] = None

    confidence: float
    reason_chain: List[ReasonStep] = Field(default_factory=list)

    latency_ms: Optional[int] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RecommendRequest(BaseModel):
    ticker: str = Field(..., max_length=16)
    bar_date: date
    trigger: str = "ON_DEMAND"


class UserRiskPrefsRequest(BaseModel):
    account_equity: float = Field(..., gt=0)
    risk_per_trade_pct: float = Field(default=1.0, ge=0.1, le=10.0)
    max_concurrent_positions: int = Field(default=5, ge=1, le=20)
    max_correlation: float = Field(default=0.7, ge=0.0, le=1.0)
    loss_streak_size_cut: float = Field(default=0.5, ge=0.0, le=1.0)
    loss_streak_threshold: int = Field(default=3, ge=1, le=10)


class UserRiskPrefsResponse(BaseModel):
    user_id: int
    account_equity: float
    risk_per_trade_pct: float
    max_concurrent_positions: int
    max_correlation: float
    loss_streak_size_cut: float
    loss_streak_threshold: int
    updated_at: datetime


# ---------------------------------------------------------------------------
# Position state
# ---------------------------------------------------------------------------

class PositionStateResponse(BaseModel):
    user_id: int
    ticker: str
    state: str                   # FLAT | LONG | SHORT
    entry_bar_date: Optional[date] = None
    entry_price: Optional[float] = None
    position_size: int = 0
    current_stop: Optional[float] = None
    current_target: Optional[float] = None
    entry_signal_kind: Optional[str] = None
