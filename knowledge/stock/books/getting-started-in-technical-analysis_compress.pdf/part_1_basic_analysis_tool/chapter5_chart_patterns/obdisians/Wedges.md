# Wedges

> Part of: [[Chapter_05_Chart_Patterns]] → Top and Bottom Formations

## Definition

A **rising wedge** is a converging pattern in which both the highs and lows step upward — but the upper line is *less steep* than the lower line, so the channel narrows over time. A **declining wedge** is the inverse: both highs and lows step downward, but the lower line is less steep than the upper.

The key insight: in a rising wedge, the bulls are pushing into new high ground but with *diminishing energy* (each new high barely exceeds the last). The hidden message is that selling pressure is mounting on every probe higher. The eventual resolution is usually **opposite to the slope** of the wedge: a rising wedge typically breaks **down**, a declining wedge typically breaks **up**.

Wedges can take a long time to complete — sometimes years on weekly charts.

## Illustration

![[wedges_illustration.svg]]

## Analogy — Climbing Stairs that Get Smaller

Imagine walking up a staircase. The first few steps are tall — you're making real progress upward. But each step gets shorter than the last: nine inches, then six, then four, then two. You're still going up, but the climb is fading. By the time you're stepping up an inch at a time, your forward momentum is exhausted — the next move is going to be backward, and probably hard.

A rising wedge is that staircase. You can see the stair-heights shrinking even as the price keeps rising. The pattern is the chart's way of telling you: "Yes, technically still going up. But there's nothing left in the tank."

## Numeric Example

A rising wedge in a stock:

| Pivot | Type | Price |
|---|---|---|
| 1 | Low  | 50.00 |
| 2 | High | 55.00 |
| 3 | Low  | 52.50 |
| 4 | High | 56.30 |
| 5 | Low  | 54.00 |
| 6 | High | 57.10 |
| 7 | Low  | 55.20 |
| 8 | High | 57.50 |
| **Break** | Lower line broken | 55.00 |

Slope check:
- Highs: 55.00 → 57.50 over 8 pivots ⇒ **+0.31** per pivot
- Lows:  50.00 → 55.20 over 8 pivots ⇒ **+0.65** per pivot
- Lows rising faster than highs → converging from below → rising wedge ✓
- Resolution: break of the lower line (55.00) → bearish

Target: depth of the wedge at its widest = 55.00 − 50.00 = **5.00 → projected target ≈ 50.00**.

## Python Code

```python
import numpy as np
import pandas as pd

def detect_wedge(df: pd.DataFrame, window: int = 40,
                min_pivots: int = 4) -> dict | None:
    """
    Look for converging trendlines where both slopes have the same sign:
      both positive => rising wedge
      both negative => declining wedge
    """
    recent = df.iloc[-window:]

    is_high = recent["high"] == recent["high"].rolling(5, center=True).max()
    is_low  = recent["low"]  == recent["low"].rolling(5, center=True).min()
    highs = recent[is_high]
    lows  = recent[is_low]
    if len(highs) < min_pivots // 2 or len(lows) < min_pivots // 2:
        return None

    x_h = np.arange(len(recent))[is_high.values]
    x_l = np.arange(len(recent))[is_low.values]
    h_slope, _ = np.polyfit(x_h, highs["high"].values, 1)
    l_slope, _ = np.polyfit(x_l, lows["low"].values, 1)

    if h_slope > 0 and l_slope > 0 and l_slope > h_slope:
        kind = "rising_wedge"      # bearish bias on break
    elif h_slope < 0 and l_slope < 0 and h_slope > l_slope:
        kind = "declining_wedge"   # bullish bias on break
    else:
        return None

    return {
        "type": kind,
        "high_slope": h_slope,
        "low_slope":  l_slope,
        "convergence_bars": (
            (highs.iloc[-1]["high"] - lows.iloc[-1]["low"]) / max(abs(h_slope - l_slope), 1e-9)
        ),
    }


def wedge_target(wedge_widest: float, breakout_price: float,
                 direction: str) -> float:
    return breakout_price - wedge_widest if direction == "down" \
           else breakout_price + wedge_widest
```

## Relationships

### Within Chapter 5

- **Versus [[Triangles]]**: a triangle has one flat boundary or *opposing-sign* slopes; a wedge has *same-sign* slopes (both up, or both down). Triangles tend to break in the direction of the prior trend; wedges tend to break *opposite* to their own slope.
- **Versus [[Flags and Pennants]]**: flags/pennants are short (1–3 weeks); wedges are long (months to years). Flags resolve in the prior-trend direction; wedges resolve against their slope.
- **Confirmed by [[Wide-Ranging Days]] / [[Thrust Days]]** breaking the constraining line.

### Outside Chapter 5

- **[[Chapter 03 - Trends]]** — a rising wedge inside an uptrend signals the uptrend is *failing*; even though prices are still rising, the wedge geometry warns of imminent reversal.
- **[[Chapter 06 - Oscillators]]** — wedges very often coincide with bearish/bullish *divergences* on momentum oscillators (price makes higher highs while RSI makes lower highs). The combination is one of the strongest reversal setups.
- **[[Chapter 10 - Setting Objectives]]** — measured target = wedge's widest height projected from breakout.
- **[[Chapter 11 - The Most Important Rule]]** — a wedge that breaks *in the same direction as its slope* (rising wedge breaks up) is a failed pattern, often presaging a powerful continuation.

### When does this concept work well?

- **Best**: long-duration wedges (≥3 months) on weekly charts, with clear convergence of the trendlines, and momentum divergence.
- **Worst**: tight, short-term wedges in noisy markets — easily mistaken for normal pullbacks or pennants.

#chart-patterns #reversal-pattern #wedges
