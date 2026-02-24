"""Dashboard Service — Compute All Journal Dashboard Metrics"""
from typing import Optional
from collections import defaultdict
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.account_repository import AccountRepository
from app.repositories.trade_repository import TradeRepository
from app.services.trade_service import TradeService
from app.models.domain import TradeDirection, TradeStatus


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.dash_repo = DashboardRepository(session)
        self.account_repo = AccountRepository(session)
        self.trade_repo = TradeRepository(session)
        self.trade_service = TradeService(session)

    # =========================================================================
    # Main Dashboard Endpoint
    # =========================================================================

    async def get_dashboard(self, account_id: int, user_id: int) -> Optional[dict]:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None

        stats = await self.dash_repo.get_trade_stats(account_id)
        closed_trades = await self.dash_repo.get_closed_trades(account_id)
        equity_snapshots = await self.dash_repo.get_equity_snapshots(account_id)
        cum_risk = await self.trade_service.get_cumulative_risk(account_id, account.current_equity)

        # Compute metrics from closed trades
        metrics = self._compute_metrics(closed_trades, account)
        by_ticker = self._segment_by_ticker(closed_trades, account)
        by_direction = self._segment_by_direction(closed_trades, account)
        by_month = self._segment_by_month(closed_trades, account)
        equity_curve = self._build_equity_curve(closed_trades, account)

        return {
            "account": {
                "id": account.id,
                "account_name": account.account_name,
                "starting_equity": account.starting_equity,
                "current_equity": account.current_equity,
                "currency": account.currency,
                "max_risk_per_trade": account.max_risk_per_trade,
                "max_cumulative_risk": account.max_cumulative_risk,
            },
            "stats": {
                **stats,
                **metrics,
            },
            "cumulative_risk": cum_risk,
            "equity_curve": equity_curve,
            "equity_snapshots": [
                {
                    "date": s.snapshot_date.isoformat(),
                    "equity": s.equity_value,
                    "open_trade_equity": s.open_trade_equity,
                    "total": s.total_equity,
                }
                for s in equity_snapshots
            ],
            "by_ticker": by_ticker,
            "by_direction": by_direction,
            "by_month": by_month,
        }

    # =========================================================================
    # Metrics Computation
    # =========================================================================

    def _compute_metrics(self, trades, account) -> dict:
        if not trades:
            return {
                "total_pnl": 0, "win_count": 0, "loss_count": 0,
                "win_rate": 0, "avg_win": 0, "avg_loss": 0,
                "profit_factor": 0, "avg_r_multiple": 0,
                "best_trade_pnl": 0, "worst_trade_pnl": 0,
                "max_consecutive_wins": 0, "max_consecutive_losses": 0,
                "avg_duration_days": 0, "expectancy": 0,
                "total_return_pct": 0,
            }

        pnls = []
        r_multiples = []
        durations = []
        wins = []
        losses = []

        for t in trades:
            pnl = TradeService.calc_net_pnl(t)
            r = TradeService.calc_r_multiple(t)
            dur = TradeService.calc_duration(t)

            if pnl is not None:
                pnls.append(pnl)
                if pnl > 0:
                    wins.append(pnl)
                elif pnl < 0:
                    losses.append(pnl)
            if r is not None:
                r_multiples.append(r)
            if dur is not None:
                durations.append(dur)

        total_pnl = sum(pnls)
        win_count = len(wins)
        loss_count = len(losses)
        total_trades = len(pnls)

        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        avg_win = (sum(wins) / win_count) if win_count > 0 else 0
        avg_loss = (sum(losses) / loss_count) if loss_count > 0 else 0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0)
        avg_r = (sum(r_multiples) / len(r_multiples)) if r_multiples else 0
        avg_dur = (sum(durations) / len(durations)) if durations else 0

        # Expectancy = (Win% * Avg Win) + (Loss% * Avg Loss)
        win_pct = win_count / total_trades if total_trades > 0 else 0
        loss_pct = loss_count / total_trades if total_trades > 0 else 0
        expectancy = (win_pct * avg_win) + (loss_pct * avg_loss)

        # Consecutive wins/losses
        max_con_wins, max_con_losses = self._max_consecutive(pnls)

        total_return_pct = (total_pnl / account.starting_equity * 100) if account.starting_equity > 0 else 0

        return {
            "total_pnl": round(total_pnl, 2),
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": round(win_rate, 1),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_r_multiple": round(avg_r, 2),
            "best_trade_pnl": round(max(pnls), 2) if pnls else 0,
            "worst_trade_pnl": round(min(pnls), 2) if pnls else 0,
            "max_consecutive_wins": max_con_wins,
            "max_consecutive_losses": max_con_losses,
            "avg_duration_days": round(avg_dur, 1),
            "expectancy": round(expectancy, 2),
            "total_return_pct": round(total_return_pct, 2),
        }

    @staticmethod
    def _max_consecutive(pnls) -> tuple:
        max_wins = max_losses = cur_wins = cur_losses = 0
        for pnl in pnls:
            if pnl > 0:
                cur_wins += 1
                cur_losses = 0
            elif pnl < 0:
                cur_losses += 1
                cur_wins = 0
            else:
                cur_wins = 0
                cur_losses = 0
            max_wins = max(max_wins, cur_wins)
            max_losses = max(max_losses, cur_losses)
        return max_wins, max_losses

    # =========================================================================
    # Segmented Analysis
    # =========================================================================

    def _segment_by_ticker(self, trades, account) -> list:
        groups = defaultdict(list)
        for t in trades:
            groups[t.market_ticker].append(t)

        result = []
        for ticker, ticker_trades in sorted(groups.items()):
            pnls = [TradeService.calc_net_pnl(t) for t in ticker_trades]
            pnls = [p for p in pnls if p is not None]
            wins = [p for p in pnls if p > 0]
            result.append({
                "ticker": ticker,
                "trade_count": len(ticker_trades),
                "total_pnl": round(sum(pnls), 2),
                "win_count": len(wins),
                "win_rate": round(len(wins) / len(pnls) * 100, 1) if pnls else 0,
                "avg_pnl": round(sum(pnls) / len(pnls), 2) if pnls else 0,
            })
        return sorted(result, key=lambda x: x["total_pnl"], reverse=True)

    def _segment_by_direction(self, trades, account) -> list:
        result = []
        for direction in [TradeDirection.LONG, TradeDirection.SHORT]:
            dir_trades = [t for t in trades if t.direction == direction]
            if not dir_trades:
                continue
            pnls = [TradeService.calc_net_pnl(t) for t in dir_trades]
            pnls = [p for p in pnls if p is not None]
            wins = [p for p in pnls if p > 0]
            r_mults = [TradeService.calc_r_multiple(t) for t in dir_trades]
            r_mults = [r for r in r_mults if r is not None]
            result.append({
                "direction": direction.value,
                "trade_count": len(dir_trades),
                "total_pnl": round(sum(pnls), 2),
                "win_count": len(wins),
                "win_rate": round(len(wins) / len(pnls) * 100, 1) if pnls else 0,
                "avg_r": round(sum(r_mults) / len(r_mults), 2) if r_mults else 0,
            })
        return result

    def _segment_by_month(self, trades, account) -> list:
        groups = defaultdict(list)
        for t in trades:
            if t.exit_date:
                key = t.exit_date.strftime("%Y-%m")
                groups[key].append(t)

        result = []
        for month, month_trades in sorted(groups.items()):
            pnls = [TradeService.calc_net_pnl(t) for t in month_trades]
            pnls = [p for p in pnls if p is not None]
            wins = [p for p in pnls if p > 0]
            result.append({
                "month": month,
                "trade_count": len(month_trades),
                "total_pnl": round(sum(pnls), 2),
                "win_count": len(wins),
                "win_rate": round(len(wins) / len(pnls) * 100, 1) if pnls else 0,
            })
        return result

    # =========================================================================
    # Equity Curve (computed from closed trades)
    # =========================================================================

    def _build_equity_curve(self, trades, account) -> list:
        """Build equity curve from starting equity + cumulative P/L of closed trades"""
        if not trades:
            return [{"date": date.today().isoformat(), "equity": account.starting_equity}]

        curve = [{"date": account.created_at.strftime("%Y-%m-%d"), "equity": account.starting_equity}]
        cumulative = account.starting_equity

        for t in trades:
            pnl = TradeService.calc_net_pnl(t)
            if pnl is not None and t.exit_date:
                cumulative += pnl
                curve.append({
                    "date": t.exit_date.isoformat(),
                    "equity": round(cumulative, 2),
                    "trade": f"#{t.trade_number} {t.market_ticker}",
                    "pnl": round(pnl, 2),
                })

        return curve

    # =========================================================================
    # Equity Snapshots
    # =========================================================================

    async def get_equity_snapshots(self, account_id: int, user_id: int) -> Optional[list]:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        snapshots = await self.dash_repo.get_equity_snapshots(account_id)
        return [
            {
                "id": s.id,
                "date": s.snapshot_date.isoformat(),
                "equity": s.equity_value,
                "open_trade_equity": s.open_trade_equity,
                "total": s.total_equity,
            }
            for s in snapshots
        ]

    async def create_equity_snapshot(self, account_id: int, user_id: int,
                                      snapshot_date: date,
                                      equity_value: float,
                                      open_trade_equity: float = 0.0) -> Optional[dict]:
        account = await self.account_repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        snapshot = await self.dash_repo.create_equity_snapshot(
            account_id, snapshot_date, equity_value, open_trade_equity
        )
        return {
            "id": snapshot.id,
            "date": snapshot.snapshot_date.isoformat(),
            "equity": snapshot.equity_value,
            "open_trade_equity": snapshot.open_trade_equity,
            "total": snapshot.total_equity,
        }
