---
tags: [technical-analysis, schwager, one-day-pattern, gaps]
source: "Schwager - Getting Started in Technical Analysis, Chapter 5, pp.73-75"
related: ["[[One-Day Patterns MOC]]", "[[Filled Gaps]]"]
---

# Gaps

## Definition

A gap occurs when today's entire price range doesn't overlap with yesterday's.

- **Upside gap**: `low[t] > high[t-1]`
- **Downside gap**: `high[t] < low[t-1]`

## The Four Types

### Common Gap
- **Where**: Inside a trading range
- **Significance**: Low — just noise
- **Analogy**: A hiccup mid-conversation. Means nothing, everyone moves on.

### Breakaway Gap
- **Where**: At the edge of a trading range, surging beyond its boundary
- **Significance**: **High** — one of the most reliable chart signals if unfilled for a few days
- **Analogy**: Kicking down a door. The market leaves the room and doesn't look back.
- **Key rule**: A breakaway gap not filled within the first week should be viewed as a particularly reliable signal (Schwager Rule #55)

### Runaway Gap
- **Where**: Mid-trend, during acceleration
- **Significance**: Moderate — confirms trend strength
- **Analogy**: A sprinter hitting their stride — each step covers more ground. Can occur in series during powerful trends.

### Exhaustion Gap
- **Where**: After an extended price move, soon followed by reversal
- **Significance**: Tricky — indistinguishable from runaway in real time
- **Analogy**: A sprinter's final lunge across the finish line — maximum effort, then collapse.

## Key Insight

> The difference between a runaway gap and an exhaustion gap is **hindsight**. You can't tell them apart in real time unless the exhaustion gap quickly becomes part of an [[Island Reversals|island reversal]].

## Classification Heuristic

Since gap type depends on context, classification is inherently a heuristic:

1. Is the gap at the boundary of a trading range? → **Breakaway** candidate
2. Is the gap filled within a few days? → **Common** or **Exhaustion**
3. Is the gap mid-trend and unfilled? → **Runaway**
4. Is the gap at the end of an extended move and followed by reversal? → **Exhaustion** (only clear in hindsight)

## Trading Implications

- Trade in the direction of wide gaps (Rule #53)
- Breakaway gaps from 1-2 month trading ranges are excellent signals, especially in bear markets (Rule #54)
- A breakout to new highs/lows followed by a gap back into the range = [[Bull and Bear Traps|bull/bear trap]] (Rule #56)

## Connection to Failed Signals

When a gap is **filled**, it becomes a failed signal — see [[Filled Gaps]]. Schwager prefers a strict definition: close below (above) the close of the day *prior* to the gap, not just intraday touch.

## Python Detection

```python
def detect_gaps(df: pd.DataFrame) -> pd.DataFrame:
    gaps = []
    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]
        if curr['low'] > prev['high']:
            gaps.append({
                'date': df.index[i],
                'direction': 'up',
                'gap_size': curr['low'] - prev['high'],
            })
        elif curr['high'] < prev['low']:
            gaps.append({
                'date': df.index[i],
                'direction': 'down',
                'gap_size': prev['low'] - curr['high'],
            })
    return pd.DataFrame(gaps)
```
