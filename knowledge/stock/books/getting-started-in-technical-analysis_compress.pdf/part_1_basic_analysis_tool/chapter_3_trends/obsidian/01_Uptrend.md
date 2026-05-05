---
chapter: 3
concept: Uptrend
tags: [technical-analysis, trends, chapter-3]
source: "Schwager, Getting Started in Technical Analysis, Ch. 3, pp. 33-34"
---

# Uptrend

## Definition

An **uptrend** is a price sequence characterized by a succession of **higher highs (RH)** and **higher lows (RL)**. Each new swing peak exceeds the previous peak, and each new swing trough sits above the previous trough. The uptrend remains *intact* until the most recent reaction low (RL) is broken — at which point the pattern is violated and a possible trend reversal is signaled (a clue, not absolute proof).

## Illustration

![[01_uptrend_highs_lows.png]]

The green ▼ markers are relative highs (each higher than the previous), and the red ▲ markers are relative lows (each higher than the previous). Together they form the staircase pattern that defines an uptrend.

## Analogy

Think of climbing a staircase while bouncing a basketball. The ball bounces up to a peak (the high), comes down (the low), then bounces up again — but each bounce happens one step higher than the last. As long as every bounce-down lands on a step higher than the previous low step, you're still climbing. The moment a bounce-down reaches a step *lower* than the previous low, you've stopped going up — the staircase ends.

## Numeric Example

| Swing | Type | Price |
|------:|:-----|------:|
| 1     | RL   | 102   |
| 2     | RH   | 108   |
| 3     | RL   | 105   |
| 4     | RH   | 113   |
| 5     | RL   | 110   |
| 6     | RH   | 120   |
| 7     | RL   | 117   |

Each RH (108 → 113 → 120) is higher than the last; each RL (102 → 105 → 110 → 117) is also higher. **Uptrend confirmed.** If the next pullback drops below 117, the uptrend pattern is violated.

## Python Implementation

See [[01_trend_pivots.py]]:

```python
from trend_pivots import find_pivots, classify_trend, trend_broken

pivots = find_pivots(highs, lows, n=3)
state = classify_trend(pivots)        # "uptrend" / "downtrend" / "no trend"
broken = trend_broken(pivots, current_price)
```

## Relationships

**Within Chapter 3:**
- The mirror image of [[02_Downtrend]] (lower lows + lower highs).
- Provides the swing points used to draw an [[03_Trend_Line]] (the uptrend line connects the higher lows).
- Once defined, can be enclosed by a [[05_Trend_Channel]] using a parallel return line through the higher highs.
- [[06_TD_Line]] formalizes the rule for selecting *which* highs/lows anchor the trend line.
- [[07_Internal_Trend_Line]] takes a different stance: extreme RHs/RLs may be emotional noise, not the "real" trend.
- [[08_Moving_Average]] gives a non-pivot way of detecting the same up/down behavior — it rises whenever today's close > close from N days ago.

**Outside Chapter 3:**
- The reaction lows that define the uptrend become natural **support** levels (Ch. 4: Trading Ranges and Support and Resistance).
- Trend reversal signals here connect to **chart patterns** like head-and-shoulders tops (Ch. 5).
- A clean uptrend creates the conditions where **midtrend entry** strategies (Ch. 8) become attractive.
- The trend's *end* is what motivates **stop-loss** placement just below the latest RL (Ch. 9).

## When does this concept work well?

| Market type | Effectiveness |
|---|---|
| Strong directional move | ✅ Excellent — pattern is unambiguous |
| Choppy/sideways | ⚠️ Misleading — false reactions look like trend breaks |
| News-driven gap | ❌ Pattern resets; previous RL/RH may become irrelevant |

## Source

Schwager, Jack D. *Getting Started in Technical Analysis* (Wiley, 1999), Chapter 3, pp. 33-34. Quoted reference: the trend "is intact until a previous relative low point (a 'reaction' low) is broken."
