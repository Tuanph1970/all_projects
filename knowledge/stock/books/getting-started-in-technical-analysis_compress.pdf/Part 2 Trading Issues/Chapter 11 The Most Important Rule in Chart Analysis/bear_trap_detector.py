"""
Bear Trap Detector — Chapter 11, Concept 3
============================================
A bear trap is a major downside breakout that is soon followed by an abrupt
reversal upward. The mirror image of a bull trap.

Schwager: "In the case of a bear trap the market falls just enough to trigger
resting stops below the low end of a trading range, but fails to uncover any
additional selling pressure after the breakout — an indication of substantial
underlying strength."

Key example: July 1993 Silver — six-year downtrend culminated in a bear trap
that preceded a dramatic rally.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional
from failed_signal_detector import detect_consolidation_range, SignalDirection


class ConfirmationType:
    INITIAL_PRICE = "initial_price"
    STRONG_PRICE = "strong_price"
    TIME = "time"


@dataclass
class BearTrap:
    """A confirmed bear trap with full context."""
    breakout_date: pd.Timestamp
    breakout_low: float
    range_high: float
    range_low: float
    range_midpoint: float
    confirmation_date: pd.Timestamp
    confirmation_type: str
    entry_price: float
    stop_loss: float
    initial_confirmed: bool = False
    strong_confirmed: bool = False
    time_confirmed: bool = False


def detect_bear_trap(
    df: pd.DataFrame,
    lookback: int = 20,
    max_range_pct: float = 0.10,
    min_breakout_pct: float = 0.005,
    time_confirm_bars: int = 20,
    invalidation_buffer: float = 0.995,
) -> Optional[BearTrap]:
    """
    Scan for a bear trap: consolidation -> downside breakout -> failure.

    Mirror of detect_bull_trap():
    1. Find consolidation range
    2. Detect downside breakout (close below support)
    3. Monitor for confirmation or invalidation:
       - Invalidation: price falls below breakout_low * buffer
       - Initial: close above midpoint
       - Strong: close above resistance (range high)
       - Time: N bars without reclaiming breakout low
    """
    if len(df) < lookback + 2:
        return None

    consolidation = detect_consolidation_range(
        df.iloc[:lookback], lookback=lookback, max_range_pct=max_range_pct
    )
    if consolidation is None:
        return None

    rh, rl, mid = consolidation['high'], consolidation['low'], consolidation['midpoint']
    range_size = rh - rl

    # Find downside breakout
    breakout_idx = None
    breakout_low = None
    for i in range(lookback, len(df)):
        if df.iloc[i]['close'] < rl - range_size * min_breakout_pct:
            breakout_idx = i
            breakout_low = df.iloc[i]['low']
            break

    if breakout_idx is None:
        return None

    # Track lowest point of breakout move
    j = breakout_idx + 1
    while j < len(df) and df.iloc[j]['low'] < df.iloc[j - 1]['close']:
        breakout_low = min(breakout_low, df.iloc[j]['low'])
        j += 1

    # Monitor for confirmation or invalidation
    post_start = j if j < len(df) else breakout_idx + 1
    initial_confirmed = strong_confirmed = time_confirmed = False
    first_confirmation = None

    for k in range(post_start, len(df)):
        bar = df.iloc[k]

        if bar['low'] < breakout_low * invalidation_buffer:
            return None

        if not initial_confirmed and bar['close'] > mid:
            initial_confirmed = True
            if first_confirmation is None:
                first_confirmation = (df.index[k], ConfirmationType.INITIAL_PRICE, bar['close'])

        if not strong_confirmed and bar['close'] > rh:
            strong_confirmed = True
            if first_confirmation is None:
                first_confirmation = (df.index[k], ConfirmationType.STRONG_PRICE, bar['close'])

        if not time_confirmed and (k - breakout_idx) >= time_confirm_bars:
            if bar['close'] > rl:
                time_confirmed = True
                if first_confirmation is None:
                    first_confirmation = (df.index[k], ConfirmationType.TIME, bar['close'])

    if first_confirmation is None:
        return None

    conf_date, conf_type, entry = first_confirmation
    return BearTrap(
        breakout_date=df.index[breakout_idx],
        breakout_low=breakout_low,
        range_high=rh, range_low=rl, range_midpoint=mid,
        confirmation_date=conf_date,
        confirmation_type=conf_type,
        entry_price=entry,
        stop_loss=breakout_low,
        initial_confirmed=initial_confirmed,
        strong_confirmed=strong_confirmed,
        time_confirmed=time_confirmed,
    )


def bear_trap_reward_risk(trap: BearTrap, target_multiple: float = 2.0) -> dict:
    """Calculate reward-to-risk for a bear trap long trade."""
    risk = trap.entry_price - trap.stop_loss
    range_height = trap.range_high - trap.range_low
    target = trap.range_high + (range_height * target_multiple)
    reward = target - trap.entry_price
    return {
        'entry': trap.entry_price,
        'stop_loss': trap.stop_loss,
        'target': target,
        'risk': risk,
        'reward': reward,
        'reward_to_risk': reward / risk if risk > 0 else 0,
    }


if __name__ == "__main__":
    np.random.seed(99)
    dates = pd.date_range('2024-01-01', periods=50, freq='B')
    consol = np.clip(100 + np.random.randn(20) * 2, 96, 104)
    breakdown = [94, 91, 89]
    recovery = [90, 93, 97, 100, 103, 106, 109, 112, 114, 116,
                118, 120, 122, 123, 124, 125, 126, 127, 128, 129,
                130, 131, 132, 133, 134, 135, 136]
    all_close = np.concatenate([consol, breakdown, recovery])
    highs = all_close + np.random.uniform(0.5, 2.5, len(all_close))
    lows = all_close - np.random.uniform(0.5, 2.5, len(all_close))
    df = pd.DataFrame({'high': highs, 'low': lows, 'close': all_close}, index=dates)

    trap = detect_bear_trap(df, lookback=20)
    if trap:
        print(f"Bear Trap detected!")
        print(f"  Breakout date:  {trap.breakout_date.date()}")
        print(f"  Breakout low:   {trap.breakout_low:.1f}")
        print(f"  Range:          {trap.range_low:.1f} - {trap.range_high:.1f}")
        print(f"  Confirmation:   {trap.confirmation_type} on {trap.confirmation_date.date()}")
        print(f"  Entry (BUY):    {trap.entry_price:.1f}")
        print(f"  Stop loss:      {trap.stop_loss:.1f}")
        rr = bear_trap_reward_risk(trap)
        print(f"  Reward/Risk:    {rr['reward_to_risk']:.1f}")
    else:
        print("No bear trap detected.")
