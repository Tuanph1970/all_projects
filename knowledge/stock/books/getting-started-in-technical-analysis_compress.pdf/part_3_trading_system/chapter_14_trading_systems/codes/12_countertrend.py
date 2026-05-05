"""
Concept: Countertrend Systems
Chapter 14, Schwager.

A countertrend system waits for a meaningful price move and then trades
in the OPPOSITE direction, expecting a correction.

Three flavors covered in the chapter:
  1) Fading minimum move : trade when price moves X% against the prior
                            extreme since the last countertrend signal.
  2) Oscillators         : RSI/stochastic-style indicators flag overbought
                            or oversold conditions (covered in Ch. 6).
  3) Contrary opinion    : sentiment surveys signal extremes.

Trade-off: countertrend systems work BEST in trading-range markets
and FAIL HARDEST in trending markets — exactly the opposite of
trend-following systems.
"""
import numpy as np
import pandas as pd

def fade_minimum_move(prices, threshold=0.04):
    """Generate countertrend buy/sell signals on X% reversals."""
    p = np.asarray(prices, dtype=float)
    sigs = []
    last_signal_side = None
    peak = p[0]; trough = p[0]
    for i in range(1, len(p)):
        peak = max(peak, p[i])
        trough = min(trough, p[i])
        # buy on X% drop from recent peak
        if last_signal_side != 'BUY' and p[i] <= peak * (1 - threshold):
            sigs.append({'day': i, 'price': p[i], 'side': 'BUY'})
            last_signal_side = 'BUY'
            peak = p[i]; trough = p[i]
        # sell on X% rally from recent trough
        elif last_signal_side != 'SELL' and p[i] >= trough * (1 + threshold):
            sigs.append({'day': i, 'price': p[i], 'side': 'SELL'})
            last_signal_side = 'SELL'
            peak = p[i]; trough = p[i]
    return pd.DataFrame(sigs)

if __name__ == '__main__':
    # Range-bound market: countertrend should excel here
    t = np.arange(200)
    range_prices = 100 + 5*np.sin(t/10) + np.random.default_rng(123).normal(0, 0.6, 200)
    sigs_range = fade_minimum_move(range_prices, threshold=0.04)
    print(f"Range market : {len(sigs_range)} countertrend signals")

    # Trending market: countertrend should fail here
    trending = 100 + np.cumsum(np.random.default_rng(123).normal(0.3, 1.0, 200))
    sigs_trend = fade_minimum_move(trending, threshold=0.04)
    print(f"Trending mkt : {len(sigs_trend)} countertrend signals")

    print()
    print("Lesson: countertrend systems should be deployed selectively,")
    print("ideally combined with a regime filter that detects ranges.")
