"""Pydantic Schemas for AI Insights Service"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class InsightType(str, Enum):
    ANALYSIS = "analysis"
    SUMMARY = "summary"
    RECOMMENDATION = "recommendation"
    NEWS = "news"
    COMPARISON = "comparison"


class InsightRequest(BaseModel):
    symbol: str = Field(..., max_length=20)
    insight_type: InsightType = InsightType.ANALYSIS
    additional_context: Optional[str] = None


class InsightResponse(BaseModel):
    symbol: str
    insight_type: InsightType
    content: str
    summary: Optional[str]
    key_points: List[str]
    sentiment: str  # bullish, bearish, neutral
    confidence: float
    sources: List[str]
    generated_at: datetime


class ComparisonRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=2, max_length=5)
    focus: Optional[str] = None  # e.g., "valuation", "growth", "dividends"


class ComparisonResponse(BaseModel):
    symbols: List[str]
    analysis: str
    rankings: Dict[str, int]
    recommendation: str
    generated_at: datetime


class NewsAnalysisRequest(BaseModel):
    symbol: str = Field(..., max_length=20)
    news_items: List[Dict[str, str]]  # [{title, content, source, date}]


class NewsAnalysisResponse(BaseModel):
    symbol: str
    overall_sentiment: str
    sentiment_score: float  # -1 to 1
    key_events: List[str]
    potential_impact: str
    summary: str
    generated_at: datetime


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=10, max_length=500)
    context: Optional[str] = None
    symbols: Optional[List[str]] = None


class QuestionResponse(BaseModel):
    question: str
    answer: str
    relevant_data: Dict[str, Any]
    sources: List[str]
    generated_at: datetime


class MarketOverviewRequest(BaseModel):
    focus: Optional[str] = None  # sector, index, or general


class MarketOverviewResponse(BaseModel):
    summary: str
    key_movers: List[Dict[str, Any]]
    sector_analysis: Dict[str, str]
    outlook: str
    generated_at: datetime


# Additional schemas for new endpoints

class BatchInsightRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, max_length=20)
    insight_type: InsightType = InsightType.SUMMARY
    include_comparison: bool = False


class BatchInsightItem(BaseModel):
    symbol: str
    insight: Optional[InsightResponse] = None
    success: bool
    error: Optional[str] = None


class BatchInsightResponse(BaseModel):
    results: List[BatchInsightItem]
    successful: int
    failed: int
    comparison: Optional[ComparisonResponse] = None
    generated_at: datetime


class TrendingTopic(BaseModel):
    topic: str
    category: str  # stock, sector, market, news
    mentions: int
    sentiment: str
    related_symbols: List[str]


class TrendingResponse(BaseModel):
    topics: List[TrendingTopic]
    hot_stocks: List[str]
    market_mood: str
    generated_at: datetime


class PortfolioInsightRequest(BaseModel):
    holdings: List[Dict[str, Any]]  # [{symbol, quantity, avg_cost}]
    include_recommendations: bool = True


class HoldingInsight(BaseModel):
    symbol: str
    quantity: int
    current_value: float
    gain_loss_percent: float
    sentiment: str
    recommendation: str
    risk_level: str


class PortfolioInsightResponse(BaseModel):
    total_value: float
    total_gain_loss_percent: float
    portfolio_sentiment: str
    diversification_score: float
    risk_assessment: str
    holdings_insights: List[HoldingInsight]
    recommendations: List[str]
    generated_at: datetime


class SectorInsight(BaseModel):
    sector_code: str
    sector_name: str
    sentiment: str
    outlook: str
    key_drivers: List[str]
    top_picks: List[str]


class SectorsResponse(BaseModel):
    sectors: List[SectorInsight]
    best_sector: str
    worst_sector: str
    market_rotation: str
    generated_at: datetime


# ==========================================
# Comprehensive AI Insights Schemas
# ==========================================

class IndicatorCategory(BaseModel):
    """Available indicators in a category"""
    category: str
    indicators: List[str]
    description: str


class AvailableIndicatorsResponse(BaseModel):
    """Response for available indicators endpoint"""
    categories: List[IndicatorCategory]
    total_indicators: int


class IndicatorDataRequest(BaseModel):
    """Request for indicator data"""
    symbol: str = Field(..., max_length=20)
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    indicators: Dict[str, str]  # {category: indicator_name}


class IndicatorDataPoint(BaseModel):
    """Single data point with indicators"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    # Trend indicators
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    wma_20: Optional[float] = None
    # Momentum indicators
    rsi: Optional[float] = None
    stoch_k: Optional[float] = None
    stoch_d: Optional[float] = None
    mfi: Optional[float] = None
    # Volatility indicators
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    atr: Optional[float] = None
    # Volume indicators
    obv: Optional[float] = None
    vwap: Optional[float] = None


