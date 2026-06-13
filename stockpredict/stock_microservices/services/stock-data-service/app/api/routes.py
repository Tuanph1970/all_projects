"""
API Routes for Stock Data Service
"""
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.models.schemas import (
    CompanyResponse,
    CompanyDetailResponse,
    CompanyListingResponse,
    HistoricalDataResponse,
    TopMoverResponse,
    SearchResult,
    MarketIndexResponse,
    IndustryResponse,
    PaginatedResponse,
    MessageResponse,
    ErrorResponse,
    CompanyFinancialsResponse,
)
from app.services.stock_service import StockService
from app.api.dependencies import get_stock_service, require_admin


router = APIRouter(tags=["Stock Data"])


# ==================== Company Endpoints ====================

@router.get(
    "/companies",
    response_model=PaginatedResponse[CompanyResponse],
    summary="Get all companies",
)
async def get_companies(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    exchange: Optional[str] = Query(None, description="Filter by exchange (HOSE, HNX, UPCOM)"),
    industry_id: Optional[int] = Query(None, description="Filter by industry ID"),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    Get paginated list of all companies.

    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page (max 100)
    - **exchange**: Optional filter by exchange
    - **industry_id**: Optional filter by industry
    """
    companies, total, total_pages = await stock_service.get_all_companies(
        page=page,
        page_size=page_size,
        exchange=exchange,
        industry_id=industry_id,
    )

    return PaginatedResponse(
        items=companies,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/companies/all",
    response_model=List[CompanyListingResponse],
    summary="Get all companies from VNStock (live)",
)
async def get_all_companies(
    stock_service: StockService = Depends(get_stock_service),
):
    """
    Get all listed companies from VNStock (live data).

    This endpoint fetches company data directly from VNStock API,
    providing the most up-to-date listing of all Vietnamese stocks.
    """
    return await stock_service.get_all_companies_live()


@router.get(
    "/companies/group/{group}",
    response_model=List[CompanyListingResponse],
    summary="Get companies by stock group (live)",
)
async def get_companies_by_group(
    group: str,
    stock_service: StockService = Depends(get_stock_service),
):
    """
    Get companies by stock group from VNStock (live data).

    - **group**: Stock group (VN30, VN100, HOSE, HNX, UPCOM, etc.)

    Returns list of symbols in the specified group.
    """
    return await stock_service.get_companies_by_group_live(group=group)


@router.get(
    "/stocks/search",
    response_model=List[CompanyListingResponse],
    summary="Search companies (live)",
)
async def search_companies(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Max results"),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    Search companies by symbol or name from VNStock (live data).

    - **q**: Search query (symbol or name)
    - **limit**: Maximum number of results
    """
    return await stock_service.search_companies_live(query=q, limit=limit)


@router.get(
    "/stocks/{symbol}",
    response_model=CompanyDetailResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get company details",
)
async def get_company_detail(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service),
):
    """Get detailed information for a specific company/stock."""
    company = await stock_service.get_company_detail(symbol)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company not found: {symbol}",
        )
    return company


@router.get(
    "/stocks/{symbol}/history",
    response_model=HistoricalDataResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get historical price data",
)
async def get_historical_data(
    symbol: str,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    Get historical OHLCV data for a symbol.

    - **symbol**: Stock symbol (e.g., VNM, FPT)
    - **start_date**: Start date (default: 1 year ago)
    - **end_date**: End date (default: today)
    """
    data = await stock_service.get_historical_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No price data for '{symbol}' in the requested range "
                f"({start_date or 'default'} to {end_date or 'today'}). "
                f"The symbol may not exist or has no data for that period."
            ),
        )
    return data


# ==================== Company Info Endpoints ====================

@router.post(
    "/companies/sync",
    response_model=MessageResponse,
    summary="Manually trigger company data sync",
)
async def sync_company_data(
    stock_service: StockService = Depends(get_stock_service),
    _user: dict = Depends(require_admin),
):
    """
    Manually trigger a full re-sync of VN30 company profiles,
    financial statements, and historical price data.

    Admin-only — gated to prevent unauthenticated request floods that would
    hammer VNStock and the database (SECURITY_AUDIT.md HIGH #4).
    """
    import asyncio
    asyncio.create_task(stock_service.sync_all_company_data())
    return MessageResponse(
        message="Company data sync started in background",
        success=True,
    )


@router.get(
    "/companies/{symbol}/profile",
    response_model=List[dict],
    summary="Get company profile/overview",
)
async def get_company_profile(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service),
):
    """Get company overview and profile data from DB cache."""
    return await stock_service.get_company_profile_cached(symbol=symbol)


@router.get(
    "/companies/{symbol}/news",
    response_model=List[dict],
    summary="Get company news",
)
async def get_company_news(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service),
):
    """Get latest news articles for a company."""
    return await stock_service.get_company_news_data(symbol=symbol)


@router.get(
    "/companies/{symbol}/events",
    response_model=List[dict],
    summary="Get company events",
)
async def get_company_events(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service),
):
    """Get corporate events (dividends, stock splits, AGMs, etc.)."""
    return await stock_service.get_company_events_data(symbol=symbol)


@router.get(
    "/companies/{symbol}/dividends",
    response_model=List[dict],
    summary="Get company dividends",
)
async def get_company_dividends(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service),
):
    """Get dividend history for a company."""
    return await stock_service.get_company_dividends_data(symbol=symbol)


@router.get(
    "/companies/{symbol}/historical-data",
    response_model=HistoricalDataResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get historical price data by company",
)
async def get_company_historical_data(
    symbol: str,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    Get historical OHLCV data via /companies/ path.
    Matches webapi: views.getAllHistoricalData
    """
    data = await stock_service.get_historical_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No price data for '{symbol}' in the requested range "
                f"({start_date or 'default'} to {end_date or 'today'}). "
                f"The symbol may not exist or has no data for that period."
            ),
        )
    return data


