# Equilibrium Line

> Schwager, Ch. 6, p. 112

## Definition

The **equilibrium line** is the horizontal reference value on an oscillator that represents "no change" between the current price and the look-back price. Crossing the equilibrium line is interpreted as a basic regime switch: from net up-pressure to net down-pressure (or vice-versa).

| Oscillator | Equilibrium value |
|------------|------------------|
| Momentum | 0 |
| ROC (ratio form) | 1.0 |
| ROC (% form) | 0 |
| Moving Average Oscillator | 0 |
| Price Oscillator / MACD | 0 |
| RSI | 50 |
| Stochastics | 50 |

## Illustration

![[03_equilibrium_line.png]]

The red line in each lower panel is the equilibrium. When momentum is **above** it, today's price is higher than the price *n* days earlier; when **below**, the opposite.

## Easy analogy

Think of the equilibrium line as **sea level on a topographic map**. Above it is land (positive territory); below it is the ocean (negative territory). The shoreline itself doesn't tell you anything dramatic, but stepping from shore into deep water is meaningfully different from stepping from shore onto a hill — even if it's only one inch on the map.

## Numeric example

Suppose 10-day momentum readings over a week are:

| Day | Momentum | Side of equilibrium |
|-----|----------|---------------------|
| Mon | −2.3 | below 0 → bearish bias |
| Tue | −0.4 | still below |
| Wed | +0.1 | crossed up |
| Thu | +1.2 | above 0 → bullish bias |
| Fri | +2.5 | accelerating up |

Wednesday's tiny crossing of the zero line is the *moment* the indicator flipped from net-down to net-up momentum.

## Python code

```python
def equilibrium_crossings(indicator, equilibrium=0):
    """Detect bull (up-cross) and bear (down-cross) flips."""
    above = indicator > equilibrium
    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & (above.shift(1).fillna(False))
    return cross_up, cross_down
```

Full code: [[oscillators_master.py]]

## Relationships

### Within Chapter 6

- Defined per oscillator: 0 for [[02_Momentum]] / [[06_MA_Oscillator]] / [[07_Price_Oscillator]] / [[08_MACD]], 1.0 for ROC ratio (see [[03_Rate_of_Change]]), 50 for normalized oscillators ([[11_RSI]], [[12_Stochastics]]).
- For [[06_MA_Oscillator]] specifically, an equilibrium crossing is exactly a price-vs-moving-average crossover.
- Same crossing on [[07_Price_Oscillator]] is exactly a short-MA / long-MA crossover.

### Outside the chapter

- Same idea as a **price–moving-average crossover** in [[Chapter_3_Trends]].
- The MACD signal-line and zero-line crossovers are the equilibrium-line concept inside a [[Chapter_14_Trading_Systems]] trend-following rule.
- A breakout past a [[Chapter_4_Trading_Ranges]] boundary is the *price* analogue of an equilibrium-line cross.
