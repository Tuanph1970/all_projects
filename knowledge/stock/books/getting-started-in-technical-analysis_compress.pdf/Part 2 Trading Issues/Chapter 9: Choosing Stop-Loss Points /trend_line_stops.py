"""
Trend Line Stops — Chapter 9, Concept 2
========================================
Place stops below an uptrend line (long) or above a downtrend line (short).
Earliest signal but most prone to false triggers due to trend line redefinition.

This module provides:
  - TrendLine: dataclass representing a trend line with slope/intercept
  - compute_trend_line: fit a trend line through swing lows (uptrend) or highs (downtrend)
  - trend_line_stop_price: get the current stop price from a trend line at a given bar
  - evaluate_trend_line_stop: backtest trend line stops on price data
"""

from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class TrendLine:
    """
    A trend line defined by two anchor points.
    
    Attributes:
        bar1: Index of first anchor bar
        price1: Price at first anchor
        bar2: Index of second anchor bar
        price2: Price at second anchor
        direction: 'up' or 'down'
    """
    bar1: int
    price1: float
    bar2: int
    price2: float
    direction: str  # 'up' or 'down'

    @property
    def slope_per_bar(self) -> float:
        """Price change per bar along the trend line."""
        if self.bar2 == self.bar1:
            return 0.0
        return (self.price2 - self.price1) / (self.bar2 - self.bar1)

    def price_at(self, bar: int) -> float:
        """Get the trend line price at any bar index."""
        return self.price1 + self.slope_per_bar * (bar - self.bar1)

    def is_penetrated(self, bar: int, price: float) -> bool:
        """
        Check if a given price penetrates this trend line.
        For uptrend: price drops below the line.
        For downtrend: price rises above the line.
        """
        tl_price = self.price_at(bar)
        if self.direction == 'up':
            return price < tl_price
        else:
            return price > tl_price


def find_swing_lows(prices: list[float], lookback: int = 5) -> list[int]:
    """
    Find relative lows in a price series.
    A swing low at index i means prices[i] is the lowest in
    [i-lookback, i+lookback].
    """
    swings = []
    for i in range(lookback, len(prices) - lookback):
        window = prices[i - lookback: i + lookback + 1]
        if prices[i] == min(window):
            swings.append(i)
    return swings


def find_swing_highs(prices: list[float], lookback: int = 5) -> list[int]:
    """Find relative highs in a price series."""
    swings = []
    for i in range(lookback, len(prices) - lookback):
        window = prices[i - lookback: i + lookback + 1]
        if prices[i] == max(window):
            swings.append(i)
    return swings


def compute_trend_line(
    prices: list[float],
    direction: str = 'up',
    lookback: int = 5,
    anchor_count: int = 2,
) -> Optional[TrendLine]:
    """
    Fit a trend line through the most recent swing lows (uptrend)
    or swing highs (downtrend).
    
    Args:
        prices: Price series
        direction: 'up' for uptrend line (connecting lows),
                   'down' for downtrend line (connecting highs)
        lookback: Window for swing detection
        anchor_count: Minimum number of swing points needed
    
    Returns:
        TrendLine or None if insufficient anchors
    """
    if direction == 'up':
        swings = find_swing_lows(prices, lookback)
    else:
        swings = find_swing_highs(prices, lookback)

    if len(swings) < anchor_count:
        return None

    # Use the two most recent swing points
    b1, b2 = swings[-2], swings[-1]
    return TrendLine(
        bar1=b1,
        price1=prices[b1],
        bar2=b2,
        price2=prices[b2],
        direction=direction,
    )


def trend_line_stop_price(tl: TrendLine, current_bar: int) -> float:
    """
    Get the stop-loss price at the current bar based on a trend line.
    This is simply the trend line's projected price at that bar.
    """
    return tl.price_at(current_bar)


