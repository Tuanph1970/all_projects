---
tags: [technical-analysis, schwager, one-day-pattern, wide-ranging-days, volatility]
source: "Schwager - Getting Started in Technical Analysis, Chapter 5 pp.83-86, Appendix p.324"
related: ["[[One-Day Patterns MOC]]", "[[True Range and ADTR]]", "[[Return to Wide-Ranging Day Extremes]]"]
---

# Wide-Ranging Days

## Definition

A day whose price range is **significantly larger** than recent days — a volatility explosion. Defined by the Volatility Ratio:

```
VR = today's true range / average true range of past N days
Wide-ranging day: VR > k   (e.g., k = 2.0, N = 15)
```

## Analogy

A wide-ranging day is like a shouting match in a normally quiet meeting room. The volume of noise (range) tells you something dramatic just happened. **Who wins the argument** (where the close falls) tells you the direction.

- **Strong close after a long decline** = the quiet person who finally stands up and shouts — that person has something to say and the room listens.
- **Weak close after a long advance** = the leader whose voice cracks — confidence is breaking.

## What It Signals

The meaning depends entirely on **close position** + **preceding trend**:

| Close Position | After a Decline | After an Advance |
|----------------|-----------------|------------------|
| **Near the high** (strong close) | 🟢 Bullish reversal | Trend continuation |
| **Near the low** (weak close) | Trend continuation | 🔴 Bearish reversal |

### Examples from Schwager
- Wide-ranging up days after extended declines → heralded major advances (Figures 5.12, 5.13)
- Wide-ranging down days near peaks of major advances → serious warning flags (Figures 5.14, 5.15)
- Four consecutive wide-ranging down days retraced 4 months of upward movement (Figure 5.16)

## Close Position as the Key Variable

The [[Close Position Within Range]] metric (0 = at low, 1 = at high) is what transforms a wide-ranging day from "something happened" into "here's what it means":

- `close_position > 0.7` → strong close → bullish implications
- `close_position < 0.3` → weak close → bearish implications
- `0.3 - 0.7` → neutral → ambiguous signal

## Trading Rules (from Chapter 17)

> Wide-ranging days with a close counter to the main trend tend to provide a reliable early signal of a trend change — particularly if they also trigger a reversal signal (e.g., filling of a runaway gap, complete penetration of prior consolidation).
> — Rule #65

## Connection to Failed Signals

When prices later close beyond the extreme of a wide-ranging day in the opposite direction, the original signal is negated — see [[Return to Wide-Ranging Day Extremes]].

## Python Detection

```python
def detect_wide_ranging_days(df: pd.DataFrame, k: float = 2.0,
                              atr_period: int = 15) -> pd.DataFrame:
    tr = compute_true_range(df)  # see [[True Range and ADTR]]
    adtr = tr.rolling(atr_period).mean()
    vr = tr / adtr

    results = []
    for i in range(atr_period, len(df)):
        if vr.iloc[i] > k:
            curr = df.iloc[i]
            day_range = curr['high'] - curr['low']
            close_pos = (curr['close'] - curr['low']) / day_range if day_range > 0 else 0.5

            results.append({
                'date': df.index[i],
                'volatility_ratio': vr.iloc[i],
                'close_position': close_pos,
                'signal': 'strong_close' if close_pos > 0.7 else
                          'weak_close' if close_pos < 0.3 else 'neutral',
            })
    return pd.DataFrame(results)
```
