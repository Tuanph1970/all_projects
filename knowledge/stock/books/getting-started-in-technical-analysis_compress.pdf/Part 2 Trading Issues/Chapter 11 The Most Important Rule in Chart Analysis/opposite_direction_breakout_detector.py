"""
Opposite Direction Breakout After Normal Breakout — Ch 11, Concept 10
======================================================================
A flag/pennant breaks out in the EXPECTED direction (normal), but then
price reverses and closes beyond the OPPOSITE end of the flag/pennant.

This two-phase failure is arguably stronger than a direct counter breakout
(Concept 9) because the market explicitly TRIED to continue and failed.

Confirmation: close beyond the opposite end (not just intraday touch).

Schwager: "This combined price action provides another example of a failed
signal, since the anticipated breakout of the flag or pennant is followed
by a price reversal instead of a price follow-through."

Key examples:
- DuPont (Fig 11.24): flag at top of 4-month advance, upside breakout
  lasted only 3 days, then reversed below the flag low.
- Coffee (Fig 11.25): downside breakout after extended slide, prices
  soon rebounded above the pennant top → large advance.
- Heating oil (Fig 11.26): same pattern, plus a Concept 9 counter
  breakout at the market top on the same chart.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional
from counter_flag_breakout_detector import (
    FlagPennant,
    PriorTrend,
    detect_flag_pennant,
)


@dataclass
class OppositeDirectionBreakout:
    """A confirmed opposite-direction breakout after a normal breakout."""
    pattern: FlagPennant
    # Phase 1: Normal breakout
    normal_breakout_date: pd.Timestamp
    normal_breakout_idx: int
    normal_breakout_price: float
    normal_breakout_bars: int        # How many bars the normal breakout lasted
    normal_closes_beyond: int        # How many closes beyond the boundary

    # Phase 2: Reversal
    reversal_date: pd.Timestamp
    reversal_idx: int
    reversal_price: float            # Close at confirmation
    trade_direction: str             # 'short' or 'long'

    # The two-phase nature is the key differentiator from Concept 9
    total_bars_from_breakout: int    # Bars from normal breakout to reversal


def detect_opposite_direction_breakout(
    df: pd.DataFrame,
    pattern: FlagPennant,
    max_normal_bars: int = 10,
    max_reversal_bars: int = 15,
) -> Optional[OppositeDirectionBreakout]:
    """
    Detect the two-phase pattern: normal breakout → stall → reversal
    through the opposite end of the flag/pennant.

    Phase 1: Flag breaks in expected direction (close beyond boundary)
    Phase 2: Price reverses and closes beyond OPPOSITE boundary

    Parameters
    ----------
    df : DataFrame with ['high', 'low', 'close']
    pattern : FlagPennant object
    max_normal_bars : max bars to scan for the normal breakout
    max_reversal_bars : max bars after stall to look for reversal

    Returns
    -------
    OppositeDirectionBreakout or None
    """
    # Phase 1: Find normal breakout
    normal_breakout_idx = None
    normal_breakout_price = None
    normal_closes = 0

    scan_end = min(pattern.end_idx + max_normal_bars, len(df))

    for i in range(pattern.end_idx + 1, scan_end):
        bar = df.iloc[i]

        if pattern.expected_breakout == 'up':
            if bar['close'] > pattern.upper_bound:
                if normal_breakout_idx is None:
                    normal_breakout_idx = i
                    normal_breakout_price = bar['close']
                normal_closes += 1
        elif pattern.expected_breakout == 'down':
            if bar['close'] < pattern.lower_bound:
                if normal_breakout_idx is None:
                    normal_breakout_idx = i
                    normal_breakout_price = bar['close']
                normal_closes += 1

    if normal_breakout_idx is None:
        return None  # No normal breakout occurred

    # Phase 2: Look for reversal through opposite end
    reversal_scan_end = min(normal_breakout_idx + max_reversal_bars, len(df))

    for j in range(normal_breakout_idx + 1, reversal_scan_end):
        bar = df.iloc[j]

        if pattern.expected_breakout == 'up':
            # Normal was up, reversal = close below lower bound
            if bar['close'] < pattern.lower_bound:
                # Count how many bars the normal breakout lasted
                normal_bars = 0
                for k in range(normal_breakout_idx, j):
                    if pattern.expected_breakout == 'up' and \
                       df.iloc[k]['close'] > pattern.upper_bound:
                        normal_bars += 1
                    else:
                        break

                return OppositeDirectionBreakout(
                    pattern=pattern,
                    normal_breakout_date=df.index[normal_breakout_idx],
                    normal_breakout_idx=normal_breakout_idx,
                    normal_breakout_price=normal_breakout_price,
                    normal_breakout_bars=normal_bars,
                    normal_closes_beyond=normal_closes,
                    reversal_date=df.index[j],
                    reversal_idx=j,
                    reversal_price=bar['close'],
                    trade_direction='short',
                    total_bars_from_breakout=j - normal_breakout_idx,
                )

        elif pattern.expected_breakout == 'down':
            # Normal was down, reversal = close above upper bound
            if bar['close'] > pattern.upper_bound:
                normal_bars = 0
                for k in range(normal_breakout_idx, j):
                    if pattern.expected_breakout == 'down' and \
                       df.iloc[k]['close'] < pattern.lower_bound:
                        normal_bars += 1
                    else:
                        break

                return OppositeDirectionBreakout(
                    pattern=pattern,
                    normal_breakout_date=df.index[normal_breakout_idx],
                    normal_breakout_idx=normal_breakout_idx,
                    normal_breakout_price=normal_breakout_price,
                    normal_breakout_bars=normal_bars,
                    normal_closes_beyond=normal_closes,
                    reversal_date=df.index[j],
                    reversal_idx=j,
                    reversal_price=bar['close'],
                    trade_direction='long',
                    total_bars_from_breakout=j - normal_breakout_idx,
                )

    return None  # Normal breakout occurred but no reversal


def scan_for_both_flag_failures(
    df: pd.DataFrame,
    consolidation_start: int,
    min_flag_bars: int = 3,
    max_flag_bars: int = 20,
) -> dict:
    """
    Scan for BOTH Concept 9 (counter breakout) and Concept 10 (opposite
    after normal) at a single flag/pennant location.

    Schwager's heating oil chart (Fig 11.26) contains BOTH types on the
    same chart. This function checks for either possibility.

    Returns
    -------
    dict with 'pattern', 'concept_9' (CounterBreakout or None),
    'concept_10' (OppositeDirectionBreakout or None)
    """
    from counter_flag_breakout_detector import detect_counter_breakout

    pattern = detect_flag_pennant(df, consolidation_start,
                                  min_bars=min_flag_bars, max_bars=max_flag_bars)
    if pattern is None:
        return {'pattern': None, 'concept_9': None, 'concept_10': None}

    c9 = detect_counter_breakout(df, pattern)
    c10 = detect_opposite_direction_breakout(df, pattern)

    return {
        'pattern': pattern,
        'concept_9': c9,
        'concept_10': c10,
    }


# ── Example usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=60, freq='B')

    # Simulate: uptrend → flag → normal upside breakout → stall → reversal
    prices = [100]
    for i in range(14):
        prices.append(prices[-1] + 1.2 + np.random.randn() * 0.3)
    # Flag (slight downward drift)
    for i in range(8):
        prices.append(prices[-1] - 0.15 + np.random.randn() * 0.2)
    # Normal upside breakout (3 bars)
    for i in range(3):
        prices.append(prices[-1] + 0.8 + np.random.randn() * 0.2)
    # Stall and reverse
    for i in range(3):
        prices.append(prices[-1] - 0.3 + np.random.randn() * 0.2)
    # Collapse through lower bound
    for i in range(29):
        prices.append(prices[-1] - 0.9 + np.random.randn() * 0.3)

    prices = np.array(prices)
    highs = prices + np.random.uniform(0.3, 1.2, 60)
    lows = prices - np.random.uniform(0.3, 1.2, 60)

    df = pd.DataFrame({
        'high': highs, 'low': lows, 'close': prices
    }, index=dates)

    fp = detect_flag_pennant(df, consolidation_start=15, min_bars=4, max_bars=10)
    if fp:
        print(f"Flag detected:")
        print(f"  Type:     {fp.pattern_type.value}")
        print(f"  Trend:    {fp.prior_trend.value}")
        print(f"  Bounds:   {fp.lower_bound:.1f} - {fp.upper_bound:.1f}")
        print(f"  Expected: break {fp.expected_breakout}")

        odb = detect_opposite_direction_breakout(df, fp)
        if odb:
            print(f"\n  Opposite direction breakout detected!")
            print(f"    Normal breakout: {odb.normal_breakout_date.date()}")
            print(f"      Price:         {odb.normal_breakout_price:.1f}")
            print(f"      Lasted:        {odb.normal_breakout_bars} bars")
            print(f"      Closes beyond: {odb.normal_closes_beyond}")
            print(f"    Reversal:        {odb.reversal_date.date()}")
            print(f"      Price:         {odb.reversal_price:.1f}")
            print(f"      Trade:         {odb.trade_direction}")
            print(f"      Total bars:    {odb.total_bars_from_breakout}")
        else:
            print("  No opposite direction breakout detected.")
    else:
        print("No flag detected.")
