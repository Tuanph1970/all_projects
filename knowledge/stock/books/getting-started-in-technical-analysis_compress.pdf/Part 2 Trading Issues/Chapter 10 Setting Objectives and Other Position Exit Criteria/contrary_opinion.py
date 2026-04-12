"""
Contrary Opinion — Chapter 10, Concept 5
==========================================
Uses sentiment extremes as signals to liquidate positions or
anticipate reversals.

Schwager: "Although contrary opinion is undoubtedly a sound
theoretical concept, the Achilles' heel of this approach is
the difficulty of measuring market sentiment accurately."

This module provides:
  - Sentiment extreme detection
  - Signal generation with quality assessment
  - Sentiment data simulation (for testing)
  - Confluence with other exit methods
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Literal


@dataclass
class SentimentReading:
    """A single sentiment survey data point."""
    index: int
    date: Optional[str]
    bullish_pct: float
    bearish_pct: float
    neutral_pct: float = 0.0

    def __post_init__(self):
        if self.neutral_pct == 0.0:
            self.neutral_pct = 100.0 - self.bullish_pct - self.bearish_pct


@dataclass
class ContrarySignal:
    """
    An exit/caution signal from contrary opinion analysis.
    
    Schwager uses these as position LIQUIDATION signals,
    not as entry signals on their own. In Chapter 14,
    he mentions using them as countertrend system inputs
    contingent on technical confirmation.
    """
    index: int
    price: float
    bullish_pct: float
    signal_type: str  # 'extreme_bullish' or 'extreme_bearish'
    threshold: float
    action: str  # 'exit_long', 'exit_short', or 'caution'

    @property
    def description(self) -> str:
        extremity = "bullish" if self.signal_type == 'extreme_bullish' else "bearish"
        return (f"Extreme {extremity} sentiment ({self.bullish_pct:.0f}% bullish) "
                f"→ {self.action} at {self.price:.2f}")

    @property
    def schwager_caveat(self) -> str:
        return (
            "Contrary opinion provides useful information as long as "
            "it is not used as the sole trading guideline. "
            "Sentiment can stay extreme during strong trends."
        )


def detect_sentiment_extremes(
    bullish_pct: pd.Series,
    prices: pd.Series,
    bullish_threshold: float = 75.0,
    bearish_threshold: float = 25.0,
) -> List[ContrarySignal]:
    """
    Detect sentiment extreme crossings that suggest position exits.
    
    Schwager's framework:
    - Extreme bullish (>threshold) → "those who want to be long
      are already long" → exit longs / caution on new longs
    - Extreme bearish (<threshold) → paucity of sellers remaining
      → exit shorts / caution on new shorts
    
    Parameters
    ----------
    bullish_pct : pd.Series
        Percentage of bulls in sentiment survey (0-100).
    prices : pd.Series
        Corresponding price series.
    bullish_threshold : float
        Above this = extreme bullish sentiment.
    bearish_threshold : float
        Below this = extreme bearish sentiment.
        
    Returns
    -------
    list of ContrarySignal
    """
    signals = []
    
    for i in range(1, len(bullish_pct)):
        bp = float(bullish_pct.iloc[i])
        bp_prev = float(bullish_pct.iloc[i-1])
        
        # Crosses into extreme bullish zone
        if bp >= bullish_threshold and bp_prev < bullish_threshold:
            signals.append(ContrarySignal(
                index=i,
                price=float(prices.iloc[i]),
                bullish_pct=bp,
                signal_type='extreme_bullish',
                threshold=bullish_threshold,
                action='exit_long',
            ))
        
        # Crosses into extreme bearish zone
        if bp <= bearish_threshold and bp_prev > bearish_threshold:
            signals.append(ContrarySignal(
                index=i,
                price=float(prices.iloc[i]),
                bullish_pct=bp,
                signal_type='extreme_bearish',
                threshold=bearish_threshold,
                action='exit_short',
            ))
    
    return signals


def assess_contrary_signals(
    prices: pd.Series,
    signals: List[ContrarySignal],
    forward_bars: int = 15,
    reversal_pct: float = 2.0
) -> dict:
    """
    Evaluate the quality of contrary opinion signals.
    
    Checks whether price reversed after extreme sentiment readings,
    demonstrating Schwager's observation that these signals
    "have frequently signaled major turning points" but can also
    persist during trends.
    
    Parameters
    ----------
    prices : pd.Series
        Price series.
    signals : list of ContrarySignal
        Generated signals.
    forward_bars : int
        Bars to look ahead for reversal.
    reversal_pct : float
        Minimum % reversal to count as correct.
        
    Returns
    -------
    dict with keys: total, correct, false, hit_rate, persistence_cases
    """
    correct = 0
    false_signals = 0
    persistence = 0  # Schwager's "stay high while market climbs"
    
    for sig in signals:
        end_idx = min(sig.index + forward_bars, len(prices) - 1)
        if end_idx <= sig.index:
            continue
        
        future = prices.iloc[sig.index:end_idx + 1]
        
        if sig.signal_type == 'extreme_bullish':
            # Correct if price drops
            max_drop = (sig.price - float(future.min())) / sig.price * 100
            continued_up = (float(future.max()) - sig.price) / sig.price * 100
            
            if max_drop >= reversal_pct:
                correct += 1
            else:
                false_signals += 1
                if continued_up > reversal_pct:
                    persistence += 1
        else:
            # Correct if price rises
            max_rise = (float(future.max()) - sig.price) / sig.price * 100
            continued_down = (sig.price - float(future.min())) / sig.price * 100
            
            if max_rise >= reversal_pct:
                correct += 1
            else:
                false_signals += 1
                if continued_down > reversal_pct:
                    persistence += 1
    
    total = correct + false_signals
    return {
        'total': total,
        'correct': correct,
        'false': false_signals,
        'hit_rate': correct / total if total > 0 else 0.0,
        'persistence_cases': persistence,
        'persistence_note': (
            f"{persistence} case(s) where sentiment stayed extreme "
            f"and price continued trending — Schwager's Achilles' heel."
        ) if persistence > 0 else "No persistence issues detected.",
    }


def simulate_sentiment(
    prices: pd.Series,
    lag: int = 5,
    noise_std: float = 10.0,
    sensitivity: float = 3.0,
    seed: int = 42
) -> pd.Series:
    """
    Simulate a sentiment survey series from price data.
    
    Real sentiment tends to:
    - Track recent price direction (herding behavior)
    - Lag behind price (surveys published weekly)
    - Have measurement noise (small sample, selection bias)
    
    Parameters
    ----------
    prices : pd.Series
        Price series to derive sentiment from.
    lag : int
        How many bars sentiment lags behind price.
    noise_std : float
        Standard deviation of measurement noise.
    sensitivity : float
        How strongly returns translate to sentiment shifts.
    seed : int
        Random seed for reproducibility.
        
    Returns
    -------
    pd.Series
        Simulated bullish percentage (0-100).
    """
    np.random.seed(seed)
    
    # Recent returns drive sentiment
    lookback = max(lag, 10)
    sentiment = pd.Series(50.0, index=prices.index)
    
    for i in range(lookback, len(prices)):
        # Lagged return
        ret = (prices.iloc[i - lag] - prices.iloc[i - lookback]) / prices.iloc[i - lookback] * 100
        raw = 50.0 + ret * sensitivity + np.random.randn() * noise_std
        # Clamp to 5-95 range
        sentiment.iloc[i] = max(5, min(95, raw))
    
    return sentiment


def contrary_with_confirmation(
    prices: pd.Series,
    sentiment: pd.Series,
    rsi: pd.Series,
    bullish_threshold: float = 75.0,
    bearish_threshold: float = 25.0,
    rsi_confirm_ob: float = 70.0,
    rsi_confirm_os: float = 30.0,
) -> List[ContrarySignal]:
    """
    Generate contrary opinion signals WITH technical confirmation.
    
    Schwager (Ch. 14): contrary opinion as a countertrend input
    "contingent on confirmation by a very sensitive technical
    indicator." This combines sentiment extremes with RSI
    confirmation to filter false signals.
    
    Parameters
    ----------
    prices : pd.Series
        Price series.
    sentiment : pd.Series
        Bullish percentage.
    rsi : pd.Series
        Pre-calculated RSI.
    bullish_threshold, bearish_threshold : float
        Sentiment extreme thresholds.
    rsi_confirm_ob, rsi_confirm_os : float
        RSI must also be in OB/OS zone to confirm.
        
    Returns
    -------
    list of ContrarySignal
        Only signals where BOTH sentiment AND RSI confirm.
    """
    raw_signals = detect_sentiment_extremes(
        sentiment, prices, bullish_threshold, bearish_threshold
    )
    
    confirmed = []
    for sig in raw_signals:
        rsi_val = float(rsi.iloc[sig.index])
        
        if (sig.signal_type == 'extreme_bullish' and rsi_val >= rsi_confirm_ob):
            sig.action = 'exit_long (sentiment + RSI confirmed)'
            confirmed.append(sig)
        elif (sig.signal_type == 'extreme_bearish' and rsi_val <= rsi_confirm_os):
            sig.action = 'exit_short (sentiment + RSI confirmed)'
            confirmed.append(sig)
    
    return confirmed


# --- Example usage ---
if __name__ == "__main__":
    np.random.seed(42)
    N = 200
    
    # Generate price + sentiment
    prices = pd.Series(100 + np.cumsum(
        np.sin(np.arange(N) * 0.05) * 0.8 + np.random.randn(N) * 1.0
    ))
    sentiment = simulate_sentiment(prices, lag=5, noise_std=10)
    
    print("=== Contrary Opinion Signals ===")
    signals = detect_sentiment_extremes(sentiment, prices, 75, 25)
    for s in signals[:5]:
        print(f"  {s.description}")
    
    print(f"\n  Total signals: {len(signals)}")
    
    print("\n=== Signal Quality Assessment ===")
    quality = assess_contrary_signals(prices, signals)
    print(f"  Correct: {quality['correct']}/{quality['total']} "
          f"({quality['hit_rate']:.0%})")
    print(f"  False: {quality['false']}")
    print(f"  {quality['persistence_note']}")
    
    print("\n=== With RSI Confirmation (Ch. 14 approach) ===")
    from obos_exit_signals import calculate_rsi
    rsi = calculate_rsi(prices)
    confirmed = contrary_with_confirmation(
        prices, sentiment, rsi,
        bullish_threshold=75, bearish_threshold=25,
        rsi_confirm_ob=65, rsi_confirm_os=35
    )
    print(f"  Raw signals: {len(signals)}")
    print(f"  Confirmed signals: {len(confirmed)}")
    for s in confirmed[:3]:
        print(f"    {s.description}")
    
    if confirmed:
        q2 = assess_contrary_signals(prices, confirmed)
        print(f"  Confirmed hit rate: {q2['hit_rate']:.0%}")
