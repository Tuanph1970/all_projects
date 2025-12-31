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


class TechnicalAnalysisResponse(BaseModel):
    symbol: str
    current_price: float
    indicators: List[TechnicalIndicator]
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


class FundamentalAnalysisResponse(BaseModel):
    symbol: str
    company_name: Optional[str]
    valuation: List[FundamentalMetric]
    profitability: List[FundamentalMetric]
    growth: List[FundamentalMetric]
    financial_health: List[FundamentalMetric]
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
