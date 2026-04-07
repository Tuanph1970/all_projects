---
tags: [technical-analysis, schwager, one-day-pattern, spikes]
source: "Schwager - Getting Started in Technical Analysis, Chapter 5 pp.75-77, Appendix pp.319-321"
related: ["[[One-Day Patterns MOC]]", "[[Reversal Days]]", "[[Spike-Reversal Combination]]", "[[Return to Spike Extremes]]"]
---

# Spikes

## Definition

A **spike high** is a day whose high pokes sharply above the highs of both the preceding and succeeding days, with a close typically near the day's low.

A **spike low** is the mirror: the low drops sharply below neighboring lows, with close near the day's high.

Spikes represent climactic buying or selling pressure — the final exhaustive push that drains the trend's momentum.

## Analogy

Think of a basketball player jumping for a slam dunk. They leap way above everyone else's reach (the high pokes far above neighboring days), but gravity pulls them right back down and they land near the floor (close near the day's low). The higher the jump compared to everyone else, and the harder the landing, the more dramatic the signal.

**Spike low**: Someone diving into a pool, touching the bottom far deeper than anyone else, then immediately shooting back up to the surface.

## Three Significance Enhancers

1. **Protrusion magnitude** — How far does the spike exceed neighboring highs/lows?
2. **Close position** — Does the close sit near the opposite end of the day's range?
3. **Preceding trend** — Was there a substantive advance/decline before the spike?

> The more extreme each of these conditions, the greater the likelihood that a spike will prove to be an important turning point or even major top/bottom.

## Schwager's Appendix Formula (Spike High)

All three conditions must be met:

1. **Protrusion**: `H[t] - max(H[t-1], H[t+1]) > k × ADTR`
   - Spike exceeds surrounding highs by at least k × [[True Range and ADTR|average true range]] (e.g., k = 0.75)

2. **Close position**: `H[t] - C[t] > 3 × (C[t] - L[t])`
   - Close is in the lower quartile of the day's range

3. **Preceding advance**: `H[t] > max(H[t-N:t])`
   - High exceeds the highest high of the past N days (e.g., N = 50)

Spike low conditions are the mirror image.

## Real-Time Limitation

⚠️ Spikes require the **next day's data** (t+1) to confirm condition 1. A spike cannot be definitively identified on the day it occurs — only one day later.

## Spike vs. Reversal Day

These are **not the same pattern** — see [[Reversal Days]] for the distinction:

- A spike high may NOT close below the prior day's low/close → fails reversal definition
- A reversal high day may NOT protrude above the next day's high → fails spike definition
- A day that is **both** → see [[Spike-Reversal Combination]]

## Connection to Failed Signals

When prices later return to a prior spike extreme, the original spike becomes a failed signal — see [[Return to Spike Extremes]]. The more extreme the original spike and the more time elapsed, the more significant the failure.

## Python Detection

```python
def detect_spikes(df: pd.DataFrame, k: float = 0.75,
                  atr_period: int = 10, lookback_n: int = 50) -> pd.DataFrame:
    tr = compute_true_range(df)  # see [[True Range and ADTR]]
    adtr = tr.rolling(atr_period).mean()
    spikes = []

    for i in range(lookback_n, len(df) - 1):
        h, l, c = df.iloc[i][['high', 'low', 'close']]
        h_prev, h_next = df.iloc[i-1]['high'], df.iloc[i+1]['high']
        l_prev, l_next = df.iloc[i-1]['low'], df.iloc[i+1]['low']
        past_high = df['high'].iloc[i-lookback_n:i].max()
        past_low  = df['low'].iloc[i-lookback_n:i].min()
        day_range = h - l
        if day_range == 0:
            continue

        # Spike High
        protrusion_h = h - max(h_prev, h_next)
        if (protrusion_h > k * adtr.iloc[i]
            and (c - l) > 0 and (h - c) > 3 * (c - l)
            and h > past_high):
            spikes.append({'date': df.index[i], 'type': 'spike_high',
                           'protrusion': protrusion_h,
                           'close_position': (c - l) / day_range})

        # Spike Low (mirror)
        protrusion_l = min(l_prev, l_next) - l
        if (protrusion_l > k * adtr.iloc[i]
            and (h - c) > 0 and (c - l) > 3 * (h - c)
            and l < past_low):
            spikes.append({'date': df.index[i], 'type': 'spike_low',
                           'protrusion': protrusion_l,
                           'close_position': (c - l) / day_range})

    return pd.DataFrame(spikes)
```
