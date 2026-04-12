"""
Relative High/Low Stops — Chapter 9, Concept 6
================================================
Use the most recent relative high or relative low as the stop point.
A relative low is a day whose low is below the lows of the preceding
AND succeeding N days (N = 5 to 15 per Schwager).

This is the most versatile stop reference: it works for both
initial stops AND as the anchor for trailing stops.

This module provides:
  - find_relative_lows: detect swing lows with configurable N
  - find_relative_highs: detect swing highs with configurable N
  - nearest_relative_low_stop: get the most recent relative low as stop
  - evaluate_n_parameter: compare performance across different N values
  - relative_low_trailing_stop: implement Schwager's Walt Disney example
"""

from dataclasses import dataclass
from typing import Optional
import random


@dataclass
class SwingPoint:
    """A detected relative high or relative low."""
    bar_index: int
    price: float
    n_parameter: int
    point_type: str  # 'low' or 'high'

    @property
    def significance(self) -> str:
        """Qualitative significance based on N."""
        if self.n_parameter <= 5:
            return "minor"
        elif self.n_parameter <= 10:
            return "moderate"
        else:
            return "major"


def find_relative_lows(
    prices: list[float],
    n: int = 5,
) -> list[SwingPoint]:
    """
    Find relative lows in a price series.
    
    A relative low at index i means prices[i] is the lowest
    price in the window [i-n, i+n].
    
    Schwager: "A reasonable range for N is between 5 and 15."
    
    Args:
        prices: Price series
        n: Lookback AND look-forward window size
    
    Returns:
        List of SwingPoint objects
    """
    lows = []
    for i in range(n, len(prices) - n):
        window = prices[i - n: i + n + 1]
        if prices[i] == min(window):
            # Ensure it's strictly the minimum (handle ties)
            if window.count(prices[i]) == 1 or i == prices.index(min(window), i - n):
                lows.append(SwingPoint(
                    bar_index=i,
                    price=prices[i],
                    n_parameter=n,
                    point_type='low',
                ))
    return lows


def find_relative_highs(
    prices: list[float],
    n: int = 5,
) -> list[SwingPoint]:
    """
    Find relative highs in a price series.
    Analogous to find_relative_lows.
    """
    highs = []
    for i in range(n, len(prices) - n):
        window = prices[i - n: i + n + 1]
        if prices[i] == max(window):
            if window.count(prices[i]) == 1 or i == prices.index(max(window), i - n):
                highs.append(SwingPoint(
                    bar_index=i,
                    price=prices[i],
                    n_parameter=n,
                    point_type='high',
                ))
    return highs


def nearest_relative_low_stop(
    prices: list[float],
    entry_bar: int,
    n: int = 5,
    max_risk_pct: float = 15.0,
) -> dict:
    """
    Find the most recent relative low before the entry bar
    and evaluate it as a stop level.
    
    Args:
        prices: Price series
        entry_bar: Bar index of trade entry
        n: Parameter for relative low detection
        max_risk_pct: Maximum acceptable risk percentage
    
    Returns:
        dict with stop_price, risk_pct, swing_point, and warnings
    """
    lows = find_relative_lows(prices[:entry_bar + n + 1], n)
    prior_lows = [l for l in lows if l.bar_index < entry_bar]
    
    if not prior_lows:
        return {
            "stop_price": None,
            "risk_pct": None,
            "swing_point": None,
            "warnings": ["No relative low found before entry bar"],
        }
    
    nearest = prior_lows[-1]
    entry_price = prices[entry_bar]
    risk_pct = (entry_price - nearest.price) / entry_price * 100
    
    warnings = []
    if risk_pct > max_risk_pct:
        warnings.append(
            f"Risk of {risk_pct:.1f}% exceeds max {max_risk_pct:.1f}%. "
            f"Consider a money stop instead (see Schwager's lumber example)."
        )
    
    return {
        "stop_price": nearest.price,
        "risk_pct": round(risk_pct, 2),
        "swing_point": nearest,
        "warnings": warnings,
    }


def relative_low_trailing_stop(
    prices: list[float],
    entry_bar: int,
    n: int = 10,
) -> dict:
    """
    Implement Schwager's trailing stop keyed to relative lows
    (the Walt Disney example).
    
    Rule: the stop is raised to each new relative low as the
    market moves to new high ground. The position is liquidated
    on a close below the most recent relative low.
    
    Args:
        prices: Price series
        entry_bar: Bar index of trade entry
        n: Parameter for relative low detection
    
    Returns:
        dict with stop_history (list of {bar, stop_price}),
        exit_bar, exit_price, pnl_pct
    """
    entry_price = prices[entry_bar]
    highest_since_entry = entry_price
    current_stop = None
    stop_history = []
    
    # Find initial stop: nearest relative low before entry
    initial_lows = find_relative_lows(prices[:entry_bar + n + 1], n)
    prior_lows = [l for l in initial_lows if l.bar_index < entry_bar]
    
    if prior_lows:
        current_stop = prior_lows[-1].price
        stop_history.append({
            "bar": entry_bar,
            "stop_price": current_stop,
            "reason": f"Initial: relative low at bar {prior_lows[-1].bar_index}",
        })
    
    # Walk forward
    for i in range(entry_bar + 1, len(prices)):
        # Check if stopped
        if current_stop is not None and prices[i] <= current_stop:
            return {
                "stop_history": stop_history,
                "exit_bar": i,
                "exit_price": round(prices[i], 2),
                "entry_price": round(entry_price, 2),
                "pnl_pct": round((prices[i] - entry_price) / entry_price * 100, 2),
                "bars_held": i - entry_bar,
            }
        
        # Check for new high ground
        if prices[i] > highest_since_entry:
            highest_since_entry = prices[i]
            
            # Look for new relative low to raise stop to
            # We need enough forward data to confirm the relative low
            if i >= n:
                new_lows = find_relative_lows(prices[:min(i + n + 1, len(prices))], n)
                candidate_lows = [
                    l for l in new_lows
                    if l.bar_index > entry_bar
                    and l.bar_index < i
                    and l.price > (current_stop or 0)
                ]
                
                if candidate_lows:
                    new_stop_point = candidate_lows[-1]
                    current_stop = new_stop_point.price
                    stop_history.append({
                        "bar": i,
                        "stop_price": current_stop,
                        "reason": f"Raised: new relative low at bar {new_stop_point.bar_index}",
                    })
    
    # Never stopped
    final = prices[-1]
    return {
        "stop_history": stop_history,
        "exit_bar": len(prices) - 1,
        "exit_price": round(final, 2),
        "entry_price": round(entry_price, 2),
        "pnl_pct": round((final - entry_price) / entry_price * 100, 2),
        "bars_held": len(prices) - 1 - entry_bar,
    }


