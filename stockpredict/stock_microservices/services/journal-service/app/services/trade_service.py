"""Trade Service — Business Logic with Schwager's Risk Rules"""
from typing import Optional, List
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.trade_repository import TradeRepository
from app.repositories.account_repository import AccountRepository
from app.models.domain import Trade, Account, TradeDirection, TradeStatus
from app.models.schemas import TradeCreate, TradeUpdate, StopRevisionCreate


class TradeService:
    def __init__(self, session: AsyncSession):
        self.trade_repo = TradeRepository(session)
        self.account_repo = AccountRepository(session)

    # =========================================================================
    # Risk Calculation Helpers (computed, never stored)
    # =========================================================================

    @staticmethod
    def calc_risk_amount(trade: Trade) -> float:
        """Risk per trade = |Entry Price - Initial Stop| x Position Size"""
        return abs(trade.entry_price - trade.initial_stop) * trade.position_size

    @staticmethod
    def calc_risk_percent(trade: Trade, equity: float) -> float:
        """Risk % = Risk per trade / Account equity"""
        if equity <= 0:
            return 0.0
        risk = abs(trade.entry_price - trade.initial_stop) * trade.position_size
        return (risk / equity) * 100

    @staticmethod
    def calc_net_pnl(trade: Trade) -> Optional[float]:
        """Net P/L: Long = (Exit - Entry) x Size - Commission; Short = (Entry - Exit) x Size - Commission"""
        if trade.exit_price is None:
            return None
        if trade.direction == TradeDirection.LONG:
            return (trade.exit_price - trade.entry_price) * trade.position_size - trade.commission
        else:
            return (trade.entry_price - trade.exit_price) * trade.position_size - trade.commission

    @staticmethod
    def calc_r_multiple(trade: Trade) -> Optional[float]:
        """R-Multiple = Net P/L / Risk per trade"""
        pnl = TradeService.calc_net_pnl(trade)
        if pnl is None:
            return None
        risk = abs(trade.entry_price - trade.initial_stop) * trade.position_size
        if risk == 0:
            return None
        return pnl / risk

    @staticmethod
    def calc_duration(trade: Trade) -> Optional[int]:
        """Duration = Exit Date - Entry Date in days"""
        if trade.exit_date is None:
            return None
        return (trade.exit_date - trade.entry_date).days

    def enrich_trade(self, trade: Trade, equity: float) -> dict:
        """Add computed fields to trade for API response"""
        trade_dict = {
            "id": trade.id,
            "account_id": trade.account_id,
            "trade_number": trade.trade_number,
            "entry_date": trade.entry_date,
            "market_ticker": trade.market_ticker,
            "direction": trade.direction,
            "entry_price": trade.entry_price,
            "entry_type": trade.entry_type,
            "initial_stop": trade.initial_stop,
            "revised_stop": trade.revised_stop,
            "position_size": trade.position_size,
            "commission": trade.commission,
            "objective_1": trade.objective_1,
            "objective_2": trade.objective_2,
            "exit_date": trade.exit_date,
            "exit_price": trade.exit_price,
            "status": trade.status,
            "entry_reason": trade.entry_reason,
            "exit_reason": trade.exit_reason,
            "lessons_learned": trade.lessons_learned,
            "created_at": trade.created_at,
            "updated_at": trade.updated_at,
            # Computed fields
            "risk_amount": self.calc_risk_amount(trade),
            "risk_percent": self.calc_risk_percent(trade, equity),
            "net_pnl": self.calc_net_pnl(trade),
            "r_multiple": self.calc_r_multiple(trade),
            "duration_days": self.calc_duration(trade),
        }
        return trade_dict

    # =========================================================================
    # Risk Warning Logic
    # =========================================================================

    async def get_cumulative_risk(self, account_id: int, equity: float) -> dict:
        """Calculate cumulative risk from all open trades"""
        open_trades = await self.trade_repo.get_open_trades(account_id)
        total_risk = 0.0
        for t in open_trades:
            total_risk += self.calc_risk_amount(t)

        cumulative_percent = (total_risk / equity * 100) if equity > 0 else 0.0
        return {
            "open_trade_count": len(open_trades),
            "total_risk_amount": total_risk,
            "cumulative_risk_percent": round(cumulative_percent, 2)
        }

    def get_risk_warnings(self, risk_percent: float, cumulative_percent: float,
                          max_per_trade: float, max_cumulative: float) -> list:
        """Generate risk warning messages"""
        warnings = []
        if risk_percent > max_per_trade:
            warnings.append({
                "level": "warning",
                "message": f"Rủi ro lệnh ({risk_percent:.1f}%) vượt giới hạn ({max_per_trade}%)"
            })
        # Yellow warning at the configured cumulative threshold
        if cumulative_percent > max_cumulative:
            warnings.append({
                "level": "danger",
                "message": f"Rủi ro tích lũy ({cumulative_percent:.1f}%) vượt giới hạn ({max_cumulative}%). Không nên mở lệnh mới!"
            })
        elif cumulative_percent > max_cumulative * 0.7:
            warnings.append({
                "level": "caution",
                "message": f"Rủi ro tích lũy ({cumulative_percent:.1f}%) đang tiến gần giới hạn ({max_cumulative}%)"
            })
        return warnings

    # =========================================================================
    # Stop Revision Validation (Schwager's rule: only tighten stops)
    # =========================================================================

    @staticmethod
    def validate_stop_revision(trade: Trade, new_stop: float) -> Optional[str]:
        """Stops may ONLY be revised to reduce risk.
        Long: new stop >= current stop. Short: new stop <= current stop."""
        current_stop = trade.revised_stop if trade.revised_stop else trade.initial_stop
        if trade.direction == TradeDirection.LONG:
            if new_stop < current_stop:
                return f"Long trade: stop mới ({new_stop}) phải >= stop hiện tại ({current_stop}). Chỉ được thắt chặt stop."
        else:
            if new_stop > current_stop:
                return f"Short trade: stop mới ({new_stop}) phải <= stop hiện tại ({current_stop}). Chỉ được thắt chặt stop."
        return None

    # =========================================================================
    # Trade CRUD Operations
    # =========================================================================

    async def create_trade(self, account_id: int, user_id: int,
                           data: TradeCreate) -> Optional[dict]:
        """Create trade with auto-numbering and risk checks"""
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None

        # Get risk info for warnings
        cum_risk = await self.get_cumulative_risk(account_id, account.current_equity)

        # Calculate this trade's risk
        trade_risk = abs(data.entry_price - data.initial_stop) * data.position_size
        trade_risk_pct = (trade_risk / account.current_equity * 100) if account.current_equity > 0 else 0

        new_cumulative = cum_risk["cumulative_risk_percent"] + trade_risk_pct

        # Block if cumulative risk exceeds hard limit (max_cumulative_risk * 1.4 = ~35% default)
        block_threshold = account.max_cumulative_risk * 1.4
        if new_cumulative > block_threshold:
            return {
                "error": True,
                "message": f"Rủi ro tích lũy sẽ đạt {new_cumulative:.1f}%, vượt ngưỡng chặn {block_threshold:.0f}%. Không thể mở lệnh mới.",
                "cumulative_risk": cum_risk
            }

        trade_number = await self.trade_repo.get_next_trade_number(account_id)
        trade = await self.trade_repo.create_trade(
            account_id=account_id,
            trade_number=trade_number,
            entry_date=data.entry_date,
            market_ticker=data.market_ticker,
            direction=data.direction,
            entry_price=data.entry_price,
            entry_type=data.entry_type,
            initial_stop=data.initial_stop,
            position_size=data.position_size,
            commission=data.commission,
            objective_1=data.objective_1,
            objective_2=data.objective_2,
            entry_reason=data.entry_reason
        )

        result = self.enrich_trade(trade, account.current_equity)
        # Attach warnings
        warnings = self.get_risk_warnings(
            trade_risk_pct, new_cumulative,
            account.max_risk_per_trade, account.max_cumulative_risk
        )
        result["warnings"] = warnings
        result["cumulative_risk"] = {
            "open_trade_count": cum_risk["open_trade_count"] + 1,
            "total_risk_amount": cum_risk["total_risk_amount"] + trade_risk,
            "cumulative_risk_percent": round(new_cumulative, 2)
        }
        return result

    async def get_trades(self, account_id: int, user_id: int,
                         status: Optional[str] = None,
                         ticker: Optional[str] = None,
                         direction: Optional[str] = None,
                         limit: int = 100, offset: int = 0) -> Optional[dict]:
        """Get trades with computed fields and cumulative risk"""
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None

        status_enum = TradeStatus(status) if status else None
        direction_enum = TradeDirection(direction) if direction else None

        trades = await self.trade_repo.get_trades_by_account(
            account_id, status=status_enum, ticker=ticker,
            direction=direction_enum, limit=limit, offset=offset
        )
        total = await self.trade_repo.count_trades(account_id, status=status_enum)
        cum_risk = await self.get_cumulative_risk(account_id, account.current_equity)

        enriched = [self.enrich_trade(t, account.current_equity) for t in trades]
        return {
            "trades": enriched,
            "total": total,
            "cumulative_risk": cum_risk,
            "account_equity": account.current_equity
        }

    async def get_trade(self, account_id: int, user_id: int,
                        trade_id: int) -> Optional[dict]:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        trade = await self.trade_repo.get_trade_by_id(trade_id, account_id)
        if not trade:
            return None
        return self.enrich_trade(trade, account.current_equity)

    async def update_trade(self, account_id: int, user_id: int,
                           trade_id: int, data: TradeUpdate) -> Optional[dict]:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            trade = await self.trade_repo.get_trade_by_id(trade_id, account_id)
            if not trade:
                return None
            return self.enrich_trade(trade, account.current_equity)

        # If closing trade, ensure exit fields are present
        if update_data.get("status") == TradeStatus.CLOSED:
            trade = await self.trade_repo.get_trade_by_id(trade_id, account_id)
            if not trade:
                return None
            if not update_data.get("exit_price") and not trade.exit_price:
                return {"error": True, "message": "Phải có giá thoát khi đóng lệnh"}
            if not update_data.get("exit_date") and not trade.exit_date:
                update_data["exit_date"] = date.today()

        trade = await self.trade_repo.update_trade(trade_id, account_id, **update_data)
        if not trade:
            return None
        return self.enrich_trade(trade, account.current_equity)

    async def close_trade(self, account_id: int, user_id: int,
                          trade_id: int, exit_price: float,
                          exit_date_val: Optional[date] = None,
                          exit_reason: Optional[str] = None) -> Optional[dict]:
        """Convenience method to close a trade"""
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None

        trade = await self.trade_repo.get_trade_by_id(trade_id, account_id)
        if not trade:
            return None
        if trade.status != TradeStatus.OPEN:
            return {"error": True, "message": "Chỉ có thể đóng lệnh đang mở"}

        trade = await self.trade_repo.update_trade(
            trade_id, account_id,
            exit_price=exit_price,
            exit_date=exit_date_val or date.today(),
            exit_reason=exit_reason,
            status=TradeStatus.CLOSED
        )
        return self.enrich_trade(trade, account.current_equity)

    async def revise_stop(self, account_id: int, user_id: int,
                          trade_id: int, data: StopRevisionCreate) -> Optional[dict]:
        """Revise stop with Schwager's validation: only tighten"""
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None

        trade = await self.trade_repo.get_trade_by_id(trade_id, account_id)
        if not trade:
            return None
        if trade.status != TradeStatus.OPEN:
            return {"error": True, "message": "Chỉ có thể điều chỉnh stop cho lệnh đang mở"}

        # Validate: stops can only be tightened
        error = self.validate_stop_revision(trade, data.new_stop)
        if error:
            return {"error": True, "message": error}

        current_stop = trade.revised_stop if trade.revised_stop else trade.initial_stop

        # Create audit trail
        await self.trade_repo.create_stop_revision(
            trade_id=trade_id,
            previous_stop=current_stop,
            new_stop=data.new_stop,
            reason=data.reason
        )

        # Update trade's revised_stop
        trade = await self.trade_repo.update_trade(
            trade_id, account_id, revised_stop=data.new_stop
        )

        result = self.enrich_trade(trade, account.current_equity)
        result["stop_revisions"] = [
            {
                "id": r.id,
                "previous_stop": r.previous_stop,
                "new_stop": r.new_stop,
                "reason": r.reason,
                "revised_at": r.revised_at
            }
            for r in (await self.trade_repo.get_stop_revisions(trade_id))
        ]
        return result

    async def delete_trade(self, account_id: int, user_id: int, trade_id: int) -> bool:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return False
        return await self.trade_repo.delete_trade(trade_id, account_id)
