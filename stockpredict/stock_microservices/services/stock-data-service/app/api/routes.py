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
)
from app.services.stock_service import StockService
from app.api.dependencies import get_stock_service


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
            detail=f"Company not found: {symbol}",
        )
    return data


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


# ==================== Data Sync Endpoints ====================

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
