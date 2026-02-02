"""Analysis Service API Routes"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user_optional, get_current_user
from app.services.analysis_service import AnalysisService
from app.models.schemas import (
    TechnicalAnalysisResponse, FundamentalAnalysisResponse,
    ScreenerRequest, ScreenerResponse, ScreenerConfigCreate, ScreenerConfigResponse,
    ScreenerFilter, FilterOperator,
    StockComparisonRequest, StockComparisonResponse, StockComparisonItem,
    IndustryAnalysisResponse, CombinedAnalysisResponse,
    TopSignalsResponse, SignalStock, QuickSummaryResponse, SignalType
)

router = APIRouter()


@router.get("/technical/{symbol}", response_model=TechnicalAnalysisResponse)
async def get_technical_analysis(
    symbol: str,
    period: int = Query(default=100, ge=20, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Get technical analysis for a symbol"""
    service = AnalysisService(db)
    result = await service.get_technical_analysis(symbol, period)
    if not result:
        raise HTTPException(status_code=404, detail=f"Could not generate analysis for {symbol}")
    return result


@router.get("/fundamental/{symbol}", response_model=FundamentalAnalysisResponse)
async def get_fundamental_analysis(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """Get fundamental analysis for a symbol"""
    service = AnalysisService(db)
    result = await service.get_fundamental_analysis(symbol)
    if not result:
        raise HTTPException(status_code=404, detail=f"Could not generate analysis for {symbol}")
    return result


@router.post("/screener", response_model=ScreenerResponse)
async def run_screener(
    data: ScreenerRequest,
    db: AsyncSession = Depends(get_db)
):
    """Run stock screener with filters"""
    service = AnalysisService(db)
    return await service.run_screener(
        filters=data.filters,
        sort_by=data.sort_by,
        sort_order=data.sort_order,
        limit=data.limit,
        offset=data.offset
    )


@router.get("/screener", response_model=ScreenerResponse)
async def get_default_screener(
    exchange: str = Query(None, description="Filter by exchange (HOSE, HNX, UPCOM)"),
    min_price: float = Query(None, description="Minimum price"),
    max_price: float = Query(None, description="Maximum price"),
    min_volume: float = Query(None, description="Minimum volume"),
    min_market_cap: float = Query(None, description="Minimum market cap"),
    limit: int = Query(50, description="Number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    sort_by: str = Query("symbol", description="Sort by field"),
    sort_order: str = Query("asc", description="Sort order (asc/desc)"),
    db: AsyncSession = Depends(get_db)
):
    """Get default screened stocks with optional query parameters"""
    service = AnalysisService(db)

    # Build filters from query parameters using ScreenerFilter objects
    filters = []
    if exchange and exchange != 'ALL':
        filters.append(ScreenerFilter(field="exchange", operator=FilterOperator.EQ, value=exchange))
    if min_price is not None:
        filters.append(ScreenerFilter(field="price", operator=FilterOperator.GTE, value=min_price))
    if max_price is not None:
        filters.append(ScreenerFilter(field="price", operator=FilterOperator.LTE, value=max_price))
    if min_volume is not None:
        filters.append(ScreenerFilter(field="volume", operator=FilterOperator.GTE, value=min_volume))
    if min_market_cap is not None:
        filters.append(ScreenerFilter(field="market_cap", operator=FilterOperator.GTE, value=min_market_cap))

    return await service.run_screener(
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )


@router.post("/screener/configs", response_model=ScreenerConfigResponse)
async def save_screener_config(
    data: ScreenerConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Save screener configuration"""
    service = AnalysisService(db)
    config = await service.repo.save_screener_config(
        user_id=current_user["user_id"],
        name=data.name,
        description=data.description,
        filters=[f.model_dump() for f in data.filters],
        is_public=data.is_public
    )
    return ScreenerConfigResponse.model_validate(config)


@router.get("/screener/configs", response_model=List[ScreenerConfigResponse])
async def get_screener_configs(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get saved screener configurations"""
    service = AnalysisService(db)
    configs = await service.repo.get_screener_configs(current_user["user_id"])
    return [ScreenerConfigResponse.model_validate(c) for c in configs]


@router.delete("/screener/configs/{config_id}")
async def delete_screener_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete screener configuration"""
    service = AnalysisService(db)
    deleted = await service.repo.delete_screener_config(config_id, current_user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"message": "Deleted"}


@router.get("/filters")
async def get_available_filters():
    """Get available filter options"""
    return {
        "technical": [
            {"field": "rsi", "label": "RSI", "type": "number", "min": 0, "max": 100},
            {"field": "macd", "label": "MACD", "type": "number"},
            {"field": "sma_20", "label": "SMA 20", "type": "number"},
            {"field": "volume", "label": "Volume", "type": "number"},
        ],
        "fundamental": [
            {"field": "pe_ratio", "label": "P/E Ratio", "type": "number"},
            {"field": "pb_ratio", "label": "P/B Ratio", "type": "number"},
            {"field": "roe", "label": "ROE %", "type": "number"},
            {"field": "market_cap", "label": "Market Cap", "type": "number"},
        ],
        "market": [
            {"field": "price", "label": "Price", "type": "number"},
            {"field": "change_percent", "label": "Change %", "type": "number"},
            {"field": "industry", "label": "Industry", "type": "string"},
        ]
    }


@router.post("/compare", response_model=StockComparisonResponse)
async def compare_stocks(
    data: StockComparisonRequest,
    db: AsyncSession = Depends(get_db)
):
    """Compare multiple stocks side by side"""
    service = AnalysisService(db)
    stocks = []

    for symbol in data.symbols:
        try:
            technical = await service.get_technical_analysis(symbol)
            fundamental = await service.get_fundamental_analysis(symbol)

            if technical and fundamental:
                stocks.append(StockComparisonItem(
                    symbol=symbol.upper(),
                    name=fundamental.company_name,
                    price=technical.current_price,
                    change_percent=0.0,  # Would come from quote
                    technical_score=technical.technical_score,
                    fundamental_score=fundamental.fundamental_score,
                    overall_signal=technical.overall_signal,
                    metrics={
                        "rsi": next((i.value for i in technical.indicators if i.name == "RSI"), None),
                        "pe_ratio": next((m.value for m in fundamental.valuation if m.name == "P/E"), None),
                        "roe": next((m.value for m in fundamental.profitability if m.name == "ROE"), None),
                    }
                ))
        except Exception:
            continue

    if not stocks:
        raise HTTPException(status_code=404, detail="Could not analyze any of the provided symbols")

    # Determine best performers
    best_tech = max(stocks, key=lambda s: s.technical_score)
    best_fund = max(stocks, key=lambda s: s.fundamental_score)

    return StockComparisonResponse(
        stocks=stocks,
        best_technical=best_tech.symbol,
        best_fundamental=best_fund.symbol,
        recommendation=best_tech.symbol if best_tech.technical_score > 50 else best_fund.symbol,
        generated_at=datetime.utcnow()
    )


@router.get("/industry/{industry_code}", response_model=IndustryAnalysisResponse)
async def get_industry_analysis(
    industry_code: str,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get analysis for an industry sector"""
    service = AnalysisService(db)

    # Run screener for this industry
    from app.models.schemas import ScreenerFilter, FilterOperator

    result = await service.run_screener(
        filters=[ScreenerFilter(field="industry", operator=FilterOperator.EQ, value=industry_code)],
        sort_by="change_percent",
        sort_order="desc",
        limit=100
    )

    if not result.stocks:
        raise HTTPException(status_code=404, detail=f"No stocks found for industry {industry_code}")

    # Calculate industry averages
    pe_ratios = [s.pe_ratio for s in result.stocks if s.pe_ratio]

    return IndustryAnalysisResponse(
        industry_code=industry_code,
        industry_name=industry_code,  # Would map to full name
        stock_count=result.total,
        avg_pe_ratio=sum(pe_ratios) / len(pe_ratios) if pe_ratios else None,
        avg_pb_ratio=None,
        avg_roe=None,
        market_cap_total=sum(s.market_cap or 0 for s in result.stocks),
        top_performers=result.stocks[:limit],
        worst_performers=list(reversed(result.stocks[-limit:])),
        sector_signal="neutral",
        generated_at=datetime.utcnow()
    )


@router.get("/combined/{symbol}", response_model=CombinedAnalysisResponse)
async def get_combined_analysis(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """Get combined technical and fundamental analysis"""
    service = AnalysisService(db)

    technical = await service.get_technical_analysis(symbol)
    fundamental = await service.get_fundamental_analysis(symbol)

    if not technical or not fundamental:
        raise HTTPException(status_code=404, detail=f"Could not generate analysis for {symbol}")

    # Calculate combined score (weighted average)
    combined_score = (technical.technical_score * 0.4 + fundamental.fundamental_score * 0.6)

    # Generate key insights
    insights = []
    if technical.technical_score > 60:
        insights.append(f"Technical indicators are bullish with score {technical.technical_score:.0f}")
    elif technical.technical_score < 40:
        insights.append(f"Technical indicators are bearish with score {technical.technical_score:.0f}")

    if fundamental.fundamental_score > 70:
        insights.append("Strong fundamentals suggest long-term value")

    if technical.overall_signal in [SignalType.STRONG_BUY, SignalType.BUY]:
        insights.append(f"Signal: {technical.overall_signal.value.replace('_', ' ').title()}")

    # Determine recommendation
    if combined_score >= 70:
        recommendation = "Strong Buy"
    elif combined_score >= 55:
        recommendation = "Buy"
    elif combined_score >= 45:
        recommendation = "Hold"
    elif combined_score >= 30:
        recommendation = "Sell"
    else:
        recommendation = "Strong Sell"

    return CombinedAnalysisResponse(
        symbol=symbol.upper(),
        technical=technical,
        fundamental=fundamental,
        combined_score=combined_score,
        recommendation=recommendation,
        confidence=min(technical.signal_strength, 0.95),
        key_insights=insights if insights else ["Analysis complete - review individual scores"],
        generated_at=datetime.utcnow()
    )


@router.get("/signals", response_model=TopSignalsResponse)
async def get_top_signals(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get top buy and sell signals across the market"""
    service = AnalysisService(db)

    # Get all stocks with strong signals
    buy_result = await service.run_screener(
        filters=[],
        sort_by="rsi",
        sort_order="asc",  # Oversold first for buys
        limit=limit * 2
    )

    sell_result = await service.run_screener(
        filters=[],
        sort_by="rsi",
        sort_order="desc",  # Overbought first for sells
        limit=limit * 2
    )

    buy_signals = []
    for stock in buy_result.stocks[:limit]:
        if stock.rsi and stock.rsi < 35:
            buy_signals.append(SignalStock(
                symbol=stock.symbol,
                name=stock.name,
                price=stock.price,
                change_percent=stock.change_percent,
                signal=SignalType.BUY if stock.rsi > 25 else SignalType.STRONG_BUY,
                signal_strength=min((35 - stock.rsi) / 35, 1.0),
                trigger_reason=f"RSI oversold at {stock.rsi:.1f}"
            ))

    sell_signals = []
    for stock in sell_result.stocks[:limit]:
        if stock.rsi and stock.rsi > 65:
            sell_signals.append(SignalStock(
                symbol=stock.symbol,
                name=stock.name,
                price=stock.price,
                change_percent=stock.change_percent,
                signal=SignalType.SELL if stock.rsi < 75 else SignalType.STRONG_SELL,
                signal_strength=min((stock.rsi - 65) / 35, 1.0),
                trigger_reason=f"RSI overbought at {stock.rsi:.1f}"
            ))

    return TopSignalsResponse(
        buy_signals=buy_signals,
        sell_signals=sell_signals,
        generated_at=datetime.utcnow()
    )


@router.get("/summary/{symbol}", response_model=QuickSummaryResponse)
async def get_quick_summary(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a quick summary of a stock"""
    service = AnalysisService(db)

    technical = await service.get_technical_analysis(symbol)
    fundamental = await service.get_fundamental_analysis(symbol)

    if not technical:
        raise HTTPException(status_code=404, detail=f"Could not generate summary for {symbol}")

    # Generate one-liner
    signal_text = technical.overall_signal.value.replace("_", " ").title()
    one_liner = f"{symbol} shows {signal_text} signal with technical score {technical.technical_score:.0f}/100"

    return QuickSummaryResponse(
        symbol=symbol.upper(),
        name=fundamental.company_name if fundamental else None,
        price=technical.current_price,
        change_percent=0.0,
        volume=0,
        technical_signal=technical.overall_signal,
        technical_score=technical.technical_score,
        fundamental_rating=fundamental.overall_rating if fundamental else "N/A",
        fundamental_score=fundamental.fundamental_score if fundamental else 0.0,
        key_levels={
            "support_1": technical.support_levels[0] if technical.support_levels else 0,
            "resistance_1": technical.resistance_levels[0] if technical.resistance_levels else 0,
        },
        one_liner=one_liner,
        generated_at=datetime.utcnow()
    )
