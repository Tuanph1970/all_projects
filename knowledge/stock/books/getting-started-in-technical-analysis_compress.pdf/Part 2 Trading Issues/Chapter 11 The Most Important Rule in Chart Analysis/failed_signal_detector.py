"""
Failed Signal Detector — Chapter 11, Concept 1
================================================
Implements the overarching principle: when a breakout fails to follow
through, treat it as a high-reliability signal in the OPPOSITE direction.

This is the base module. Specific failed signal types (bull traps,
bear traps, false trend line breakouts, etc.) build on this foundation.

Schwager: "A failed signal is among the most reliable of all chart signals."
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SignalDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class FailedSignalStatus(Enum):
    PENDING = "pending"          # Breakout occurred, watching for follow-through
    CONFIRMED = "confirmed"      # Failed signal confirmed — trade opposite direction
    INVALIDATED = "invalidated"  # Breakout succeeded — not a failed signal


@dataclass
class BreakoutEvent:
    """Records when price breaks out of a range."""
    date: pd.Timestamp
    direction: SignalDirection
    breakout_price: float
    range_high: float
    range_low: float
    range_midpoint: float


@dataclass
class FailedSignal:
    """A confirmed failed signal — the core output of this module."""
    breakout: BreakoutEvent
    confirmation_date: pd.Timestamp
    confirmation_type: str          # 'initial_price', 'strong_price', 'time'
    signal_direction: SignalDirection  # The TRADING direction (opposite to breakout)
    entry_price: float
    stop_loss: float                # Invalidation level


def detect_consolidation_range(
    df: pd.DataFrame,
    lookback: int = 20,
    max_range_pct: float = 0.10
) -> Optional[dict]:
    """
    Identify if the last `lookback` bars form a consolidation range.

    A consolidation exists when the high-low range over the lookback
    period is within `max_range_pct` of the midpoint price.

    Parameters
    ----------
    df : DataFrame with columns ['high', 'low', 'close']
    lookback : number of bars to examine
    max_range_pct : maximum range as percentage of midpoint

    Returns
    -------
    dict with 'high', 'low', 'midpoint' or None if no consolidation found
    """
    if len(df) < lookback:
        return None

    window = df.iloc[-lookback:]
    range_high = window['high'].max()
    range_low = window['low'].min()
    midpoint = (range_high + range_low) / 2
    range_pct = (range_high - range_low) / midpoint

    if range_pct <= max_range_pct:
        return {
            'high': range_high,
            'low': range_low,
            'midpoint': midpoint
        }
    return None


def detect_breakout(
    df: pd.DataFrame,
    consolidation: dict,
    min_penetration_pct: float = 0.01
) -> Optional[BreakoutEvent]:
    """
    Check if the most recent bar breaks out of the consolidation range.

    Parameters
    ----------
    df : DataFrame with columns ['high', 'low', 'close'] and DatetimeIndex
    consolidation : dict from detect_consolidation_range()
    min_penetration_pct : minimum close beyond boundary as % of range

    Returns
    -------
    BreakoutEvent or None
    """
    last = df.iloc[-1]
    range_size = consolidation['high'] - consolidation['low']
    min_pen = range_size * min_penetration_pct

    if last['close'] > consolidation['high'] + min_pen:
        return BreakoutEvent(
            date=df.index[-1],
            direction=SignalDirection.BULLISH,
            breakout_price=last['close'],
            range_high=consolidation['high'],
            range_low=consolidation['low'],
            range_midpoint=consolidation['midpoint']
        )
    elif last['close'] < consolidation['low'] - min_pen:
        return BreakoutEvent(
            date=df.index[-1],
            direction=SignalDirection.BEARISH,
            breakout_price=last['close'],
            range_high=consolidation['high'],
            range_low=consolidation['low'],
            range_midpoint=consolidation['midpoint']
        )
    return None


def check_failed_signal(
    df: pd.DataFrame,
    breakout: BreakoutEvent,
    time_confirm_bars: int = 20
) -> tuple[FailedSignalStatus, Optional[FailedSignal]]:
    """
    After a breakout, monitor subsequent price action for failure.

    Schwager defines three confirmation levels:
    1. Initial Price: retracement to range midpoint
    2. Strong Price: retracement to opposite boundary
    3. Time: failure to return to breakout extreme within N bars

    Parameters
    ----------
    df : DataFrame containing bars AFTER the breakout date
    breakout : the BreakoutEvent to monitor
    time_confirm_bars : bars before time confirmation triggers

    Returns
    -------
    (status, FailedSignal or None)
    """
    post_breakout = df[df.index > breakout.date]

    if len(post_breakout) == 0:
        return FailedSignalStatus.PENDING, None

    if breakout.direction == SignalDirection.BULLISH:
        # Bull breakout failed = bearish trading signal
        # Check invalidation first: did price make new highs?
        if post_breakout['high'].max() > breakout.breakout_price * 1.02:
            return FailedSignalStatus.INVALIDATED, None

        # Initial price confirmation: close below midpoint
        for i, (date, row) in enumerate(post_breakout.iterrows()):
            if row['close'] < breakout.range_midpoint:
                return FailedSignalStatus.CONFIRMED, FailedSignal(
                    breakout=breakout,
                    confirmation_date=date,
                    confirmation_type='initial_price',
                    signal_direction=SignalDirection.BEARISH,
                    entry_price=row['close'],
                    stop_loss=breakout.breakout_price
                )

        # Strong price confirmation: close below range low
        for i, (date, row) in enumerate(post_breakout.iterrows()):
            if row['close'] < breakout.range_low:
                return FailedSignalStatus.CONFIRMED, FailedSignal(
                    breakout=breakout,
                    confirmation_date=date,
                    confirmation_type='strong_price',
                    signal_direction=SignalDirection.BEARISH,
                    entry_price=row['close'],
                    stop_loss=breakout.breakout_price
                )

        # Time confirmation
        if len(post_breakout) >= time_confirm_bars:
            last = post_breakout.iloc[-1]
            if last['close'] < breakout.range_high:
                return FailedSignalStatus.CONFIRMED, FailedSignal(
                    breakout=breakout,
                    confirmation_date=post_breakout.index[-1],
                    confirmation_type='time',
                    signal_direction=SignalDirection.BEARISH,
                    entry_price=last['close'],
                    stop_loss=breakout.breakout_price
                )

    elif breakout.direction == SignalDirection.BEARISH:
        # Bear breakout failed = bullish trading signal
        if post_breakout['low'].min() < breakout.breakout_price * 0.98:
            return FailedSignalStatus.INVALIDATED, None

        for i, (date, row) in enumerate(post_breakout.iterrows()):
            if row['close'] > breakout.range_midpoint:
                return FailedSignalStatus.CONFIRMED, FailedSignal(
                    breakout=breakout,
                    confirmation_date=date,
                    confirmation_type='initial_price',
                    signal_direction=SignalDirection.BULLISH,
                    entry_price=row['close'],
                    stop_loss=breakout.breakout_price
                )

        for i, (date, row) in enumerate(post_breakout.iterrows()):
            if row['close'] > breakout.range_high:
                return FailedSignalStatus.CONFIRMED, FailedSignal(
                    breakout=breakout,
                    confirmation_date=date,
                    confirmation_type='strong_price',
                    signal_direction=SignalDirection.BULLISH,
                    entry_price=row['close'],
                    stop_loss=breakout.breakout_price
                )

        if len(post_breakout) >= time_confirm_bars:
            last = post_breakout.iloc[-1]
            if last['close'] > breakout.range_low:
                return FailedSignalStatus.CONFIRMED, FailedSignal(
                    breakout=breakout,
                    confirmation_date=post_breakout.index[-1],
                    confirmation_type='time',
                    signal_direction=SignalDirection.BULLISH,
                    entry_price=last['close'],
                    stop_loss=breakout.breakout_price
                )

    return FailedSignalStatus.PENDING, None


# ── Example usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=60, freq='B')

    # Simulate: 30 bars of consolidation, breakout, then failure
    consolidation_prices = 100 + np.random.randn(30).cumsum() * 0.3
    breakout_prices = [105, 107]  # brief breakout above range
    failure_prices = [104, 101, 98, 95, 93, 91, 89, 87, 85, 83,
                      82, 81, 80, 79, 78, 77, 76, 75, 74, 73,
                      72, 71, 70, 69, 68, 67, 66, 65]

    all_close = np.concatenate([consolidation_prices, breakout_prices, failure_prices])
    highs = all_close + np.random.uniform(0.5, 2, len(all_close))
    lows = all_close - np.random.uniform(0.5, 2, len(all_close))

    df = pd.DataFrame({
        'high': highs, 'low': lows, 'close': all_close
    }, index=dates)

    # Step 1: Find consolidation
    consolidation = detect_consolidation_range(df.iloc[:30], lookback=20)
    if consolidation:
        print(f"Consolidation found: {consolidation['low']:.1f} - {consolidation['high']:.1f}")

        # Step 2: Check for breakout
        breakout = detect_breakout(df.iloc[:32], consolidation)
        if breakout:
            print(f"Breakout detected: {breakout.direction.value} on {breakout.date.date()}")
            print(f"  Breakout price: {breakout.breakout_price:.1f}")

            # Step 3: Monitor for failure
            status, signal = check_failed_signal(df, breakout)
            print(f"Status: {status.value}")
            if signal:
                print(f"  Failed signal confirmed on {signal.confirmation_date.date()}")
                print(f"  Type: {signal.confirmation_type}")
                print(f"  Trade direction: {signal.signal_direction.value}")
                print(f"  Entry: {signal.entry_price:.1f}")
                print(f"  Stop loss: {signal.stop_loss:.1f}")
