---
tags: [technical-analysis, schwager, building-block]
related: ["[[Spikes]]", "[[Wide-Ranging Days]]"]
---

# Close Position Within Range

## Definition

A normalized metric that describes where the close falls within the day's range:

```
close_position = (close - low) / (high - low)
```

- **0.0** = closed at the day's low (maximum weakness)
- **1.0** = closed at the day's high (maximum strength)
- **0.5** = closed at the midpoint (neutral)

## Why It Matters

Schwager treats the close as "by far the most important price of the day." The close represents the market's **final consensus** after all the intraday noise. Where it falls within the day's range reveals whether buyers or sellers won the session.

## Usage in Patterns

### [[Spikes]]
- Spike high: close position should be < 0.25 (lower quartile)
- Spike low: close position should be > 0.75 (upper quartile)
- Schwager's Appendix formula: `H - C > 3 × (C - L)` for spike high → close is in the bottom 25%

### [[Wide-Ranging Days]]
- Close position > 0.7 → "strong close" → bullish implications
- Close position < 0.3 → "weak close" → bearish implications
- 0.3 – 0.7 → neutral / ambiguous

## Python

```python
def close_position(row):
    """Where did the close fall within the day's range? (0=low, 1=high)"""
    day_range = row['high'] - row['low']
    if day_range == 0:
        return 0.5
    return (row['close'] - row['low']) / day_range
```
