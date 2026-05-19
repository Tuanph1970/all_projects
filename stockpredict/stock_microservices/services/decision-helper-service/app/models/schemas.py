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

# ---------------------------------------------------------------------------
# F-060..F-065 — Discipline schemas
# ---------------------------------------------------------------------------

class DisciplineViolationSchema(BaseModel):
    rule_id: str
    severity: str       # "BLOCK" | "WARNING"
    message: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class RuleAdvisorySchema(BaseModel):
    rule_id: str
    rule_text: str
    chapter: str
    triggered: bool
    severity: str       # "INFO" | "WARNING"
    detail: str = ""


class DisciplineSummaryResponse(BaseModel):
    user_id: int
    recent_losses: int
    loss_streak_threshold: int
    streak_active: bool
    current_equity: Optional[float] = None
    peak_equity: Optional[float] = None
    drawdown_pct: Optional[float] = None
    last_10_actions: List[str] = Field(default_factory=list)
    rule_advisories: List[RuleAdvisorySchema] = Field(default_factory=list)


class ValidatePlanRequest(BaseModel):
    ticker: str = Field(..., max_length=16)
    action: str
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    entry_price: Optional[float] = None
    direction: Optional[str] = None
    regime: Optional[str] = None


class ValidatePlanResponse(BaseModel):
    is_valid: bool
    violations: List[DisciplineViolationSchema] = Field(default_factory=list)
    rule_advisories: List[RuleAdvisorySchema] = Field(default_factory=list)


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
    discipline_violations: List[DisciplineViolationSchema] = Field(default_factory=list)
    rule_advisories: List[RuleAdvisorySchema] = Field(default_factory=list)

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


# ---------------------------------------------------------------------------
# F-012..F-016 — Phase B: signal analysis response
# ---------------------------------------------------------------------------

class RawSignalSchema(BaseModel):
    kind: str
    direction: str
    confidence: float
    trigger_price: float
    evidence: Dict[str, Any] = Field(default_factory=dict)


class ConfirmationStepSchema(BaseModel):
    stage: str
    result: str
    detail: Dict[str, Any] = Field(default_factory=dict)


class SignalResultSchema(BaseModel):
    signal: RawSignalSchema
    confirmed: bool
    final_confidence: float
    confirmation_steps: List[Any] = Field(default_factory=list)
    rejection_reason: Optional[str] = None


class SignalAnalysisResponse(BaseModel):
    """Phase-B response from POST /signal-analysis.

    Contains regime classification + all signals that fired + confirmation
    results.  Stop / target / size (Phase C) are not yet included.
    """
    ticker: str
    bar_date: date
    regime: str
    regime_confidence: float
    regime_features: Dict[str, Any] = Field(default_factory=dict)
    signals: List[SignalResultSchema] = Field(default_factory=list)
    best_signal: Optional[SignalResultSchema] = None
    latency_ms: Optional[int] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class SignalAnalysisRequest(BaseModel):
    ticker: str = Field(..., max_length=16)
    bar_date: date
    fast_ma: int = Field(default=10, ge=2, le=50)
    slow_ma: int = Field(default=50, ge=10, le=200)
    breakout_n: int = Field(default=20, ge=5, le=100)
    k_delay: int = Field(default=1, ge=1, le=5)


# ---------------------------------------------------------------------------
# F-050..F-054 — Phase F: Backtest / Walk-Forward schemas
# ---------------------------------------------------------------------------

class BacktestRequest(BaseModel):
    ticker: str = Field(..., max_length=16)
    start_date: date
    end_date: date
    initial_equity: float = Field(default=100_000.0, gt=0)
    risk_per_trade_pct: float = Field(default=1.0, ge=0.1, le=10.0)
    fast_ma: int = Field(default=10, ge=2, le=50)
    slow_ma: int = Field(default=50, ge=10, le=200)
    breakout_n: int = Field(default=20, ge=5, le=100)
    k_delay: int = Field(default=1, ge=1, le=5)
    slippage_bps: float = Field(default=5.0, ge=0.0, le=100.0)
    commission: float = Field(default=10.0, ge=0.0)
    walk_forward: bool = False
    wf_window_days: int = Field(default=90, ge=10, le=365)


class TradeRecordSchema(BaseModel):
    ticker: str
    direction: str
    entry_date: date
    entry_price: float
    exit_date: Optional[date] = None
    exit_price: Optional[float] = None
    shares: int
    gross_pnl: Optional[float] = None
    commission: float
    net_pnl: Optional[float] = None
    exit_reason: str


