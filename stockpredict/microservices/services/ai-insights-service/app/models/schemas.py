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
