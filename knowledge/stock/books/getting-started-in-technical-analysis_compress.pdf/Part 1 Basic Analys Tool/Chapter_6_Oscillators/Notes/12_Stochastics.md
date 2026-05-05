# Stochastics (%K and %D)

> Schwager, Ch. 6, p. 116; Appendix p. 321. Originator: George Lane.

## Definition

The **stochastic oscillator** measures where today's close sits within the recent high-low range, expressed as a 0–100 percentage. The intuition: in a healthy uptrend closes cluster near the top of the range; in a healthy downtrend they cluster near the bottom.

**Fast %K** (raw):

$$ \%K = \frac{\text{Close}_t - \text{Low}_n}{\text{High}_n - \text{Low}_n} \times 100 $$

**Fast %D** = 3-period MA of %K (default).

**Slow stochastics** (the version most often plotted): the fast %D becomes the new "slow %K", which is then smoothed again by a 3-period MA to form the slow %D. Two layers of smoothing make the indicator less jumpy.

Standard thresholds: **80 = overbought, 20 = oversold**.

## Illustration

![[09_stochastics.png]]

Blue = slow %K, red = slow %D. Crossings of %K above/below %D within the OB/OS zones are the canonical trade triggers.

## Easy analogy

A high-jumper repeatedly jumping in the same area. Recent attempts span a range — say, between 1.80 m and 2.00 m. **%K answers: where did the latest jump land within that recent range?**

- 95 % → almost touched the top → the jumper is near peak performance, hard to maintain.
- 5 % → near the floor of recent range → underperforming, likely to spring back up.

It's a contextual measurement: 1.95 m is impressive only if the recent range is 1.80–2.00 m. If the range is 1.95–2.10 m, that same 1.95 m is actually weak.

## Numeric example

Suppose over the past 14 days a stock had:

- Highest high: $60
- Lowest low: $48
- Today's close: $57

$$ \%K = \frac{57 - 48}{60 - 48} \times 100 = \frac{9}{12} \times 100 = 75 $$

A reading of 75 — close to overbought (80) but not quite there. If today's reading reaches 81 tomorrow with close = $57.72, the indicator crosses into overbought territory and triggers an alert.

## Python code

```python
import pandas as pd

def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               n: int = 14, d_period: int = 3):
    """Fast stochastic: %K and its 3-period MA (%D)."""
    lowest_low = low.rolling(window=n).min()
    highest_high = high.rolling(window=n).max()
    k = ((close - lowest_low) / (highest_high - lowest_low)) * 100
    d = k.rolling(window=d_period).mean()
    return k, d

def slow_stochastic(high, low, close, n=14, smooth_k=3, d_period=3):
    """Slow stochastic: smooth %K then take MA for %D."""
    fast_k, _ = stochastic(high, low, close, n, d_period=1)
    slow_k = fast_k.rolling(window=smooth_k).mean()
    slow_d = slow_k.rolling(window=d_period).mean()
    return slow_k, slow_d
```

Full implementation: [[oscillators_master.py]]

## Relationships

### Within Chapter 6

- A normalized oscillator like [[11_RSI]] — see [[10_Normalized_Unbounded]] for why this matters.
- Equilibrium = 50, see [[04_Equilibrium_Line]].
- Standard OB/OS levels of 80/20 are an instance of [[09_Overbought_Oversold]] tuned for a 0–100 oscillator.
- The dual-line %K/%D structure mimics the MACD/signal-line setup in [[08_MACD]].
- Like all oscillators here, it can produce [[13_Divergence]] signals.
- Best deployed as a [[14_Trading_Alerts]] tool, especially in trending markets where it pins to one side.

### Outside the chapter

- The "fraction of recent range" idea is conceptually related to position within Bollinger bands and to **price envelope** support/resistance ([[Chapter_4_Trading_Ranges]]).
- Used inside countertrend systems in [[Chapter_14_Trading_Systems]].
- Detailed formula in [[Appendix_Formulas]].

## RSI vs Stochastics — when to pick which

| Property | RSI | Stochastics |
|----------|-----|-------------|
| Inputs | Closes only | Closes + Highs + Lows |
| Sensitivity | Smooth | Sharper, more "twitchy" until smoothed (slow) |
| Best for | Detecting persistent strength/weakness | Detecting precise turning points within a range |
| Default OB/OS | 70 / 30 | 80 / 20 |
| Default *n* | 14 | 14 (with 3-period smoothing) |

Many traders plot **both** to require dual confirmation, exactly as Schwager does in his Figure 6.1.