@router.get(
    "/companies/{symbol}/financials",
    response_model=CompanyFinancialsResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get company financial ratios",
)
async def get_company_financials(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service),
):
    """
    Get financial ratios and metrics for a company.

    - **symbol**: Stock symbol (e.g., TCB, VNM, FPT)

    Returns P/E, P/B, ROE, ROA, EPS, and other financial metrics.
    """
    data = await stock_service.get_company_financials(symbol=symbol)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Financial data not found for: {symbol}",
        )
    return data


# ==================== Financial Statement Endpoints ====================


@router.get(
    "/companies/{symbol}/financials/income-statement",
    response_model=List[dict],
    summary="Get income statement data",
)
async def get_income_statement(
    symbol: str,
    period: str = "annual",
    stock_service: StockService = Depends(get_stock_service),
):
    """Get multi-period income statement data for a company (from DB cache)."""
    return await stock_service.get_financial_statement_cached(symbol, "income_statement", period)


@router.get(
    "/companies/{symbol}/financials/cash-flow",
    response_model=List[dict],
    summary="Get cash flow statement data",
)
async def get_cash_flow(
    symbol: str,
    period: str = "annual",
    stock_service: StockService = Depends(get_stock_service),
):
    """Get multi-period cash flow statement data for a company (from DB cache)."""
    return await stock_service.get_financial_statement_cached(symbol, "cash_flow", period)


@router.get(
    "/companies/{symbol}/financials/balance-sheet",
    response_model=List[dict],
    summary="Get balance sheet data",
)
async def get_balance_sheet(
    symbol: str,
    period: str = "annual",
    stock_service: StockService = Depends(get_stock_service),
):
    """Get multi-period balance sheet data for a company (from DB cache)."""
    return await stock_service.get_financial_statement_cached(symbol, "balance_sheet", period)


@router.get(
    "/companies/{symbol}/financials/ratios",
    response_model=List[dict],
    summary="Get financial ratios data",
)
async def get_financial_ratios(
    symbol: str,
    period: str = "annual",
    stock_service: StockService = Depends(get_stock_service),
):
    """Get multi-period financial ratio data for a company (from DB cache)."""
    return await stock_service.get_financial_statement_cached(symbol, "ratio", period)


# ==================== Top Movers Endpoints ====================

@router.get(
    "/companies/top-gainers",
    response_model=List[TopMoverResponse],
    summary="Get top gaining stocks",
)
async def get_top_gainers(
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    stock_service: StockService = Depends(get_stock_service),
):
    """Get top gaining stocks for the latest trading day."""
    return await stock_service.get_top_gainers(limit=limit)


@router.get(
    "/companies/top-losers",
    response_model=List[TopMoverResponse],
    summary="Get top losing stocks",
)
async def get_top_losers(
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    stock_service: StockService = Depends(get_stock_service),
):
    """Get top losing stocks for the latest trading day."""
    return await stock_service.get_top_losers(limit=limit)


