"""
Inverse Popularity & Failed Signal Reliability — Ch 11, Concept 13
====================================================================
Schwager's meta-observation: there is an inverse relationship between
the popularity of an indicator and its efficiency. Failed signals are
currently reliable BECAUSE they are underused. If they become popular,
their reliability will degrade.

The timeless escape: peg the concept to whatever the "conventional
wisdom" is at any given time. The failure of the POPULAR is always
informative, regardless of what specific patterns are popular.

This module provides tools to measure the historical effectiveness
of failed signals vs. conventional signals, tracking whether the
inverse popularity effect is holding.

Schwager: "The concept of failed signals can be made dynamic by
pegging it to the conventional wisdom. In this more general sense,
the concept of failed signals could prove timeless."
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class SignalEfficiency:
    """Measures the efficiency of a signal type over a period."""
    signal_type: str        # 'breakout', 'failed_breakout', etc.
    period_start: pd.Timestamp
    period_end: pd.Timestamp
    total_signals: int
    successful_signals: int
    failed_signals: int
    win_rate: float          # successful / total
    avg_profit_per_signal: float
    avg_loss_per_signal: float
    profit_factor: float     # total_wins / total_losses


@dataclass
class PopularityAssessment:
    """Assesses whether a signal type shows signs of popularity decay."""
    signal_type: str
    early_period_efficiency: SignalEfficiency
    late_period_efficiency: SignalEfficiency
    efficiency_change: float     # Negative = deterioration
    shows_popularity_decay: bool # True if efficiency declined


def measure_breakout_efficiency(
    df: pd.DataFrame,
    lookback: int = 20,
    holding_period: int = 10,
    breakout_threshold_pct: float = 0.01,
) -> SignalEfficiency:
    """
    Measure how well traditional breakouts perform.

    A breakout occurs when price closes above the N-bar high or
    below the N-bar low. Efficiency = % of breakouts that lead
    to further movement in the breakout direction within the
    holding period.

    Parameters
    ----------
    df : DataFrame with ['high', 'low', 'close'] and DatetimeIndex
    lookback : bars to define the range
    holding_period : bars to hold after breakout
    breakout_threshold_pct : minimum close beyond range as % of price

    Returns
    -------
    SignalEfficiency
    """
    total = 0
    wins = 0
    losses = 0
    total_profit = 0.0
    total_loss = 0.0

    for i in range(lookback, len(df) - holding_period):
        window = df.iloc[i - lookback:i]
        range_high = window['high'].max()
        range_low = window['low'].min()
        bar = df.iloc[i]
        mid = (range_high + range_low) / 2

        # Upside breakout
        if bar['close'] > range_high * (1 + breakout_threshold_pct):
            total += 1
            future_close = df.iloc[i + holding_period]['close']
            pnl = (future_close - bar['close']) / bar['close']
            if pnl > 0:
                wins += 1
                total_profit += pnl
            else:
                losses += 1
                total_loss += abs(pnl)

        # Downside breakout
        elif bar['close'] < range_low * (1 - breakout_threshold_pct):
            total += 1
            future_close = df.iloc[i + holding_period]['close']
            pnl = (bar['close'] - future_close) / bar['close']
            if pnl > 0:
                wins += 1
                total_profit += pnl
            else:
                losses += 1
                total_loss += abs(pnl)

    win_rate = wins / total if total > 0 else 0
    avg_profit = total_profit / wins if wins > 0 else 0
    avg_loss = total_loss / losses if losses > 0 else 0
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

    return SignalEfficiency(
        signal_type='breakout',
        period_start=df.index[lookback],
        period_end=df.index[-holding_period - 1],
        total_signals=total,
        successful_signals=wins,
        failed_signals=losses,
        win_rate=round(win_rate, 3),
        avg_profit_per_signal=round(avg_profit, 4),
        avg_loss_per_signal=round(avg_loss, 4),
        profit_factor=round(profit_factor, 2),
    )


def measure_failed_breakout_efficiency(
    df: pd.DataFrame,
    lookback: int = 20,
    holding_period: int = 10,
    breakout_threshold_pct: float = 0.01,
    failure_bars: int = 3,
) -> SignalEfficiency:
    """
    Measure how well failed breakout signals perform.

    A failed breakout: price breaks out, then within `failure_bars`
    bars retreats back into the range. The trade is taken in the
    OPPOSITE direction of the original breakout.

    Parameters
    ----------
    df : DataFrame with price data
    lookback : bars to define the range
    holding_period : bars to hold after failed breakout confirmed
    breakout_threshold_pct : minimum close beyond range for breakout
    failure_bars : bars within which the breakout must fail

    Returns
    -------
    SignalEfficiency
    """
    total = 0
    wins = 0
    losses = 0
    total_profit = 0.0
    total_loss = 0.0

    for i in range(lookback, len(df) - holding_period - failure_bars):
        window = df.iloc[i - lookback:i]
        range_high = window['high'].max()
        range_low = window['low'].min()
        bar = df.iloc[i]

        # Upside breakout
        if bar['close'] > range_high * (1 + breakout_threshold_pct):
            # Check if it fails within failure_bars
            failed = False
            fail_idx = None
            for j in range(i + 1, min(i + failure_bars + 1, len(df))):
                if df.iloc[j]['close'] < range_high:
                    failed = True
                    fail_idx = j
                    break

            if failed and fail_idx is not None:
                if fail_idx + holding_period < len(df):
                    total += 1
                    entry = df.iloc[fail_idx]['close']
                    exit_price = df.iloc[fail_idx + holding_period]['close']
                    # Trade SHORT (opposite of failed upside breakout)
                    pnl = (entry - exit_price) / entry
                    if pnl > 0:
                        wins += 1
                        total_profit += pnl
                    else:
                        losses += 1
                        total_loss += abs(pnl)

        # Downside breakout
        elif bar['close'] < range_low * (1 - breakout_threshold_pct):
            failed = False
            fail_idx = None
            for j in range(i + 1, min(i + failure_bars + 1, len(df))):
                if df.iloc[j]['close'] > range_low:
                    failed = True
                    fail_idx = j
                    break

            if failed and fail_idx is not None:
                if fail_idx + holding_period < len(df):
                    total += 1
                    entry = df.iloc[fail_idx]['close']
                    exit_price = df.iloc[fail_idx + holding_period]['close']
                    # Trade LONG (opposite of failed downside breakout)
                    pnl = (exit_price - entry) / entry
                    if pnl > 0:
                        wins += 1
                        total_profit += pnl
                    else:
                        losses += 1
                        total_loss += abs(pnl)

    win_rate = wins / total if total > 0 else 0
    avg_profit = total_profit / wins if wins > 0 else 0
    avg_loss = total_loss / losses if losses > 0 else 0
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

    return SignalEfficiency(
        signal_type='failed_breakout',
        period_start=df.index[lookback],
        period_end=df.index[-holding_period - failure_bars - 1],
        total_signals=total,
        successful_signals=wins,
        failed_signals=losses,
        win_rate=round(win_rate, 3),
        avg_profit_per_signal=round(avg_profit, 4),
        avg_loss_per_signal=round(avg_loss, 4),
        profit_factor=round(profit_factor, 2),
    )


def compare_signal_efficiency(
    df: pd.DataFrame,
    split_pct: float = 0.5,
    **kwargs,
) -> dict:
    """
    Compare breakout vs. failed-breakout efficiency, and check for
    popularity decay by splitting the data into early/late halves.

    This implements Schwager's core thesis: if breakouts have degraded
    over time while failed breakouts remain effective, the inverse
    popularity effect is in play.

    Returns
    -------
    dict with 'breakout_early', 'breakout_late', 'failed_early',
    'failed_late', 'breakout_decay', 'failed_decay'
    """
    split = int(len(df) * split_pct)
    early = df.iloc[:split]
    late = df.iloc[split:]

    bo_early = measure_breakout_efficiency(early, **kwargs)
    bo_late = measure_breakout_efficiency(late, **kwargs)
    fb_early = measure_failed_breakout_efficiency(early, **kwargs)
    fb_late = measure_failed_breakout_efficiency(late, **kwargs)

    bo_decay = bo_late.win_rate - bo_early.win_rate
    fb_decay = fb_late.win_rate - fb_early.win_rate

    return {
        'breakout_early': bo_early,
        'breakout_late': bo_late,
        'failed_early': fb_early,
        'failed_late': fb_late,
        'breakout_decay': round(bo_decay, 3),
        'failed_decay': round(fb_decay, 3),
        'inverse_popularity_observed': bo_decay < 0 and fb_decay >= 0,
    }


# ── Example usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=500, freq='B')

    # Simulate price data with some mean-reverting tendencies
    prices = [100]
    for i in range(499):
        prices.append(prices[-1] + np.random.randn() * 1.5)
    prices = np.array(prices)
    highs = prices + np.random.uniform(0.5, 2.5, 500)
    lows = prices - np.random.uniform(0.5, 2.5, 500)

    df = pd.DataFrame({
        'high': highs, 'low': lows, 'close': prices
    }, index=dates)

    # Measure breakout efficiency
    bo = measure_breakout_efficiency(df)
    print(f"Breakout efficiency:")
    print(f"  Signals: {bo.total_signals}")
    print(f"  Win rate: {bo.win_rate:.1%}")
    print(f"  Profit factor: {bo.profit_factor}")

    # Measure failed breakout efficiency
    fb = measure_failed_breakout_efficiency(df)
    print(f"\nFailed breakout efficiency:")
    print(f"  Signals: {fb.total_signals}")
    print(f"  Win rate: {fb.win_rate:.1%}")
    print(f"  Profit factor: {fb.profit_factor}")

    # Compare early vs late
    comparison = compare_signal_efficiency(df)
    print(f"\nBreakout decay:  {comparison['breakout_decay']:+.1%}")
    print(f"Failed decay:    {comparison['failed_decay']:+.1%}")
    print(f"Inverse popularity observed: {comparison['inverse_popularity_observed']}")