class IndicatorDataResponse(BaseModel):
    """Response for indicator data endpoint"""
    status: str
    symbol: str
    data: List[IndicatorDataPoint]
    count: int


class AIScoreComponent(BaseModel):
    """AI score breakdown"""
    overall_score: float
    confidence_level: str
    pattern_score: float
    sentiment_score: float
    risk_score: float
    prediction_score: float


class SentimentAnalysis(BaseModel):
    """Sentiment analysis result"""
    sentiment_type: str  # bullish, bearish, neutral
    score: float  # -1 to 1
    confidence: float  # 0 to 1
    news_count: int
    summary: str


class RiskFactor(BaseModel):
    """Individual risk factor"""
    factor: str
    level: str  # low, medium, high
    description: str


class RiskAssessment(BaseModel):
    """Risk assessment result"""
    risk_level: str  # low, medium, high, very_high
    volatility: float
    beta: Optional[float]
    var_95: float  # Value at Risk 95%
    risk_score: float  # 0-100
    factors: List[RiskFactor]


class PatternResult(BaseModel):
    """Pattern recognition result"""
    pattern_name: str
    pattern_type: str  # bullish, bearish, neutral
    confidence: float
    signal_strength: str  # weak, moderate, strong
    description: str


class PatternRecognition(BaseModel):
    """Pattern recognition analysis"""
    summary: str
    patterns: List[PatternResult]


class PredictionModel(BaseModel):
    """Single model prediction"""
    model_name: str
    predicted_price: float
    predicted_change: float
    confidence: float
    direction: str  # up, down, neutral
    lower_bound: float
    upper_bound: float


class PricePrediction(BaseModel):
    """Price prediction from multiple models"""
    random_forest: Optional[PredictionModel] = None
    xgboost: Optional[PredictionModel] = None
    ensemble: Optional[PredictionModel] = None
    model_comparison: str


class ComprehensiveInsightsRequest(BaseModel):
    """Request for comprehensive insights"""
    symbol: str = Field(..., max_length=20)
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    selected_indicators: Dict[str, str]  # {category: indicator_name}


class ComprehensiveInsights(BaseModel):
    """Comprehensive AI insights"""
    ai_score: AIScoreComponent
    sentiment_analysis: SentimentAnalysis
    risk_assessment: RiskAssessment
    pattern_recognition: PatternRecognition
    price_prediction: PricePrediction


class ComprehensiveInsightsResponse(BaseModel):
    """Response for comprehensive insights endpoint.

    `insights` is Optional so the error path (insufficient data, fetch
    failure) can return {status: "error", insights: None} without
    tripping pydantic validation. See Backlog #42.
    """
    status: str
    symbol: str
    insights: Optional[ComprehensiveInsights] = None
    generated_at: datetime


# ==========================================
# F-005 — Extended pattern catalog (Schwager Ch 5, 11, 12)
# Day 1 ships the four reversal patterns; continuation + bar patterns
# join the schema on Day 2 (flag/pennant/triangle/gap/WRD).
# ==========================================

class PatternMatch(BaseModel):
    """Uniform detector result.

    `measured_move_target` is the projected breakout price (Ch 5); for
    bearish patterns it sits below the neckline, for bullish patterns
    above. The decision-helper-service consumes this directly into its
    target_module (Ch 10) and failed-signal detector (Ch 11).
    """
    pattern_name: str
    pattern_type: str                    # "bullish" | "bearish"
    found: bool
    confidence: float                    # 0..1
    key_bars: List[int]                  # bar indices defining the pattern
    measured_move_target: Optional[float] = None
    neckline: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ReversalPatternsResponse(BaseModel):
    """Aggregated reversal-pattern scan for one symbol."""
    symbol: str
    lookback_bars: int
    patterns: List[PatternMatch]
    generated_at: datetime


class AllPatternsResponse(BaseModel):
    """Aggregated full-catalog scan (F-005 Day 3 + F-006): all reversal,
    continuation, bar, and trap patterns found in the lookback window."""
    symbol: str
    lookback_bars: int
    patterns: List[PatternMatch]          # all found patterns, newest-first
    pattern_count: int                    # len(patterns) for quick inspection
    categories: Dict[str, int]            # {"reversal": N, "continuation": N, "trap": N}
    generated_at: datetime
