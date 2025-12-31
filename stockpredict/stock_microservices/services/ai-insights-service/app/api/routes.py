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
    SectorsResponse, SectorInsight
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
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get trending topics and hot stocks"""
    # In production, this would aggregate from news, social media, trading volume
    # For now, return mock trending data
    topics = [
        TrendingTopic(
            topic="VN-Index rally",
            category="market",
            mentions=150,
            sentiment="bullish",
            related_symbols=["VNM", "VIC", "VHM"]
        ),
        TrendingTopic(
            topic="Banking sector growth",
            category="sector",
            mentions=89,
            sentiment="bullish",
            related_symbols=["VCB", "BID", "CTG", "TCB"]
        ),
        TrendingTopic(
            topic="Tech stocks momentum",
            category="sector",
            mentions=67,
            sentiment="neutral",
            related_symbols=["FPT", "CMG"]
        ),
    ]

    return TrendingResponse(
        topics=topics,
        hot_stocks=["VNM", "FPT", "VCB", "VIC", "HPG"],
        market_mood="cautiously_optimistic",
        generated_at=datetime.now()
    )


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
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get AI insights for market sectors"""
    sectors = [
        SectorInsight(
            sector_code="BANK",
            sector_name="Banking",
            sentiment="bullish",
            outlook="positive",
            key_drivers=["Interest rate stability", "Credit growth", "Digital transformation"],
            top_picks=["VCB", "TCB", "MBB"]
        ),
        SectorInsight(
            sector_code="REAL",
            sector_name="Real Estate",
            sentiment="neutral",
            outlook="mixed",
            key_drivers=["Policy changes", "Infrastructure development", "Urbanization"],
            top_picks=["VHM", "NVL", "KDH"]
        ),
        SectorInsight(
            sector_code="TECH",
            sector_name="Technology",
            sentiment="bullish",
            outlook="positive",
            key_drivers=["Digital transformation", "Outsourcing growth", "AI adoption"],
            top_picks=["FPT", "CMG"]
        ),
        SectorInsight(
            sector_code="CONS",
            sector_name="Consumer Goods",
            sentiment="neutral",
            outlook="stable",
            key_drivers=["Domestic consumption", "Export recovery", "Brand strength"],
            top_picks=["VNM", "MSN", "SAB"]
        ),
        SectorInsight(
            sector_code="MANU",
            sector_name="Manufacturing",
            sentiment="neutral",
            outlook="recovering",
            key_drivers=["Export orders", "Raw material costs", "Labor availability"],
            top_picks=["HPG", "HSG", "NKG"]
        ),
    ]

    # Determine best and worst sectors
    sentiment_scores = {"bullish": 2, "neutral": 1, "bearish": 0}
    best = max(sectors, key=lambda s: sentiment_scores.get(s.sentiment, 1))
    worst = min(sectors, key=lambda s: sentiment_scores.get(s.sentiment, 1))

    return SectorsResponse(
        sectors=sectors,
        best_sector=best.sector_code,
        worst_sector=worst.sector_code,
        market_rotation="Growth sectors favored, defensive sectors stable",
        generated_at=datetime.now()
    )
