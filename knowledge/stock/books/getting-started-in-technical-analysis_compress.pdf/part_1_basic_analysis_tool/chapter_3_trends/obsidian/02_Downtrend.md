---
chapter: 3
concept: Downtrend
tags: [technical-analysis, trends, chapter-3]
source: "Schwager, Getting Started in Technical Analysis, Ch. 3, p. 34"
---

# Downtrend

## Definition

A **downtrend** is a price sequence characterized by a succession of **lower lows (RL)** and **lower highs (RH)**. Each new swing trough sinks below the previous trough, and each new swing peak fails to reach the previous peak. The downtrend remains *intact* until the most recent reaction high is exceeded.

## Illustration

![[02_downtrend_highs_lows.png]]

The red ▲ markers are relative lows (each lower than the previous), and the green ▼ markers are relative highs (each lower than the previous). The staircase descends.

## Analogy

Imagine walking down a flight of stairs and pausing on each step. You step down (a new low), pause and look back up briefly (a small bounce — the lower high), then step down again to a step further below than before. As long as every step-down lands lower than where you stood before, and your "look back up" never reaches the height of your previous standing point, you're still descending. The moment your look-back reaches a previous standing height, the descent has stopped.

## Numeric Example

| Swing | Type | Price |
|------:|:-----|------:|
| 1     | RH   | 130   |
| 2     | RL   | 122   |
| 3     | RH   | 124   |
| 4     | RL   | 116   |
| 5     | RH   | 118   |
| 6     | RL   | 105   |
| 7     | RH   | 110   |

Each RL (122 → 116 → 105) is lower than the last; each RH (130 → 124 → 118 → 110) is also lower. **Downtrend confirmed.** If price rallies above 110, the downtrend pattern is violated.

## Python Implementation

See [[01_trend_pivots.py]] (same module — direction is inferred):

```python
from trend_pivots import find_pivots, classify_trend, trend_broken

pivots = find_pivots(highs, lows, n=3)
if classify_trend(pivots) == "downtrend":
    if trend_broken(pivots, current_price):
        print("Downtrend may be ending")
```

## Relationships

**Within Chapter 3:**
- The mirror image of [[01_Uptrend]] — same logic flipped.
- Drawn on the chart using a [[04_Downtrend_Line]] connecting the lower highs.
- Wrapped by a [[05_Trend_Channel]] using a parallel return line through the lower lows.
- [[06_TD_Line]] for downtrends connects the most recent RH to the most recent earlier *higher* RH.
- [[08_Moving_Average]] reflects a downtrend whenever today's close is lower than the close N days ago.

**Outside Chapter 3:**
- Reaction highs in a downtrend become natural **resistance** zones (Ch. 4).
- Topping patterns like head-and-shoulders tops mark the *birth* of a downtrend (Ch. 5).
- Stops in a short position go just above the latest RH (Ch. 9).
- Downtrends often run faster than uptrends — relevant for sizing, exits, and the "fear vs. greed" asymmetry discussed in trading psychology chapters.

## When does this concept work well?

| Market type | Effectiveness |
|---|---|
| Bear-market regime | ✅ Excellent — relentless lower lows/highs |
| Climactic capitulation | ⚠️ The final RL may be a reversal, not continuation |
| Bottoming process | ❌ Higher lows start forming inside still-lower highs (mixed signal) |

## Source

Schwager, *Getting Started in Technical Analysis*, Ch. 3, p. 34: defined "in similar fashion" to the uptrend — succession of lower lows and lower highs, intact until a previous relative high is exceeded.
