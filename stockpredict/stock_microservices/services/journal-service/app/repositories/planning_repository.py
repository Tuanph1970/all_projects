"""Planning Repository — Daily Plans & Weekly Reviews CRUD"""
from typing import Optional, List
from datetime import date
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import DailyPlan, WeeklyReview, Trade, TradeStatus


class PlanningRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Daily Plans
    # =========================================================================

    async def get_daily_plans(self, account_id: int,
                              limit: int = 30, offset: int = 0) -> List[DailyPlan]:
        result = await self.session.execute(
            select(DailyPlan)
            .where(DailyPlan.account_id == account_id)
            .order_by(DailyPlan.plan_date.desc())
            .offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def get_daily_plan_by_id(self, plan_id: int,
                                    account_id: int) -> Optional[DailyPlan]:
        result = await self.session.execute(
            select(DailyPlan).where(
                and_(DailyPlan.id == plan_id, DailyPlan.account_id == account_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_daily_plan_by_date(self, account_id: int,
                                      plan_date: date) -> Optional[DailyPlan]:
        result = await self.session.execute(
            select(DailyPlan).where(
                and_(DailyPlan.account_id == account_id,
                     DailyPlan.plan_date == plan_date)
            )
        )
        return result.scalar_one_or_none()

    async def create_daily_plan(self, account_id: int, plan_date: date,
                                 market_review: str = None,
                                 new_trade_ideas: str = None,
                                 stop_objective_updates: str = None,
                                 emotional_checkin: str = None) -> DailyPlan:
        plan = DailyPlan(
            account_id=account_id,
            plan_date=plan_date,
            market_review=market_review,
            new_trade_ideas=new_trade_ideas,
            stop_objective_updates=stop_objective_updates,
            emotional_checkin=emotional_checkin,
        )
        self.session.add(plan)
        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def update_daily_plan(self, plan_id: int, account_id: int,
                                 **kwargs) -> Optional[DailyPlan]:
        plan = await self.get_daily_plan_by_id(plan_id, account_id)
        if not plan:
            return None
        for key, value in kwargs.items():
            if hasattr(plan, key):
                setattr(plan, key, value)
        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def delete_daily_plan(self, plan_id: int, account_id: int) -> bool:
        plan = await self.get_daily_plan_by_id(plan_id, account_id)
        if not plan:
            return False
        await self.session.delete(plan)
        await self.session.commit()
        return True

    # =========================================================================
    # Weekly Reviews
    # =========================================================================

    async def get_weekly_reviews(self, account_id: int,
                                  limit: int = 20, offset: int = 0) -> List[WeeklyReview]:
        result = await self.session.execute(
            select(WeeklyReview)
            .where(WeeklyReview.account_id == account_id)
            .order_by(WeeklyReview.week_start.desc())
            .offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def get_weekly_review_by_id(self, review_id: int,
                                       account_id: int) -> Optional[WeeklyReview]:
        result = await self.session.execute(
            select(WeeklyReview).where(
                and_(WeeklyReview.id == review_id,
                     WeeklyReview.account_id == account_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_weekly_review_by_week(self, account_id: int,
                                         week_start: date) -> Optional[WeeklyReview]:
        result = await self.session.execute(
            select(WeeklyReview).where(
                and_(WeeklyReview.account_id == account_id,
                     WeeklyReview.week_start == week_start)
            )
        )
        return result.scalar_one_or_none()

    async def create_weekly_review(self, account_id: int, week_start: date,
                                    what_went_well: str = None,
                                    what_went_wrong: str = None,
                                    key_adjustments: str = None,
                                    trades_taken: int = 0,
                                    trades_won: int = 0,
                                    weekly_pnl: float = 0.0) -> WeeklyReview:
        review = WeeklyReview(
            account_id=account_id,
            week_start=week_start,
            what_went_well=what_went_well,
            what_went_wrong=what_went_wrong,
            key_adjustments=key_adjustments,
            trades_taken=trades_taken,
            trades_won=trades_won,
            weekly_pnl=weekly_pnl,
        )
        self.session.add(review)
        await self.session.commit()
        await self.session.refresh(review)
        return review

    async def update_weekly_review(self, review_id: int, account_id: int,
                                    **kwargs) -> Optional[WeeklyReview]:
        review = await self.get_weekly_review_by_id(review_id, account_id)
        if not review:
            return None
        for key, value in kwargs.items():
            if hasattr(review, key):
                setattr(review, key, value)
        await self.session.commit()
        await self.session.refresh(review)
        return review

    async def delete_weekly_review(self, review_id: int, account_id: int) -> bool:
        review = await self.get_weekly_review_by_id(review_id, account_id)
        if not review:
            return False
        await self.session.delete(review)
        await self.session.commit()
        return True

    # =========================================================================
    # Weekly Stats Helpers
    # =========================================================================

    async def get_week_trade_stats(self, account_id: int,
                                    week_start: date, week_end: date) -> dict:
        """Get trade statistics for a specific week (closed trades by exit_date)"""
        base = and_(
            Trade.account_id == account_id,
            Trade.status == TradeStatus.CLOSED,
            Trade.exit_date >= week_start,
            Trade.exit_date <= week_end,
        )
        result = await self.session.execute(
            select(Trade).where(base)
        )
        trades = list(result.scalars().all())

        trades_taken = len(trades)
        trades_won = 0
        weekly_pnl = 0.0

        for t in trades:
            if t.exit_price is not None:
                if t.direction.value == "Long":
                    pnl = (t.exit_price - t.entry_price) * t.position_size - t.commission
                else:
                    pnl = (t.entry_price - t.exit_price) * t.position_size - t.commission
                weekly_pnl += pnl
                if pnl > 0:
                    trades_won += 1

        return {
            "trades_taken": trades_taken,
            "trades_won": trades_won,
            "weekly_pnl": round(weekly_pnl, 2),
        }
