"""Pydantic Schemas for Analysis Service"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class AnalysisType(str, Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    COMBINED = "combined"


class SignalType(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class TechnicalIndicator(BaseModel):
    name: str
    value: float
    signal: str
    description: Optional[str] = None


class CurrentPriceData(BaseModel):
    """Current price data with OHLCV"""
    price: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[int] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None


class MovingAverages(BaseModel):
    """Moving averages data"""
    SMA_20: Optional[float] = None
    SMA_50: Optional[float] = None
    SMA_200: Optional[float] = None
    EMA_12: Optional[float] = None
    EMA_26: Optional[float] = None


class TradingAnalysis(BaseModel):
    """Trading recommendation based on technical analysis"""
    recommendation: str  # BUY, SELL, HOLD, STRONG_BUY, STRONG_SELL
    score: float
    confidence: float
    reasons: List[str] = []


class ChartData(BaseModel):
    """Historical data for charts"""
    dates: List[str]
    prices: List[float]
    volumes: List[int]
    opens: List[float] = []
    highs: List[float] = []
    lows: List[float] = []


class TechnicalAnalysisResponse(BaseModel):
    symbol: str
    current_price: CurrentPriceData
    indicators: List[TechnicalIndicator]
    moving_averages: Optional[MovingAverages] = None
    trading_analysis: Optional[TradingAnalysis] = None
    chart_data: Optional[ChartData] = None
    overall_signal: SignalType
    signal_strength: float
    technical_score: float
    support_levels: List[float]
    resistance_levels: List[float]
    trend: str
    volatility: str
    generated_at: datetime


class FundamentalMetric(BaseModel):
    name: str
    value: Optional[float]
    industry_avg: Optional[float] = None
    rating: Optional[str] = None


class CompanyInfo(BaseModel):
    """Company information for fundamental analysis"""
    name: Optional[str] = None
    marketCap: Optional[float] = None
    industry: Optional[str] = None
    sector: Optional[str] = None
    exchange: Optional[str] = None


class ValuationFactor(BaseModel):
    """Valuation factor"""
    factor: str
    value: str
    status: str


class ValuationSummary(BaseModel):
    """Valuation summary"""
    status: str
    score: float
    factors: List[ValuationFactor] = []


class FinancialRatios(BaseModel):
    """Financial ratios"""
    pe: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debtToEquity: Optional[float] = None
    currentRatio: Optional[float] = None
    quickRatio: Optional[float] = None
    grossMargin: Optional[float] = None
    operatingMargin: Optional[float] = None
    netMargin: Optional[float] = None


class GrowthMetrics(BaseModel):
    """Growth metrics"""
    revenueGrowth: Optional[float] = None
    earningsGrowth: Optional[float] = None
    epsGrowth: Optional[float] = None


class IncomeStatement(BaseModel):
    """Income statement data"""
    revenue: Optional[float] = None
    grossProfit: Optional[float] = None
    operatingIncome: Optional[float] = None
    netIncome: Optional[float] = None
    eps: Optional[float] = None


class BalanceSheet(BaseModel):
    """Balance sheet data"""
    totalAssets: Optional[float] = None
    totalLiabilities: Optional[float] = None
    totalEquity: Optional[float] = None
    cash: Optional[float] = None
    longTermDebt: Optional[float] = None


class CashFlow(BaseModel):
    """Cash flow data"""
    operatingCashFlow: Optional[float] = None
    investingCashFlow: Optional[float] = None
    financingCashFlow: Optional[float] = None
    freeCashFlow: Optional[float] = None
    netCashFlow: Optional[float] = None


class FundamentalAnalysisResponse(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    company_info: Optional[CompanyInfo] = None
    valuation_summary: Optional[ValuationSummary] = None
    financial_ratios: Optional[FinancialRatios] = None
    growth_metrics: Optional[GrowthMetrics] = None
    income_statement: Optional[IncomeStatement] = None
    balance_sheet: Optional[BalanceSheet] = None
    cash_flow: Optional[CashFlow] = None
    fundamental_score: float
    overall_rating: str
    generated_at: datetime


class FilterOperator(str, Enum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    BETWEEN = "between"


class ScreenerFilter(BaseModel):
    field: str
    operator: FilterOperator
    value: Any
    value2: Optional[Any] = None


class ScreenerRequest(BaseModel):
    filters: List[ScreenerFilter]
    sort_by: str = "symbol"
    sort_order: str = "asc"
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ScreenerStock(BaseModel):
    symbol: str
    name: Optional[str]
    exchange: Optional[str] = None
    price: float
    change_percent: float
    volume: int
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    rsi: Optional[float]
    signal: Optional[str]


class ScreenerResponse(BaseModel):
    total: int
    stocks: List[ScreenerStock]
    generated_at: datetime


class ScreenerConfigCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    filters: List[ScreenerFilter]
    is_public: bool = False


class ScreenerConfigResponse(BaseModel):
    id: int
    user_id: int
    name: str
    filters: List[Dict[str, Any]]
    is_public: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Additional schemas for new endpoints

class StockComparisonRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=2, max_length=10)
    metrics: Optional[List[str]] = None  # specific metrics to compare


class StockComparisonItem(BaseModel):
    symbol: str
    name: Optional[str]
    price: float
    change_percent: float
    technical_score: float
    fundamental_score: float
    overall_signal: SignalType
    metrics: Dict[str, Any]


class StockComparisonResponse(BaseModel):
    stocks: List[StockComparisonItem]
    best_technical: str
    best_fundamental: str
    recommendation: str
    generated_at: datetime


class IndustryAnalysisResponse(BaseModel):
    industry_code: str
    industry_name: str
    stock_count: int
    avg_pe_ratio: Optional[float]
    avg_pb_ratio: Optional[float]
    avg_roe: Optional[float]
    market_cap_total: Optional[float]
    top_performers: List[ScreenerStock]
    worst_performers: List[ScreenerStock]
    sector_signal: str
    generated_at: datetime


class CombinedAnalysisResponse(BaseModel):
    symbol: str
    technical: TechnicalAnalysisResponse
    fundamental: FundamentalAnalysisResponse
    combined_score: float
    recommendation: str
    confidence: float
    key_insights: List[str]
    generated_at: datetime


class SignalStock(BaseModel):
    symbol: str
    name: Optional[str]
    price: float
    change_percent: float
    signal: SignalType
    signal_strength: float
    trigger_reason: str


# ---------------------------------------------------------------------------
# Trader-helper foundations (road_map_version_11.xlsx — F-001, F-002)
# Consumed by the decision-helper-service (Ch 3, 9 of Schwager).
# ---------------------------------------------------------------------------

class AtrPoint(BaseModel):
    """Single ATR bar."""
    date: str
    atr: float


class AtrResponse(BaseModel):
    """ATR series + latest value for a symbol."""
    symbol: str
    period: int
    latest: float
    series: List[AtrPoint]
    generated_at: datetime


class SwingType(str, Enum):
    HIGH = "high"
    LOW = "low"


class SwingPivot(BaseModel):
    """A confirmed swing pivot (HH/HL/LH/LL — Ch 3)."""
    bar_index: int
    date: str
    type: SwingType
    price: float


class SwingsResponse(BaseModel):
    symbol: str
    window: int
    pivots: List[SwingPivot]
    generated_at: datetime


class SRLevelType(str, Enum):
    """A level acts as support, resistance, or both (Schwager Ch 4 — S/R flip)."""
    SUPPORT = "support"
    RESISTANCE = "resistance"
    FLIP = "flip"


class SRTouch(BaseModel):
    """One swing pivot that contributes to an S/R level."""
    bar_index: int
    date: str
    price: float
    pivot_type: SwingType


class SRLevel(BaseModel):
    """A clustered support/resistance level built from swing pivots (Ch 4)."""
    price: float                      # cluster mean
    type: SRLevelType
    strength: int                     # number of touches
    age_bars: int                     # bars since most recent touch
    touches: List[SRTouch]


class SRResponse(BaseModel):
    symbol: str
    window: int
    tolerance_pct: float
    supports: List[SRLevel]           # type in {support, flip}, sorted price asc
    resistances: List[SRLevel]        # type in {resistance, flip}, sorted price asc
    generated_at: datetime


class TopSignalsResponse(BaseModel):
    buy_signals: List[SignalStock]
    sell_signals: List[SignalStock]
    generated_at: datetime


class QuickSummaryResponse(BaseModel):
    symbol: str
    name: Optional[str]
    price: float
    change_percent: float
    volume: int
    technical_signal: SignalType
    technical_score: float
    fundamental_rating: str
    fundamental_score: float
    key_levels: Dict[str, float]
    one_liner: str
    generated_at: datetime
