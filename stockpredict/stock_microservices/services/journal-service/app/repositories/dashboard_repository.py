"""Dashboard Repository — Aggregation Queries for Journal Dashboard"""
from typing import Optional, List
from datetime import date
from sqlalchemy import select, func, and_, case, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import (
    Trade, TradeStatus, TradeDirection, EquitySnapshot, Account
)


class DashboardRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Trade Statistics
    # =========================================================================

    async def get_trade_stats(self, account_id: int) -> dict:
        """Aggregate trade statistics for closed trades"""
        # Base query: closed trades only
        base = and_(Trade.account_id == account_id, Trade.status == TradeStatus.CLOSED)

        result = await self.session.execute(
            select(
                func.count(Trade.id).label("total_closed"),
                func.min(Trade.entry_date).label("first_trade_date"),
                func.max(Trade.exit_date).label("last_trade_date"),
            ).where(base)
        )
        row = result.one()
        total_closed = row.total_closed or 0

        if total_closed == 0:
            return {
                "total_closed": 0,
                "total_open": 0,
                "first_trade_date": None,
                "last_trade_date": None,
            }

        # Count open trades
        open_result = await self.session.execute(
            select(func.count(Trade.id)).where(
                and_(Trade.account_id == account_id, Trade.status == TradeStatus.OPEN)
            )
        )
        total_open = open_result.scalar() or 0

        return {
            "total_closed": total_closed,
            "total_open": total_open,
            "first_trade_date": row.first_trade_date,
            "last_trade_date": row.last_trade_date,
        }

    async def get_closed_trades(self, account_id: int) -> List[Trade]:
        """Get all closed trades for P/L computation"""
        result = await self.session.execute(
            select(Trade)
            .where(and_(Trade.account_id == account_id, Trade.status == TradeStatus.CLOSED))
            .order_by(Trade.exit_date, Trade.trade_number)
        )
        return list(result.scalars().all())

    async def get_all_trades(self, account_id: int) -> List[Trade]:
        """Get all trades for comprehensive analysis"""
        result = await self.session.execute(
            select(Trade)
            .where(Trade.account_id == account_id)
            .order_by(Trade.entry_date, Trade.trade_number)
        )
        return list(result.scalars().all())

    # =========================================================================
    # Equity Snapshots
    # =========================================================================

    async def get_equity_snapshots(self, account_id: int,
                                    limit: int = 365) -> List[EquitySnapshot]:
        result = await self.session.execute(
            select(EquitySnapshot)
            .where(EquitySnapshot.account_id == account_id)
            .order_by(EquitySnapshot.snapshot_date)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_equity_snapshot(self, account_id: int,
                                      snapshot_date: date,
                                      equity_value: float,
                                      open_trade_equity: float = 0.0) -> EquitySnapshot:
        snapshot = EquitySnapshot(
            account_id=account_id,
            snapshot_date=snapshot_date,
            equity_value=equity_value,
            open_trade_equity=open_trade_equity,
            total_equity=equity_value + open_trade_equity
        )
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_latest_snapshot(self, account_id: int) -> Optional[EquitySnapshot]:
        result = await self.session.execute(
            select(EquitySnapshot)
            .where(EquitySnapshot.account_id == account_id)
            .order_by(EquitySnapshot.snapshot_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
