"""
Concepts 3, 4, 5: Trend Lines and Trend Channels.

- Uptrend line  : straight line connecting successive higher lows
- Downtrend line: straight line connecting successive lower highs
- Channel       : trend line + parallel return line on the opposite side

Trend Line Rules (from Schwager Ch.3, p.34-35):
  Rule 1: Pullbacks toward the trend line are entries in trend direction.
  Rule 2: Penetration (esp. on a close) is a reversal signal — usually
          confirmed by a minimum % move or N closes through the line.
  Rule 3: Opposite end of the channel is a profit-taking zone.

Reference: Schwager, "Getting Started in Technical Analysis", Ch. 3.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class TrendLine:
    x1: int          # bar index of first anchor
    y1: float        # price at first anchor
    slope: float     # price units per bar
    kind: str        # "uptrend" or "downtrend"

    def value_at(self, x: int) -> float:
        """The trend-line price at bar `x`."""
        return self.y1 + self.slope * (x - self.x1)


def fit_uptrend_line(prices: List[float], pivot_lows_idx: List[int]) -> Optional[TrendLine]:
    """Fit an uptrend line through two of the most recent qualifying lows."""
    if len(pivot_lows_idx) < 2:
        return None
    a, b = pivot_lows_idx[-2], pivot_lows_idx[-1]
    slope = (prices[b] - prices[a]) / (b - a)
    return TrendLine(x1=a, y1=prices[a], slope=slope, kind="uptrend")


def fit_downtrend_line(prices: List[float], pivot_highs_idx: List[int]) -> Optional[TrendLine]:
    """Fit a downtrend line through two of the most recent qualifying highs."""
    if len(pivot_highs_idx) < 2:
        return None
    a, b = pivot_highs_idx[-2], pivot_highs_idx[-1]
    slope = (prices[b] - prices[a]) / (b - a)
    return TrendLine(x1=a, y1=prices[a], slope=slope, kind="downtrend")


def channel(line: TrendLine, prices: List[float], pivots_opposite: List[int]) -> Tuple[TrendLine, TrendLine]:
    """Build a channel: the trend line plus a parallel line passing
    through the most extreme opposite pivot."""
    if not pivots_opposite:
        return line, line
    if line.kind == "uptrend":
        idx = max(pivots_opposite, key=lambda i: prices[i] - line.value_at(i))
    else:
        idx = max(pivots_opposite, key=lambda i: line.value_at(i) - prices[i])
    parallel = TrendLine(x1=idx, y1=prices[idx], slope=line.slope, kind=line.kind + "_parallel")
    return line, parallel


# ---------- Trend-line rule implementations ----------

def trend_line_signal(line: TrendLine, prices: List[float], current_bar: int,
                      confirm_closes: int = 1, pct_threshold: float = 0.0) -> Optional[str]:
    """Apply Rule 2: detect a confirmed trend-line penetration.

    Args:
        line: the trend line being monitored
        prices: full close-price series
        current_bar: index to evaluate at
        confirm_closes: number of consecutive closes beyond the line required
        pct_threshold: additional % buffer beyond the line (e.g. 0.02 = 2%)

    Returns: "buy", "sell", or None.
    """
    if current_bar - confirm_closes + 1 < 0:
        return None
    closes = prices[current_bar - confirm_closes + 1: current_bar + 1]
    line_vals = [line.value_at(i) for i in range(current_bar - confirm_closes + 1, current_bar + 1)]

    if line.kind == "uptrend":
        # Sell signal: every close in window below line by at least pct_threshold
        if all(c < lv * (1 - pct_threshold) for c, lv in zip(closes, line_vals)):
            return "sell"
    else:
        if all(c > lv * (1 + pct_threshold) for c, lv in zip(closes, line_vals)):
            return "buy"
    return None


def near_trend_line(line: TrendLine, price: float, bar: int, tolerance_pct: float = 0.01) -> bool:
    """Apply Rule 1: detect price pullback to within tolerance of the line."""
    target = line.value_at(bar)
    return abs(price - target) / target <= tolerance_pct


if __name__ == "__main__":
    import random
    random.seed(1)
    n = 80
    closes = [60 + 0.25 * i + 2 * (random.random() - 0.5) for i in range(n)]
    pivot_lows = [12, 32, 55]

    line = fit_uptrend_line(closes, pivot_lows)
    print(f"Uptrend line: y1={line.y1:.2f} slope={line.slope:.4f}")
    print(f"  value at bar 70: {line.value_at(70):.2f}")
    print(f"  value at bar 79: {line.value_at(79):.2f}")

    # Test signals
    for bar in [60, 75, 79]:
        sig = trend_line_signal(line, closes, bar, confirm_closes=2)
        print(f"  bar {bar}: close={closes[bar]:.2f}, line={line.value_at(bar):.2f}, signal={sig}")