def evaluate_n_parameter(
    n_values: list[int] = [3, 5, 7, 10, 12, 15],
    n_trials: int = 500,
    seed_base: int = 7,
) -> list[dict]:
    """
    Compare relative low stop performance across different N values.
    
    Returns:
        List of dicts with performance metrics per N
    """
    results = []
    
    for n in n_values:
        pnls = []
        risks = []
        false_stops = 0
        total_stopped = 0

        for t in range(n_trials):
            random.seed(seed_base + t * 41)
            
            # Generate uptrend with reversal
            prices = [100.0]
            for i in range(1, 100):
                drift = 0.2 if i < 65 else -0.15
                vol = 1.5 + random.random() * 0.6
                prices.append(prices[-1] + drift + vol * (random.gauss(0, 1) - 0.02))
            
            # Entry at bar 55
            entry_bar = 55
            entry_price = prices[entry_bar]
            
            # Find nearest relative low
            result = nearest_relative_low_stop(prices, entry_bar, n)
            if result["stop_price"] is None:
                continue
            
            stop = result["stop_price"]
            risks.append(result["risk_pct"])
            
            # Evaluate
            stopped = False
            for i in range(entry_bar + 1, len(prices)):
                if prices[i] <= stop:
                    pnl = (prices[i] - entry_price) / entry_price * 100
                    pnls.append(pnl)
                    total_stopped += 1
                    future = prices[i + 1:min(i + 20, len(prices))]
                    if any(p > entry_price for p in future):
                        false_stops += 1
                    stopped = True
                    break
            
            if not stopped:
                pnl = (prices[-1] - entry_price) / entry_price * 100
                pnls.append(pnl)
        
        results.append({
            "n": n,
            "avg_risk_pct": round(sum(risks) / max(len(risks), 1), 1),
            "avg_pnl": round(sum(pnls) / max(len(pnls), 1), 2),
            "worst_pnl": round(min(pnls) if pnls else 0, 2),
            "false_stop_rate": round(false_stops / max(total_stopped, 1) * 100, 1),
            "total_stopped": total_stopped,
        })
    
    return results


# --- Demo ---
if __name__ == "__main__":
    random.seed(42)
    
    # 1. Generate sample data
    prices = [100.0]
    for i in range(1, 80):
        drift = 0.2 if i < 50 else -0.1
        prices.append(prices[-1] + drift + 1.5 * random.gauss(0, 1))
    
    # 2. Find relative lows at different N
    print("--- Relative lows at different N ---")
    for n in [5, 10, 15]:
        lows = find_relative_lows(prices, n)
        print(f"  N={n:2d}: {len(lows)} relative lows found "
              f"({', '.join(f'bar {l.bar_index}={l.price:.1f}' for l in lows[:4])}{'...' if len(lows)>4 else ''})")
    
    # 3. Get stop from nearest relative low
    stop_info = nearest_relative_low_stop(prices, entry_bar=40, n=10)
    print(f"\nNearest relative low stop (N=10, entry at bar 40):")
    print(f"  Stop: {stop_info['stop_price']:.1f}, Risk: {stop_info['risk_pct']}%")
    if stop_info['warnings']:
        for w in stop_info['warnings']:
            print(f"  WARNING: {w}")
    
    # 4. Compare N values
    print("\n--- N parameter comparison (500 trials) ---")
    print(f"{'N':>4} {'Avg Risk':>9} {'Avg P&L':>8} {'Worst':>8} {'False%':>8}")
    print("-" * 42)
    for r in evaluate_n_parameter():
        print(f"N={r['n']:<2d} {r['avg_risk_pct']:>8.1f}% "
              f"{r['avg_pnl']:>+7.1f}% {r['worst_pnl']:>+7.1f}% "
              f"{r['false_stop_rate']:>7.1f}%")
    
    # 5. Trailing stop demo
    print("\n--- Trailing stop (N=10) ---")
    trail = relative_low_trailing_stop(prices, entry_bar=20, n=10)
    print(f"Entry: {trail['entry_price']:.1f} at bar 20")
    for s in trail['stop_history']:
        print(f"  Bar {s['bar']}: stop → {s['stop_price']:.1f} ({s['reason']})")
    print(f"Exit: {trail['exit_price']:.1f} at bar {trail['exit_bar']}, "
          f"P&L: {trail['pnl_pct']:+.1f}%, held {trail['bars_held']} bars")
