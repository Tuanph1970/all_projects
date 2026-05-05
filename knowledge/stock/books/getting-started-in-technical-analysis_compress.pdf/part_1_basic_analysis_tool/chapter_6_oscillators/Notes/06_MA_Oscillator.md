# Moving Average Oscillator

> Schwager, Ch. 6, pp. 113–114

## Definition

A **moving average (MA) oscillator** measures the distance between price and its moving average:

$$ \text{MA Oscillator} = \text{Close}_t - \text{MA}_n $$

When the oscillator is above zero, price is above the average (bullish bias); below zero, price is below the average (bearish bias). The further the value from zero, the more "stretched" the price is from its baseline — a candidate for overbought/oversold.

## Illustration

![[04_ma_oscillator.png]]

The top panel shows price and its 20-day MA. The bottom panel shows the difference. A zero crossing in the lower panel is exactly when price crosses its MA in the upper panel.

## Easy analogy

Think of a dog being walked on a long leash. The owner (the moving average) walks in a fairly straight, slow line. The dog (the price) wanders ahead and behind, sniffing things, but eventually snaps back to the owner because of the leash. The MA oscillator measures **how far the dog has strayed** at any moment. The further the stretch, the more likely a sharp tug back.

## Numeric example

| Day | Close | 5-day MA | Oscillator |
|-----|-------|----------|-----------|
| 6 | 55 | 52.4 | +2.6 |
| 7 | 56 | 53.0 | +3.0 |
| 8 | 54 | 53.6 | +0.4 |
| 9 | 53 | 54.0 | −1.0 |
| 10 | 52 | 54.0 | −2.0 |

On day 9 the oscillator crossed below zero — the moment price slipped under its 5-day average.

## Python code

```python
import pandas as pd

def ma_oscillator(close: pd.Series, n: int = 20) -> pd.Series:
    """Price minus n-day simple moving average."""
    return close - close.rolling(window=n).mean()
```

Full code: [[oscillators_master.py]]

## Relationships

### Within Chapter 6

- A simpler cousin of [[07_Price_Oscillator]] — instead of (short MA – long MA), it's (price – MA), which is just the same idea with a 1-period "short MA."
- Equilibrium = 0, see [[04_Equilibrium_Line]].
- Sensitivity tunable via the MA length, see [[05_Sensitivity]].
- Can be used to set [[09_Overbought_Oversold]] zones based on its historical range.

### Outside the chapter

- Equivalent to the **price-vs-MA crossover** strategy described in [[Chapter_3_Trends]].
- Forms the core of the moving-average trading systems in [[Chapter_14_Trading_Systems]].
- Bollinger-style envelopes (Ch. 4 and Appendix) extend this idea by adding standard-deviation bands around the MA.

## When this oscillator works well

| Market regime | Verdict |
|---------------|---------|
| Trending market | Stays mostly on one side of zero — useful for trend confirmation, poor as a countertrend signal |
| Trading range  | Oscillates symmetrically around zero — excellent countertrend tool |
| Choppy/news-driven | Very noisy — use a longer MA |
