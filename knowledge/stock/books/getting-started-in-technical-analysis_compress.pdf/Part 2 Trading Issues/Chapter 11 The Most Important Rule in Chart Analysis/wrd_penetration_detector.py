"""
Wide-Ranging Day Extreme Penetration Detector — Chapter 11, Concept 8
======================================================================
Wide-ranging days (WRDs) with strong/weak closes normally lead to price
extensions in the same direction. When a subsequent close penetrates the
OPPOSITE extreme of a WRD, the original day becomes a failed signal.

- Close above high of downside WRD → bullish failed signal (BUY)
- Close below low of upside WRD → bearish failed signal (SELL)

Confluence: multiple WRD penetrations compounding, or the penetration
itself being a WRD, amplifies the signal (Schwager's DuPont and sugar
examples).

Schwager: "The close above the high price of a downside wide-ranging day
or below the low price of an upside wide-ranging day can be viewed as
confirming such days as failed signals."
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class WRDType(Enum):
    UPSIDE = "upside"     # Close near high → bullish continuation expected
    DOWNSIDE = "downside"  # Close near low → bearish continuation expected


@dataclass
class WideRangingDay:
    """A wide-ranging day identified in the data."""
    date: pd.Timestamp
    bar_idx: int
    wrd_type: WRDType
    high: float
    low: float
    close: float
    range_size: float         # high - low
    range_ratio: float        # ratio vs. average range (how "wide")
    close_position: float     # 0 = at low, 1 = at high


@dataclass
class WRDPenetration:
    """A confirmed WRD penetration — the failed signal."""
    wrd: WideRangingDay
    penetration_date: pd.Timestamp
    penetration_bar_idx: int
    penetration_price: float       # Close at penetration
    trade_direction: str           # 'long' or 'short'
    bars_elapsed: int              # Bars between WRD and penetration
    penetration_is_wrd: bool       # Is the penetrating bar itself a WRD?


def detect_wide_ranging_days(
    df: pd.DataFrame,
    range_multiplier: float = 1.5,
    lookback: int = 20,
    close_threshold: float = 0.3,
) -> list[WideRangingDay]:
    """
    Find wide-ranging days in the data.

    A WRD is a bar whose range (high - low) exceeds the average range
    of the preceding `lookback` bars by `range_multiplier` times.

    WRD type is determined by close position:
    - Close in upper `close_threshold` of range → upside WRD
    - Close in lower `close_threshold` of range → downside WRD

    Parameters
    ----------
    df : DataFrame with ['high', 'low', 'close']
    range_multiplier : how many times avg range for WRD qualification
    lookback : bars to compute average range
    close_threshold : proportion from extreme to qualify close position

    Returns
    -------
    List of WideRangingDay objects
    """
    wrds = []

    for i in range(lookback, len(df)):
        bar = df.iloc[i]
        bar_range = bar['high'] - bar['low']

        if bar_range <= 0:
            continue

        # Average range of preceding bars
        avg_range = (df.iloc[i - lookback:i]['high'] -
                     df.iloc[i - lookback:i]['low']).mean()

        if avg_range <= 0:
            continue

        range_ratio = bar_range / avg_range

        if range_ratio >= range_multiplier:
            close_pos = (bar['close'] - bar['low']) / bar_range

            if close_pos >= (1 - close_threshold):
                wrd_type = WRDType.UPSIDE
            elif close_pos <= close_threshold:
                wrd_type = WRDType.DOWNSIDE
            else:
                continue  # Close in middle — not a clear WRD

            wrds.append(WideRangingDay(
                date=df.index[i],
                bar_idx=i,
                wrd_type=wrd_type,
                high=bar['high'],
                low=bar['low'],
                close=bar['close'],
                range_size=bar_range,
                range_ratio=round(range_ratio, 2),
                close_position=round(close_pos, 2),
            ))

    return wrds


def detect_wrd_penetration(
    df: pd.DataFrame,
    wrd: WideRangingDay,
    lookback_for_wrd_check: int = 20,
    range_multiplier_for_wrd: float = 1.5,
) -> Optional[WRDPenetration]:
    """
    Check if a WRD's opposite extreme is later penetrated by a close.

    - Downside WRD: close above WRD high → BUY
    - Upside WRD: close below WRD low → SELL

    Also checks whether the penetrating bar is itself a WRD (confluence).

    Parameters
    ----------
    df : DataFrame with price data
    wrd : WideRangingDay to monitor
    lookback_for_wrd_check : lookback for checking if penetration bar is WRD
    range_multiplier_for_wrd : threshold for WRD check on penetration bar

    Returns
    -------
    WRDPenetration or None
    """
    for i in range(wrd.bar_idx + 1, len(df)):
        bar = df.iloc[i]
        bar_range = bar['high'] - bar['low']

        penetrated = False
        trade_dir = ''

        if wrd.wrd_type == WRDType.DOWNSIDE:
            # Close above WRD high → bullish
            if bar['close'] > wrd.high:
                penetrated = True
                trade_dir = 'long'

        elif wrd.wrd_type == WRDType.UPSIDE:
            # Close below WRD low → bearish
            if bar['close'] < wrd.low:
                penetrated = True
                trade_dir = 'short'

        if penetrated:
            # Check if penetration bar is itself a WRD
            is_wrd = False
            if i >= lookback_for_wrd_check:
                avg_range = (df.iloc[i - lookback_for_wrd_check:i]['high'] -
                             df.iloc[i - lookback_for_wrd_check:i]['low']).mean()
                if avg_range > 0 and bar_range / avg_range >= range_multiplier_for_wrd:
                    is_wrd = True

            return WRDPenetration(
                wrd=wrd,
                penetration_date=df.index[i],
                penetration_bar_idx=i,
                penetration_price=bar['close'],
                trade_direction=trade_dir,
                bars_elapsed=i - wrd.bar_idx,
                penetration_is_wrd=is_wrd,
            )

    return None


def scan_wrd_confluence(
    df: pd.DataFrame,
    range_multiplier: float = 1.5,
    lookback: int = 20,
    proximity_bars: int = 10,
) -> list[dict]:
    """
    Find clusters of WRD penetrations that compound (confluence).

    Schwager's sugar example: two downside WRDs in close proximity both
    penetrated upside, with an upside WRD between them.

    Parameters
    ----------
    df : DataFrame with price data
    range_multiplier : WRD detection threshold
    lookback : average range lookback
    proximity_bars : max bars between WRDs to count as a cluster

    Returns
    -------
    List of dicts with 'wrds', 'penetrations', 'confluence_score'
    """
    wrds = detect_wide_ranging_days(df, range_multiplier, lookback)
    penetrations = []

    for wrd in wrds:
        pen = detect_wrd_penetration(df, wrd)
        if pen:
            penetrations.append(pen)

    if not penetrations:
        return []

    # Group same-direction penetrations that are near each other
    clusters = []
    current_cluster = [penetrations[0]]

    for i in range(1, len(penetrations)):
        prev = penetrations[i - 1]
        curr = penetrations[i]

        same_dir = curr.trade_direction == prev.trade_direction
        close_in_time = (curr.wrd.bar_idx - prev.wrd.bar_idx) <= proximity_bars

        if same_dir and close_in_time:
            current_cluster.append(curr)
        else:
            if len(current_cluster) >= 1:
                clusters.append(current_cluster)
            current_cluster = [curr]

    clusters.append(current_cluster)

    results = []
    for cluster in clusters:
        # Score: 1 base + 1 per additional WRD + 1 if any penetration is itself a WRD
        score = len(cluster)
        if any(p.penetration_is_wrd for p in cluster):
            score += 1

        results.append({
            'wrds': [p.wrd for p in cluster],
            'penetrations': cluster,
            'confluence_score': score,
            'trade_direction': cluster[0].trade_direction,
        })

    return results


# ── Example usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=80, freq='B')

    # Simulate normal bars then a downside WRD then recovery
    closes = [100]
    for i in range(79):
        closes.append(closes[-1] + np.random.randn() * 0.5)
    closes = np.array(closes)

    highs = closes + np.random.uniform(0.5, 1.5, 80)
    lows = closes - np.random.uniform(0.5, 1.5, 80)

    # Inject downside WRD at bar 30
    highs[30] = closes[30] + 1
    lows[30] = closes[30] - 8  # Very wide range
    closes[30] = lows[30] + 0.5  # Close near low

    # Recovery crosses above WRD high around bar 50
    for i in range(45, 60):
        closes[i] += 5
        highs[i] += 5
        lows[i] += 5

    df = pd.DataFrame({
        'high': highs, 'low': lows, 'close': closes
    }, index=dates)

    wrds = detect_wide_ranging_days(df, range_multiplier=1.5, lookback=15)
    print(f"Found {len(wrds)} WRDs:")
    for w in wrds:
        print(f"  {w.wrd_type.value} on {w.date.date()}, "
              f"range={w.range_size:.1f}, ratio={w.range_ratio}x, "
              f"close_pos={w.close_position}")

    for w in wrds:
        pen = detect_wrd_penetration(df, w)
        if pen:
            print(f"\n  WRD PENETRATED on {pen.penetration_date.date()}")
            print(f"    Trade:             {pen.trade_direction}")
            print(f"    Entry price:       {pen.penetration_price:.1f}")
            print(f"    Bars elapsed:      {pen.bars_elapsed}")
            print(f"    Penetration is WRD:{pen.penetration_is_wrd}")
