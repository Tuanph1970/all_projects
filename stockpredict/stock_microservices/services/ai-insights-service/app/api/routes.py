"""AI Insights Service API Routes"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user_optional, get_current_user
from app.services.insights_service import InsightsService
from app.models.schemas import (
    InsightRequest, InsightResponse, InsightType,
    ComparisonRequest, ComparisonResponse,
    NewsAnalysisRequest, NewsAnalysisResponse,
    QuestionRequest, QuestionResponse,
    MarketOverviewRequest, MarketOverviewResponse,
    BatchInsightRequest, BatchInsightResponse, BatchInsightItem,
    TrendingResponse, TrendingTopic,
    PortfolioInsightRequest, PortfolioInsightResponse, HoldingInsight,
    SectorsResponse, SectorInsight,
    # Comprehensive insights
    AvailableIndicatorsResponse,
    IndicatorDataRequest, IndicatorDataResponse,
    ComprehensiveInsightsRequest, ComprehensiveInsightsResponse,
    # F-005 / F-006 pattern catalog
    ReversalPatternsResponse,
    AllPatternsResponse,
)

router = APIRouter()


@router.post("/insight", response_model=InsightResponse)
async def get_stock_insight(
    data: InsightRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Generate AI-powered insight for a stock"""
    service = InsightsService()
    return await service.generate_insight(
        symbol=data.symbol,
        insight_type=data.insight_type,
        additional_context=data.additional_context
    )


