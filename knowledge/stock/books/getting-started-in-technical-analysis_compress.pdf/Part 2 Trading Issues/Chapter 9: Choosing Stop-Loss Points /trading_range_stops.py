"""
Trading Range Stops — Chapter 9, Concept 3
============================================
After a breakout from a trading range, use the range's interior
as a stop reference. Schwager identifies three zones with
distinct stop-placement implications.

This module provides:
  - TradingRange: dataclass representing a detected range
  - detect_trading_range: find the most recent consolidation range
  - trading_range_stop_price: compute stop at a given zone within the range
  - evaluate_zone_performance: backtest different stop zones
"""

from dataclasses import dataclass
from typing import Optional
import random


@dataclass
class TradingRange:
    """
    A detected trading range (consolidation zone).
    
    Attributes:
        high: Upper boundary of the range
        low: Lower boundary of the range
        start_bar: First bar of the range
        end_bar: Last bar of the range (breakout bar)
    """
    high: float
    low: float
    start_bar: int
    end_bar: int

    @property
    def width(self) -> float:
        """Absolute width of the range."""
        return self.high - self.low

    @property
    def width_pct(self) -> float:
        """Width as percentage of the midpoint."""
        mid = (self.high + self.low) / 2
        return self.width / mid * 100

    @property
    def midpoint(self) -> float:
        """Midpoint of the range."""
        return (self.high + self.low) / 2

    @property
    def duration(self) -> int:
        """Number of bars the range lasted."""
        return self.end_bar - self.start_bar

    def stop_at_zone(self, zone_pct: float) -> float:
        """
        Compute stop price at a given zone within the range.
        
        For a long trade (upside breakout):
          zone_pct=0   → stop at the upper boundary (near side) — TOO TIGHT
          zone_pct=50  → stop at the midpoint — RECOMMENDED
          zone_pct=75  → stop 75% of the way to the far boundary
          zone_pct=100 → stop at the lower boundary (far side) — MAXIMUM
        
        Args:
            zone_pct: 0-100, percentage depth into the range from the breakout side
        
        Returns:
            Stop price
        """
        return self.high - (self.width * zone_pct / 100)

    def classify_zone(self, stop_price: float) -> str:
        """
        Classify where a stop price falls relative to the range.
        Returns one of: 'above_range', 'near_boundary', 'recommended',
                        'far_boundary', 'below_range'
        """
        if stop_price > self.high:
            return "above_range"
        
        depth_pct = (self.high - stop_price) / self.width * 100
        
        if depth_pct < 25:
            return "near_boundary"      # Schwager: DON'T stop here
        elif depth_pct <= 100:
            return "recommended"        # Schwager: midpoint to far boundary
        else:
            return "below_range"


def detect_trading_range(
    prices: list[float],
    min_bars: int = 15,
    max_range_pct: float = 15.0,
) -> Optional[TradingRange]:
    """
    Detect the most recent trading range in a price series.
    
    A trading range is a period of at least min_bars where price
    oscillates within a band narrower than max_range_pct.
    
    Args:
        prices: Price series
        min_bars: Minimum number of bars for a valid range
        max_range_pct: Maximum width as % of midpoint to qualify as a range
    
    Returns:
        TradingRange or None
    """
    best = None
    n = len(prices)

    for end in range(n - 1, min_bars, -1):
        for start in range(max(0, end - 60), end - min_bars + 1):
            segment = prices[start:end + 1]
            hi, lo = max(segment), min(segment)
            mid = (hi + lo) / 2
            width_pct = (hi - lo) / mid * 100 if mid > 0 else 999

            if width_pct <= max_range_pct and (end - start) >= min_bars:
                candidate = TradingRange(
                    high=hi, low=lo, start_bar=start, end_bar=end
                )
                if best is None or candidate.duration > best.duration:
                    best = candidate

        if best is not None:
            return best

    return best


def trading_range_stop_price(
    tr: TradingRange,
    zone_pct: float = 50.0,
    buffer_pct: float = 0.0,
) -> float:
    """
    Compute the stop-loss price for a long trade after an upside breakout.
    
    Args:
        tr: The detected trading range
        zone_pct: How deep into the range (0=near, 50=mid, 100=far)
        buffer_pct: Extra buffer below the zone level (reduces false signals)
    
    Returns:
        Stop price
    """
    base_stop = tr.stop_at_zone(zone_pct)
    return base_stop * (1 - buffer_pct / 100)


