"""
Stop-Loss Principle — Chapter 9, Concept 1
==========================================
Schwager's foundational rule: define the exit before the entry.

This module provides:
  - StopLossOrder: dataclass representing a pre-defined stop
  - validate_stop_placement: checks if a stop is at a technically meaningful level
  - simulate_discipline_vs_hope: compares outcomes of disciplined exit vs holding
  - backtest_stop_discipline: runs the simulation over many trials for statistics
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import random


class StopType(Enum):
    """Classification of stop-loss types from Chapter 9."""
    TREND_LINE = "trend_line"
    TRADING_RANGE = "trading_range"
    FLAG_PENNANT = "flag_pennant"
    WIDE_RANGING_DAY = "wide_ranging_day"
    RELATIVE_HIGH_LOW = "relative_high_low"
    MONEY_STOP = "money_stop"       # non-technical, pure dollar risk
    TRAILING = "trailing"


@dataclass
class StopLossOrder:
    """
    A pre-defined stop-loss order — Schwager's Rule 1.
    
    Attributes:
        entry_price: Price at which the trade was entered
        stop_price: Price at which the position will be liquidated
        stop_type: The technical basis for the stop level
        rationale: Why this level invalidates the trade thesis
    """
    entry_price: float
    stop_price: float
    stop_type: StopType
    rationale: str = ""

    @property
    def risk_pct(self) -> float:
        """Percentage risk from entry to stop."""
        return abs(self.entry_price - self.stop_price) / self.entry_price * 100

    @property
    def is_long(self) -> bool:
        """True if this is a long-side stop (stop below entry)."""
        return self.stop_price < self.entry_price

    def is_triggered(self, price: float) -> bool:
        """Check if a given price triggers this stop."""
        if self.is_long:
            return price <= self.stop_price
        else:
            return price >= self.stop_price

    def tighten(self, new_stop: float) -> 'StopLossOrder':
        """
        Schwager's Rule 3: stops should only be changed to reduce risk.
        Returns a new StopLossOrder with reduced risk, or raises ValueError
        if the new stop would increase risk (the CIC anti-pattern).
        """
        if self.is_long and new_stop < self.stop_price:
            raise ValueError(
                f"CIC anti-pattern: moving long stop DOWN from {self.stop_price} "
                f"to {new_stop} increases risk. Stops only tighten."
            )
        if not self.is_long and new_stop > self.stop_price:
            raise ValueError(
                f"CIC anti-pattern: moving short stop UP from {self.stop_price} "
                f"to {new_stop} increases risk. Stops only tighten."
            )
        return StopLossOrder(
            entry_price=self.entry_price,
            stop_price=new_stop,
            stop_type=self.stop_type,
            rationale=f"Tightened from {self.stop_price:.2f}"
        )


def validate_stop_placement(
    entry_price: float,
    stop_price: float,
    technical_levels: list[float],
    max_risk_pct: float = 10.0,
) -> dict:
    """
    Schwager's Rule 2: the stop should be at or before the point where
    the technical picture changes.
    
    Args:
        entry_price: Trade entry price
        stop_price: Proposed stop price
        technical_levels: List of technically significant prices
                          (support/resistance levels, trend lines, etc.)
        max_risk_pct: Maximum acceptable risk as percentage of entry
    
    Returns:
        dict with 'valid', 'risk_pct', 'nearest_technical_level', 'warnings'
    """
    is_long = stop_price < entry_price
    risk_pct = abs(entry_price - stop_price) / entry_price * 100
    
    # Find nearest technical level beyond the stop
    if is_long:
        relevant = [l for l in technical_levels if l < entry_price]
        relevant.sort(reverse=True)  # closest support first
    else:
        relevant = [l for l in technical_levels if l > entry_price]
        relevant.sort()  # closest resistance first
    
    warnings = []
    nearest = relevant[0] if relevant else None
    
    # Check if stop is at a technically meaningful level
    if nearest and is_long and stop_price > nearest:
        warnings.append(
            f"Stop at {stop_price:.2f} is ABOVE nearest support {nearest:.2f}. "
            f"Price can hit your stop without invalidating the technical picture."
        )
    
    if risk_pct > max_risk_pct:
        warnings.append(
            f"Risk of {risk_pct:.1f}% exceeds max {max_risk_pct:.1f}%. "
            f"Consider a money stop or waiting for a retracement entry."
        )
    
    return {
        "valid": len(warnings) == 0,
        "risk_pct": round(risk_pct, 2),
        "nearest_technical_level": nearest,
        "warnings": warnings,
    }


def simulate_discipline_vs_hope(
    entry_price: float = 100.0,
    stop_pct: float = 5.0,
    n_bars: int = 100,
    drift: float = -0.1,
    volatility: float = 2.0,
    seed: Optional[int] = None,
) -> dict:
    """
    Simulate a single trade comparing disciplined stop-loss exit
    vs. holding and hoping for recovery.
    
    Args:
        entry_price: Starting price at entry
        stop_pct: Stop distance as percentage below entry
        n_bars: Number of price bars to simulate
        drift: Average price change per bar (negative = bearish)
        volatility: Standard deviation of price changes
        seed: Random seed for reproducibility
    
    Returns:
        dict with 'prices', 'stop_price', 'stopped_at_bar',
        'disciplined_pnl_pct', 'hope_pnl_pct'
    """
    if seed is not None:
        random.seed(seed)
    
    stop_price = entry_price * (1 - stop_pct / 100)
    prices = [entry_price]
    stopped_at = None
    
    for i in range(1, n_bars):
        change = drift + volatility * (random.gauss(0, 1))
        prices.append(max(1, prices[-1] + change))
        
        if stopped_at is None and prices[-1] <= stop_price:
            stopped_at = i
    
    disciplined_exit = prices[stopped_at] if stopped_at else prices[-1]
    hope_exit = prices[-1]
    
    return {
        "prices": prices,
        "stop_price": stop_price,
        "stopped_at_bar": stopped_at,
        "disciplined_pnl_pct": round((disciplined_exit - entry_price) / entry_price * 100, 2),
        "hope_pnl_pct": round((hope_exit - entry_price) / entry_price * 100, 2),
    }


def backtest_stop_discipline(
    n_trials: int = 1000,
    stop_pct: float = 5.0,
    **sim_kwargs,
) -> dict:
    """
    Run many trials to show the statistical advantage of disciplined stops.
    
    Returns:
        dict with mean/median/worst outcomes for both approaches
    """
    disc_results = []
    hope_results = []
    
    for i in range(n_trials):
        result = simulate_discipline_vs_hope(stop_pct=stop_pct, seed=i, **sim_kwargs)
        disc_results.append(result["disciplined_pnl_pct"])
        hope_results.append(result["hope_pnl_pct"])
    
    disc_results.sort()
    hope_results.sort()
    
    def stats(arr):
        n = len(arr)
        return {
            "mean": round(sum(arr) / n, 2),
            "median": round(arr[n // 2], 2),
            "worst": round(arr[0], 2),
            "best": round(arr[-1], 2),
            "pct_losing": round(sum(1 for x in arr if x < 0) / n * 100, 1),
        }
    
    return {
        "n_trials": n_trials,
        "stop_pct": stop_pct,
        "disciplined": stats(disc_results),
        "hope": stats(hope_results),
    }


# --- Demo ---
if __name__ == "__main__":
    # 1. Create a stop order
    stop = StopLossOrder(
        entry_price=50.0,
        stop_price=47.5,
        stop_type=StopType.TRADING_RANGE,
        rationale="Below lower boundary of 3-month trading range"
    )
    print(f"Stop order: entry={stop.entry_price}, stop={stop.stop_price}, "
          f"risk={stop.risk_pct:.1f}%, type={stop.stop_type.value}")
    
    # 2. Try to widen the stop (should fail — CIC anti-pattern)
    try:
        stop.tighten(46.0)
    except ValueError as e:
        print(f"Blocked: {e}")
    
    # 3. Tighten the stop (should succeed)
    tighter = stop.tighten(48.0)
    print(f"Tightened: new stop={tighter.stop_price}, risk={tighter.risk_pct:.1f}%")
    
    # 4. Validate placement
    result = validate_stop_placement(
        entry_price=50.0,
        stop_price=49.0,
        technical_levels=[45.0, 47.5, 52.0, 55.0],
    )
    print(f"\nValidation: {result}")
    
    # 5. Backtest discipline vs hope
    bt = backtest_stop_discipline(n_trials=1000, stop_pct=5.0)
    print(f"\n--- Backtest: {bt['n_trials']} trials, {bt['stop_pct']}% stop ---")
    print(f"Disciplined: mean={bt['disciplined']['mean']}%, "
          f"worst={bt['disciplined']['worst']}%")
    print(f"Hope & hold: mean={bt['hope']['mean']}%, "
          f"worst={bt['hope']['worst']}%")