@router.get(
    "/companies/top-actives",
    response_model=List[TopMoverResponse],
    summary="Get most active stocks",
)
async def get_most_active(
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    stock_service: StockService = Depends(get_stock_service),
):
    """Get most actively traded stocks by volume."""
    return await stock_service.get_most_active(limit=limit)


# ==================== Industry Endpoints ====================

@router.get(
    "/industries",
    response_model=List[IndustryResponse],
    summary="Get all industries",
)
async def get_industries(
    stock_service: StockService = Depends(get_stock_service),
):
    """Get list of all industries/sectors."""
    return await stock_service.get_all_industries()


@router.get(
    "/industries/{industry_code}/companies",
    response_model=PaginatedResponse[CompanyResponse],
    summary="Get companies by industry",
)
async def get_companies_by_industry(
    industry_code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    stock_service: StockService = Depends(get_stock_service),
):
    """Get all companies in a specific industry by ICB code."""
    return await stock_service.get_companies_by_industry_code(
        industry_code=industry_code,
        page=page,
        page_size=page_size,
    )


# ==================== Market Index Endpoints ====================

@router.get(
    "/market/indices",
    response_model=List[MarketIndexResponse],
    summary="Get market indices",
)
async def get_market_indices(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    stock_service: StockService = Depends(get_stock_service),
):
    """Get market index data (VNINDEX, VN30, HNX, etc.)."""
    return await stock_service.get_market_indices(
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/market/indices/latest",
    response_model=List[MarketIndexResponse],
    summary="Get latest market indices",
)
async def get_latest_indices(
    stock_service: StockService = Depends(get_stock_service),
):
    """Get latest market index values."""
    return await stock_service.get_latest_indices()


# ==================== Price Board Endpoints ====================

@router.get(
    "/priceboards",
    response_model=List[dict],
    summary="Get price board data",
)
async def get_price_board(
    group: str = Query("VN30", description="Stock group (VN30, VN100, HOSE, HNX, etc.)"),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    Get real-time price board data for a stock group.

    - **group**: Stock group to fetch (default: VN30)

    Returns bid/ask prices, match prices, volumes, etc. for all stocks in the group.
    """
    return await stock_service.get_price_board(group=group)


@router.post(
    "/priceboards/refresh",
    response_model=MessageResponse,
    summary="Refresh price board cache from Vietcap API",
)
async def refresh_price_board(
    group: str = Query("VN30", description="Stock group (VN30, VN100)"),
    stock_service: StockService = Depends(get_stock_service),
    _user: dict = Depends(require_admin),
):
    """
    Fetch fresh price board data from Vietcap API and store in DB.
    Called after login to warm the cache. Slow (~20s) but non-blocking for the caller.

    Admin-only — the call is expensive and previously could be triggered by
    any unauthenticated client (SECURITY_AUDIT.md HIGH #4).
    """
    try:
        count = await stock_service.refresh_price_board(group=group)
        return MessageResponse(
            message=f"Refreshed {count} records for {group.upper()}",
            success=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh price board: {str(e)}",
        )


# ==================== Data Sync Endpoints ====================

@router.post(
    "/stocks/{symbol}/ensure-and-sync",
    response_model=MessageResponse,
    summary="Ensure company exists and sync historical data",
)
async def ensure_and_sync_stock(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service),
):
    """
    Ensure a company record exists and sync 5 years of historical data.
    Called by portfolio-service when a user adds a stock to their portfolio.

    - **symbol**: Stock symbol (e.g., TCB, VNM)

    Idempotent: skips sync if data was synced within the last 24 hours.
    """
    try:
        result = await stock_service.ensure_company_and_sync(symbol=symbol)
        if result["skipped"]:
            return MessageResponse(
                message=f"Sync skipped for {symbol.upper()}, data is recent",
                success=True,
            )
        return MessageResponse(
            message=f"{'Created' if result['created'] else 'Found'} company {symbol.upper()}, synced {result['synced']} records",
            success=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ensure and sync data for {symbol}: {str(e)}",
        )


@router.post(
    "/stocks/{symbol}/sync",
    response_model=MessageResponse,
    summary="Sync stock data",
)
async def sync_stock_data(
    symbol: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    Fetch and sync historical data for a symbol from VNStock.

    - **symbol**: Stock symbol to sync
    - **start_date**: Start date (default: 1 year ago)
    - **end_date**: End date (default: today)
    """
    try:
        count = await stock_service.fetch_and_save_historical_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
        return MessageResponse(
            message=f"Synced {count} records for {symbol}",
            success=True,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync data: {str(e)}",
        )
