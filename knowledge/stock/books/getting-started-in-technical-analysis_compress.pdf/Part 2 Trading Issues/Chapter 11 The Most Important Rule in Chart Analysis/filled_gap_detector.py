"""
Filled Gap Detector — Chapter 11, Concept 6
=============================================
Gaps normally presage continuation in the gap direction. When a gap is
filled, it qualifies the original gap as a failed signal — implying a
move in the OPPOSITE direction.

Schwager provides two definitions of "filled":
- Typical: intraday price reaches the high/low of the day before the gap
- Strict (preferred): close beyond the close of the day before the gap

Significance enhancers:
1. Gap is particularly wide
2. Gap is a breakaway gap (at a range boundary)
3. Two or more consecutive gaps are filled

Invalidation:
- Filled upside gap: signal valid until close above the gap
- Filled downside gap: signal valid until close below the gap
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GapDirection(Enum):
    UP = "upside"      # Low > previous high
    DOWN = "downside"   # High < previous low


class FillDefinition(Enum):
    TYPICAL = "typical"   # Intraday touches pre-gap high/low
    STRICT = "strict"     # Close beyond pre-gap close (Schwager's preference)


@dataclass
class Gap:
    """A price gap between two consecutive bars."""
    date: pd.Timestamp
    bar_idx: int
    direction: GapDirection
    gap_low: float         # Lower edge of the gap space
    gap_high: float        # Upper edge of the gap space
    gap_size: float        # Absolute size of the gap
    pre_gap_close: float   # Close of the day before the gap
    pre_gap_high: float    # High of the day before the gap
    pre_gap_low: float     # Low of the day before the gap
    is_wide: bool = False  # Significance enhancer
    is_breakaway: bool = False  # Significance enhancer


@dataclass
class FilledGap:
    """A confirmed filled gap — the failed signal output."""
    gap: Gap
    fill_date: pd.Timestamp
    fill_bar_idx: int
    fill_definition: FillDefinition
    fill_price: float       # Close at fill confirmation
    trade_direction: str    # 'short' for filled upside gap, 'long' for filled downside
    invalidation_price: float  # Close beyond this = signal invalidated
    significance_score: int    # 0-3 based on enhancers


def detect_gaps(
    df: pd.DataFrame,
    wide_threshold_pct: float = 0.02,
    range_lookback: int = 20,
    range_threshold_pct: float = 0.005,
) -> list[Gap]:
    """
    Scan price data for gaps.

    Parameters
    ----------
    df : DataFrame with ['high', 'low', 'close'] and DatetimeIndex
    wide_threshold_pct : gap size as % of price to qualify as "wide"
    range_lookback : bars to look back for range boundary (breakaway detection)
    range_threshold_pct : proximity to range boundary for breakaway status

    Returns
    -------
    List of Gap objects
    """
    gaps = []

    for i in range(1, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i - 1]

        if curr['low'] > prev['high']:
            # Upside gap
            gap_size = curr['low'] - prev['high']
            mid_price = (curr['low'] + prev['high']) / 2
            is_wide = (gap_size / mid_price) >= wide_threshold_pct

            # Check if breakaway (near range high)
            is_breakaway = False
            if i >= range_lookback:
                window = df.iloc[i - range_lookback:i]
                range_high = window['high'].max()
                if abs(prev['close'] - range_high) / range_high < range_threshold_pct:
                    is_breakaway = True

            gaps.append(Gap(
                date=df.index[i],
                bar_idx=i,
                direction=GapDirection.UP,
                gap_low=prev['high'],
                gap_high=curr['low'],
                gap_size=gap_size,
                pre_gap_close=prev['close'],
                pre_gap_high=prev['high'],
                pre_gap_low=prev['low'],
                is_wide=is_wide,
                is_breakaway=is_breakaway,
            ))

        elif curr['high'] < prev['low']:
            # Downside gap
            gap_size = prev['low'] - curr['high']
            mid_price = (prev['low'] + curr['high']) / 2
            is_wide = (gap_size / mid_price) >= wide_threshold_pct

            is_breakaway = False
            if i >= range_lookback:
                window = df.iloc[i - range_lookback:i]
                range_low = window['low'].min()
                if abs(prev['close'] - range_low) / range_low < range_threshold_pct:
                    is_breakaway = True

            gaps.append(Gap(
                date=df.index[i],
                bar_idx=i,
                direction=GapDirection.DOWN,
                gap_low=curr['high'],
                gap_high=prev['low'],
                gap_size=gap_size,
                pre_gap_close=prev['close'],
                pre_gap_high=prev['high'],
                pre_gap_low=prev['low'],
                is_wide=is_wide,
                is_breakaway=is_breakaway,
            ))

    return gaps


def check_gap_filled(
    df: pd.DataFrame,
    gap: Gap,
    definition: FillDefinition = FillDefinition.STRICT,
) -> Optional[FilledGap]:
    """
    Check if a gap has been filled in subsequent price action.

    Parameters
    ----------
    df : DataFrame with price data
    gap : Gap object to check
    definition : which fill definition to use

    Returns
    -------
    FilledGap or None
    """
    for i in range(gap.bar_idx + 1, len(df)):
        bar = df.iloc[i]

        filled = False

        if gap.direction == GapDirection.UP:
            if definition == FillDefinition.TYPICAL:
                filled = bar['low'] <= gap.gap_low  # Touches pre-gap high
            else:  # STRICT
                filled = bar['close'] < gap.pre_gap_close

        elif gap.direction == GapDirection.DOWN:
            if definition == FillDefinition.TYPICAL:
                filled = bar['high'] >= gap.gap_high  # Touches pre-gap low
            else:  # STRICT
                filled = bar['close'] > gap.pre_gap_close

        if filled:
            # Calculate significance score
            score = 0
            if gap.is_wide:
                score += 1
            if gap.is_breakaway:
                score += 1

            # Trade direction and invalidation
            if gap.direction == GapDirection.UP:
                trade_dir = 'short'
                invalidation = gap.gap_high  # Close above gap invalidates
            else:
                trade_dir = 'long'
                invalidation = gap.gap_low   # Close below gap invalidates

            return FilledGap(
                gap=gap,
                fill_date=df.index[i],
                fill_bar_idx=i,
                fill_definition=definition,
                fill_price=bar['close'],
                trade_direction=trade_dir,
                invalidation_price=invalidation,
                significance_score=score,
            )

    return None


def detect_consecutive_filled_gaps(
    df: pd.DataFrame,
    definition: FillDefinition = FillDefinition.STRICT,
) -> list[list[FilledGap]]:
    """
    Find groups of consecutive gaps (same direction) that are all filled.
    Consecutive filled gaps are a significance enhancer (score +1).

    Returns
    -------
    List of groups, where each group is a list of FilledGap objects
    """
    gaps = detect_gaps(df)
    filled_gaps = []

    for gap in gaps:
        fg = check_gap_filled(df, gap, definition)
        if fg:
            filled_gaps.append(fg)

    if not filled_gaps:
        return []

    # Group consecutive same-direction filled gaps
    groups = []
    current_group = [filled_gaps[0]]

    for i in range(1, len(filled_gaps)):
        prev_fg = filled_gaps[i - 1]
        curr_fg = filled_gaps[i]

        # Consecutive = same direction, gap bars are within 5 bars of each other
        if (curr_fg.gap.direction == prev_fg.gap.direction and
                curr_fg.gap.bar_idx - prev_fg.gap.bar_idx <= 5):
            current_group.append(curr_fg)
        else:
            if len(current_group) >= 2:
                # Bump significance score for consecutive
                for fg in current_group:
                    fg.significance_score += 1
                groups.append(current_group)
            current_group = [curr_fg]

    if len(current_group) >= 2:
        for fg in current_group:
            fg.significance_score += 1
        groups.append(current_group)

    return groups


def check_signal_validity(
    df: pd.DataFrame,
    filled_gap: FilledGap,
) -> dict:
    """
    Check if a filled gap signal is still valid or has been invalidated.

    Schwager's rule:
    - Filled upside gap: valid until close above the gap
    - Filled downside gap: valid until close below the gap

    Returns
    -------
    dict with 'valid', 'invalidation_date' (if invalidated)
    """
    for i in range(filled_gap.fill_bar_idx + 1, len(df)):
        bar = df.iloc[i]

        if filled_gap.gap.direction == GapDirection.UP:
            if bar['close'] > filled_gap.invalidation_price:
                return {'valid': False, 'invalidation_date': df.index[i]}
        else:
            if bar['close'] < filled_gap.invalidation_price:
                return {'valid': False, 'invalidation_date': df.index[i]}

    return {'valid': True, 'invalidation_date': None}


# ── Example usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=60, freq='B')

    # Simulate uptrend with an upside gap that gets filled
    prices = [100]
    for i in range(59):
        prices.append(prices[-1] + 0.5 + np.random.randn() * 0.8)
    prices = np.array(prices)

    highs = prices + np.random.uniform(0.5, 2, 60)
    lows = prices - np.random.uniform(0.5, 2, 60)

    # Inject a gap at bar 20
    for i in range(20, 60):
        prices[i] += 5
        highs[i] += 5
        lows[i] += 5
    lows[20] = highs[19] + 1  # Force gap: low > prev high

    # Fill the gap around bar 30
    for i in range(28, 40):
        prices[i] -= (i - 27) * 1.5
        highs[i] -= (i - 27) * 1.5
        lows[i] -= (i - 27) * 1.5

    df = pd.DataFrame({
        'high': highs, 'low': lows, 'close': prices
    }, index=dates)

    # Detect gaps
    gaps = detect_gaps(df)
    print(f"Found {len(gaps)} gaps:")
    for gap in gaps:
        print(f"  {gap.direction.value} gap on {gap.date.date()}, "
              f"size={gap.gap_size:.1f}, wide={gap.is_wide}, "
              f"breakaway={gap.is_breakaway}")

    # Check if filled
    for gap in gaps:
        fg = check_gap_filled(df, gap, FillDefinition.STRICT)
        if fg:
            print(f"\n  Gap FILLED on {fg.fill_date.date()}")
            print(f"    Fill price:     {fg.fill_price:.1f}")
            print(f"    Trade:          {fg.trade_direction}")
            print(f"    Significance:   {fg.significance_score}/3")
            print(f"    Invalidation:   close beyond {fg.invalidation_price:.1f}")

            validity = check_signal_validity(df, fg)
            print(f"    Still valid:    {validity['valid']}")
