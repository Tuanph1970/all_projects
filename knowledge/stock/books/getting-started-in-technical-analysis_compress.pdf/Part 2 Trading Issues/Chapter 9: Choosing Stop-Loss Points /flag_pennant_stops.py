"""
Flag and Pennant Stops — Chapter 9, Concept 4
===============================================
After a breakout from a flag or pennant (a narrow, short-duration
consolidation within a trend), the return to the opposite boundary
signals trend reversal → stop placement.

Flags = parallel boundaries with slight counter-trend slope.
Pennants = converging boundaries (like a tiny triangle).

This module provides:
  - FlagPattern: dataclass representing a detected flag/pennant
  - detect_flag: find a flag-like consolidation after a trend move
  - flag_stop_price: compute the stop at the opposite boundary
  - evaluate_flag_stop: backtest flag stop performance
  - compare_flag_vs_range_stops: show why flag stops are tighter
"""

from dataclasses import dataclass
from typing import Optional
import random
import math


@dataclass
class FlagPattern:
    """
    A detected flag or pennant pattern.
    
    Attributes:
        pattern_type: 'flag' (parallel) or 'pennant' (converging)
        direction: 'bullish' (pause in uptrend) or 'bearish' (pause in downtrend)
        upper_start: Upper boundary price at start of pattern
        upper_end: Upper boundary price at end of pattern
        lower_start: Lower boundary price at start of pattern
        lower_end: Lower boundary price at end of pattern
        start_bar: First bar of the pattern
        end_bar: Last bar of the pattern
    """
    pattern_type: str      # 'flag' or 'pennant'
    direction: str         # 'bullish' or 'bearish'
    upper_start: float
    upper_end: float
    lower_start: float
    lower_end: float
    start_bar: int
    end_bar: int

    @property
    def duration(self) -> int:
        return self.end_bar - self.start_bar

    @property
    def width_at_start(self) -> float:
        return self.upper_start - self.lower_start

    @property
    def width_at_end(self) -> float:
        return self.upper_end - self.lower_end

    @property
    def width_pct(self) -> float:
        """Average width as percentage of midpoint."""
        mid = (self.upper_start + self.lower_start) / 2
        avg_width = (self.width_at_start + self.width_at_end) / 2
        return avg_width / mid * 100

    @property
    def is_converging(self) -> bool:
        """True if boundaries converge (pennant-like)."""
        return self.width_at_end < self.width_at_start * 0.7

    @property
    def stop_price(self) -> float:
        """
        Stop at the opposite boundary (at the end of the pattern).
        For bullish: stop at lower boundary.
        For bearish: stop at upper boundary.
        """
        if self.direction == 'bullish':
            return self.lower_end
        else:
            return self.upper_end

    @property
    def breakout_price(self) -> float:
        """Expected breakout level (continuation side)."""
        if self.direction == 'bullish':
            return self.upper_end
        else:
            return self.lower_end

    @property
    def risk_pct(self) -> float:
        """Risk from breakout to stop as percentage."""
        return abs(self.breakout_price - self.stop_price) / self.breakout_price * 100


