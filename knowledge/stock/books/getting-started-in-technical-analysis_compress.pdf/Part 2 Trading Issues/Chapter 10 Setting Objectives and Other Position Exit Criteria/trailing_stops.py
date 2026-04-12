"""
Trailing Stops — Chapter 10, Concept 6 (detailed in Chapter 9)
================================================================
Dynamically adjusts stop-loss levels to protect accumulating
profits while allowing winning trades to run.

Schwager: "The use of trailing stops may be among the least
glamorous, but most sensible, methods of determining a trade
exit point... the approach comes closest to the ideal of
permitting a profitable trade to run its course."

This module provides:
  - Multiple trailing stop methods (relative low, percentage,
    ATR-based, trend line)
  - The "ratchet" principle: stops only move to reduce risk
  - Comparative analysis across methods
  - Integration with other Chapter 10 exit tools
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Literal


@dataclass
class TrailingStopResult:
    """Result of a trailing stop calculation over a position's life."""
    method: str
    entry_idx: int
    entry_price: float
    exit_idx: int
    exit_price: float
    max_price: float
    stop_levels: List[float]
    ratchet_points: List[int]  # Indices where stop moved up

    @property
    def profit(self) -> float:
        return self.exit_price - self.entry_price

    @property
    def max_profit(self) -> float:
        return self.max_price - self.entry_price

    @property
    def profit_captured_pct(self) -> float:
        """Percentage of maximum available profit captured."""
        if self.max_profit <= 0:
            return 0.0
        return max(0.0, self.profit / self.max_profit * 100)

    @property
    def profit_surrendered(self) -> float:
        """Profit given back from peak to exit."""
        return self.max_price - self.exit_price

    @property
    def summary(self) -> str:
        return (
            f"{self.method}: entry ${self.entry_price:.2f} → "
            f"exit ${self.exit_price:.2f} "
            f"(captured {self.profit_captured_pct:.0f}% of "
            f"max ${self.max_profit:.2f} profit, "
            f"{len(self.ratchet_points)} ratchets)"
        )


def trailing_stop_relative_low(
    prices: pd.Series,
    entry_idx: int,
    lookback: int = 10,
    direction: str = 'long'
) -> TrailingStopResult:
    """
    Trailing stop using relative lows (Schwager's preferred method).
    
    From Chapter 9, Figure 9.6 (Walt Disney example):
    Stop is raised to the most recent relative low each time
    the market makes new highs. The reference point is revised
    each time price reaches new high ground.
    
    Parameters
    ----------
    prices : pd.Series
        Price series.
    entry_idx : int
        Index of trade entry.
    lookback : int
        N-bar lookback for defining relative lows.
        Schwager: "A reasonable range for N is between 5 and 15."
    direction : str
        'long' or 'short'.
        
    Returns
    -------
    TrailingStopResult
    """
    stop_levels = [0.0] * len(prices)
    current_stop = 0.0
    exit_idx = len(prices) - 1
    ratchet_points = []
    
    if direction == 'long':
        for i in range(entry_idx, len(prices)):
            window_start = max(0, i - lookback)
            window_low = float(prices.iloc[window_start:i + 1].min())
            
            if window_low > current_stop:
                if current_stop > 0:
                    ratchet_points.append(i)
                current_stop = window_low
            
            stop_levels[i] = current_stop
            
            if i > entry_idx + lookback and prices.iloc[i] < current_stop:
                exit_idx = i
                break
    else:  # short
        current_stop = float('inf')
        for i in range(entry_idx, len(prices)):
            window_start = max(0, i - lookback)
            window_high = float(prices.iloc[window_start:i + 1].max())
            
            if window_high < current_stop:
                if current_stop < float('inf'):
                    ratchet_points.append(i)
                current_stop = window_high
            
            stop_levels[i] = current_stop
            
            if i > entry_idx + lookback and prices.iloc[i] > current_stop:
                exit_idx = i
                break
    
    return TrailingStopResult(
        method=f"Relative low (N={lookback})",
        entry_idx=entry_idx,
        entry_price=float(prices.iloc[entry_idx]),
        exit_idx=exit_idx,
        exit_price=float(prices.iloc[exit_idx]),
        max_price=float(prices.iloc[entry_idx:exit_idx + 1].max()),
        stop_levels=stop_levels,
        ratchet_points=ratchet_points,
    )


