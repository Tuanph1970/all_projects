# Momentum

> Schwager, Ch. 6, pp. 110–112

## Definition

**Momentum** is the rate (or speed) at which prices change. Its simplest mathematical form:

$$ \text{Momentum}(n) = \text{Close}_t - \text{Close}_{t-n} $$

A positive value means the market is higher than it was *n* days ago; a negative value means it is lower. The further from zero, the stronger the move.

## Illustration

![[01_momentum.png]]

The bottom panel shows 10-day momentum below price. Bars above zero (green-shaded) signal upward force; bars below (red-shaded) signal downward force.

## Easy analogy

Imagine pushing a shopping cart down an aisle. Two carts can both end up at the same spot at the back of the store, but one might have been **shoved hard once** while the other was **gently nudged the whole way**. Momentum doesn't ask "where did you arrive?"; it asks "how forcefully did you get there?" A cart with strong forward push will keep rolling even after you stop pushing — markets behave the same way.

## Numeric example

Closing prices of a stock for the last 11 days:

```
Day:    1   2   3   4   5   6   7   8   9   10  11
Close: 50  51  53  52  54  55  57  56  58  60  62
```

10-day momentum at day 11:

$$ M_{10} = 62 - 50 = +12 $$

Momentum is +12, meaning the stock is $12 higher than it was 10 trading days ago — a strong upward thrust.

Compare with another stock that drifts: 50, 50.5, 51, 50.8, 51.2, 51.5, 51.8, 51.5, 52, 52.2, **52.4**.
- Momentum = 52.4 − 50 = **+2.4**.

Both stocks rose, but the first has roughly **5× the momentum** of the second.

## Python code

```python
import pandas as pd

def momentum(close: pd.Series, n: int = 10) -> pd.Series:
    """N-day momentum: today's close minus close N days ago."""
    return close - close.shift(n)

closes = pd.Series([50, 51, 53, 52, 54, 55, 57, 56, 58, 60, 62])
print(momentum(closes, 10).iloc[-1])   # 12.0
```

Full implementation: [[oscillators_master.py]] · Chart code: [[generate_images.py]]

## Relationships

### Within Chapter 6

- Conceptual parent of **every other oscillator** in the chapter — RSI, Stochastics, MACD, ROC are all alternative measurements of the same idea.
- Direct algebraic twin of [[03_Rate_of_Change]] (subtraction vs division).
- Sensitivity depends on the look-back period — see [[05_Sensitivity]].
- Crosses zero at the [[04_Equilibrium_Line]].
- Extreme readings define [[09_Overbought_Oversold]] zones.

### Outside the chapter

- Healthy momentum confirms a trend → [[Chapter_3_Trends]].
- Waning momentum often precedes a [[Chart_Pattern_Reversal]] (Ch. 5).
- A **thrust day** in Ch. 5 is essentially a single-day surge of momentum.
- Used as a confirmation filter inside trend-following systems in [[Chapter_14_Trading_Systems]].

## When to use it

| Market regime | Effectiveness of momentum signals |
|---------------|-----------------------------------|
| Strong trend  | Good for **confirming** direction; bad as a countertrend signal |
| Trading range | Useful for spotting overshoots; works best when paired with [[Chapter_4_Trading_Ranges]] support/resistance |
| Choppy / news-driven | Noisy — use longer look-back to filter |
