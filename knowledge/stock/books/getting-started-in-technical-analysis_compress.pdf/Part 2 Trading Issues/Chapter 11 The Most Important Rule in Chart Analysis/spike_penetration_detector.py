"""
Spike Extreme Penetration Detector — Chapter 11, Concept 7
============================================================
Price spikes frequently occur at important reversals. The return of price
to a prior spike extreme transforms the spike into a failed signal,
implying a substantial move in the penetration direction.

Significance enhancers:
1. Greater spike magnitude (how far it protrudes beyond neighboring bars)
2. More time elapsed since original spike (weeks minimum, months preferred)

Negation rule: a close beyond the OPPOSITE extreme of the spike day
negates the failed signal ("failed failed signal").

Schwager: "The more extreme the spike, the greater the significance of
its penetration."
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SpikeType(Enum):
    HIGH = "spike_high"   # High sharply above neighboring highs
    LOW = "spike_low"     # Low sharply below neighboring lows


@dataclass
class Spike:
    """A price spike — a day with an extreme that sharply exceeds neighbors."""
    date: pd.Timestamp
    bar_idx: int
    spike_type: SpikeType
    spike_price: float         # The extreme (high for spike high, low for spike low)
    opposite_extreme: float    # The other extreme of the spike day
    close: float               # Close on spike day
    magnitude: float           # How far spike protrudes beyond neighbors (absolute)
    magnitude_pct: float       # Magnitude as percentage of price


@dataclass
class SpikePenetration:
    """A confirmed spike penetration — the failed signal."""
    spike: Spike
    penetration_date: pd.Timestamp
    penetration_bar_idx: int
    penetration_price: float     # Close at penetration
    bars_elapsed: int            # Bars between spike and penetration
    trade_direction: str         # 'long' for penetrated spike high, 'short' for spike low
    negation_price: float        # Close beyond this = signal negated
    significance_score: float    # Based on magnitude and time elapsed


def detect_spikes(
    df: pd.DataFrame,
    min_protrusion_pct: float = 0.005,
    neighbor_window: int = 2,
) -> list[Spike]:
    """
    Find price spikes in the data.

    A spike high: high[i] > high[i-1..i-n] AND high[i] > high[i+1..i+n]
    by at least min_protrusion_pct of the price.

    Parameters
    ----------
    df : DataFrame with ['high', 'low', 'close'] and DatetimeIndex
    min_protrusion_pct : minimum protrusion as % of price
    neighbor_window : how many bars on each side to compare

    Returns
    -------
    List of Spike objects
    """
    spikes = []
    n = len(df)

    for i in range(neighbor_window, n - neighbor_window):
        hi = df.iloc[i]['high']
        lo = df.iloc[i]['low']
        close = df.iloc[i]['close']

        # Check spike high
        neighbor_highs = [df.iloc[j]['high']
                          for j in range(i - neighbor_window, i + neighbor_window + 1)
                          if j != i]
        max_neighbor_high = max(neighbor_highs)
        protrusion_high = hi - max_neighbor_high

        if protrusion_high > 0 and (protrusion_high / hi) >= min_protrusion_pct:
            spikes.append(Spike(
                date=df.index[i],
                bar_idx=i,
                spike_type=SpikeType.HIGH,
                spike_price=hi,
                opposite_extreme=lo,
                close=close,
                magnitude=protrusion_high,
                magnitude_pct=protrusion_high / hi,
            ))

        # Check spike low
        neighbor_lows = [df.iloc[j]['low']
                         for j in range(i - neighbor_window, i + neighbor_window + 1)
                         if j != i]
        min_neighbor_low = min(neighbor_lows)
        protrusion_low = min_neighbor_low - lo

        if protrusion_low > 0 and (protrusion_low / lo) >= min_protrusion_pct:
            spikes.append(Spike(
                date=df.index[i],
                bar_idx=i,
                spike_type=SpikeType.LOW,
                spike_price=lo,
                opposite_extreme=hi,
                close=close,
                magnitude=protrusion_low,
                magnitude_pct=protrusion_low / lo,
            ))

    return spikes


def detect_spike_penetration(
    df: pd.DataFrame,
    spike: Spike,
    min_elapsed_bars: int = 10,
) -> Optional[SpikePenetration]:
    """
    Check if a spike extreme is later penetrated.

    For spike high: price closes above the spike high → BUY
    For spike low: price closes below the spike low → SELL

    Parameters
    ----------
    df : DataFrame with price data
    spike : Spike object to monitor
    min_elapsed_bars : minimum bars before a penetration counts
                       (Schwager prefers weeks/months)

    Returns
    -------
    SpikePenetration or None
    """
    for i in range(spike.bar_idx + min_elapsed_bars, len(df)):
        bar = df.iloc[i]
        bars_elapsed = i - spike.bar_idx

        if spike.spike_type == SpikeType.HIGH:
            if bar['close'] > spike.spike_price:
                # Calculate significance
                mag_score = min(spike.magnitude_pct / 0.02, 1.0)  # Normalize
                time_score = min(bars_elapsed / 60, 1.0)  # ~3 months = max
                sig = (mag_score + time_score) / 2

                return SpikePenetration(
                    spike=spike,
                    penetration_date=df.index[i],
                    penetration_bar_idx=i,
                    penetration_price=bar['close'],
                    bars_elapsed=bars_elapsed,
                    trade_direction='long',
                    negation_price=spike.opposite_extreme,  # Spike day's low
                    significance_score=round(sig, 2),
                )

        elif spike.spike_type == SpikeType.LOW:
            if bar['close'] < spike.spike_price:
                mag_score = min(spike.magnitude_pct / 0.02, 1.0)
                time_score = min(bars_elapsed / 60, 1.0)
                sig = (mag_score + time_score) / 2

                return SpikePenetration(
                    spike=spike,
                    penetration_date=df.index[i],
                    penetration_bar_idx=i,
                    penetration_price=bar['close'],
                    bars_elapsed=bars_elapsed,
                    trade_direction='short',
                    negation_price=spike.opposite_extreme,  # Spike day's high
                    significance_score=round(sig, 2),
                )

    return None


def check_penetration_negated(
    df: pd.DataFrame,
    penetration: SpikePenetration,
) -> dict:
    """
    Check if a spike penetration signal has been negated.

    Schwager's rule: a close beyond the OPPOSITE extreme of the spike
    day negates the failed signal.

    For penetrated spike high (long trade): negated if close < spike day's low
    For penetrated spike low (short trade): negated if close > spike day's high

    Returns
    -------
    dict with 'negated', 'negation_date'
    """
    for i in range(penetration.penetration_bar_idx + 1, len(df)):
        bar = df.iloc[i]

        if penetration.trade_direction == 'long':
            # Long from spike high penetration; negated if close < spike day low
            if bar['close'] < penetration.negation_price:
                return {'negated': True, 'negation_date': df.index[i]}
        else:
            # Short from spike low penetration; negated if close > spike day high
            if bar['close'] > penetration.negation_price:
                return {'negated': True, 'negation_date': df.index[i]}

    return {'negated': False, 'negation_date': None}


# ── Example usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='B')

    # Simulate: uptrend, spike high at bar 30, decline, then rally back through
    prices = [100]
    for i in range(99):
        if i < 28:
            prices.append(prices[-1] + 0.5 + np.random.randn() * 0.5)
        elif i == 29:
            prices.append(prices[-1] + 0.3)  # spike day close
        elif i < 60:
            prices.append(prices[-1] - 0.3 + np.random.randn() * 0.5)
        else:
            prices.append(prices[-1] + 0.4 + np.random.randn() * 0.5)

    prices = np.array(prices)
    highs = prices + np.random.uniform(0.5, 2, 100)
    lows = prices - np.random.uniform(0.5, 2, 100)

    # Inject a spike high at bar 30
    highs[30] = prices[30] + 8  # Sharp protrusion

    df = pd.DataFrame({
        'high': highs, 'low': lows, 'close': prices
    }, index=dates)

    spikes = detect_spikes(df, min_protrusion_pct=0.01)
    print(f"Found {len(spikes)} spikes:")
    for sp in spikes:
        print(f"  {sp.spike_type.value} on {sp.date.date()}, "
              f"price={sp.spike_price:.1f}, magnitude={sp.magnitude_pct:.1%}")

    for sp in spikes:
        pen = detect_spike_penetration(df, sp, min_elapsed_bars=15)
        if pen:
            print(f"\n  Spike PENETRATED on {pen.penetration_date.date()}")
            print(f"    Bars elapsed:    {pen.bars_elapsed}")
            print(f"    Trade:           {pen.trade_direction}")
            print(f"    Entry price:     {pen.penetration_price:.1f}")
            print(f"    Negation level:  {pen.negation_price:.1f}")
            print(f"    Significance:    {pen.significance_score:.2f}")

            neg = check_penetration_negated(df, pen)
            print(f"    Negated:         {neg['negated']}")
