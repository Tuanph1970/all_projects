"""
Portfolio Management for Stock Trading Simulation
Implements Observer Pattern for portfolio events and comprehensive tracking
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import pandas as pd


class TransactionType(Enum):
    """Transaction types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Transaction:
    """Represents a single transaction"""
    date: datetime
    transaction_type: TransactionType
    price: float
    shares: int
    total_value: float
    portfolio_value: float
    cash_balance: float
    shares_owned: int

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'date': self.date.isoformat() if isinstance(self.date, datetime) else str(self.date),
            'type': self.transaction_type.value,
            'price': float(self.price),
            'shares': int(self.shares),
            'total_value': float(self.total_value),
            'portfolio_value': float(self.portfolio_value),
            'cash_balance': float(self.cash_balance),
            'shares_owned': int(self.shares_owned)
        }


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    initial_capital: float
    final_value: float
    total_return: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    buy_and_hold_return: float
    buy_and_hold_return_pct: float
    alpha: float  # Excess return over buy-and-hold

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'initial_capital': float(self.initial_capital),
            'final_value': float(self.final_value),
            'total_return': float(self.total_return),
            'total_return_pct': float(self.total_return_pct),
            'total_trades': int(self.total_trades),
            'winning_trades': int(self.winning_trades),
            'losing_trades': int(self.losing_trades),
            'win_rate': float(self.win_rate),
            'max_drawdown': float(self.max_drawdown),
            'sharpe_ratio': float(self.sharpe_ratio),
            'buy_and_hold_return': float(self.buy_and_hold_return),
            'buy_and_hold_return_pct': float(self.buy_and_hold_return_pct),
            'alpha': float(self.alpha)
        }


class PortfolioObserver:
    """Observer interface for portfolio events"""

    def on_transaction(self, transaction: Transaction) -> None:
        """Called when a transaction occurs"""
        pass

    def on_portfolio_update(self, portfolio_value: float, cash: float, shares: int) -> None:
        """Called when portfolio is updated"""
        pass


