# 02 — Simple Moving Average (SMA) System

## Definition

A **simple moving average** at day *t* is the arithmetic mean of the closing prices over the prior *N* days (including *t*). It is "moving" because the window slides forward each day.

$$\text{SMA}_t(N) = \frac{1}{N}\sum_{k=0}^{N-1} \text{Close}_{t-k}$$

The simplest possible trading system built on it:

- **Buy** when price closes above the SMA (and was at/below it the previous day).
- **Sell** when price closes below the SMA (and was at/above it the previous day).

This is a one-parameter system — only *N* needs to be chosen. It is always either long or short (no flat state in the basic version).

The big weakness: the SMA is itself just one number, so a short, sharp price jump can yank price across the line and back, producing a false signal. The simple MA system is whipsaw-prone, even in trending markets.

## Illustration

![[02_simple_ma.png]]

The orange line is the 20-day SMA. Each crossover triggers a trade. Note the false signals during the choppy zones — the cost of the system's most appealing feature, simplicity.

## Analogy

Think of the moving average as your **rolling 20-day mood** about the price. Today's close is just today's emotion; the SMA is your average emotion across the last three weeks.

- If today's emotion is suddenly *better* than your three-week average → something has improved, time to lean optimistic.
- If today's emotion is suddenly *worse* than your three-week average → something has cooled off, lean cautious.

The catch: a single bad-news day can push your "mood today" below the 20-day average even if nothing has actually changed for the week. That false alarm is exactly the whipsaw problem.

## Numeric example

A 10-day SMA on a stock that drifts up then back down:

| Day | Close | 10-day SMA | Signal |
|-----|-------|------------|--------|
| 10  | 85.20 | 82.54 | — (long since start)|
| 14  | 85.20 | 83.87 | — |
| 17  | 84.10 | 84.64 | **SELL** (close < SMA) |
| 18  | 89.50 | 84.68 | — |
| 26  | 82.80 | 82.68 | **BUY** (close > SMA) |
| 27  | 89.40 | 82.61 | — |

Notice the sell at day 17 was followed immediately by a 5-point rally on day 18 — a classic whipsaw. The system reverses a day too early.

## Code

[[../codes/02_moving_average.py]]

```python
import pandas as pd

def sma_signals(prices, n):
    ma = pd.Series(prices).rolling(n).mean().values
    sigs, pos = [], 0
    for i in range(n, len(prices)):
        if prices[i] > ma[i] and prices[i-1] <= ma[i-1] and pos != 1:
            sigs.append((i, prices[i], 'BUY')); pos = 1
        elif prices[i] < ma[i] and prices[i-1] >= ma[i-1] and pos != -1:
            sigs.append((i, prices[i], 'SELL')); pos = -1
    return sigs, ma
```

## Relationships

### Within the chapter

- **Subset of:** [[01_Trend_Following_Systems]]. The simple MA system is the most basic concrete trend-follower.
- **Improved by:** [[04_Crossover_Moving_Average_System]] — replacing price with a second smoothed series cuts most of the whipsaws.
- **Alternative formulation:** [[03_Weighted_Moving_Averages]] — try to give recent days more influence (mixed real-world evidence).
- **First major rescue:** [[07_Filter]] — the classic filter (only take signals that match the slope of the MA itself) is most often illustrated on top of a simple MA system.

### Beyond the chapter

- **Ch. 3 (Trends):** introduces moving averages visually as trend indicators.
- **Ch. 8 (Midtrend Entry):** uses moving averages in a *different* way — as bounce zones for entries with the trend, not as crossover signals.
- **Ch. 4 (Support / Resistance):** the MA can act as soft support or resistance.
- **Appendix:** formulas for weighted variants.

### When does the simple MA system actually work well?

- Markets with strong, persistent, visually obvious trends (commodity bull/bear runs).
- When combined with at least a filter or confirmation rule.
- As one component of a larger ensemble — never on its own with a single parameter set.
