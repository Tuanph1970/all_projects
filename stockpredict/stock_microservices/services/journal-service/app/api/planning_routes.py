"""Daily Plans & Weekly Reviews API Routes"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.services.planning_service import PlanningService
from app.models.schemas import (
    DailyPlanCreate, DailyPlanUpdate, DailyPlanResponse,
    WeeklyReviewCreate, WeeklyReviewUpdate, WeeklyReviewResponse
)

router = APIRouter()


# =============================================================================
# Daily Plan Endpoints
# =============================================================================

@router.get("/accounts/{account_id}/plans")
async def get_daily_plans(
    account_id: int,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get daily plans for an account (most recent first)"""
    service = PlanningService(db)
    plans = await service.get_daily_plans(
        account_id, current_user["user_id"], limit, offset
    )
    if plans is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return plans


@router.get("/accounts/{account_id}/plans/{plan_id}")
async def get_daily_plan(
    account_id: int,
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific daily plan"""
    service = PlanningService(db)
    plan = await service.get_daily_plan(
        account_id, current_user["user_id"], plan_id
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/accounts/{account_id}/plans", status_code=status.HTTP_201_CREATED)
async def create_daily_plan(
    account_id: int,
    data: DailyPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create or get daily plan for a date (one plan per date)"""
    service = PlanningService(db)
    result = await service.get_or_create_daily_plan(
        account_id, current_user["user_id"], data
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return result


@router.put("/accounts/{account_id}/plans/{plan_id}")
async def update_daily_plan(
    account_id: int,
    plan_id: int,
    data: DailyPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a daily plan"""
    service = PlanningService(db)
    plan = await service.update_daily_plan(
        account_id, current_user["user_id"], plan_id, data
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.delete("/accounts/{account_id}/plans/{plan_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_daily_plan(
    account_id: int,
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a daily plan"""
    service = PlanningService(db)
    deleted = await service.delete_daily_plan(
        account_id, current_user["user_id"], plan_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Plan not found")


# =============================================================================
# Weekly Review Endpoints
# =============================================================================

@router.get("/accounts/{account_id}/reviews")
async def get_weekly_reviews(
    account_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get weekly reviews for an account (most recent first)"""
    service = PlanningService(db)
    reviews = await service.get_weekly_reviews(
        account_id, current_user["user_id"], limit, offset
    )
    if reviews is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return reviews


@router.get("/accounts/{account_id}/reviews/{review_id}")
async def get_weekly_review(
    account_id: int,
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific weekly review"""
    service = PlanningService(db)
    review = await service.get_weekly_review(
        account_id, current_user["user_id"], review_id
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("/accounts/{account_id}/reviews", status_code=status.HTTP_201_CREATED)
async def create_weekly_review(
    account_id: int,
    data: WeeklyReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create weekly review with auto-computed trade stats"""
    service = PlanningService(db)
    result = await service.create_weekly_review(
        account_id, current_user["user_id"], data
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.put("/accounts/{account_id}/reviews/{review_id}")
async def update_weekly_review(
    account_id: int,
    review_id: int,
    data: WeeklyReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a weekly review (reflective content only; stats are auto-computed)"""
    service = PlanningService(db)
    review = await service.update_weekly_review(
        account_id, current_user["user_id"], review_id, data
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("/accounts/{account_id}/reviews/{review_id}/recalculate")
async def recalculate_weekly_stats(
    account_id: int,
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Recalculate trade statistics for a weekly review"""
    service = PlanningService(db)
    review = await service.recalculate_weekly_stats(
        account_id, current_user["user_id"], review_id
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.delete("/accounts/{account_id}/reviews/{review_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_weekly_review(
    account_id: int,
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a weekly review"""
    service = PlanningService(db)
    deleted = await service.delete_weekly_review(
        account_id, current_user["user_id"], review_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Review not found")
