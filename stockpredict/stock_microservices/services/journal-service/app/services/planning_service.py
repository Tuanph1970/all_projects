"""Planning Service — Daily Plans & Weekly Reviews Business Logic"""
from typing import Optional
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.planning_repository import PlanningRepository
from app.repositories.account_repository import AccountRepository
from app.models.schemas import (
    DailyPlanCreate, DailyPlanUpdate,
    WeeklyReviewCreate, WeeklyReviewUpdate
)


class PlanningService:
    def __init__(self, session: AsyncSession):
        self.plan_repo = PlanningRepository(session)
        self.account_repo = AccountRepository(session)

    # =========================================================================
    # Daily Plans
    # =========================================================================

    async def get_daily_plans(self, account_id: int, user_id: int,
                               limit: int = 30, offset: int = 0) -> Optional[list]:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        plans = await self.plan_repo.get_daily_plans(account_id, limit, offset)
        return [self._plan_to_dict(p) for p in plans]

    async def get_daily_plan(self, account_id: int, user_id: int,
                              plan_id: int) -> Optional[dict]:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        plan = await self.plan_repo.get_daily_plan_by_id(plan_id, account_id)
        if not plan:
            return None
        return self._plan_to_dict(plan)

    async def get_or_create_daily_plan(self, account_id: int, user_id: int,
                                        data: DailyPlanCreate) -> Optional[dict]:
        """Get existing plan for date or create a new one"""
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None

        # Check if plan already exists for this date
        existing = await self.plan_repo.get_daily_plan_by_date(account_id, data.plan_date)
        if existing:
            return self._plan_to_dict(existing)

        plan = await self.plan_repo.create_daily_plan(
            account_id=account_id,
            plan_date=data.plan_date,
            market_review=data.market_review,
            new_trade_ideas=data.new_trade_ideas,
            stop_objective_updates=data.stop_objective_updates,
            emotional_checkin=data.emotional_checkin,
        )
        return self._plan_to_dict(plan)

    async def update_daily_plan(self, account_id: int, user_id: int,
                                 plan_id: int, data: DailyPlanUpdate) -> Optional[dict]:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            plan = await self.plan_repo.get_daily_plan_by_id(plan_id, account_id)
            return self._plan_to_dict(plan) if plan else None

        plan = await self.plan_repo.update_daily_plan(plan_id, account_id, **update_data)
        if not plan:
            return None
        return self._plan_to_dict(plan)

    async def delete_daily_plan(self, account_id: int, user_id: int,
                                 plan_id: int) -> bool:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return False
        return await self.plan_repo.delete_daily_plan(plan_id, account_id)

    @staticmethod
    def _plan_to_dict(plan) -> dict:
        return {
            "id": plan.id,
            "account_id": plan.account_id,
            "plan_date": plan.plan_date.isoformat(),
            "market_review": plan.market_review,
            "new_trade_ideas": plan.new_trade_ideas,
            "stop_objective_updates": plan.stop_objective_updates,
            "emotional_checkin": plan.emotional_checkin,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
        }

    # =========================================================================
    # Weekly Reviews
    # =========================================================================

    async def get_weekly_reviews(self, account_id: int, user_id: int,
                                  limit: int = 20, offset: int = 0) -> Optional[list]:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        reviews = await self.plan_repo.get_weekly_reviews(account_id, limit, offset)
        return [self._review_to_dict(r) for r in reviews]

    async def get_weekly_review(self, account_id: int, user_id: int,
                                 review_id: int) -> Optional[dict]:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        review = await self.plan_repo.get_weekly_review_by_id(review_id, account_id)
        if not review:
            return None
        return self._review_to_dict(review)

    async def create_weekly_review(self, account_id: int, user_id: int,
                                    data: WeeklyReviewCreate) -> Optional[dict]:
        """Create weekly review with auto-computed trade stats"""
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None

        # Check if review already exists for this week
        existing = await self.plan_repo.get_weekly_review_by_week(
            account_id, data.week_start
        )
        if existing:
            return {"error": True, "message": "Đã có review cho tuần này. Vui lòng chỉnh sửa review hiện có."}

        # Auto-compute weekly stats from closed trades
        week_end = data.week_start + timedelta(days=6)
        week_stats = await self.plan_repo.get_week_trade_stats(
            account_id, data.week_start, week_end
        )

        review = await self.plan_repo.create_weekly_review(
            account_id=account_id,
            week_start=data.week_start,
            what_went_well=data.what_went_well,
            what_went_wrong=data.what_went_wrong,
            key_adjustments=data.key_adjustments,
            trades_taken=week_stats["trades_taken"],
            trades_won=week_stats["trades_won"],
            weekly_pnl=week_stats["weekly_pnl"],
        )
        return self._review_to_dict(review)

    async def update_weekly_review(self, account_id: int, user_id: int,
                                    review_id: int,
                                    data: WeeklyReviewUpdate) -> Optional[dict]:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            review = await self.plan_repo.get_weekly_review_by_id(review_id, account_id)
            return self._review_to_dict(review) if review else None

        review = await self.plan_repo.update_weekly_review(review_id, account_id, **update_data)
        if not review:
            return None
        return self._review_to_dict(review)

    async def recalculate_weekly_stats(self, account_id: int, user_id: int,
                                        review_id: int) -> Optional[dict]:
        """Recalculate trade stats for a weekly review"""
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        review = await self.plan_repo.get_weekly_review_by_id(review_id, account_id)
        if not review:
            return None

        week_end = review.week_start + timedelta(days=6)
        week_stats = await self.plan_repo.get_week_trade_stats(
            account_id, review.week_start, week_end
        )

        review = await self.plan_repo.update_weekly_review(
            review_id, account_id,
            trades_taken=week_stats["trades_taken"],
            trades_won=week_stats["trades_won"],
            weekly_pnl=week_stats["weekly_pnl"],
        )
        return self._review_to_dict(review)

    async def delete_weekly_review(self, account_id: int, user_id: int,
                                    review_id: int) -> bool:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return False
        return await self.plan_repo.delete_weekly_review(review_id, account_id)

    @staticmethod
    def _review_to_dict(review) -> dict:
        win_rate = 0
        if review.trades_taken > 0:
            win_rate = round(review.trades_won / review.trades_taken * 100, 1)
        return {
            "id": review.id,
            "account_id": review.account_id,
            "week_start": review.week_start.isoformat(),
            "what_went_well": review.what_went_well,
            "what_went_wrong": review.what_went_wrong,
            "key_adjustments": review.key_adjustments,
            "trades_taken": review.trades_taken,
            "trades_won": review.trades_won,
            "weekly_pnl": review.weekly_pnl,
            "win_rate": win_rate,
            "created_at": review.created_at.isoformat() if review.created_at else None,
            "updated_at": review.updated_at.isoformat() if review.updated_at else None,
        }
