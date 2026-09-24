"""Portfolio Service - Business Logic"""
import asyncio
import logging
from typing import Optional, List
from datetime import datetime
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories.portfolio_repository import PortfolioRepository
from app.models.domain import Portfolio, PortfolioHolding, Transaction, PriceAlert, TransactionType, AlertType
from app.models.schemas import (
    PortfolioCreate, PortfolioUpdate, PortfolioResponse, PortfolioWithHoldings, PortfolioSummary,
    HoldingCreate, HoldingUpdate, HoldingResponse,
    TransactionCreate, TransactionResponse,
    AlertCreate, AlertUpdate, AlertResponse,
    WatchlistAdd
)

settings = get_settings()
logger = logging.getLogger(__name__)


class PortfolioService:
    def __init__(self, session: AsyncSession):
        self.repo = PortfolioRepository(session)
        self.session = session

    # Portfolio Management
    async def create_portfolio(self, user_id: int, data: PortfolioCreate) -> PortfolioResponse:
        """Create a new portfolio for a user"""
        # If this is set as default, unset other defaults
        if data.is_default:
            existing_default = await self.repo.get_default_portfolio(user_id)
            if existing_default:
                await self.repo.update_portfolio(existing_default.id, user_id, is_default=False)

        portfolio = await self.repo.create_portfolio(
            user_id=user_id,
            name=data.name,
            description=data.description,
            is_default=data.is_default
        )
        return PortfolioResponse.model_validate(portfolio)

    async def get_portfolio(self, portfolio_id: int, user_id: int) -> Optional[PortfolioWithHoldings]:
        """Get portfolio with holdings and transactions"""
        portfolio = await self.repo.get_portfolio_by_id(portfolio_id, user_id)
        if not portfolio:
            return None
        return PortfolioWithHoldings.model_validate(portfolio)

    async def get_user_portfolios(self, user_id: int) -> List[PortfolioResponse]:
        """Get all portfolios for a user"""
        portfolios = await self.repo.get_portfolios_by_user(user_id)
        return [PortfolioResponse.model_validate(p) for p in portfolios]

    async def get_all_watched_symbols(self) -> List[str]:
        """Distinct owned+watched tickers across all users (news-service feed)."""
        return await self.repo.get_all_watched_symbols()

    async def get_or_create_default_portfolio(self, user_id: int) -> PortfolioResponse:
        """Get default portfolio or create one if it doesn't exist"""
        portfolio = await self.repo.get_default_portfolio(user_id)
        if not portfolio:
            portfolios = await self.repo.get_portfolios_by_user(user_id)
            if portfolios:
                portfolio = portfolios[0]
                await self.repo.update_portfolio(portfolio.id, user_id, is_default=True)
            else:
                portfolio = await self.repo.create_portfolio(
                    user_id=user_id,
                    name="Default Portfolio",
                    is_default=True
                )
        return PortfolioResponse.model_validate(portfolio)

    async def update_portfolio(self, portfolio_id: int, user_id: int, data: PortfolioUpdate) -> Optional[PortfolioResponse]:
        """Update portfolio details"""
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            portfolio = await self.repo.get_portfolio_by_id(portfolio_id, user_id)
            return PortfolioResponse.model_validate(portfolio) if portfolio else None

        if data.is_default:
            existing_default = await self.repo.get_default_portfolio(user_id)
            if existing_default and existing_default.id != portfolio_id:
                await self.repo.update_portfolio(existing_default.id, user_id, is_default=False)

        portfolio = await self.repo.update_portfolio(portfolio_id, user_id, **update_data)
        return PortfolioResponse.model_validate(portfolio) if portfolio else None

    async def delete_portfolio(self, portfolio_id: int, user_id: int) -> bool:
        """Delete a portfolio"""
        return await self.repo.delete_portfolio(portfolio_id, user_id)

    async def get_portfolio_summary(self, portfolio_id: int, user_id: int) -> Optional[PortfolioSummary]:
        """Get portfolio summary with statistics"""
        portfolio = await self.repo.get_portfolio_by_id(portfolio_id, user_id)
        if not portfolio:
            return None

        # Mark to market first. Nothing else drives refresh_prices — the
        # POST /refresh-prices route exists but no caller invokes it — so
        # without this the summary reports cost basis forever (Backlog #43).
        # Best-effort: a price-table outage degrades to cost basis rather
        # than failing the whole summary.
        try:
            await self.refresh_prices(portfolio_id, user_id)
        except Exception as e:
            logger.warning(f"Price refresh failed for portfolio {portfolio_id}: {e}")

        stats = await self.repo.get_portfolio_stats(portfolio_id)
        holdings = await self.repo.get_holdings_by_portfolio(portfolio_id, watchlist_only=False)

        # Sort for top/worst performers
        sorted_holdings = sorted(
            [h for h in holdings if h.profit_loss_percent is not None],
            key=lambda x: x.profit_loss_percent or 0,
            reverse=True
        )

        return PortfolioSummary(
            portfolio_id=portfolio.id,
            portfolio_name=portfolio.name,
            total_holdings=stats["total_holdings"],
            total_invested=stats["total_invested"],
            current_value=stats["current_value"],
            total_profit_loss=stats["total_profit_loss"],
            total_profit_loss_percent=stats["profit_loss_percent"],
            top_performers=[HoldingResponse.model_validate(h) for h in sorted_holdings[:3]],
            worst_performers=[HoldingResponse.model_validate(h) for h in sorted_holdings[-3:]]
        )

    # Holdings Management
    async def add_holding(self, portfolio_id: int, user_id: int, data: HoldingCreate) -> Optional[HoldingResponse]:
        """Add a stock to portfolio"""
        portfolio = await self.repo.get_portfolio_by_id(portfolio_id, user_id)
        if not portfolio:
            return None

        # Check if holding already exists
        existing = await self.repo.get_holding(portfolio_id, data.symbol)
        if existing:
            # Update existing holding
            new_quantity = existing.quantity + data.quantity
            if data.average_price and data.quantity > 0:
                new_total_cost = existing.total_cost + (data.quantity * data.average_price)
                new_avg_price = new_total_cost / new_quantity if new_quantity > 0 else 0
            else:
                new_total_cost = existing.total_cost
                new_avg_price = existing.average_price

            holding = await self.repo.update_holding(
                existing.id,
                quantity=new_quantity,
                average_price=new_avg_price,
                total_cost=new_total_cost,
                is_watchlist_only=data.is_watchlist_only
            )
        else:
            holding = await self.repo.add_holding(
                portfolio_id=portfolio_id,
                symbol=data.symbol,
                quantity=data.quantity,
                average_price=data.average_price,
                is_watchlist_only=data.is_watchlist_only
            )

        # Fire-and-forget: trigger stock-data-service to ensure company exists and sync historical data
        asyncio.create_task(self._trigger_ensure_and_sync(data.symbol))

        return HoldingResponse.model_validate(holding) if holding else None

    async def add_to_watchlist(
        self, portfolio_id: int, user_id: int, data: WatchlistAdd
    ) -> Optional[HoldingResponse]:
        """Put a symbol on the watchlist, carrying an optional proposal.

        Deliberately not `add_holding`: that method merges quantities and rewrites
        `is_watchlist_only` from its input, so pushing a broker recommendation for a
        stock the user actually owns would demote the position to watchlist-only and
        drop it out of the holdings screen. Here an existing row keeps its quantity and
        its watchlist flag untouched — only the proposal columns are refreshed, which is
        exactly what a new call on a symbol you already hold should do.
        """
        portfolio = await self.repo.get_portfolio_by_id(portfolio_id, user_id)
        if not portfolio:
            return None

        proposal = {
            "proposal_by": data.proposal_by,
            "proposal_action": data.proposal_action,
            "proposal_label": data.proposal_label,
            "proposal_date": data.proposal_date,
            "proposal_note": data.proposal_note,
        }
        supplied = {k: v for k, v in proposal.items() if v is not None}

        existing = await self.repo.get_holding(portfolio_id, data.symbol)
        if existing:
            holding = (
                await self.repo.update_holding(existing.id, **supplied)
                if supplied else existing
            )
        else:
            holding = await self.repo.add_holding(
                portfolio_id=portfolio_id,
                symbol=data.symbol,
                quantity=0,
                is_watchlist_only=True,
                **supplied,
            )

        # Fire-and-forget: make sure the company exists and its history is synced.
        asyncio.create_task(self._trigger_ensure_and_sync(data.symbol))

        return HoldingResponse.model_validate(holding) if holding else None

    async def get_holdings(self, portfolio_id: int, user_id: int, watchlist_only: Optional[bool] = None) -> List[HoldingResponse]:
        """Get all holdings in a portfolio"""
        portfolio = await self.repo.get_portfolio_by_id(portfolio_id, user_id)
        if not portfolio:
            return []

        holdings = await self.repo.get_holdings_by_portfolio(portfolio_id, watchlist_only)
        return [HoldingResponse.model_validate(h) for h in holdings]

    async def update_holding(self, portfolio_id: int, user_id: int, symbol: str, data: HoldingUpdate) -> Optional[HoldingResponse]:
        """Update holding details"""
        portfolio = await self.repo.get_portfolio_by_id(portfolio_id, user_id)
        if not portfolio:
            return None

        holding = await self.repo.get_holding(portfolio_id, symbol)
        if not holding:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "quantity" in update_data and "average_price" in update_data:
            update_data["total_cost"] = update_data["quantity"] * update_data["average_price"]
        elif "quantity" in update_data and holding.average_price:
            update_data["total_cost"] = update_data["quantity"] * holding.average_price

        updated = await self.repo.update_holding(holding.id, **update_data)
        return HoldingResponse.model_validate(updated) if updated else None

    async def remove_holding(self, portfolio_id: int, user_id: int, symbol: str) -> bool:
        """Remove a stock from portfolio"""
        portfolio = await self.repo.get_portfolio_by_id(portfolio_id, user_id)
        if not portfolio:
            return False

        holding = await self.repo.get_holding(portfolio_id, symbol)
        if not holding:
            return False

        return await self.repo.delete_holding(holding.id)

    async def refresh_prices(self, portfolio_id: int, user_id: int) -> int:
        """Mark holdings to the latest close stored for each symbol.

        Reads the stock-data-service tables (companies + stock_prices) that
        share this MySQL instance rather than calling over HTTP: the previous
        implementation POSTed to /stocks/quotes, an endpoint stock-data-service
        does not expose, so every refresh 404'd, was swallowed, and left
        current_price/current_value NULL on every holding.

        Unit contract — get_latest_prices_for_symbols returns the Vietnamese
        thousands-quote (12.75 means 12,750 VND/share) while holdings store
        average_price and total_cost in actual VND, so scale by 1000. This is
        the same conversion get_alerts applies to target_price.

        Returns the number of holdings repriced.
        """
        portfolio = await self.repo.get_portfolio_by_id(portfolio_id, user_id)
        if not portfolio:
            return 0

        holdings = await self.repo.get_holdings_by_portfolio(portfolio_id, watchlist_only=False)
        if not holdings:
            return 0

        symbols = sorted({h.symbol for h in holdings})
        quotes = await self.repo.get_latest_prices_for_symbols(symbols)
        if not quotes:
            # No price history for these symbols yet. Leave current_value NULL
            # so get_portfolio_stats falls back to cost basis; writing 0 here
            # would report the portfolio as a total loss.
            return 0

        price_data = {symbol: close * 1000 for symbol, close in quotes.items()}
        return await self.repo.update_holding_prices(portfolio_id, price_data)

    # Transaction Management
    async def record_transaction(self, portfolio_id: int, user_id: int, data: TransactionCreate) -> Optional[TransactionResponse]:
        """Record a buy/sell transaction and update holdings"""
        portfolio = await self.repo.get_portfolio_by_id(portfolio_id, user_id)
        if not portfolio:
            return None

        # Create transaction - use helper method to get transaction type from either field
        tx_type = TransactionType(data.get_transaction_type().value)
        transaction = await self.repo.create_transaction(
            portfolio_id=portfolio_id,
            symbol=data.symbol,
            transaction_type=tx_type,
            quantity=data.quantity,
            price=data.price,
            fees=data.fees,
            notes=data.notes,
            transaction_date=data.transaction_date
        )

        # Update holding
        holding = await self.repo.get_holding(portfolio_id, data.symbol)

        if tx_type == TransactionType.BUY:
            if holding:
                new_quantity = holding.quantity + data.quantity
                new_total_cost = holding.total_cost + (data.quantity * data.price) + data.fees
                new_avg_price = new_total_cost / new_quantity if new_quantity > 0 else 0
                await self.repo.update_holding(
                    holding.id,
                    quantity=new_quantity,
                    average_price=new_avg_price,
                    total_cost=new_total_cost
                )
            else:
                total_cost = (data.quantity * data.price) + data.fees
                await self.repo.add_holding(
                    portfolio_id=portfolio_id,
                    symbol=data.symbol,
                    quantity=data.quantity,
                    average_price=total_cost / data.quantity
                )
        elif tx_type == TransactionType.SELL:
            if holding:
                new_quantity = max(0, holding.quantity - data.quantity)
                if new_quantity == 0:
                    await self.repo.delete_holding(holding.id)
                else:
                    new_total_cost = new_quantity * holding.average_price if holding.average_price else 0
                    await self.repo.update_holding(
                        holding.id,
                        quantity=new_quantity,
                        total_cost=new_total_cost
                    )

        # Fire-and-forget: trigger stock-data-service to ensure company exists and sync historical data
        if tx_type == TransactionType.BUY:
            asyncio.create_task(self._trigger_ensure_and_sync(data.symbol))

        return TransactionResponse.model_validate(transaction)

    async def get_transactions(self, portfolio_id: int, user_id: int,
                              symbol: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[TransactionResponse]:
        """Get transaction history"""
        portfolio = await self.repo.get_portfolio_by_id(portfolio_id, user_id)
        if not portfolio:
            return []

        transactions = await self.repo.get_transactions_by_portfolio(portfolio_id, symbol, limit, offset)
        return [TransactionResponse.model_validate(t) for t in transactions]

    async def delete_transaction(self, portfolio_id: int, user_id: int, transaction_id: int) -> bool:
        """Delete a transaction (doesn't reverse holding changes)"""
        portfolio = await self.repo.get_portfolio_by_id(portfolio_id, user_id)
        if not portfolio:
            return False

        transaction = await self.repo.get_transaction_by_id(transaction_id)
        if not transaction or transaction.portfolio_id != portfolio_id:
            return False

        return await self.repo.delete_transaction(transaction_id)

    # Price Alerts
    async def create_alert(self, user_id: int, data: AlertCreate) -> AlertResponse:
        """Create a price alert - use helper method to get alert type from either field"""
        alert_type = AlertType(data.get_alert_type().value)
        alert = await self.repo.create_alert(
            user_id=user_id,
            symbol=data.symbol,
            alert_type=alert_type,
            target_price=data.target_price,
            target_percent=data.target_percent,
            notes=data.notes
        )
        return AlertResponse.model_validate(alert)

    async def get_alerts(self, user_id: int, active_only: bool = True) -> List[AlertResponse]:
        """Get user's price alerts, enriched with each symbol's latest close.

        The stock_prices table stores prices in the Vietnamese thousands-quote
        unit (e.g. 73.5 for 73,500 VND/share). User-entered target_price is in
        actual VND, so we multiply by 1000 here to keep both columns on the
        same axis in the UI.
        """
        alerts = await self.repo.get_alerts_by_user(user_id, active_only)
        if not alerts:
            return []

        symbols = list({a.symbol for a in alerts})
        latest_prices = await self.repo.get_latest_prices_for_symbols(symbols)

        responses: List[AlertResponse] = []
        for a in alerts:
            resp = AlertResponse.model_validate(a)
            quote = latest_prices.get(a.symbol)
            resp.current_price = quote * 1000 if quote is not None else None
            responses.append(resp)
        return responses

    async def update_alert(self, alert_id: int, user_id: int, data: AlertUpdate) -> Optional[AlertResponse]:
        """Update a price alert"""
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            alert = await self.repo.get_alert_by_id(alert_id, user_id)
            return AlertResponse.model_validate(alert) if alert else None

        alert = await self.repo.update_alert(alert_id, user_id, **update_data)
        return AlertResponse.model_validate(alert) if alert else None

    async def delete_alert(self, alert_id: int, user_id: int) -> bool:
        """Delete a price alert"""
        return await self.repo.delete_alert(alert_id, user_id)

    async def _trigger_ensure_and_sync(self, symbol: str) -> None:
        """Background task: trigger stock-data-service to ensure company exists and sync data."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/stocks/{symbol}/ensure-and-sync",
                    timeout=120.0,
                )
                logger.info(f"Triggered ensure-and-sync for {symbol}")
        except Exception as e:
            logger.warning(f"Failed to trigger ensure-and-sync for {symbol}: {e}")

    async def check_alerts(self, user_id: int, price_data: dict) -> List[AlertResponse]:
        """Check and trigger alerts based on current prices.

        Unit contract — IMPORTANT:
            price_data values MUST be in the same unit as alert.target_price,
            which is whatever the user typed into the Add-Alert form (actual
            VND in the current UI — e.g. 73900, not 73.9).

            Two upstream Vietcap feeds carry different units:
              * tbl_price_board.match_price → actual VND  (USE THIS)
              * stock_prices.close          → thousands-quote (multiply by
                1000 before passing in)

        Not invoked in production today; the live alert path is the
        event-driven `_handle_price_update` in alert_event_handler.py, which
        subscribes to stock.price.updated events sourced from the priceboard
        (already in actual VND).
        """
        alerts = await self.repo.get_alerts_by_user(user_id, active_only=True)
        triggered = []

        for alert in alerts:
            if alert.symbol not in price_data:
                continue

            current_price = price_data[alert.symbol]
            should_trigger = False

            if alert.alert_type == AlertType.ABOVE and alert.target_price:
                should_trigger = current_price >= alert.target_price
            elif alert.alert_type == AlertType.BELOW and alert.target_price:
                should_trigger = current_price <= alert.target_price

            if should_trigger:
                await self.repo.trigger_alert(alert.id)
                await self.repo.update_alert(alert.id, user_id, is_active=False)
                triggered.append(AlertResponse.model_validate(alert))

        return triggered