def detect_flag(
    prices: list[float],
    min_trend_bars: int = 10,
    min_trend_pct: float = 5.0,
    max_flag_bars: int = 20,
    min_flag_bars: int = 5,
    max_flag_width_pct: float = 8.0,
) -> Optional[FlagPattern]:
    """
    Detect a bullish flag pattern: a strong uptrend followed by
    a narrow, short consolidation.
    
    Args:
        prices: Price series
        min_trend_bars: Minimum bars for the prior trend move
        min_trend_pct: Minimum % move to qualify as a trend
        max_flag_bars: Maximum duration of the flag
        min_flag_bars: Minimum duration of the flag
        max_flag_width_pct: Maximum flag width as % of price
    
    Returns:
        FlagPattern or None
    """
    n = len(prices)
    if n < min_trend_bars + min_flag_bars:
        return None

    # Find the trend peak
    peak_bar = None
    peak_price = 0
    for i in range(min_trend_bars, n - min_flag_bars):
        trend_start = prices[i - min_trend_bars]
        trend_pct = (prices[i] - trend_start) / trend_start * 100
        if trend_pct >= min_trend_pct and prices[i] > peak_price:
            peak_price = prices[i]
            peak_bar = i

    if peak_bar is None:
        return None

    # Look for flag after peak
    for flag_len in range(min_flag_bars, min(max_flag_bars, n - peak_bar)):
        segment = prices[peak_bar:peak_bar + flag_len]
        hi, lo = max(segment), min(segment)
        mid = (hi + lo) / 2
        width_pct = (hi - lo) / mid * 100

        if width_pct <= max_flag_width_pct and flag_len >= min_flag_bars:
            # Check if it slopes down slightly (counter-trend)
            first_half = sum(segment[:len(segment)//2]) / (len(segment)//2)
            second_half = sum(segment[len(segment)//2:]) / (len(segment) - len(segment)//2)
            is_converging = (hi - lo) > (max(segment[-3:]) - min(segment[-3:])) * 1.5

            return FlagPattern(
                pattern_type='pennant' if is_converging else 'flag',
                direction='bullish',
                upper_start=max(segment[:len(segment)//2]),
                upper_end=max(segment[len(segment)//2:]),
                lower_start=min(segment[:len(segment)//2]),
                lower_end=min(segment[len(segment)//2:]),
                start_bar=peak_bar,
                end_bar=peak_bar + flag_len - 1,
            )

    return None


def flag_stop_price(flag: FlagPattern, buffer_pct: float = 0.0) -> float:
    """
    Compute stop price for a flag/pennant pattern.
    Uses the opposite boundary at the end of the pattern.
    
    Args:
        flag: Detected flag pattern
        buffer_pct: Optional buffer beyond the boundary
    
    Returns:
        Stop price
    """
    base = flag.stop_price
    if flag.direction == 'bullish':
        return base * (1 - buffer_pct / 100)
    else:
        return base * (1 + buffer_pct / 100)


def evaluate_flag_stop(
    n_trials: int = 500,
    flag_width_pct: float = 4.0,
    trend_strength: float = 0.65,
    seed_base: int = 13,
) -> dict:
    """
    Backtest flag stop performance across simulated scenarios.
    
    Args:
        n_trials: Number of simulated flag breakouts
        flag_width_pct: Width of the flag as % of price
        trend_strength: Probability the trend continues (0-1)
        seed_base: Random seed base
    
    Returns:
        Performance metrics
    """
    pnls = []
    false_stops = 0
    total_stopped = 0
    survived = 0

    for t in range(n_trials):
        random.seed(seed_base + t * 17)
        
        # Generate: uptrend → flag → outcome
        price = 100.0
        prices = []
        
        # Uptrend (15 bars)
        for i in range(15):
            price += 0.5 + random.gauss(0, 0.3)
            prices.append(price)
        
        # Flag (8 bars, narrow consolidation)
        flag_hi = price
        flag_lo = price * (1 - flag_width_pct / 100)
        for i in range(8):
            prices.append(flag_lo + random.random() * (flag_hi - flag_lo))
        
        # Breakout + outcome
        entry_price = flag_hi + 0.5
        prices.append(entry_price)
        stop = flag_lo
        
        continues = random.random() < trend_strength
        for i in range(40):
            drift = 0.2 if continues else -0.15
            vol = 0.8 + random.random() * 0.5
            prices.append(prices[-1] + drift + vol * random.gauss(0, 1))
        
        # Evaluate
        stopped = False
        for i in range(24, len(prices)):
            if prices[i] <= stop:
                pnl = (prices[i] - entry_price) / entry_price * 100
                pnls.append(pnl)
                total_stopped += 1
                future = prices[i+1:min(i+20, len(prices))]
                if any(p > entry_price for p in future):
                    false_stops += 1
                stopped = True
                break
        
        if not stopped:
            pnl = (prices[-1] - entry_price) / entry_price * 100
            pnls.append(pnl)
            survived += 1

    return {
        "n_trials": n_trials,
        "flag_width_pct": flag_width_pct,
        "risk_per_trade": round(flag_width_pct, 1),
        "avg_pnl": round(sum(pnls) / len(pnls), 2),
        "worst_pnl": round(min(pnls), 2),
        "best_pnl": round(max(pnls), 2),
        "false_stop_rate": round(false_stops / max(total_stopped, 1) * 100, 1),
        "survival_rate": round(survived / n_trials * 100, 1),
    }


def compare_flag_vs_range_stops(n_trials: int = 500) -> dict:
    """
    Compare flag stops (narrow) vs trading range stops (wide)
    to demonstrate the risk advantage of flag-based entries.
    """
    flag_result = evaluate_flag_stop(
        n_trials=n_trials, flag_width_pct=4.0, seed_base=13
    )
    
    # Simulate wider range stop for comparison
    range_result = evaluate_flag_stop(
        n_trials=n_trials, flag_width_pct=12.0, seed_base=13
    )

    return {
        "flag_stop": flag_result,
        "range_stop": range_result,
        "risk_reduction": round(
            (1 - flag_result["risk_per_trade"] / range_result["risk_per_trade"]) * 100, 1
        ),
    }


# --- Demo ---
if __name__ == "__main__":
    # 1. Create a flag pattern
    flag = FlagPattern(
        pattern_type='flag',
        direction='bullish',
        upper_start=122.0, upper_end=119.0,
        lower_start=118.0, lower_end=116.5,
        start_bar=20, end_bar=34,
    )
    print(f"Pattern: {flag.pattern_type} ({flag.direction})")
    print(f"Width: {flag.width_pct:.1f}%, Duration: {flag.duration} bars")
    print(f"Breakout: {flag.breakout_price:.1f}, Stop: {flag.stop_price:.1f}, "
          f"Risk: {flag.risk_pct:.1f}%")

    # 2. Backtest flag stops at different widths
    print("\n--- Flag width comparison ---")
    print(f"{'Width':>8} {'Risk':>6} {'Avg P&L':>8} {'Worst':>8} {'False%':>8}")
    print("-" * 45)
    for w in [2.0, 4.0, 6.0, 8.0]:
        r = evaluate_flag_stop(n_trials=500, flag_width_pct=w)
        print(f"{w:>7.1f}% {r['risk_per_trade']:>5.1f}% "
              f"{r['avg_pnl']:>+7.1f}% {r['worst_pnl']:>+7.1f}% "
              f"{r['false_stop_rate']:>7.1f}%")

    # 3. Flag vs range comparison
    print("\n--- Flag stop vs trading range stop ---")
    comp = compare_flag_vs_range_stops()
    print(f"Flag (4% width):  risk={comp['flag_stop']['risk_per_trade']}%, "
          f"avg={comp['flag_stop']['avg_pnl']:+.1f}%, "
          f"false={comp['flag_stop']['false_stop_rate']}%")
    print(f"Range (12% width): risk={comp['range_stop']['risk_per_trade']}%, "
          f"avg={comp['range_stop']['avg_pnl']:+.1f}%, "
          f"false={comp['range_stop']['false_stop_rate']}%")
    print(f"Risk reduction: {comp['risk_reduction']}%")