def trailing_stop_percentage(
    prices: pd.Series,
    entry_idx: int,
    trail_pct: float = 5.0,
    direction: str = 'long'
) -> TrailingStopResult:
    """
    Trailing stop using a fixed percentage from the high-water mark.
    
    Schwager (Ch. 9): "A trailing stop could follow a position
    by a fixed dollar, percentage, or point value. This technique
    has the same implications as the simple money stop: it keeps
    risk at a known level but may also liquidate a trade when
    there is no technical reason for doing so."
    
    Parameters
    ----------
    prices : pd.Series
        Price series.
    entry_idx : int
        Index of trade entry.
    trail_pct : float
        Percentage below high-water mark for long positions.
    direction : str
        'long' or 'short'.
        
    Returns
    -------
    TrailingStopResult
    """
    stop_levels = [0.0] * len(prices)
    exit_idx = len(prices) - 1
    ratchet_points = []
    
    if direction == 'long':
        high_water = float(prices.iloc[entry_idx])
        current_stop = high_water * (1 - trail_pct / 100)
        
        for i in range(entry_idx, len(prices)):
            p = float(prices.iloc[i])
            if p > high_water:
                old_stop = current_stop
                high_water = p
                current_stop = high_water * (1 - trail_pct / 100)
                if current_stop > old_stop:
                    ratchet_points.append(i)
            
            stop_levels[i] = current_stop
            
            if i > entry_idx + 2 and p < current_stop:
                exit_idx = i
                break
    else:
        low_water = float(prices.iloc[entry_idx])
        current_stop = low_water * (1 + trail_pct / 100)
        
        for i in range(entry_idx, len(prices)):
            p = float(prices.iloc[i])
            if p < low_water:
                old_stop = current_stop
                low_water = p
                current_stop = low_water * (1 + trail_pct / 100)
                if current_stop < old_stop:
                    ratchet_points.append(i)
            
            stop_levels[i] = current_stop
            
            if i > entry_idx + 2 and p > current_stop:
                exit_idx = i
                break
    
    return TrailingStopResult(
        method=f"Percentage ({trail_pct}%)",
        entry_idx=entry_idx,
        entry_price=float(prices.iloc[entry_idx]),
        exit_idx=exit_idx,
        exit_price=float(prices.iloc[exit_idx]),
        max_price=float(prices.iloc[entry_idx:exit_idx + 1].max()),
        stop_levels=stop_levels,
        ratchet_points=ratchet_points,
    )


def trailing_stop_atr(
    prices: pd.Series,
    entry_idx: int,
    atr_multiple: float = 2.5,
    atr_period: int = 14,
    direction: str = 'long'
) -> TrailingStopResult:
    """
    Trailing stop using ATR (Average True Range) multiple.
    
    Combines Schwager's money-stop simplicity with volatility
    adaptiveness. Stop = high_water - (ATR × multiple).
    Wider in volatile markets, tighter in calm ones.
    
    Parameters
    ----------
    prices : pd.Series
        Price series (closing prices used as proxy for TR).
    entry_idx : int
        Index of trade entry.
    atr_multiple : float
        Multiplier for ATR distance.
    atr_period : int
        ATR lookback period.
    direction : str
        'long' or 'short'.
        
    Returns
    -------
    TrailingStopResult
    """
    # Approximate ATR from closes
    tr = prices.diff().abs()
    atr = tr.rolling(atr_period, min_periods=1).mean()
    
    stop_levels = [0.0] * len(prices)
    exit_idx = len(prices) - 1
    ratchet_points = []
    
    if direction == 'long':
        high_water = float(prices.iloc[entry_idx])
        current_stop = high_water - float(atr.iloc[entry_idx]) * atr_multiple
        
        for i in range(entry_idx, len(prices)):
            p = float(prices.iloc[i])
            if p > high_water:
                old_stop = current_stop
                high_water = p
                new_stop = high_water - float(atr.iloc[i]) * atr_multiple
                if new_stop > current_stop:
                    current_stop = new_stop
                    if old_stop > 0:
                        ratchet_points.append(i)
            
            stop_levels[i] = current_stop
            
            if i > entry_idx + atr_period and p < current_stop:
                exit_idx = i
                break
    else:
        low_water = float(prices.iloc[entry_idx])
        current_stop = low_water + float(atr.iloc[entry_idx]) * atr_multiple
        
        for i in range(entry_idx, len(prices)):
            p = float(prices.iloc[i])
            if p < low_water:
                old_stop = current_stop
                low_water = p
                new_stop = low_water + float(atr.iloc[i]) * atr_multiple
                if new_stop < current_stop:
                    current_stop = new_stop
                    if old_stop < float('inf'):
                        ratchet_points.append(i)
            
            stop_levels[i] = current_stop
            
            if i > entry_idx + atr_period and p > current_stop:
                exit_idx = i
                break
    
    return TrailingStopResult(
        method=f"ATR ({atr_multiple}× {atr_period}-period)",
        entry_idx=entry_idx,
        entry_price=float(prices.iloc[entry_idx]),
        exit_idx=exit_idx,
        exit_price=float(prices.iloc[exit_idx]),
        max_price=float(prices.iloc[entry_idx:exit_idx + 1].max()),
        stop_levels=stop_levels,
        ratchet_points=ratchet_points,
    )


