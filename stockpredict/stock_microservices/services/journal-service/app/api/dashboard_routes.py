"""Dashboard & Equity Snapshot API Routes"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.services.dashboard_service import DashboardService

router = APIRouter()


# =============================================================================
# Dashboard Endpoint
# =============================================================================

@router.get("/accounts/{account_id}/dashboard")
async def get_dashboard(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get full dashboard data: stats, metrics, equity curve, segmented analysis"""
    service = DashboardService(db)
    result = await service.get_dashboard(account_id, current_user["user_id"])
    if result is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return result


# =============================================================================
# Equity Snapshot Endpoints
# =============================================================================

@router.get("/accounts/{account_id}/equity")
async def get_equity_snapshots(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get equity snapshots for an account"""
    service = DashboardService(db)
    snapshots = await service.get_equity_snapshots(account_id, current_user["user_id"])
    if snapshots is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return snapshots


@router.post("/accounts/{account_id}/equity", status_code=status.HTTP_201_CREATED)
async def create_equity_snapshot(
    account_id: int,
    snapshot_date: date = Query(..., description="Snapshot date"),
    equity_value: float = Query(..., gt=0, description="Account equity value"),
    open_trade_equity: float = Query(0.0, description="Unrealized P/L from open trades"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record an equity snapshot for tracking over time"""
    service = DashboardService(db)
    result = await service.create_equity_snapshot(
        account_id, current_user["user_id"],
        snapshot_date, equity_value, open_trade_equity
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return result
