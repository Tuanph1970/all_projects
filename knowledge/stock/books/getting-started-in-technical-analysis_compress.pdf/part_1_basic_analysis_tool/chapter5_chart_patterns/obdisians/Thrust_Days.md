# Thrust Days

> Part of: [[Chapter_05_Chart_Patterns]] → One-Day Patterns

## Definition

- **Upthrust day**: a day whose close is *above the previous day's high*.
- **Downthrust day**: a day whose close is *below the previous day's low*.

The logic rests on Schwager's belief that **the close is the single most important price of the day** — it's where the market settled after digesting all of that day's news. A close that finishes outside yesterday's entire range tells you the day had real conviction.

A cluster of upthrust days suggests powerful underlying buying; a cluster of downthrust days, powerful selling. They function as confirmations of trend strength rather than reversals.

## Illustration

![[thrust_days_illustration.svg]]

## Analogy — Crossing Yesterday's Finish Line

Picture a tug-of-war that's reset every morning. Yesterday's rope ended at a certain mark on the ground. Today, your team pulls so hard the rope's *final* position lands beyond where the *winning* edge of yesterday's rope was.

That's an upthrust. It doesn't matter how the tug went minute-by-minute — the *settled* position is past the previous day's best. One day like that is encouraging. Three or four in a row, and the other team is breaking.

## Numeric Example

A stock in an early uptrend:

| Day | High | Low | **Close** | Type |
|---|---|---|---|---|
| T−1 | 42.50 | 41.80 | **42.30** | — |
| T   | 43.10 | 42.00 | **42.85** | Upthrust (42.85 > 42.50) ✓ |
| T+1 | 43.40 | 42.70 | **43.30** | Upthrust (43.30 > 43.10) ✓ |
| T+2 | 43.60 | 42.90 | **43.55** | Upthrust (43.55 > 43.40) ✓ |

Three consecutive upthrusts → strongly confirms uptrend pressure.

## Python Code

```python
import pandas as pd

def thrust_days(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mark each bar as 'up' / 'down' / None thrust day.
    """
    df = df.copy()
    prev_high = df["high"].shift(1)
    prev_low  = df["low"].shift(1)

    df["thrust"] = None
    df.loc[df["close"] > prev_high, "thrust"] = "up"
    df.loc[df["close"] < prev_low,  "thrust"] = "down"
    return df


def thrust_clusters(df: pd.DataFrame, n: int = 3) -> pd.Series:
    """
    Returns True where the bar is the END of a cluster of n consecutive
    same-direction thrusts -- a high-conviction trend confirmation.
    """
    t = thrust_days(df)["thrust"]
    up_streak   = (t == "up").rolling(n).sum() == n
    down_streak = (t == "down").rolling(n).sum() == n
    return up_streak | down_streak
```

## Relationships

### Within Chapter 5

- **Versus [[Reversal Days]]**: an upthrust day is a *bullish* signal (close above prior high); a reversal high day is a *bearish* signal (close below prior close/low). They are at opposite ends of the bullish/bearish spectrum of single-bar bars.
- **Combines with [[Wide-Ranging Days]]**: a wide-ranging upthrust is much more meaningful than a narrow upthrust.
- **Confirms [[Triangles|triangle]] and [[Flags and Pennants|flag/pennant]] breakouts**: a closing breakout from a continuation pattern *that is itself a thrust day* is a high-conviction entry.

### Outside Chapter 5

- **[[Chapter 04 - Trading Ranges and Support and Resistance]]** — an upthrust through the top of a multi-month range = breakout closure, not just an intraday peek above resistance.
- **[[Chapter 03 - Trends]]** — a sequence of upthrust days is essentially the bar-level evidence of a strong trend with little overlap, the kind that systems try to ride.
- **[[Chapter 14 - Trend-Following Systems]]** — many breakout systems implicitly trade on thrust-day-like conditions (close above N-day high).

### When does this concept work well?

- **Best**: clustered, in the direction of the larger trend, near the edge of a consolidation.
- **Worst**: isolated thrusts in choppy ranges — they tend to mark short-term exhaustion, not continuation.

#chart-patterns #one-day-pattern #thrust-days
