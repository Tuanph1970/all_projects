---
tags: [technical-analysis, schwager, one-day-pattern, thrust-days]
source: "Schwager - Getting Started in Technical Analysis, Chapter 5 pp.81-83"
related: ["[[One-Day Patterns MOC]]", "[[Run Days]]"]
---

# Thrust Days

## Definition

- **Upthrust day**: Close is above the previous day's **high**
  `close[t] > high[t-1]`

- **Downthrust day**: Close is below the previous day's **low**
  `close[t] < low[t-1]`

The significance comes from the close being the most important price of the day. When the close doesn't just beat the prior close, but exceeds the prior day's *entire range*, that's a decisive statement.

## Analogy

A thrust day is like a decisive vote in an election. The close doesn't just vote "up" — it votes "higher than anything that happened yesterday." One vote doesn't swing an election, but a series of consecutive upthrust days is a landslide.

- **Bull markets** → upthrust days significantly outnumber downthrust days
- **Bear markets** → downthrust days dominate
- **Sideways markets** → roughly balanced

## Key Usage: Count, Don't Trade Singles

> A single thrust day is not particularly meaningful, since thrust days are quite common.

Thrust days are **regime indicators**, not trade signals. Their power is in aggregation — a rolling count of upthrust vs. downthrust days over a window reveals the market's underlying character.

## Relationship to [[Run Days]]

Run days are a "more powerful version" of thrust days. Most run days are also thrust days, but run days add the requirement of dominating both past and future neighborhoods. Think of thrust days as the common currency and run days as the rare, high-denomination bills.

## Python Detection

```python
def detect_thrust_days(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for i in range(1, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i - 1]
        if curr['close'] > prev['high']:
            results.append({'date': df.index[i], 'type': 'upthrust',
                            'magnitude': curr['close'] - prev['high']})
        elif curr['close'] < prev['low']:
            results.append({'date': df.index[i], 'type': 'downthrust',
                            'magnitude': prev['low'] - curr['close']})
    return pd.DataFrame(results)


def thrust_day_balance(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Rolling count: +1 upthrust, -1 downthrust, 0 otherwise.
    Positive balance → bullish regime.
    Negative balance → bearish regime.
    """
    thrusts = detect_thrust_days(df)
    thrust_series = pd.Series(0, index=df.index)
    for _, row in thrusts.iterrows():
        thrust_series.loc[row['date']] = 1 if row['type'] == 'upthrust' else -1
    return thrust_series.rolling(window).sum()
```
