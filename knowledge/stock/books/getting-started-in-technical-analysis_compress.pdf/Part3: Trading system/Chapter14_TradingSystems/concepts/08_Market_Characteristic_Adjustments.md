# 08 — Market Characteristic Adjustments

## Definition

A **market characteristic adjustment** makes a system's parameters depend on the current state of the market, rather than holding them fixed forever. The criticism it answers: a 20-day breakout in a quiet bond market is not the same event as a 20-day breakout in a wildly volatile crude oil market — yet a static system treats them identically.

The most natural state-classifier is **volatility**, but you could also classify by:
- average volume,
- average true range,
- a fundamental regime classification (e.g., yield-curve shape),
- explicit trend-vs-range detection.

In a breakout system, instead of *N = 20* always, you might use:
- *N = 12* in low-volatility regimes,
- *N = 20* in medium-volatility regimes,
- *N = 30* in high-volatility regimes.

This turns a static system into a **dynamic** one — same skeleton, different parameters depending on conditions.

## Illustration

![[08_market_adjustments.png]]

Blue line is price spanning two regimes: a calm first half and a much more volatile second half. The purple dashed line shows the adaptive *N* — small when volatility is low (so the system stays sensitive enough to catch real moves in quiet markets) and larger when volatility spikes (so noise doesn't constantly flip the position).

## Analogy

You're a security guard. In a quiet office building at 3 AM, even a small unusual sound is worth investigating — your "alarm threshold" is low. In a busy bus station at rush hour, you'd be running every two seconds if you reacted to every loud noise — your alarm threshold is automatically much higher.

You haven't changed your *job description* (investigate suspicious sounds). You've just calibrated your sensitivity to the ambient noise level. Market characteristic adjustment does the same thing for trading systems.

## Numeric example

Synthetic two-regime series — 80 days of low volatility, then 80 days of high volatility:

| Day | Side | Adaptive *N* | Price |
|-----|------|----|-------|
| 51 | BUY | 12 | 104.73 |
| 77 | SELL | 12 | 104.26 |
| 82 | BUY | 12 | 106.73 |
| 85 | SELL | 12 | 103.02 |
| 111 | BUY | 12 | 99.63 |
| 118 | SELL | 12 | 94.59 |
| 129 | BUY | 12 | 98.62 |

In the example here, the simulated regime didn't push high enough on the volatility metric to trigger N=20 or N=30 — but the framework would have done so for a sharper regime change. The *mechanism* is what matters: same code path, different *N* contingent on state.

## Code

[[../codes/08_market_adjustments.py]]

```python
def realized_volatility(prices, lookback=50):
    p = np.asarray(prices, dtype=float)
    rng = np.zeros(len(p))
    for i in range(2, len(p)):
        rng[i] = abs(p[i] - p[i-2]) / p[i]
    return pd.Series(rng).rolling(lookback).mean().values

def adaptive_N(vol, low_thresh=0.04, high_thresh=0.08,
               low_N=12, mid_N=20, high_N=30):
    if np.isnan(vol):       return mid_N
    if vol < low_thresh:    return low_N
    if vol < high_thresh:   return mid_N
    return high_N
```

## Relationships

### Within the chapter

- **Modification of:** [[05_Breakout_Systems]] (most natural fit), but applies equally to [[02_Moving_Average_Systems]] and [[04_Crossover_Moving_Average_System]].
- **Sibling of:** [[09_Buy_Sell_Differentiation]] — both add asymmetry. One asymmetry is across volatility regimes; the other is across direction.
- **Adds parameters:** the *thresholds* and *N values* are themselves parameters, increasing fit risk. Keep the table short (2–3 regimes max).
- **Often combined with:** [[07_Filter]] (the regime classification can become both an adjustment and a filter — skip signals entirely in certain regimes).

### Beyond the chapter

- **Ch. 4 (Trading Ranges):** explicit regime detection — range vs trend — feeds directly into adjustments.
- **Ch. 15 (Testing):** Schwager strongly warns about overfitting; market-characteristic rules must be tested with the same discipline as base parameters.
- **Modern echo:** "regime switching" models (HMMs, volatility regime classifiers) and adaptive bandwidth indicators (Adaptive Moving Average, KAMA) are direct descendants of this idea.

### When market characteristic adjustments help most

- Across markets that swing between calm/volatile cycles (most commodities, FX in macro shifts).
- For multi-market portfolios where one set of parameters can't possibly fit all instruments.
- When you have enough data per regime to validate the adjustment honestly — not on a sample of 5 events.

They hurt when the regime classifier is itself unstable — chasing regime estimates that flip every other week creates a meta-whipsaw.
