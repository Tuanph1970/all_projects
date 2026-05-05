# Price Oscillator

> Schwager, Ch. 6, pp. 113–114

## Definition

A **price oscillator** is the difference between two moving averages of different lengths:

$$ \text{Price Oscillator} = \text{MA}_{\text{short}} - \text{MA}_{\text{long}} $$

It's a refinement of the [[06_MA_Oscillator]] — instead of comparing raw price (which is jumpy) to a moving average, it compares a *smoothed* short-term average to a longer-term one. The result is a less-noisy oscillator that still flips sign at exactly the same moments as a moving-average crossover.

A multiplicative version exists too: $\text{MA}_{\text{short}} / \text{MA}_{\text{long}}$. Schwager notes the resulting indicator is equivalent.

## Illustration

![[05_price_oscillator.png]]

The top panel shows price plus a 10-day and 20-day MA. The bottom panel is the 10-day minus 20-day. Equilibrium crossings in the bottom panel correspond exactly to the points where the short MA crosses the long MA in the top panel.

## Easy analogy

Imagine measuring the speed of two cars on a highway:

- **Car A** (short MA) is responsive: it reacts quickly to traffic.
- **Car B** (long MA) is steady: it cruises at a stable pace.

When Car A is **pulling ahead** of Car B, the gap is positive — the market is accelerating. When Car A **falls behind** Car B, the gap goes negative — the market is decelerating. The price oscillator is just **the gap between the two cars**, plotted over time.

## Numeric example

| Day | Close | MA(3) | MA(5) | Price Osc (MA3 − MA5) |
|-----|-------|-------|-------|----------------------|
| 5 | 54 | 53.0 | 52.4 | +0.6 |
| 6 | 55 | 54.0 | 53.0 | +1.0 |
| 7 | 57 | 55.3 | 54.2 | +1.1 |
| 8 | 56 | 56.0 | 54.8 | +1.2 |
| 9 | 58 | 57.0 | 56.0 | +1.0 |

A sustained positive oscillator (the short average pulling away upward) confirms an uptrend; a sustained negative one confirms a downtrend.

## Python code

```python
import pandas as pd

def price_oscillator(close: pd.Series, short: int = 10, long: int = 20) -> pd.Series:
    """Difference between short and long moving averages."""
    return close.rolling(window=short).mean() - close.rolling(window=long).mean()

# Example
import numpy as np
closes = pd.Series(np.cumsum(np.random.randn(100)) + 50)
osc = price_oscillator(closes, 10, 20)
```

Full code: [[oscillators_master.py]]

## Relationships

### Within Chapter 6

- Direct generalization of [[06_MA_Oscillator]] (replaces raw price with a short MA).
- Equilibrium-line crossings = MA crossover signals — see [[04_Equilibrium_Line]].
- The famous [[08_MACD]] is a specific price oscillator using *exponential* MAs of length 12 and 26, plus an extra 9-day signal-line smoothing.
- Same overbought/oversold logic applies — see [[09_Overbought_Oversold]].

### Outside the chapter

- Equivalent to the dual-MA crossover system described in [[Chapter_14_Trading_Systems]].
- Closely related to "trend-following with two MAs" approach in [[Chapter_3_Trends]].
- The choice of `short` and `long` is a classic optimization parameter — see [[Chapter_15_Testing_Optimizing]] on the dangers of curve-fitting these values.

## When to use it vs the simpler MA Oscillator

| Need | Pick |
|------|------|
| Cleanest noise-free signal | **Price oscillator** (smoothed both sides) |
| Earliest possible signal | [[06_MA_Oscillator]] (uses raw price) |
| Standardized industry indicator | [[08_MACD]] (a price oscillator with EMAs) |