def compare_trailing_methods(
    prices: pd.Series,
    entry_idx: int,
    direction: str = 'long'
) -> pd.DataFrame:
    """
    Compare all trailing stop methods on the same price data.
    
    Parameters
    ----------
    prices : pd.Series
        Price series.
    entry_idx : int
        Index of trade entry.
    direction : str
        'long' or 'short'.
        
    Returns
    -------
    pd.DataFrame
        Comparison of methods.
    """
    methods = [
        trailing_stop_relative_low(prices, entry_idx, lookback=10, direction=direction),
        trailing_stop_relative_low(prices, entry_idx, lookback=5, direction=direction),
        trailing_stop_percentage(prices, entry_idx, trail_pct=5.0, direction=direction),
        trailing_stop_percentage(prices, entry_idx, trail_pct=8.0, direction=direction),
        trailing_stop_atr(prices, entry_idx, atr_multiple=2.0, direction=direction),
        trailing_stop_atr(prices, entry_idx, atr_multiple=3.0, direction=direction),
    ]
    
    rows = []
    for r in methods:
        rows.append({
            'Method': r.method,
            'Exit price': f"${r.exit_price:.2f}",
            'Profit': f"${r.profit:.2f}",
            'Max profit': f"${r.max_profit:.2f}",
            'Captured': f"{r.profit_captured_pct:.0f}%",
            'Surrendered': f"${r.profit_surrendered:.2f}",
            'Ratchets': len(r.ratchet_points),
            'Bars held': r.exit_idx - r.entry_idx,
        })
    
    return pd.DataFrame(rows)


# --- Example usage ---
if __name__ == "__main__":
    np.random.seed(42)
    N = 200
    
    # Trending then reversing price series
    trend = np.cumsum(np.concatenate([
        np.random.randn(80) * 1.0 + 0.4,   # Uptrend
        np.random.randn(40) * 1.2 + 0.1,    # Plateau
        np.random.randn(80) * 1.3 - 0.5,    # Decline
    ]))
    prices = pd.Series(100 + trend)
    
    entry_idx = 10
    
    print("=== Trailing Stop Method Comparison ===")
    print(f"Entry at bar {entry_idx}: ${prices.iloc[entry_idx]:.2f}\n")
    
    df = compare_trailing_methods(prices, entry_idx, 'long')
    print(df.to_string(index=False))
    
    print("\n=== Detailed: Relative Low (N=10) ===")
    result = trailing_stop_relative_low(prices, entry_idx, lookback=10)
    print(f"  {result.summary}")
    print(f"  Profit surrendered from peak: ${result.profit_surrendered:.2f}")
    print(f"  Bars held: {result.exit_idx - result.entry_idx}")
    
    print("\n=== Schwager's Key Rule ===")
    print("  'Stops should only be changed in order to reduce risk.'")
    print("  'Revising the stop to allow greater risk defeats")
    print("   the entire purpose of the stop.'")
    print(f"\n  All {len(result.ratchet_points)} ratchet moves were upward")
    print(f"  (risk-reducing), never downward.")
