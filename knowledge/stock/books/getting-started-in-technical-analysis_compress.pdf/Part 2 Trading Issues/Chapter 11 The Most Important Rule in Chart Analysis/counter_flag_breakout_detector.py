"""
Counter-to-Anticipated Flag/Pennant Breakout Detector — Ch 11, Concept 9
=========================================================================
Flags and pennants normally break out in the SAME direction as the preceding
swing. When they break in the OPPOSITE direction, it's a failed signal —
one of the most powerful reversal indicators.

- Flag in downtrend breaks UPSIDE → BUY (trend exhaustion at bottom)
- Flag in uptrend breaks DOWNSIDE → SELL (trend exhaustion at top)

Invalidation: close beyond the opposite end of the flag/pennant.

Schwager: "counter-to-anticipated breakouts provided extraordinarily
timely indications of major trend reversals."
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PriorTrend(Enum):
    UP = "uptrend"
    DOWN = "downtrend"


class PatternType(Enum):
    FLAG = "flag"
    PENNANT = "pennant"


@dataclass
class FlagPennant:
    """A detected flag or pennant consolidation pattern."""
    pattern_type: PatternType
    prior_trend: PriorTrend
    start_idx: int
    end_idx: int
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    upper_bound: float       # Upper boundary of the flag/pennant
    lower_bound: float       # Lower boundary
    expected_breakout: str   # 'up' for uptrend flag, 'down' for downtrend flag
    prior_swing_size: float  # Magnitude of the preceding swing


@dataclass
class CounterBreakout:
    """A confirmed counter-to-anticipated breakout."""
    pattern: FlagPennant
    breakout_date: pd.Timestamp
    breakout_bar_idx: int
    breakout_price: float
    trade_direction: str         # 'long' or 'short'
    invalidation_price: float    # Opposite end of flag/pennant
    is_valid: bool = True        # Becomes False if invalidated


def find_prior_swing(
    df: pd.DataFrame,
    end_idx: int,
    min_swing_bars: int = 5,
    max_swing_bars: int = 40,
    min_swing_pct: float = 0.03,
) -> Optional[dict]:
    """
    Identify the directional swing that precedes a consolidation.

    Looks backward from end_idx for a sustained move.

    Returns
    -------
    dict with 'direction', 'start_idx', 'swing_size' or None
    """
    if end_idx < min_swing_bars:
        return None

    start = max(0, end_idx - max_swing_bars)
    window = df.iloc[start:end_idx + 1]

    # Check for downswing: close declining
    total_change = window.iloc[-1]['close'] - window.iloc[0]['close']
    avg_price = window['close'].mean()
    change_pct = abs(total_change) / avg_price

    if change_pct < min_swing_pct:
        return None

    direction = PriorTrend.DOWN if total_change < 0 else PriorTrend.UP

    return {
        'direction': direction,
        'start_idx': start,
        'swing_size': abs(total_change),
    }


def detect_flag_pennant(
    df: pd.DataFrame,
    consolidation_start: int,
    min_bars: int = 3,
    max_bars: int = 20,
    max_range_pct: float = 0.06,
) -> Optional[FlagPennant]:
    """
    Detect a flag or pennant starting at a given bar index.

    A flag has roughly parallel boundaries; a pennant converges.
    Both are brief consolidations within a larger trend.

    Parameters
    ----------
    df : DataFrame with ['high', 'low', 'close']
    consolidation_start : bar index where consolidation begins
    min_bars : minimum bars for the consolidation
    max_bars : maximum bars to scan
    max_range_pct : max consolidation range as % of price

    Returns
    -------
    FlagPennant or None
    """
    prior = find_prior_swing(df, consolidation_start - 1)
    if prior is None:
        return None

    # Scan for consolidation
    best_end = None
    for length in range(min_bars, min(max_bars, len(df) - consolidation_start)):
        end_idx = consolidation_start + length
        window = df.iloc[consolidation_start:end_idx + 1]

        upper = window['high'].max()
        lower = window['low'].min()
        mid = (upper + lower) / 2
        range_pct = (upper - lower) / mid

        if range_pct <= max_range_pct:
            best_end = end_idx

    if best_end is None:
        return None

    window = df.iloc[consolidation_start:best_end + 1]
    upper = window['high'].max()
    lower = window['low'].min()

    # Determine if flag or pennant (rough heuristic)
    first_half = df.iloc[consolidation_start:consolidation_start + (best_end - consolidation_start) // 2 + 1]
    second_half = df.iloc[consolidation_start + (best_end - consolidation_start) // 2:best_end + 1]

    first_range = first_half['high'].max() - first_half['low'].min()
    second_range = second_half['high'].max() - second_half['low'].min()

    pattern_type = PatternType.PENNANT if second_range < first_range * 0.7 else PatternType.FLAG

    expected = 'down' if prior['direction'] == PriorTrend.DOWN else 'up'

    return FlagPennant(
        pattern_type=pattern_type,
        prior_trend=prior['direction'],
        start_idx=consolidation_start,
        end_idx=best_end,
        start_date=df.index[consolidation_start],
        end_date=df.index[best_end],
        upper_bound=upper,
        lower_bound=lower,
        expected_breakout=expected,
        prior_swing_size=prior['swing_size'],
    )


def detect_counter_breakout(
    df: pd.DataFrame,
    pattern: FlagPennant,
    scan_bars: int = 10,
) -> Optional[CounterBreakout]:
    """
    Check if a flag/pennant breaks out in the opposite-to-expected direction.

    - Downtrend flag expected to break down → if breaks UP = counter breakout (BUY)
    - Uptrend flag expected to break up → if breaks DOWN = counter breakout (SELL)

    Parameters
    ----------
    df : DataFrame with price data
    pattern : FlagPennant object
    scan_bars : bars after pattern end to look for breakout

    Returns
    -------
    CounterBreakout or None
    """
    end = min(pattern.end_idx + scan_bars, len(df))

    for i in range(pattern.end_idx + 1, end):
        bar = df.iloc[i]

        if pattern.expected_breakout == 'down':
            # Expected down, but breaks UP = counter = BUY
            if bar['close'] > pattern.upper_bound:
                return CounterBreakout(
                    pattern=pattern,
                    breakout_date=df.index[i],
                    breakout_bar_idx=i,
                    breakout_price=bar['close'],
                    trade_direction='long',
                    invalidation_price=pattern.lower_bound,
                )

        elif pattern.expected_breakout == 'up':
            # Expected up, but breaks DOWN = counter = SELL
            if bar['close'] < pattern.lower_bound:
                return CounterBreakout(
                    pattern=pattern,
                    breakout_date=df.index[i],
                    breakout_bar_idx=i,
                    breakout_price=bar['close'],
                    trade_direction='short',
                    invalidation_price=pattern.upper_bound,
                )

    return None


def check_counter_breakout_validity(
    df: pd.DataFrame,
    counter: CounterBreakout,
) -> dict:
    """
    Monitor whether a counter breakout signal remains valid.

    Schwager's rule: signal stays valid as long as price does not close
    beyond the opposite end of the flag/pennant.

    Returns
    -------
    dict with 'valid', 'invalidation_date', 'max_pullback'
    """
    max_pullback = 0.0

    for i in range(counter.breakout_bar_idx + 1, len(df)):
        bar = df.iloc[i]

        if counter.trade_direction == 'long':
            # Long from counter breakout; invalid if close below flag lower bound
            pullback = counter.breakout_price - bar['close']
            max_pullback = max(max_pullback, pullback)
            if bar['close'] < counter.invalidation_price:
                return {
                    'valid': False,
                    'invalidation_date': df.index[i],
                    'max_pullback': max_pullback,
                }
        else:
            # Short from counter breakout; invalid if close above flag upper bound
            pullback = bar['close'] - counter.breakout_price
            max_pullback = max(max_pullback, pullback)
            if bar['close'] > counter.invalidation_price:
                return {
                    'valid': False,
                    'invalidation_date': df.index[i],
                    'max_pullback': max_pullback,
                }

    return {'valid': True, 'invalidation_date': None, 'max_pullback': max_pullback}


# ── Example usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=60, freq='B')

    # Simulate: downtrend → flag → counter upside breakout
    prices = [120]
    for i in range(14):
        prices.append(prices[-1] - 1.5 + np.random.randn() * 0.3)
    # Flag consolidation (slight upward drift)
    for i in range(10):
        prices.append(prices[-1] + 0.2 + np.random.randn() * 0.3)
    # Counter breakout UP
    for i in range(35):
        prices.append(prices[-1] + 0.8 + np.random.randn() * 0.4)

    prices = np.array(prices)
    highs = prices + np.random.uniform(0.5, 1.5, 60)
    lows = prices - np.random.uniform(0.5, 1.5, 60)

    df = pd.DataFrame({
        'high': highs, 'low': lows, 'close': prices
    }, index=dates)

    # Try to detect flag after the downtrend
    fp = detect_flag_pennant(df, consolidation_start=15, min_bars=5, max_bars=12)
    if fp:
        print(f"Flag/Pennant detected:")
        print(f"  Type:     {fp.pattern_type.value}")
        print(f"  Trend:    {fp.prior_trend.value}")
        print(f"  Bounds:   {fp.lower_bound:.1f} - {fp.upper_bound:.1f}")
        print(f"  Expected: break {fp.expected_breakout}")

        cb = detect_counter_breakout(df, fp)
        if cb:
            print(f"\n  COUNTER breakout detected!")
            print(f"    Date:       {cb.breakout_date.date()}")
            print(f"    Price:      {cb.breakout_price:.1f}")
            print(f"    Trade:      {cb.trade_direction}")
            print(f"    Invalidation: {cb.invalidation_price:.1f}")

            validity = check_counter_breakout_validity(df, cb)
            print(f"    Valid:      {validity['valid']}")
            print(f"    Max pullback: {validity['max_pullback']:.1f}")
    else:
        print("No flag/pennant detected.")
