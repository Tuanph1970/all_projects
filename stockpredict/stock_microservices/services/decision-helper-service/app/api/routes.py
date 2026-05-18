"""API routes for decision-helper-service.

F-010 bootstrap: health + risk-prefs + position-state stubs.
The recommendation engine (F-012 onwards) mounts on POST /recommend.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_current_user_optional, get_db
from app.models.schemas import (
    PositionStateResponse,
    UserRiskPrefsRequest,
    UserRiskPrefsResponse,
)

router = APIRouter()


@router.get("/capabilities")
async def get_capabilities():
    return {
        "service": "decision-helper-service",
        "version": "0.1.0",
        "phase": "A — bootstrap",
        "features": [
            "user_risk_prefs",
            "position_state",
        ],
        "coming_soon": [
            "recommend",
            "signal_history",
            "backtest_replay",
        ],
    }


# ---------------------------------------------------------------------------
# User risk preferences (F-011 prerequisite)
# ---------------------------------------------------------------------------

@router.get("/risk-prefs", response_model=UserRiskPrefsResponse)
async def get_risk_prefs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's risk preferences (or 404 if not set)."""
    from sqlalchemy import select
    from app.models.domain import UserRiskPrefs

    user_id = current_user["user_id"]
    result = await db.execute(
        select(UserRiskPrefs).where(UserRiskPrefs.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        raise HTTPException(status_code=404, detail="Risk preferences not set")
    return UserRiskPrefsResponse(
        user_id=prefs.user_id,
        account_equity=float(prefs.account_equity),
        risk_per_trade_pct=float(prefs.risk_per_trade_pct),
        max_concurrent_positions=prefs.max_concurrent_positions,
        max_correlation=float(prefs.max_correlation),
        loss_streak_size_cut=float(prefs.loss_streak_size_cut),
        loss_streak_threshold=prefs.loss_streak_threshold,
        updated_at=prefs.updated_at,
    )


@router.put("/risk-prefs", response_model=UserRiskPrefsResponse)
async def upsert_risk_prefs(
    data: UserRiskPrefsRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update the authenticated user's risk preferences."""
    from sqlalchemy import select
    from app.models.domain import UserRiskPrefs

    user_id = current_user["user_id"]
    result = await db.execute(
        select(UserRiskPrefs).where(UserRiskPrefs.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()

    if prefs is None:
        prefs = UserRiskPrefs(user_id=user_id)
        db.add(prefs)

    prefs.account_equity = data.account_equity
    prefs.risk_per_trade_pct = data.risk_per_trade_pct
    prefs.max_concurrent_positions = data.max_concurrent_positions
    prefs.max_correlation = data.max_correlation
    prefs.loss_streak_size_cut = data.loss_streak_size_cut
    prefs.loss_streak_threshold = data.loss_streak_threshold

    await db.commit()
    await db.refresh(prefs)

    return UserRiskPrefsResponse(
        user_id=prefs.user_id,
        account_equity=float(prefs.account_equity),
        risk_per_trade_pct=float(prefs.risk_per_trade_pct),
        max_concurrent_positions=prefs.max_concurrent_positions,
        max_correlation=float(prefs.max_correlation),
        loss_streak_size_cut=float(prefs.loss_streak_size_cut),
        loss_streak_threshold=prefs.loss_streak_threshold,
        updated_at=prefs.updated_at,
    )


# ---------------------------------------------------------------------------
# Position state (read-only view; writes come from the decision engine)
# ---------------------------------------------------------------------------

@router.get("/positions/{ticker}", response_model=PositionStateResponse)
async def get_position(
    ticker: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current position state for (user, ticker).  FLAT if none."""
    from sqlalchemy import select
    from app.models.domain import PositionState

    user_id = current_user["user_id"]
    result = await db.execute(
        select(PositionState).where(
            PositionState.user_id == user_id,
            PositionState.ticker == ticker.upper(),
        )
    )
    pos = result.scalar_one_or_none()
    if pos is None:
        return PositionStateResponse(
            user_id=user_id, ticker=ticker.upper(), state="FLAT"
        )
    return PositionStateResponse(
        user_id=pos.user_id,
        ticker=pos.ticker,
        state=pos.state,
        entry_bar_date=pos.entry_bar_date,
        entry_price=float(pos.entry_price) if pos.entry_price else None,
        position_size=pos.position_size,
        current_stop=float(pos.current_stop) if pos.current_stop else None,
        current_target=float(pos.current_target) if pos.current_target else None,
        entry_signal_kind=pos.entry_signal_kind,
    )