class EquityPointSchema(BaseModel):
    date: date
    equity: float
    drawdown_pct: float


class BacktestStatsSchema(BaseModel):
    num_trades: int
    num_wins: int
    win_rate: float
    total_gross_pnl: float
    total_commission: float
    total_net_pnl: float
    max_drawdown_pct: float
    expectancy: float
    sharpe_ratio: Optional[float] = None
    profit_factor: Optional[float] = None


class WalkForwardWindowSchema(BaseModel):
    window_index: int
    start_date: date
    end_date: date
    stats: BacktestStatsSchema
    num_trades: int


class BacktestResultSchema(BaseModel):

    ticker: str
    start_date: date
    end_date: date
    config: Dict[str, Any]
    trade_ledger: List[TradeRecordSchema] = Field(default_factory=list)
    equity_curve: List[EquityPointSchema] = Field(default_factory=list)
    stats: BacktestStatsSchema
    walk_forward_windows: List[WalkForwardWindowSchema] = Field(default_factory=list)
    walk_forward_aggregate: Optional[Dict[str, Any]] = None
    latency_ms: int = 0


# ---------------------------------------------------------------------------
# F-070..F-073 — HelperWatchlist + ScheduledRuns (Phase H)
# ---------------------------------------------------------------------------

class WatchlistAddRequest(BaseModel):
    ticker: str = Field(..., max_length=16)
    note: Optional[str] = Field(None, max_length=255)


class WatchlistEntryResponse(BaseModel):
    id: int
    user_id: int
    ticker: str
    active: bool
    note: Optional[str]
    created_at: datetime


class ScheduledRunSummary(BaseModel):
    id: int
    ticker: str
    bar_date: date
    action: str
    regime: Optional[str]
    confidence: Optional[float]
    latency_ms: Optional[int]
    created_at: datetime
    is_alert: bool          # True when action is BUY or SELL_SHORT


class ScheduledRunsResponse(BaseModel):
    runs: List[ScheduledRunSummary]
    total: int


# ---------------------------------------------------------------------------
# F-080..F-083 — Real-time alert schemas (Phase I)
# ---------------------------------------------------------------------------

class AlertEvent(BaseModel):
    ticker: str
    action: str               # BUY | SELL_SHORT
    bar_date: str
    regime: Optional[str] = None
    confidence: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None


class AlertsListResponse(BaseModel):
    alerts: List[AlertEvent]
    total: int


# ---------------------------------------------------------------------------
# F-120..F-123 — Multi-ticker scanner (Phase M)
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    bar_date: Optional[date] = None    # defaults to today on the server


class ScanResultItem(BaseModel):
    ticker: str
    action: str
    regime: str
    confidence: float
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    position_size: Optional[int] = None
    signal_kind: Optional[str] = None
    signal_confirmed: bool = False
    is_actionable: bool              # True when action is BUY or SELL_SHORT
    error: Optional[str] = None      # set if recommendation failed for this ticker


class ScanResponse(BaseModel):
    bar_date: date
    ticker_count: int
    actionable_count: int            # BUY + SELL_SHORT results
    results: List[ScanResultItem]
    latency_ms: int


# ---------------------------------------------------------------------------
# F-130..F-133 — Performance analytics (Phase N)
# ---------------------------------------------------------------------------

class ActionBreakdownItem(BaseModel):
    action: str
    count: int
    pct: float


class RegimeBreakdownItem(BaseModel):
    regime: str
    total: int
    buy_count: int
    sell_short_count: int
    hold_wait_count: int


class SignalBreakdownItem(BaseModel):
    signal_kind: str
    fire_count: int
    confirmed_count: int
    confirmation_rate: float   # 0..1
    avg_confidence: float      # 0..1


class DailyActionablePoint(BaseModel):
    date: str                  # ISO date string
    count: int


class TopTickerItem(BaseModel):
    ticker: str
    decision_count: int
    buy_count: int
    sell_short_count: int


class ConfidenceBucketItem(BaseModel):
    bucket: str                # e.g. "70-80%"
    count: int


class AnalyticsResponse(BaseModel):
    user_id: int
    computed_at: datetime
    days: int
    total_decisions: int
    actionable_count: int
    action_breakdown: List[ActionBreakdownItem]
    regime_breakdown: List[RegimeBreakdownItem]
    signal_breakdown: List[SignalBreakdownItem]
    daily_actionable: List[DailyActionablePoint]
    top_tickers: List[TopTickerItem]
    confidence_histogram: List[ConfidenceBucketItem]