def evaluate_zone_performance(
    n_trials: int = 500,
    zones: list[float] = [0, 25, 50, 75, 100],
    range_width_pct: float = 12.0,
    n_bars: int = 120,
    bull_prob: float = 0.65,
    seed_base: int = 7,
) -> list[dict]:
    """
    Backtest different stop zone placements across many simulated
    breakout scenarios.
    
    For each zone, tracks: avg P&L, worst P&L, false stop rate,
    and survival rate (never stopped).
    
    Args:
        n_trials: Number of simulated breakout scenarios
        zones: List of zone_pct values to test
        range_width_pct: Width of the trading range
        n_bars: Total bars per simulation
        bull_prob: Probability that the breakout is genuine (bullish)
        seed_base: Base random seed
    
    Returns:
        List of dicts, one per zone, with performance metrics
    """
    range_half = range_width_pct / 2
    results = []

    for zone_pct in zones:
        pnls = []
        false_stops = 0
        total_stopped = 0
        survived = 0

        for t in range(n_trials):
            random.seed(seed_base + t * 31)
            
            # Generate range then breakout
            range_low = 100 - range_half
            range_high = 100 + range_half
            
            prices = []
            for i in range(30):
                prices.append(range_low + random.random() * (range_high - range_low))
            
            entry_price = range_high + 1
            prices.append(entry_price)
            
            is_bull = random.random() < bull_prob
            for i in range(31, n_bars):
                drift = 0.18 if is_bull else -0.25
                vol = 1.5 + random.random() * 0.8
                prices.append(prices[-1] + drift + vol * (random.gauss(0, 1)))

            # Compute stop
            stop = range_high - (range_high - range_low) * (zone_pct / 100)
            
            stopped = False
            for i in range(31, len(prices)):
                if prices[i] <= stop:
                    pnl = (prices[i] - entry_price) / entry_price * 100
                    pnls.append(pnl)
                    total_stopped += 1
                    # Check if false signal (price recovers within 30 bars)
                    future = prices[i + 1:min(i + 30, len(prices))]
                    if any(p > entry_price for p in future):
                        false_stops += 1
                    stopped = True
                    break

            if not stopped:
                pnl = (prices[-1] - entry_price) / entry_price * 100
                pnls.append(pnl)
                survived += 1

        zone_names = {
            0: "Near boundary",
            25: "25% into range",
            50: "Midpoint",
            75: "75% into range",
            100: "Far boundary",
        }
        
        risk_pct = (range_high - stop) / range_high * 100 if zone_pct > 0 else 0
        
        results.append({
            "zone_pct": zone_pct,
            "zone_name": zone_names.get(zone_pct, f"{zone_pct}%"),
            "risk_per_trade_pct": round(risk_pct, 1),
            "avg_pnl": round(sum(pnls) / len(pnls), 2),
            "worst_pnl": round(min(pnls), 2),
            "false_stop_rate": round(false_stops / max(total_stopped, 1) * 100, 1),
            "survival_rate": round(survived / n_trials * 100, 1),
            "n_stopped": total_stopped,
        })

    return results


# --- Demo ---
if __name__ == "__main__":
    # 1. Create a trading range
    tr = TradingRange(high=112.0, low=94.0, start_bar=0, end_bar=30)
    print(f"Range: {tr.low}–{tr.high}, width={tr.width:.1f} ({tr.width_pct:.1f}%), "
          f"midpoint={tr.midpoint:.1f}")

    # 2. Show stop prices at different zones
    print("\n--- Stop zones ---")
    for z in [0, 25, 50, 75, 100]:
        stop = tr.stop_at_zone(z)
        zone_class = tr.classify_zone(stop)
        print(f"  Zone {z:3d}%: stop={stop:.1f}, class={zone_class}")

    # 3. Backtest zone performance
    print("\n--- Zone performance (500 trials) ---")
    results = evaluate_zone_performance(n_trials=500)
    print(f"{'Zone':<20} {'Risk':>6} {'Avg P&L':>8} {'Worst':>8} {'False%':>8} {'Survived':>10}")
    print("-" * 65)
    for r in results:
        print(f"{r['zone_name']:<20} {r['risk_per_trade_pct']:>5.1f}% "
              f"{r['avg_pnl']:>+7.1f}% {r['worst_pnl']:>+7.1f}% "
              f"{r['false_stop_rate']:>7.1f}% {r['survival_rate']:>9.1f}%")
