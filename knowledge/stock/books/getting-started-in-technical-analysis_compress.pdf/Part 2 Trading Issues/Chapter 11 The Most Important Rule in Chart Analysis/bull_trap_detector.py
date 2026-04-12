"""
Bull Trap Detector — Chapter 11, Concept 2
============================================
A bull trap is a major upside breakout that is soon followed by an abrupt,
sharp price reversal downward. Schwager considers this "among the most
reliable indicators of major tops."

This module specializes the base failed_signal_detector for the specific
case of upside breakout failures from consolidation ranges.

Schwager: "Bull and bear traps are major breakouts that are soon followed
by abrupt, sharp price reversals, in stark contrast to the price continuation
patterns that are expected to follow breakouts."
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional
from failed_signal_detector import (
    detect_consolidation_range,
    BreakoutEvent,
    SignalDirection,
    FailedSignalStatus,
)


class ConfirmationType:
    INITIAL_PRICE = "initial_price"   # Retrace to midpoint
    STRONG_PRICE = "strong_price"     # Retrace to opposite boundary (support)
    TIME = "time"                      # No return to breakout high within N bars


@dataclass
class BullTrap:
    """A confirmed bull trap with full context."""
    breakout_date: pd.Timestamp
    breakout_high: float          # The false breakout extreme
    range_high: float             # Resistance level that was broken
    range_low: float              # Support level (strong confirmation target)
    range_midpoint: float         # Initial confirmation target

    confirmation_date: pd.Timestamp
    confirmation_type: str        # Which confirmation triggered
    entry_price: float            # Where to enter the short
    stop_loss: float              # Invalidation = breakout high

    initial_confirmed: bool = False
    strong_confirmed: bool = False
    time_confirmed: bool = False


def detect_bull_trap(
    df: pd.DataFrame,
    lookback: int = 20,
    max_range_pct: float = 0.10,
    min_breakout_pct: float = 0.005,
    time_confirm_bars: int = 20,
    invalidation_buffer: float = 1.005,
) -> Optional[BullTrap]:
    """
    Scan for a bull trap pattern in the given price data.

    The algorithm:
    1. Find a consolidation range in bars [0..lookback]
    2. Detect an upside breakout
    3. Monitor post-breakout bars for:
       a. Invalidation: price exceeds breakout high * buffer → no trap
       b. Initial confirmation: close below midpoint
       c. Strong confirmation: close below range low (support)
       d. Time confirmation: N bars pass without reclaiming breakout high

    Parameters
    ----------
    df : DataFrame with ['high', 'low', 'close'] and DatetimeIndex
    lookback : bars to define the consolidation range
    max_range_pct : max range width as % of midpoint for consolidation
    min_breakout_pct : minimum close above resistance as % of range
    time_confirm_bars : bars for time confirmation
    invalidation_buffer : multiplier above breakout high for invalidation

    Returns
    -------
    BullTrap or None
    """
    if len(df) < lookback + 2:
        return None

    # Step 1: Find consolidation
    consolidation = detect_consolidation_range(
        df.iloc[:lookback], lookback=lookback, max_range_pct=max_range_pct
    )
    if consolidation is None:
        return None

    rh = consolidation['high']
    rl = consolidation['low']
    mid = consolidation['midpoint']
    range_size = rh - rl

    # Step 2: Scan for upside breakout after consolidation
    breakout_idx = None
    breakout_high = None

    for i in range(lookback, len(df)):
        if df.iloc[i]['close'] > rh + range_size * min_breakout_pct:
            breakout_idx = i
            breakout_high = df.iloc[i]['high']
            break

    if breakout_idx is None:
        return None

    # Track the actual highest point of the breakout move
    # (could extend a few bars beyond initial breakout bar)
    j = breakout_idx + 1
    while j < len(df) and df.iloc[j]['high'] > df.iloc[j - 1]['close']:
        breakout_high = max(breakout_high, df.iloc[j]['high'])
        j += 1

    # Step 3: Monitor for confirmation or invalidation
    post_start = j if j < len(df) else breakout_idx + 1
    initial_confirmed = False
    strong_confirmed = False
    time_confirmed = False
    first_confirmation = None

    for k in range(post_start, len(df)):
        bar = df.iloc[k]

        # Invalidation check: price exceeds breakout high
        if bar['high'] > breakout_high * invalidation_buffer:
            return None  # Not a bull trap — breakout succeeded

        # Initial price confirmation
        if not initial_confirmed and bar['close'] < mid:
            initial_confirmed = True
            if first_confirmation is None:
                first_confirmation = (
                    df.index[k],
                    ConfirmationType.INITIAL_PRICE,
                    bar['close'],
                )

        # Strong price confirmation
        if not strong_confirmed and bar['close'] < rl:
            strong_confirmed = True
            if first_confirmation is None:
                first_confirmation = (
                    df.index[k],
                    ConfirmationType.STRONG_PRICE,
                    bar['close'],
                )

        # Time confirmation
        if not time_confirmed and (k - breakout_idx) >= time_confirm_bars:
            if bar['close'] < rh:  # Still below resistance
                time_confirmed = True
                if first_confirmation is None:
                    first_confirmation = (
                        df.index[k],
                        ConfirmationType.TIME,
                        bar['close'],
                    )

    if first_confirmation is None:
        return None  # No confirmation yet

    conf_date, conf_type, entry = first_confirmation

    return BullTrap(
        breakout_date=df.index[breakout_idx],
        breakout_high=breakout_high,
        range_high=rh,
        range_low=rl,
        range_midpoint=mid,
        confirmation_date=conf_date,
        confirmation_type=conf_type,
        entry_price=entry,
        stop_loss=breakout_high,
        initial_confirmed=initial_confirmed,
        strong_confirmed=strong_confirmed,
        time_confirmed=time_confirmed,
    )


def bull_trap_reward_risk(trap: BullTrap, target_multiple: float = 2.0) -> dict:
    """
    Calculate reward-to-risk ratio for a bull trap trade.

    Parameters
    ----------
    trap : BullTrap object
    target_multiple : target as multiple of range height below range low

    Returns
    -------
    dict with risk, target, reward_to_risk
    """
    risk = trap.stop_loss - trap.entry_price
    range_height = trap.range_high - trap.range_low
    target = trap.range_low - (range_height * target_multiple)
    reward = trap.entry_price - target

    return {
        'entry': trap.entry_price,
        'stop_loss': trap.stop_loss,
        'target': target,
        'risk': risk,
        'reward': reward,
        'reward_to_risk': reward / risk if risk > 0 else 0,
    }


# ── Example usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=50, freq='B')

    # Simulate: 20 bars consolidation (95-105), breakout to 110, then collapse
    consol = 100 + np.random.randn(20) * 2
    consol = np.clip(consol, 96, 104)
    breakout = [106, 109, 110]
    failure = [107, 103, 100, 97, 94, 91, 88, 86, 84, 82,
               80, 79, 78, 77, 76, 75, 74, 73, 72, 71,
               70, 69, 68, 67, 66, 65, 64]

    all_close = np.concatenate([consol, breakout, failure])
    highs = all_close + np.random.uniform(0.5, 2.5, len(all_close))
    lows = all_close - np.random.uniform(0.5, 2.5, len(all_close))

    df = pd.DataFrame({
        'high': highs, 'low': lows, 'close': all_close
    }, index=dates)

    trap = detect_bull_trap(df, lookback=20)
    if trap:
        print(f"Bull Trap detected!")
        print(f"  Breakout date:  {trap.breakout_date.date()}")
        print(f"  Breakout high:  {trap.breakout_high:.1f}")
        print(f"  Range:          {trap.range_low:.1f} - {trap.range_high:.1f}")
        print(f"  Midpoint:       {trap.range_midpoint:.1f}")
        print(f"  Confirmation:   {trap.confirmation_type} on {trap.confirmation_date.date()}")
        print(f"  Entry price:    {trap.entry_price:.1f}")
        print(f"  Stop loss:      {trap.stop_loss:.1f}")
        print(f"  Initial confirmed: {trap.initial_confirmed}")
        print(f"  Strong confirmed:  {trap.strong_confirmed}")
        print(f"  Time confirmed:    {trap.time_confirmed}")

        rr = bull_trap_reward_risk(trap)
        print(f"\n  Reward/Risk analysis:")
        print(f"    Risk:           {rr['risk']:.1f}")
        print(f"    Target:         {rr['target']:.1f}")
        print(f"    Reward/Risk:    {rr['reward_to_risk']:.1f}")
    else:
        print("No bull trap detected.")