@router.get("/insight/{symbol}", response_model=InsightResponse)
async def get_stock_insight_simple(
    symbol: str,
    insight_type: InsightType = InsightType.ANALYSIS,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get AI insight for a stock (GET endpoint)"""
    service = InsightsService()
    return await service.generate_insight(symbol=symbol, insight_type=insight_type)


@router.post("/compare", response_model=ComparisonResponse)
async def compare_stocks(
    data: ComparisonRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Compare multiple stocks using AI"""
    service = InsightsService()
    return await service.compare_stocks(symbols=data.symbols, focus=data.focus)


@router.post("/news-analysis", response_model=NewsAnalysisResponse)
async def analyze_news(
    data: NewsAnalysisRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Analyze news impact on a stock"""
    service = InsightsService()
    return await service.analyze_news(symbol=data.symbol, news_items=data.news_items)


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(
    data: QuestionRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Ask a question about stocks"""
    service = InsightsService()
    return await service.answer_question(
        question=data.question,
        context=data.context,
        symbols=data.symbols
    )


@router.get("/market-overview", response_model=MarketOverviewResponse)
async def get_market_overview(
    focus: Optional[str] = None,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get AI-generated market overview"""
    service = InsightsService()
    return await service.get_market_overview(focus=focus)


@router.get("/capabilities")
async def get_capabilities():
    """Get available AI capabilities"""
    return {
        "insight_types": [t.value for t in InsightType],
        "features": [
            "stock_analysis",
            "stock_comparison",
            "news_analysis",
            "question_answering",
            "market_overview",
            "batch_insights",
            "portfolio_insights",
            "sector_analysis",
            "trending_topics"
        ],
        "llm_configured": True
    }


@router.post("/batch", response_model=BatchInsightResponse)
async def get_batch_insights(
    data: BatchInsightRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Generate insights for multiple stocks in batch"""
    service = InsightsService()
    results = []
    successful = 0
    failed = 0

    for symbol in data.symbols:
        try:
            insight = await service.generate_insight(
                symbol=symbol,
                insight_type=data.insight_type
            )
            results.append(BatchInsightItem(
                symbol=symbol,
                insight=insight,
                success=True
            ))
            successful += 1
        except Exception as e:
            results.append(BatchInsightItem(
                symbol=symbol,
                insight=None,
                success=False,
                error=str(e)
            ))
            failed += 1

    # Optionally include comparison
    comparison = None
    if data.include_comparison and successful >= 2:
        successful_symbols = [r.symbol for r in results if r.success]
        comparison = await service.compare_stocks(symbols=successful_symbols[:5])

    return BatchInsightResponse(
        results=results,
        successful=successful,
        failed=failed,
        comparison=comparison,
        generated_at=datetime.now()
    )


@router.get("/trending", response_model=TrendingResponse)
async def get_trending(
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Get trending topics and hot stocks computed from real top-mover
    data (Backlog #2). Topics derive from gainer/loser concentration;
    hot_stocks are top-actives by volume; market_mood reflects breadth.
    Degrades gracefully (empty topics, mood='unknown') if the upstream
    stock-data feed is down.
    """
    service = InsightsService()
    return await service.get_trending_data()


@router.get("/recommendations")
@router.post("/recommendations")
async def get_stock_recommendations(
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Get AI-powered stock recommendations based on real technical analysis.
    Analyzes top market stocks and generates BUY/HOLD/SELL recommendations.
    """
    service = InsightsService()
    recommendations = await service.get_stock_recommendations()
    return {"recommendations": recommendations}


@router.post("/portfolio-insight", response_model=PortfolioInsightResponse)
async def get_portfolio_insight(
    data: PortfolioInsightRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate AI insights for a user's portfolio"""
    service = InsightsService()
    holdings_insights = []
    total_value = 0.0
    total_cost = 0.0

    for holding in data.holdings:
        symbol = holding.get("symbol", "")
        quantity = holding.get("quantity", 0)
        avg_cost = holding.get("avg_cost", 0)

        # Fetch current data
        stock_data = await service._fetch_stock_data(symbol)
        current_price = stock_data.get("quote", {}).get("price", avg_cost)

        current_value = current_price * quantity
        cost_basis = avg_cost * quantity
        gain_loss_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0

        total_value += current_value
        total_cost += cost_basis

        # Generate insight for this holding
        try:
            insight = await service.generate_insight(symbol, InsightType.SUMMARY)
            sentiment = insight.sentiment
        except Exception:
            sentiment = "neutral"

        holdings_insights.append(HoldingInsight(
            symbol=symbol,
            quantity=quantity,
            current_value=current_value,
            gain_loss_percent=gain_loss_pct,
            sentiment=sentiment,
            recommendation="hold" if abs(gain_loss_pct) < 10 else ("take_profit" if gain_loss_pct > 20 else "review"),
            risk_level="medium"
        ))

    total_gain_loss = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

    # Calculate diversification score (simplified)
    unique_sectors = len(set(h.get("sector", "unknown") for h in data.holdings))
    diversification = min(unique_sectors / 5 * 100, 100)

    # Generate recommendations
    recommendations = []
    if diversification < 50:
        recommendations.append("Consider diversifying across more sectors")
    if any(h.gain_loss_percent > 30 for h in holdings_insights):
        recommendations.append("Consider taking profits on high-gain positions")
    if any(h.gain_loss_percent < -20 for h in holdings_insights):
        recommendations.append("Review underperforming positions for potential exit")

    return PortfolioInsightResponse(
        total_value=total_value,
        total_gain_loss_percent=total_gain_loss,
        portfolio_sentiment="bullish" if total_gain_loss > 5 else ("bearish" if total_gain_loss < -5 else "neutral"),
        diversification_score=diversification,
        risk_assessment="moderate",
        holdings_insights=holdings_insights,
        recommendations=recommendations if recommendations else ["Portfolio looks balanced"],
        generated_at=datetime.now()
    )


@router.get("/sectors", response_model=SectorsResponse)
async def get_sectors_insight(
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Get AI insights for market sectors, computed from real industry data
    (Backlog #3). Sentiment is derived from average daily change_percent
    across each sector's constituents; top_picks are the day's best
    performers in that sector. Returns whatever sectors had data available
    — empty list if the upstream industries feed is down.
    """
    service = InsightsService()
    return await service.get_sectors_data()


# ==========================================
# Comprehensive AI Insights Endpoints
# ==========================================

@router.get("/insights/indicators/available")
@router.get("/insights/indicators/available/")
async def get_available_indicators(
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get list of available technical indicators by category"""
    service = InsightsService()
    result = service.get_available_indicators()

    # Format response for frontend compatibility
    # Frontend expects objects with 'name' property, not just strings
    indicators_by_category = {}
    indicator_descriptions = {
        # Trend indicators
        "MACD": "Moving Average Convergence Divergence",
        "EMA": "Exponential Moving Average",
        "SMA": "Simple Moving Average",
        "WMA": "Weighted Moving Average",
        # Momentum indicators
        "RSI": "Relative Strength Index",
        "Stochastic": "Stochastic Oscillator",
        "MFI": "Money Flow Index",
        # Volatility indicators
        "BB": "Bollinger Bands",
        "ATR": "Average True Range",
        # Volume indicators
        "OBV": "On Balance Volume",
        "VWAP": "Volume Weighted Average Price",
    }

    for cat in result.categories:
        # Convert string list to list of objects with name and description
        indicators_by_category[cat.category] = [
            {
                "name": indicator,
                "description": indicator_descriptions.get(indicator, indicator)
            }
            for indicator in cat.indicators
        ]

    return {
        "status": "success",
        "data": {
            "indicators_by_category": indicators_by_category,
            "categories": [cat.model_dump() for cat in result.categories],
            "total_indicators": result.total_indicators
        }
    }


@router.post("/insights/indicators/data")
@router.post("/insights/indicators/data/")
async def get_indicator_data(
    data: IndicatorDataRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get historical price data with calculated technical indicators"""
    service = InsightsService()
    result = await service.get_indicator_data(
        symbol=data.symbol,
        start_date=data.start_date,
        end_date=data.end_date,
        indicators=data.indicators
    )

    # Format response for frontend compatibility
    # Include indicators metadata so the chart knows which panels to render
    indicators_metadata = {}
    if data.indicators:
        # data.indicators is Dict[str, str] like {"trend": "MACD", "momentum": "RSI", ...}
        for category in ['trend', 'momentum', 'volatility', 'volume']:
            if category in data.indicators and data.indicators[category]:
                indicators_metadata[category] = {
                    'name': data.indicators[category],
                    'description': f'{data.indicators[category]} Indicator'
                }

    return {
        "status": result.status,
        "symbol": result.symbol,
        "data": [point.model_dump() for point in result.data],
        "count": result.count,
        "indicators": indicators_metadata
    }


# ==========================================
# F-005 — Reversal patterns (Day 1 slice; full pattern catalog ships Day 3)
# ==========================================

@router.get("/insights/patterns/reversal/{symbol}", response_model=ReversalPatternsResponse)
async def get_reversal_patterns(
    symbol: str,
    lookback_bars: int = 120,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Run reversal-pattern detectors (H&S, Inverse H&S, Double Top,
    Double Bottom) on the most recent `lookback_bars` daily bars.

    Empty `patterns` is a valid success response (nothing found in the
    window). The decision-helper-service uses each match's
    `measured_move_target` directly as a first-cut profit target (Ch 10)
    and as the reference price for its failed-signal detector (Ch 11).
    """
    service = InsightsService()
    return await service.get_reversal_patterns(symbol=symbol, lookback_bars=lookback_bars)


# ==========================================
# F-005 Day 3 + F-006 — Aggregated full pattern catalog
# ==========================================

@router.get("/insights/patterns/{symbol}", response_model=AllPatternsResponse)
@router.post("/insights/patterns/{symbol}", response_model=AllPatternsResponse)
async def get_all_patterns(
    symbol: str,
    lookback_bars: int = 120,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Run the complete pattern catalog on the most recent `lookback_bars`
    daily bars for `symbol`.

    Covers all F-005 detector groups (reversal, continuation, bar patterns)
    plus the F-006 bull/bear trap detector.  Patterns are sorted newest-first
    by the rightmost key bar so the decision helper sees the most actionable
    signal first.

    Empty `patterns` is a valid success response — nothing detected in the
    window is not an error.
    """
    service = InsightsService()
    return await service.get_all_patterns(symbol=symbol, lookback_bars=lookback_bars)


@router.post("/insights/comprehensive")
@router.post("/insights/comprehensive/")
async def get_comprehensive_insights(
    data: ComprehensiveInsightsRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Generate comprehensive AI insights based on real technical analysis.

    Returns:
    - AI Score (pattern, sentiment, risk, prediction components)
    - Sentiment Analysis (based on technical indicators)
    - Risk Assessment (volatility, VaR, risk factors)
    - Pattern Recognition (detected chart patterns)
    - Price Predictions (from ML models)
    """
    service = InsightsService()
    result = await service.get_comprehensive_insights(
        symbol=data.symbol,
        start_date=data.start_date,
        end_date=data.end_date,
        indicators=data.selected_indicators
    )

    # Format response for frontend compatibility
    return {
        "status": result.status,
        "data": {
            "symbol": result.symbol,
            "insights": result.insights.model_dump() if result.insights else None,
            "generated_at": result.generated_at.isoformat()
        }
    }
