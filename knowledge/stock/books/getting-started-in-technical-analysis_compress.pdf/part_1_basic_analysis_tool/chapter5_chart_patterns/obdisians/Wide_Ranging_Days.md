# Wide-Ranging Days

> Part of: [[Chapter_05_Chart_Patterns]] → One-Day Patterns

## Definition

A **wide-ranging day** is a bar whose high-to-low range is dramatically larger than the recent average — a day on which volatility temporarily explodes. The Appendix gives a precise formula:

> $VR = \dfrac{\text{today's true range}}{\text{average true range over past N days}}$, with `N = 15` and threshold `k = 2.0`.

So a day with a true range twice the recent 15-day average qualifies.

The directional information depends on the **close**:

| Type | Pattern | Meaning |
|---|---|---|
| Wide-ranging up day after long decline | strong close (near the high) | Bullish trend reversal candidate |
| Wide-ranging down day after long advance | weak close (near the low) | Bearish trend reversal candidate |

A cluster of wide-ranging bars in the same direction is one of the most explosive signals in chart analysis.

## Illustration

![[wide_ranging_days_illustration.svg]]

## Analogy — A Quiet Pond Suddenly Hit by a Boulder

For two weeks the surface of a pond has been rippling gently — small waves, predictable rhythm. Then one afternoon there's a single enormous splash that throws water in a wave higher than anything you've seen before. Even before you turn your head you know *something happened*. The pond won't go back to gentle ripples for a while.

That huge splash is a wide-ranging day. The water level afterward — whether it settles high (boulder pushed water in) or low (something exploded out) — tells you which direction the disturbance was pointing.

## Numeric Example

Past 15 days' true ranges average **0.85**. Then:

| Day | High | Low | True Range | VR |
|---|---|---|---|---|
| T   | 42.30 | 41.40 | 0.90 | 1.06 |
| T+1 | 42.50 | 41.50 | 1.00 | 1.18 |
| **T+2 (wide-ranging)** | **44.80** | **42.40** | **2.40** | **2.82** |

VR = 2.82 > 2.0 → wide-ranging day ✓

If T+2 closed at 44.65 (near the high) and the prior trend was a six-week decline → high-conviction bullish reversal signal.

## Python Code

```python
import pandas as pd

def true_range(df: pd.DataFrame) -> pd.Series:
    """Wilder's true range."""
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    return pd.concat([h - l,
                      (h - prev_c).abs(),
                      (l - prev_c).abs()], axis=1).max(axis=1)


def wide_ranging_days(df: pd.DataFrame, n: int = 15, k: float = 2.0) -> pd.DataFrame:
    """
    Detect wide-ranging days using Schwager's volatility ratio (VR).
    Adds columns: tr, atr, vr, is_wide, close_strength ('strong'/'weak'/'mid')
    """
    df = df.copy()
    df["tr"]  = true_range(df)
    df["atr"] = df["tr"].rolling(n).mean()
    df["vr"]  = df["tr"] / df["atr"]
    df["is_wide"] = df["vr"] > k

    rng = (df["high"] - df["low"]).replace(0, 1e-9)
    pos = (df["close"] - df["low"]) / rng       # 0 = at low, 1 = at high
    df["close_strength"] = "mid"
    df.loc[pos >= 0.75, "close_strength"] = "strong"
    df.loc[pos <= 0.25, "close_strength"] = "weak"
    return df


def reversal_signal(df: pd.DataFrame, lookback: int = 30) -> pd.Series:
    """
    Bullish wide-range reversal: wide-ranging day, strong close, after recent decline.
    """
    w = wide_ranging_days(df)
    decline = df["close"] < df["close"].shift(lookback)
    return w["is_wide"] & (w["close_strength"] == "strong") & decline
```

## Relationships

### Within Chapter 5

- **Combines with [[Spikes]]** and [[Reversal Days]]: a single bar that is *all three* (wide-range + spike + reversal) is the highest-conviction one-day reversal signal in the whole chapter.
- **Combines with [[Gaps]]**: a wide-ranging day with a gap-open in the same direction is doubly powerful.
- **Strengthens [[Triangles|triangle]] / [[Flags and Pennants|flag]] breakouts**: if the breakout bar is wide-ranging, the move is more reliable.

### Outside Chapter 5

- **Appendix — VR formula**: gives the exact volatility-ratio definition (`tr / atr_15 > 2.0`).
- **[[Chapter 09 - Choosing Stop-Loss Points]]** — Schwager suggests using the wide-ranging day's *opposite extreme* as a natural stop after entry on the close.
- **[[Chapter 11 - The Most Important Rule]]** — return through a prior wide-ranging day's extreme is itself a major failed-signal indicator (penetration of wide-ranging day extremes).
- **[[Chapter 14 - Trend-Following Systems]]** — many systems use ATR multiples (essentially a wide-range proxy) to size stops or trigger entries.

### When does this concept work well?

- **Best**: after extended trends, when accompanied by news, with a strong/weak close, and ideally clustered.
- **Worst**: in already-volatile names where every other day is borderline-wide — the signal blurs into noise.

#chart-patterns #one-day-pattern #wide-ranging-days #volatility