class Portfolio:
    """
    Portfolio manager with transaction tracking and performance analytics
    """

    def __init__(self, initial_capital: float, commission_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.shares_owned = 0
        self.commission_rate = commission_rate

        self.transactions: List[Transaction] = []
        self.observers: List[PortfolioObserver] = []

        # Track portfolio value over time
        self.portfolio_values: List[float] = []
        self.dates: List[datetime] = []

    def add_observer(self, observer: PortfolioObserver) -> None:
        """Add an observer"""
        self.observers.append(observer)

    def remove_observer(self, observer: PortfolioObserver) -> None:
        """Remove an observer"""
        self.observers.remove(observer)

    def notify_transaction(self, transaction: Transaction) -> None:
        """Notify observers of a transaction"""
        for observer in self.observers:
            observer.on_transaction(transaction)

    def notify_portfolio_update(self) -> None:
        """Notify observers of portfolio update"""
        portfolio_value = self.get_portfolio_value(self.get_last_price())
        for observer in self.observers:
            observer.on_portfolio_update(portfolio_value, self.cash, self.shares_owned)

    def buy(self, date: datetime, price: float, shares: int) -> bool:
        """
        Buy shares

        Args:
            date: Transaction date
            price: Share price
            shares: Number of shares to buy

        Returns:
            True if successful, False otherwise
        """
        total_cost = price * shares
        commission = total_cost * self.commission_rate
        total_with_commission = total_cost + commission

        if total_with_commission > self.cash:
            return False

        self.cash -= total_with_commission
        self.shares_owned += shares

        portfolio_value = self.get_portfolio_value(price)

        transaction = Transaction(
            date=date,
            transaction_type=TransactionType.BUY,
            price=price,
            shares=shares,
            total_value=total_with_commission,
            portfolio_value=portfolio_value,
            cash_balance=self.cash,
            shares_owned=self.shares_owned
        )

        self.transactions.append(transaction)
        self.portfolio_values.append(portfolio_value)
        self.dates.append(date)

        self.notify_transaction(transaction)
        self.notify_portfolio_update()

        return True

    def sell(self, date: datetime, price: float, shares: int = None) -> bool:
        """
        Sell shares

        Args:
            date: Transaction date
            price: Share price
            shares: Number of shares to sell (None = sell all)

        Returns:
            True if successful, False otherwise
        """
        if shares is None:
            shares = self.shares_owned

        if shares > self.shares_owned or shares <= 0:
            return False

        total_value = price * shares
        commission = total_value * self.commission_rate
        net_proceeds = total_value - commission

        self.cash += net_proceeds
        self.shares_owned -= shares

        portfolio_value = self.get_portfolio_value(price)

        transaction = Transaction(
            date=date,
            transaction_type=TransactionType.SELL,
            price=price,
            shares=shares,
            total_value=net_proceeds,
            portfolio_value=portfolio_value,
            cash_balance=self.cash,
            shares_owned=self.shares_owned
        )

        self.transactions.append(transaction)
        self.portfolio_values.append(portfolio_value)
        self.dates.append(date)

        self.notify_transaction(transaction)
        self.notify_portfolio_update()

        return True

    def hold(self, date: datetime, price: float) -> None:
        """
        Hold position (no transaction)

        Args:
            date: Current date
            price: Current price
        """
        portfolio_value = self.get_portfolio_value(price)
        self.portfolio_values.append(portfolio_value)
        self.dates.append(date)

    def get_portfolio_value(self, current_price: float) -> float:
        """Calculate current portfolio value"""
        return self.cash + (self.shares_owned * current_price)

    def get_last_price(self) -> float:
        """Get price from last transaction"""
        if self.transactions:
            return self.transactions[-1].price
        return 0.0

    def get_transaction_history(self) -> List[Dict]:
        """Get transaction history"""
        return [t.to_dict() for t in self.transactions]

    def calculate_metrics(self, prices: pd.Series) -> PortfolioMetrics:
        """
        Calculate comprehensive portfolio metrics

        Args:
            prices: Series of stock prices for buy-and-hold comparison

        Returns:
            PortfolioMetrics object
        """
        final_value = self.get_portfolio_value(prices.iloc[-1])
        total_return = final_value - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100

        # Calculate buy and hold benchmark
        shares_buy_hold = self.initial_capital // prices.iloc[0]
        buy_hold_final = shares_buy_hold * prices.iloc[-1]
        buy_hold_return = buy_hold_final - self.initial_capital
        buy_hold_return_pct = (buy_hold_return / self.initial_capital) * 100

        # Alpha (excess return)
        alpha = total_return_pct - buy_hold_return_pct

        # Trade statistics
        buy_transactions = [t for t in self.transactions if t.transaction_type == TransactionType.BUY]
        sell_transactions = [t for t in self.transactions if t.transaction_type == TransactionType.SELL]

        total_trades = len(sell_transactions)
        winning_trades = 0
        losing_trades = 0

        # Match buy-sell pairs to calculate win/loss
        for sell in sell_transactions:
            # Find corresponding buy (simplified - assumes FIFO)
            corresponding_buys = [b for b in buy_transactions if b.date < sell.date]
            if corresponding_buys:
                avg_buy_price = sum(b.price for b in corresponding_buys) / len(corresponding_buys)
                if sell.price > avg_buy_price:
                    winning_trades += 1
                else:
                    losing_trades += 1

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown()

        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio()

        return PortfolioMetrics(
            initial_capital=self.initial_capital,
            final_value=final_value,
            total_return=total_return,
            total_return_pct=total_return_pct,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            buy_and_hold_return=buy_hold_return,
            buy_and_hold_return_pct=buy_hold_return_pct,
            alpha=alpha
        )

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        if not self.portfolio_values:
            return 0.0

        peak = self.portfolio_values[0]
        max_dd = 0.0

        for value in self.portfolio_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sharpe ratio

        Args:
            risk_free_rate: Annual risk-free rate (default 2%)

        Returns:
            Sharpe ratio
        """
        if len(self.portfolio_values) < 2:
            return 0.0

        # Calculate returns
        returns = pd.Series(self.portfolio_values).pct_change().dropna()

        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        # Annualize assuming daily data
        excess_return = returns.mean() - (risk_free_rate / 252)
        return (excess_return / returns.std()) * (252 ** 0.5)

    def get_buy_sell_points(self) -> Dict[str, List[int]]:
        """
        Get indices of buy and sell transactions for visualization

        Returns:
            Dict with 'buy' and 'sell' index lists
        """
        buy_indices = []
        sell_indices = []

        for i, transaction in enumerate(self.transactions):
            if transaction.transaction_type == TransactionType.BUY:
                buy_indices.append(i)
            elif transaction.transaction_type == TransactionType.SELL:
                sell_indices.append(i)

        return {
            'buy': buy_indices,
            'sell': sell_indices
        }
