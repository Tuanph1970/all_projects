---
tags: [technical-analysis, schwager, one-day-pattern, reversal-days]
source: "Schwager - Getting Started in Technical Analysis, Chapter 5 pp.77-81"
related: ["[[One-Day Patterns MOC]]", "[[Spikes]]", "[[Spike-Reversal Combination]]", "[[Signal Frequency vs Reliability Trade-off]]"]
---

# Reversal Days

## Definition

A reversal day makes a new extreme in the direction of the current trend, then reverses to close against it. There are two definitions with very different reliability.

### Standard Definition (Schwager: "worthless")

- **Reversal high**: New high in an upmove → closes below *previous day's close*
- **Reversal low**: New low in a downmove → closes above *previous day's close*

### Restrictive Definition (Schwager's recommendation)

- **Reversal high**: New high in an upmove → closes below *previous day's low*
- **Reversal low**: New low in a downmove → closes above *previous day's high*
- Even stricter variant: close below the low of the prior **two** days

## Analogy

**Standard definition**: You're climbing stairs. You step onto a new highest step, then step back down to where you were. Could be a stumble, could be tiredness — hard to tell. This happens all the time.

**Restrictive definition**: You step onto a new highest step, then fall all the way down past the previous landing. That's not a stumble — the staircase is broken. Something fundamentally changed.

## Why the Standard Definition Fails

> Reversal high days successfully call 100 out of every 10 highs.

The condition (close < prior close) is too weak. Reversal days by this definition are extremely common. Most are false signals. Schwager explicitly calls the standard definition "worthless as a trading indicator."

The restrictive definition (close < prior low) dramatically cuts false positives, though it also misses some valid signals. This is a textbook case of the [[Signal Frequency vs Reliability Trade-off]].

## Spike vs. Reversal Day — The Distinction

| Feature | Spike | Reversal Day |
|---------|-------|-------------|
| Requires protrusion above next day's high? | ✅ Yes | ❌ No |
| Requires close below prior day's low? | ❌ Not necessarily | ✅ (strict def.) |
| Requires prior trend? | ✅ Explicitly | ⚠️ Implicitly (new high in upmove) |
| Needs t+1 data? | ✅ Yes | ❌ No |

A day can be a spike but not a reversal. A day can be a reversal but not a spike. A day that is **both** → see [[Spike-Reversal Combination]].

## Python Detection

```python
def detect_reversal_days(df: pd.DataFrame,
                         strict: bool = True) -> pd.DataFrame:
    reversals = []
    for i in range(2, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i - 1]
        threshold = prev['low'] if strict else prev['close']
        threshold_low = prev['high'] if strict else prev['close']

        # Reversal HIGH day
        if curr['high'] > prev['high'] and curr['close'] < threshold:
            reversals.append({
                'date': df.index[i], 'type': 'reversal_high',
                'definition': 'strict' if strict else 'standard',
                'severity': (curr['high'] - curr['close']) /
                            (curr['high'] - curr['low'])
                            if (curr['high'] - curr['low']) > 0 else 0,
            })

        # Reversal LOW day
        if curr['low'] < prev['low'] and curr['close'] > threshold_low:
            reversals.append({
                'date': df.index[i], 'type': 'reversal_low',
                'definition': 'strict' if strict else 'standard',
                'severity': (curr['close'] - curr['low']) /
                            (curr['high'] - curr['low'])
                            if (curr['high'] - curr['low']) > 0 else 0,
            })

    return pd.DataFrame(reversals)
```
