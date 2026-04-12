"""
False Trend Line Breakout Detector — Chapter 11, Concept 5
============================================================
Detects when a trend line breakout fails and price returns back through the
trend line — a signal to trade in the ORIGINAL trend direction.

Schwager: "In my opinion, false trend breakout signals are considerably more
reliable than conventional trend breakout signals."

Confirmation: N closes (e.g., 2 or 3) back on the original side of the
trend line after the breakout.

Key feature: supports iterative trend line redefinition when multiple
successive false breakouts occur (Schwager's FCOJ example, Figure 11.7).
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TrendDirection(Enum):
    UP = "uptrend"
    DOWN = "downtrend"


@dataclass
class TrendLine:
    """A trend line defined by two anchor points."""
    direction: TrendDirection
    anchor1_date: pd.Timestamp
    anchor1_price: float
    anchor2_date: pd.Timestamp
    anchor2_price: float
    anchor1_idx: int
    anchor2_idx: int

    def price_at(self, idx: int) -> float:
        """Interpolate/extrapolate the trend line price at a given bar index."""
        dx = self.anchor2_idx - self.anchor1_idx
        if dx == 0:
            return self.anchor1_price
        slope = (self.anchor2_price - self.anchor1_price) / dx
        return self.anchor1_price + slope * (idx - self.anchor1_idx)


@dataclass
class FalseTrendLineBreakout:
    """A confirmed false trend line breakout."""
    trend_line: TrendLine
    breakout_date: pd.Timestamp
    breakout_bar_idx: int
    breakout_price: float           # Price at breakout (close)
    confirmation_date: pd.Timestamp
    confirmation_bar_idx: int
    entry_price: float              # Price at confirmation
    trade_direction: str            # 'short' for failed upside breakout of downtrend
    n_closes_required: int          # How many closes confirmed the failure
    trend_line_price_at_confirm: float  # Where the trend line was at confirmation


def find_downtrend_line(
    df: pd.DataFrame,
    min_touches: int = 2,
    tolerance_pct: float = 0.01,
) -> Optional[TrendLine]:
    """
    Find a downtrend line by connecting significant highs.

    Scans for the best-fitting line connecting at least `min_touches`
    swing highs where the high comes within `tolerance_pct` of the line.

    Parameters
    ----------
    df : DataFrame with ['high', 'low', 'close'] and integer-indexable
    min_touches : minimum swing highs the line must connect
    tolerance_pct : how close a high must be to the line to count as a touch

    Returns
    -------
    TrendLine or None
    """
    highs = df['high'].values
    n = len(highs)
    if n < 10:
        return None

    # Find swing highs (local maxima)
    swing_highs = []
    for i in range(2, n - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
           highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            swing_highs.append(i)

    if len(swing_highs) < min_touches:
        return None

    best_line = None
    best_touches = 0

    # Try all pairs of swing highs as anchor points
    for a in range(len(swing_highs)):
        for b in range(a + 1, len(swing_highs)):
            i1, i2 = swing_highs[a], swing_highs[b]
            p1, p2 = highs[i1], highs[i2]

            # Must be descending for downtrend
            if p2 >= p1:
                continue

            slope = (p2 - p1) / (i2 - i1)
            touches = 0
            valid = True

            for sh in swing_highs:
                line_price = p1 + slope * (sh - i1)
                diff = abs(highs[sh] - line_price) / line_price
                if diff < tolerance_pct:
                    touches += 1
                # Check no high significantly pierces above the line
                if highs[sh] > line_price * (1 + tolerance_pct * 2):
                    valid = False
                    break

            if valid and touches >= min_touches and touches > best_touches:
                best_touches = touches
                best_line = TrendLine(
                    direction=TrendDirection.DOWN,
                    anchor1_date=df.index[i1],
                    anchor1_price=p1,
                    anchor2_date=df.index[i2],
                    anchor2_price=p2,
                    anchor1_idx=i1,
                    anchor2_idx=i2,
                )

    return best_line


def find_uptrend_line(
    df: pd.DataFrame,
    min_touches: int = 2,
    tolerance_pct: float = 0.01,
) -> Optional[TrendLine]:
    """
    Find an uptrend line by connecting significant lows.
    Mirror of find_downtrend_line().
    """
    lows = df['low'].values
    n = len(lows)
    if n < 10:
        return None

    swing_lows = []
    for i in range(2, n - 2):
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
           lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            swing_lows.append(i)

    if len(swing_lows) < min_touches:
        return None

    best_line = None
    best_touches = 0

    for a in range(len(swing_lows)):
        for b in range(a + 1, len(swing_lows)):
            i1, i2 = swing_lows[a], swing_lows[b]
            p1, p2 = lows[i1], lows[i2]

            if p2 <= p1:
                continue

            slope = (p2 - p1) / (i2 - i1)
            touches = 0
            valid = True

            for sl in swing_lows:
                line_price = p1 + slope * (sl - i1)
                diff = abs(lows[sl] - line_price) / line_price
                if diff < tolerance_pct:
                    touches += 1
                if lows[sl] < line_price * (1 - tolerance_pct * 2):
                    valid = False
                    break

            if valid and touches >= min_touches and touches > best_touches:
                best_touches = touches
                best_line = TrendLine(
                    direction=TrendDirection.UP,
                    anchor1_date=df.index[i1],
                    anchor1_price=p1,
                    anchor2_date=df.index[i2],
                    anchor2_price=p2,
                    anchor1_idx=i1,
                    anchor2_idx=i2,
                )

    return best_line


def detect_false_trendline_breakout(
    df: pd.DataFrame,
    trend_line: TrendLine,
    n_closes_confirm: int = 2,
    scan_start: Optional[int] = None,
) -> Optional[FalseTrendLineBreakout]:
    """
    Detect a false breakout of a trend line.

    For a downtrend line: looks for an upside breakout (close above line)
    followed by N closes back below the line = failed upside breakout = SELL.

    For an uptrend line: looks for a downside breakout (close below line)
    followed by N closes back above the line = failed downside breakout = BUY.

    Parameters
    ----------
    df : DataFrame with ['high', 'low', 'close']
    trend_line : TrendLine object
    n_closes_confirm : closes required back on original side for confirmation
    scan_start : bar index to start scanning (default: after anchor2)

    Returns
    -------
    FalseTrendLineBreakout or None
    """
    start = scan_start if scan_start else trend_line.anchor2_idx + 1

    if trend_line.direction == TrendDirection.DOWN:
        # Look for upside breakout then failure
        breakout_idx = None
        breakout_price = None

        for i in range(start, len(df)):
            line_p = trend_line.price_at(i)
            if df.iloc[i]['close'] > line_p:
                breakout_idx = i
                breakout_price = df.iloc[i]['close']
                break

        if breakout_idx is None:
            return None

        # Now count closes back below the trend line
        closes_below = 0
        for j in range(breakout_idx + 1, len(df)):
            line_p = trend_line.price_at(j)
            if df.iloc[j]['close'] < line_p:
                closes_below += 1
                if closes_below >= n_closes_confirm:
                    return FalseTrendLineBreakout(
                        trend_line=trend_line,
                        breakout_date=df.index[breakout_idx],
                        breakout_bar_idx=breakout_idx,
                        breakout_price=breakout_price,
                        confirmation_date=df.index[j],
                        confirmation_bar_idx=j,
                        entry_price=df.iloc[j]['close'],
                        trade_direction='short',
                        n_closes_required=n_closes_confirm,
                        trend_line_price_at_confirm=line_p,
                    )
            else:
                closes_below = 0  # Reset: must be consecutive

    elif trend_line.direction == TrendDirection.UP:
        # Look for downside breakout then failure
        breakout_idx = None
        breakout_price = None

        for i in range(start, len(df)):
            line_p = trend_line.price_at(i)
            if df.iloc[i]['close'] < line_p:
                breakout_idx = i
                breakout_price = df.iloc[i]['close']
                break

        if breakout_idx is None:
            return None

        closes_above = 0
        for j in range(breakout_idx + 1, len(df)):
            line_p = trend_line.price_at(j)
            if df.iloc[j]['close'] > line_p:
                closes_above += 1
                if closes_above >= n_closes_confirm:
                    return FalseTrendLineBreakout(
                        trend_line=trend_line,
                        breakout_date=df.index[breakout_idx],
                        breakout_bar_idx=breakout_idx,
                        breakout_price=breakout_price,
                        confirmation_date=df.index[j],
                        confirmation_bar_idx=j,
                        entry_price=df.iloc[j]['close'],
                        trade_direction='long',
                        n_closes_required=n_closes_confirm,
                        trend_line_price_at_confirm=line_p,
                    )
            else:
                closes_above = 0

    return None


def scan_multiple_false_breakouts(
    df: pd.DataFrame,
    trend_line: TrendLine,
    n_closes_confirm: int = 2,
    max_signals: int = 5,
) -> list[FalseTrendLineBreakout]:
    """
    Scan for multiple successive false breakouts of the same trend line.

    Schwager's FCOJ example shows three successive false breakouts as the
    trend line is repeatedly redefined. This function finds all of them.

    Parameters
    ----------
    df : DataFrame with price data
    trend_line : initial TrendLine
    n_closes_confirm : closes required for each confirmation
    max_signals : maximum false breakouts to find

    Returns
    -------
    List of FalseTrendLineBreakout objects
    """
    signals = []
    scan_from = trend_line.anchor2_idx + 1

    for _ in range(max_signals):
        fbo = detect_false_trendline_breakout(
            df, trend_line, n_closes_confirm, scan_start=scan_from
        )
        if fbo is None:
            break

        signals.append(fbo)
        scan_from = fbo.confirmation_bar_idx + 1

        # Redefine trend line using the false breakout high as new anchor
        if trend_line.direction == TrendDirection.DOWN:
            new_anchor_idx = fbo.breakout_bar_idx
            new_anchor_price = df.iloc[new_anchor_idx]['high']
            trend_line = TrendLine(
                direction=TrendDirection.DOWN,
                anchor1_date=trend_line.anchor1_date,
                anchor1_price=trend_line.anchor1_price,
                anchor2_date=df.index[new_anchor_idx],
                anchor2_price=new_anchor_price,
                anchor1_idx=trend_line.anchor1_idx,
                anchor2_idx=new_anchor_idx,
            )
        else:
            new_anchor_idx = fbo.breakout_bar_idx
            new_anchor_price = df.iloc[new_anchor_idx]['low']
            trend_line = TrendLine(
                direction=TrendDirection.UP,
                anchor1_date=trend_line.anchor1_date,
                anchor1_price=trend_line.anchor1_price,
                anchor2_date=df.index[new_anchor_idx],
                anchor2_price=new_anchor_price,
                anchor1_idx=trend_line.anchor1_idx,
                anchor2_idx=new_anchor_idx,
            )

    return signals


# ── Example usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=80, freq='B')

    # Simulate downtrend with a false upside breakout
    prices = [100]
    for i in range(79):
        prices.append(prices[-1] - 0.3 + np.random.randn() * 1.2)
    prices = np.array(prices)

    # Inject a false breakout around bar 50
    prices[48:52] += 5  # spike above trend line
    prices[52:56] -= 6  # collapse back

    highs = prices + np.random.uniform(0.5, 2, 80)
    lows = prices - np.random.uniform(0.5, 2, 80)

    df = pd.DataFrame({
        'high': highs, 'low': lows, 'close': prices
    }, index=dates)

    # Find downtrend line
    tl = find_downtrend_line(df.iloc[:45], min_touches=2)
    if tl:
        print(f"Downtrend line found:")
        print(f"  Anchor 1: {tl.anchor1_date.date()} @ {tl.anchor1_price:.1f}")
        print(f"  Anchor 2: {tl.anchor2_date.date()} @ {tl.anchor2_price:.1f}")

        fbo = detect_false_trendline_breakout(df, tl, n_closes_confirm=2)
        if fbo:
            print(f"\nFalse breakout detected!")
            print(f"  Breakout date:     {fbo.breakout_date.date()}")
            print(f"  Breakout price:    {fbo.breakout_price:.1f}")
            print(f"  Confirmed on:      {fbo.confirmation_date.date()}")
            print(f"  Entry price:       {fbo.entry_price:.1f}")
            print(f"  Trade direction:   {fbo.trade_direction}")
            print(f"  Closes required:   {fbo.n_closes_required}")
        else:
            print("No false breakout detected.")
    else:
        print("No downtrend line found.")