def evaluate_trend_line_stop(
    prices: list[float],
    entry_bar: int,
    tl: TrendLine,
    buffer_pct: float = 0.0,
) -> dict:
    """
    Evaluate a trend line stop on actual price data.
    
    Args:
        prices: Full price series
        entry_bar: Bar index where the trade was entered
        tl: The trend line to use as stop reference
        buffer_pct: Optional buffer below/above the trend line
                    to reduce false signals (0 = exact line)
    
    Returns:
        dict with 'stopped', 'stop_bar', 'stop_price', 'entry_price',
        'pnl_pct', 'bars_held', 'was_false_signal'
    """
    entry_price = prices[entry_bar]
    is_long = tl.direction == 'up'

    for i in range(entry_bar + 1, len(prices)):
        tl_price = tl.price_at(i)

        if is_long:
            effective_stop = tl_price * (1 - buffer_pct / 100)
            if prices[i] <= effective_stop:
                pnl = (prices[i] - entry_price) / entry_price * 100
                # Check if price recovered after stop — indicates false signal
                future = prices[i + 1:min(i + 20, len(prices))]
                recovered = any(p > entry_price for p in future) if future else False
                return {
                    "stopped": True,
                    "stop_bar": i,
                    "stop_price": round(prices[i], 2),
                    "entry_price": round(entry_price, 2),
                    "pnl_pct": round(pnl, 2),
                    "bars_held": i - entry_bar,
                    "was_false_signal": recovered,
                }
        else:
            effective_stop = tl_price * (1 + buffer_pct / 100)
            if prices[i] >= effective_stop:
                pnl = (entry_price - prices[i]) / entry_price * 100
                future = prices[i + 1:min(i + 20, len(prices))]
                recovered = any(p < entry_price for p in future) if future else False
                return {
                    "stopped": True,
                    "stop_bar": i,
                    "stop_price": round(prices[i], 2),
                    "entry_price": round(entry_price, 2),
                    "pnl_pct": round(pnl, 2),
                    "bars_held": i - entry_bar,
                    "was_false_signal": recovered,
                }

    # Never stopped — held to end
    final = prices[-1]
    pnl = ((final - entry_price) / entry_price * 100) if is_long else \
          ((entry_price - final) / entry_price * 100)
    return {
        "stopped": False,
        "stop_bar": None,
        "stop_price": None,
        "entry_price": round(entry_price, 2),
        "pnl_pct": round(pnl, 2),
        "bars_held": len(prices) - 1 - entry_bar,
        "was_false_signal": None,
    }


def compare_buffer_levels(
    prices: list[float],
    entry_bar: int,
    tl: TrendLine,
    buffers: list[float] = [0.0, 0.5, 1.0, 2.0],
) -> list[dict]:
    """
    Compare trend line stops at different buffer levels.
    Higher buffer = more tolerance = fewer false signals but larger losses.
    
    This demonstrates the core tradeoff Schwager describes:
    sensitivity (small buffer) vs specificity (large buffer).
    """
    results = []
    for buf in buffers:
        result = evaluate_trend_line_stop(prices, entry_bar, tl, buf)
        result["buffer_pct"] = buf
        results.append(result)
    return results


# --- Demo ---
if __name__ == "__main__":
    import random
    random.seed(42)

    # Generate uptrend with noise
    prices = [100.0]
    for i in range(1, 120):
        drift = 0.2 if i < 80 else -0.4
        prices.append(prices[-1] + drift + 1.5 * random.gauss(0, 1))

    # Compute trend line from swing lows
    tl = compute_trend_line(prices[:60], direction='up', lookback=5)
    if tl:
        print(f"Trend line: bar {tl.bar1} ({tl.price1:.1f}) → "
              f"bar {tl.bar2} ({tl.price2:.1f}), "
              f"slope={tl.slope_per_bar:.3f}/bar")

        # Evaluate with different buffers
        print("\n--- Buffer comparison ---")
        results = compare_buffer_levels(prices, entry_bar=30, tl=tl)
        for r in results:
            status = "STOPPED" if r["stopped"] else "HELD"
            false = " (FALSE SIGNAL)" if r.get("was_false_signal") else ""
            print(f"Buffer {r['buffer_pct']}%: {status} at bar {r.get('stop_bar','—')}, "
                  f"P&L={r['pnl_pct']:+.1f}%{false}")
