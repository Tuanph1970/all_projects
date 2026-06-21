"""Portfolio Repository - Database Operations"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update, delete, and_, func, text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.domain import Portfolio, PortfolioHolding, Transaction, PriceAlert, TransactionType


class PortfolioRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # Portfolio Operations
    async def create_portfolio(self, user_id: int, name: str, description: Optional[str] = None, is_default: bool = False) -> Portfolio:
        portfolio = Portfolio(
            user_id=user_id,
            name=name,
            description=description,
            is_default=is_default
        )
        self.session.add(portfolio)
        await self.session.commit()
        await self.session.refresh(portfolio)
        return portfolio

    async def get_portfolio_by_id(self, portfolio_id: int, user_id: int) -> Optional[Portfolio]:
        result = await self.session.execute(
            select(Portfolio)
            .options(selectinload(Portfolio.holdings), selectinload(Portfolio.transactions))
            .where(and_(Portfolio.id == portfolio_id, Portfolio.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def get_portfolios_by_user(self, user_id: int) -> List[Portfolio]:
        result = await self.session.execute(
            select(Portfolio)
            .where(Portfolio.user_id == user_id)
            .order_by(Portfolio.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_default_portfolio(self, user_id: int) -> Optional[Portfolio]:
        # A user may end up with more than one is_default row (e.g. duplicate
        # get-or-create races); scalar_one_or_none() would raise MultipleResultsFound
        # and 500 every default-portfolio/watchlist call. Deterministically return the
        # oldest default instead so the endpoint is robust to duplicates.
        result = await self.session.execute(
            select(Portfolio)
            .where(and_(Portfolio.user_id == user_id, Portfolio.is_default == True))
            .order_by(Portfolio.created_at.asc(), Portfolio.id.asc())
            .limit(1)
        )
        return result.scalars().first()

    async def update_portfolio(self, portfolio_id: int, user_id: int, **kwargs) -> Optional[Portfolio]:
        kwargs["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(Portfolio)
            .where(and_(Portfolio.id == portfolio_id, Portfolio.user_id == user_id))
            .values(**kwargs)
        )
        await self.session.commit()
        return await self.get_portfolio_by_id(portfolio_id, user_id)

    async def delete_portfolio(self, portfolio_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            delete(Portfolio)
            .where(and_(Portfolio.id == portfolio_id, Portfolio.user_id == user_id))
        )
        await self.session.commit()
        return result.rowcount > 0

    # Holding Operations
    async def add_holding(self, portfolio_id: int, symbol: str, quantity: int = 0,
                         average_price: Optional[float] = None, is_watchlist_only: bool = False) -> PortfolioHolding:
        total_cost = (quantity * average_price) if average_price else 0
        holding = PortfolioHolding(
            portfolio_id=portfolio_id,
            symbol=symbol.upper(),
            quantity=quantity,
            average_price=average_price,
            total_cost=total_cost,
            is_watchlist_only=is_watchlist_only
        )
        self.session.add(holding)
        await self.session.commit()
        await self.session.refresh(holding)
        return holding

    async def get_holding(self, portfolio_id: int, symbol: str) -> Optional[PortfolioHolding]:
        result = await self.session.execute(
            select(PortfolioHolding)
            .where(and_(
                PortfolioHolding.portfolio_id == portfolio_id,
                PortfolioHolding.symbol == symbol.upper()
            ))
        )
        return result.scalar_one_or_none()

    async def get_holdings_by_portfolio(self, portfolio_id: int, watchlist_only: Optional[bool] = None) -> List[PortfolioHolding]:
        query = select(PortfolioHolding).where(PortfolioHolding.portfolio_id == portfolio_id)
        if watchlist_only is not None:
            query = query.where(PortfolioHolding.is_watchlist_only == watchlist_only)
        result = await self.session.execute(query.order_by(PortfolioHolding.symbol))
        return list(result.scalars().all())

    async def update_holding(self, holding_id: int, **kwargs) -> Optional[PortfolioHolding]:
        kwargs["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(PortfolioHolding)
            .where(PortfolioHolding.id == holding_id)
            .values(**kwargs)
        )
        await self.session.commit()
        result = await self.session.execute(
            select(PortfolioHolding).where(PortfolioHolding.id == holding_id)
        )
        return result.scalar_one_or_none()

    async def delete_holding(self, holding_id: int) -> bool:
        result = await self.session.execute(
            delete(PortfolioHolding).where(PortfolioHolding.id == holding_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def update_holding_prices(self, portfolio_id: int, price_data: dict) -> int:
        """Update current prices for holdings. price_data: {symbol: price}"""
        updated = 0
        holdings = await self.get_holdings_by_portfolio(portfolio_id, watchlist_only=False)
        for holding in holdings:
            if holding.symbol in price_data:
                current_price = price_data[holding.symbol]
                current_value = holding.quantity * current_price
                profit_loss = current_value - holding.total_cost
                profit_loss_percent = (profit_loss / holding.total_cost * 100) if holding.total_cost > 0 else 0
                await self.update_holding(
                    holding.id,
                    current_price=current_price,
                    current_value=current_value,
                    profit_loss=profit_loss,
                    profit_loss_percent=profit_loss_percent
                )
                updated += 1
        return updated

    # Transaction Operations
    async def create_transaction(self, portfolio_id: int, symbol: str, transaction_type: TransactionType,
                                quantity: int, price: float, fees: float = 0,
                                notes: Optional[str] = None, transaction_date: Optional[datetime] = None) -> Transaction:
        total_value = quantity * price
        transaction = Transaction(
            portfolio_id=portfolio_id,
            symbol=symbol.upper(),
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            total_value=total_value,
            fees=fees,
            notes=notes,
            transaction_date=transaction_date or datetime.utcnow()
        )
        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)
        return transaction

    async def get_transactions_by_portfolio(self, portfolio_id: int, symbol: Optional[str] = None,
                                           limit: int = 100, offset: int = 0) -> List[Transaction]:
        query = select(Transaction).where(Transaction.portfolio_id == portfolio_id)
        if symbol:
            query = query.where(Transaction.symbol == symbol.upper())
        query = query.order_by(Transaction.transaction_date.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        result = await self.session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def delete_transaction(self, transaction_id: int) -> bool:
        result = await self.session.execute(
            delete(Transaction).where(Transaction.id == transaction_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    # Price Alert Operations
    async def create_alert(self, user_id: int, symbol: str, alert_type,
                          target_price: Optional[float] = None, target_percent: Optional[float] = None,
                          notes: Optional[str] = None) -> PriceAlert:
        alert = PriceAlert(
            user_id=user_id,
            symbol=symbol.upper(),
            alert_type=alert_type,
            target_price=target_price,
            target_percent=target_percent,
            notes=notes
        )
        self.session.add(alert)
        await self.session.commit()
        await self.session.refresh(alert)
        return alert

    async def get_latest_prices_for_symbols(self, symbols: List[str]) -> dict:
        """
        Return {symbol: latest_close} for the given symbols by joining the
        stock-data-service tables (companies + stock_prices) that live in the
        same MySQL instance. Values are in the thousands-quote unit used by
        the Vietnamese board (e.g. 73.5 means 73,500 VND/share). Callers are
        responsible for converting to actual VND if needed.
        """
        if not symbols:
            return {}
        query = text("""
            SELECT c.symbol, s.close
            FROM companies c
            JOIN stock_prices s ON s.company_id = c.id
            WHERE c.symbol IN :symbols
              AND s.date = (
                SELECT MAX(date) FROM stock_prices WHERE company_id = c.id
              )
        """).bindparams(bindparam("symbols", expanding=True))
        result = await self.session.execute(query, {"symbols": symbols})
        return {row.symbol: float(row.close) for row in result if row.close is not None}

    async def get_alerts_by_user(self, user_id: int, active_only: bool = True) -> List[PriceAlert]:
        query = select(PriceAlert).where(PriceAlert.user_id == user_id)
        if active_only:
            query = query.where(PriceAlert.is_active == True)
        result = await self.session.execute(query.order_by(PriceAlert.created_at.desc()))
        return list(result.scalars().all())

    async def get_alert_by_id(self, alert_id: int, user_id: int) -> Optional[PriceAlert]:
        result = await self.session.execute(
            select(PriceAlert)
            .where(and_(PriceAlert.id == alert_id, PriceAlert.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def update_alert(self, alert_id: int, user_id: int, **kwargs) -> Optional[PriceAlert]:
        kwargs["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(PriceAlert)
            .where(and_(PriceAlert.id == alert_id, PriceAlert.user_id == user_id))
            .values(**kwargs)
        )
        await self.session.commit()
        return await self.get_alert_by_id(alert_id, user_id)

    async def trigger_alert(self, alert_id: int) -> bool:
        await self.session.execute(
            update(PriceAlert)
            .where(PriceAlert.id == alert_id)
            .values(is_triggered=True, triggered_at=datetime.utcnow())
        )
        await self.session.commit()
        return True

    async def delete_alert(self, alert_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            delete(PriceAlert)
            .where(and_(PriceAlert.id == alert_id, PriceAlert.user_id == user_id))
        )
        await self.session.commit()
        return result.rowcount > 0

    # Statistics
    async def get_portfolio_stats(self, portfolio_id: int) -> dict:
        holdings = await self.get_holdings_by_portfolio(portfolio_id, watchlist_only=False)
        total_invested = sum(h.total_cost for h in holdings)
        current_value = sum(h.current_value or 0 for h in holdings)
        total_profit_loss = current_value - total_invested
        profit_loss_percent = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0

        return {
            "total_holdings": len(holdings),
            "total_invested": total_invested,
            "current_value": current_value,
            "total_profit_loss": total_profit_loss,
            "profit_loss_percent": profit_loss_percent
        }
