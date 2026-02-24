"""Trade Repository — Database Operations for Trades & Stop Revisions"""
from typing import Optional, List
from datetime import datetime, date
from sqlalchemy import select, update, delete, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.domain import Trade, StopRevision, TradeStatus, TradeDirection


class TradeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Trade Operations
    # =========================================================================

    async def get_next_trade_number(self, account_id: int) -> int:
        """Get next sequential trade number for an account"""
        result = await self.session.execute(
            select(func.coalesce(func.max(Trade.trade_number), 0))
            .where(Trade.account_id == account_id)
        )
        return result.scalar() + 1

    async def create_trade(self, account_id: int, trade_number: int,
                           entry_date: date, market_ticker: str,
                           direction: TradeDirection, entry_price: float,
                           entry_type, initial_stop: float,
                           position_size: float, commission: float = 0.0,
                           objective_1: Optional[float] = None,
                           objective_2: Optional[float] = None,
                           entry_reason: Optional[str] = None) -> Trade:
        trade = Trade(
            account_id=account_id,
            trade_number=trade_number,
            entry_date=entry_date,
            market_ticker=market_ticker.upper(),
            direction=direction,
            entry_price=entry_price,
            entry_type=entry_type,
            initial_stop=initial_stop,
            position_size=position_size,
            commission=commission,
            objective_1=objective_1,
            objective_2=objective_2,
            entry_reason=entry_reason,
            status=TradeStatus.OPEN
        )
        self.session.add(trade)
        await self.session.commit()
        await self.session.refresh(trade)
        return trade

    async def get_trade_by_id(self, trade_id: int, account_id: int) -> Optional[Trade]:
        result = await self.session.execute(
            select(Trade)
            .options(selectinload(Trade.stop_revisions))
            .where(and_(Trade.id == trade_id, Trade.account_id == account_id))
        )
        return result.scalar_one_or_none()

    async def get_trade_by_id_no_account(self, trade_id: int) -> Optional[Trade]:
        """Get trade by ID without account filter (for diary ownership verification)"""
        result = await self.session.execute(
            select(Trade).where(Trade.id == trade_id)
        )
        return result.scalar_one_or_none()

    async def get_trades_by_account(self, account_id: int,
                                     status: Optional[TradeStatus] = None,
                                     ticker: Optional[str] = None,
                                     direction: Optional[TradeDirection] = None,
                                     limit: int = 100, offset: int = 0) -> List[Trade]:
        query = (
            select(Trade)
            .options(selectinload(Trade.stop_revisions))
            .where(Trade.account_id == account_id)
        )
        if status:
            query = query.where(Trade.status == status)
        if ticker:
            query = query.where(Trade.market_ticker == ticker.upper())
        if direction:
            query = query.where(Trade.direction == direction)

        query = query.order_by(Trade.trade_number.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_open_trades(self, account_id: int) -> List[Trade]:
        """Get all open trades for risk calculation"""
        result = await self.session.execute(
            select(Trade)
            .where(and_(Trade.account_id == account_id, Trade.status == TradeStatus.OPEN))
            .order_by(Trade.trade_number)
        )
        return list(result.scalars().all())

    async def count_trades(self, account_id: int, status: Optional[TradeStatus] = None) -> int:
        query = select(func.count(Trade.id)).where(Trade.account_id == account_id)
        if status:
            query = query.where(Trade.status == status)
        result = await self.session.execute(query)
        return result.scalar()

    async def update_trade(self, trade_id: int, account_id: int, **kwargs) -> Optional[Trade]:
        kwargs["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(Trade)
            .where(and_(Trade.id == trade_id, Trade.account_id == account_id))
            .values(**kwargs)
        )
        await self.session.commit()
        return await self.get_trade_by_id(trade_id, account_id)

    async def delete_trade(self, trade_id: int, account_id: int) -> bool:
        result = await self.session.execute(
            delete(Trade)
            .where(and_(Trade.id == trade_id, Trade.account_id == account_id))
        )
        await self.session.commit()
        return result.rowcount > 0

    # =========================================================================
    # Stop Revision Operations
    # =========================================================================

    async def create_stop_revision(self, trade_id: int, previous_stop: float,
                                    new_stop: float, reason: Optional[str] = None) -> StopRevision:
        revision = StopRevision(
            trade_id=trade_id,
            previous_stop=previous_stop,
            new_stop=new_stop,
            reason=reason
        )
        self.session.add(revision)
        await self.session.commit()
        await self.session.refresh(revision)
        return revision

    async def get_stop_revisions(self, trade_id: int) -> List[StopRevision]:
        result = await self.session.execute(
            select(StopRevision)
            .where(StopRevision.trade_id == trade_id)
            .order_by(StopRevision.revised_at.desc())
        )
        return list(result.scalars().all())
