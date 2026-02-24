"""Trade & Stop Revision API Routes — Phase 2"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.services.trade_service import TradeService
from app.models.schemas import (
    TradeCreate, TradeUpdate, StopRevisionCreate
)

router = APIRouter()


# =============================================================================
# Trade CRUD Endpoints
# =============================================================================

@router.post("/accounts/{account_id}/trades", status_code=status.HTTP_201_CREATED)
async def create_trade(
    account_id: int,
    data: TradeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new trade with risk validation"""
    service = TradeService(db)
    result = await service.create_trade(account_id, current_user["user_id"], data)
    if result is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/accounts/{account_id}/trades")
async def get_trades(
    account_id: int,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: Open, Closed, Cancelled"),
    ticker: Optional[str] = Query(None, description="Filter by market ticker"),
    direction: Optional[str] = Query(None, description="Filter by direction: Long, Short"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get trades for an account with filters and computed fields"""
    service = TradeService(db)
    result = await service.get_trades(
        account_id, current_user["user_id"],
        status=status_filter, ticker=ticker, direction=direction,
        limit=limit, offset=offset
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return result


@router.get("/accounts/{account_id}/trades/{trade_id}")
async def get_trade(
    account_id: int,
    trade_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a single trade with computed fields"""
    service = TradeService(db)
    result = await service.get_trade(account_id, current_user["user_id"], trade_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return result


@router.put("/accounts/{account_id}/trades/{trade_id}")
async def update_trade(
    account_id: int,
    trade_id: int,
    data: TradeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update trade fields (exit info, lessons, objectives)"""
    service = TradeService(db)
    result = await service.update_trade(account_id, current_user["user_id"], trade_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/accounts/{account_id}/trades/{trade_id}/close")
async def close_trade(
    account_id: int,
    trade_id: int,
    exit_price: float = Query(..., gt=0, description="Exit price"),
    exit_date: Optional[str] = Query(None, description="Exit date (YYYY-MM-DD), defaults to today"),
    exit_reason: Optional[str] = Query(None, description="Reason for closing"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Close an open trade"""
    from datetime import date as date_type
    exit_date_val = None
    if exit_date:
        try:
            exit_date_val = date_type.fromisoformat(exit_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid exit_date format. Use YYYY-MM-DD")

    service = TradeService(db)
    result = await service.close_trade(
        account_id, current_user["user_id"], trade_id,
        exit_price=exit_price, exit_date_val=exit_date_val,
        exit_reason=exit_reason
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# =============================================================================
# Stop Revision Endpoints
# =============================================================================

@router.post("/accounts/{account_id}/trades/{trade_id}/stop")
async def revise_stop(
    account_id: int,
    trade_id: int,
    data: StopRevisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Revise stop price (Schwager's rule: only tighten)"""
    service = TradeService(db)
    result = await service.revise_stop(account_id, current_user["user_id"], trade_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# =============================================================================
# Risk Info Endpoint
# =============================================================================

@router.get("/accounts/{account_id}/risk")
async def get_risk_info(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get cumulative risk info for an account"""
    from app.repositories.account_repository import AccountRepository
    account_repo = AccountRepository(db)
    account = await account_repo.get_account_by_id(account_id, current_user["user_id"])
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    service = TradeService(db)
    cum_risk = await service.get_cumulative_risk(account_id, account.current_equity)
    return {
        **cum_risk,
        "max_risk_per_trade": account.max_risk_per_trade,
        "max_cumulative_risk": account.max_cumulative_risk,
        "current_equity": account.current_equity
    }


@router.delete("/accounts/{account_id}/trades/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(
    account_id: int,
    trade_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a trade"""
    service = TradeService(db)
    deleted = await service.delete_trade(account_id, current_user["user_id"], trade_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trade not found")
