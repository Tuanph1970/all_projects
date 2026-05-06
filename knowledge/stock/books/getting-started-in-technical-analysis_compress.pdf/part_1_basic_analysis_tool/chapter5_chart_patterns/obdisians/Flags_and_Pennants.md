# Flags and Pennants

> Part of: [[Chapter_05_Chart_Patterns]] → Continuation Patterns

## Definition

**Flags** and **pennants** are short (1–3 weeks), narrow consolidations that appear *inside* a larger trend. They differ only in geometry:

| Pattern | Boundary lines | Visual |
|---|---|---|
| **Flag** | Parallel | A small parallelogram, usually sloping against the trend |
| **Pennant** | Converging | A small symmetrical triangle |

Either way, the pattern represents a *pause* in a strong trend. The most common — and reliable — outcome is a breakout in the direction of the **prior swing**, not the slope of the flag/pennant itself.

Schwager's two important refinements:

1. He prefers to **enter inside the formation**, anticipating the breakout direction, rather than wait for confirmation. The trade-off (slightly worse fill on errors) is usually worth the better fill on winners.
2. **Flags/pennants near the top of a long range** are especially bullish (price is *not retreating* despite hitting resistance — it's gathering strength). The mirror is true for flags near the bottom of a range.

## Illustration

![[flags_pennants_illustration.svg]]

## Analogy — Catching Your Breath Mid-Climb

Picture a hiker climbing a steep trail. After 30 minutes of steady ascent, she stops at a small ledge to catch her breath, drink water, and look around. She isn't going back down — she's pausing. Her body sways slightly as she rests, but the next move is going to be *uphill again*.

A flag is that breather. The slight backward sway is the counter-trend slope of the flag. The crucial thing is: she's still on the trail, she still has gear on, and her face is pointing up the mountain. When she stands again, expect the climb to resume.

A pennant is the same breather, but instead of a level ledge, she's wedged into a narrowing rock chute — the walls press in on both sides until she has to push through.

## Numeric Example

Stock has rallied from 50 → 70 over six weeks. Then a flag forms over 10 trading days:

| Day | High | Low | Close |
|---|---|---|---|
| 1 | 70.20 | 69.50 | 69.80 |
| 2 | 69.90 | 69.10 | 69.20 |
| ... | (downward-sloping parallel lines, range narrows ~1 pt) | | |
| 10 | 69.40 | 68.60 | 68.90 |
| **11** | 71.10 | 69.30 | **70.85** ← breakout |

Calculations:
- Flagpole height = 70 − 50 = 20
- Breakout price ≈ 70.20
- **Measured target** ≈ 70.20 + 20 = **90.20** (projected continuation of flagpole length)
- Stop-loss: opposite extreme of flag = 68.60

## Python Code

```python
import numpy as np
import pandas as pd

def find_flagpole(df: pd.DataFrame, min_pct: float = 0.10,
                  max_bars: int = 25) -> tuple | None:
    """
    Identify the most recent fast move (flagpole) preceding now.
    Returns (start_idx, end_idx, magnitude_pct) or None.
    """
    closes = df["close"].values
    for end in range(len(closes) - 1, max(0, len(closes) - max_bars), -1):
        for start in range(end - 5, max(0, end - max_bars), -1):
            move = (closes[end] - closes[start]) / closes[start]
            if abs(move) >= min_pct and (end - start) <= max_bars:
                return start, end, move
    return None


def detect_flag(df: pd.DataFrame, max_bars: int = 15) -> dict | None:
    """
    Quick check: after a flagpole, does the recent action form a tight
    counter-trend channel (flag) or converging channel (pennant)?
    """
    pole = find_flagpole(df.iloc[:-max_bars])
    if pole is None:
        return None
    start, end, pole_move = pole
    flag = df.iloc[end:end + max_bars]
    if len(flag) < 5:
        return None

    x = np.arange(len(flag))
    h_slope, _ = np.polyfit(x, flag["high"].values, 1)
    l_slope, _ = np.polyfit(x, flag["low"].values, 1)

    # Both slopes counter to the pole direction => flag
    sign = np.sign(pole_move)
    if np.sign(h_slope) == -sign and np.sign(l_slope) == -sign \
       and abs(h_slope - l_slope) / max(abs(h_slope), 1e-9) < 0.20:
        kind = "flag"
    elif np.sign(h_slope) != np.sign(l_slope):
        kind = "pennant"
    else:
        return None

    return {"type": kind,
            "pole_start": start, "pole_end": end,
            "pole_move": pole_move,
            "flag_high": flag["high"].max(),
            "flag_low":  flag["low"].min()}


def flag_target(pole_start_price: float, pole_end_price: float,
                breakout_price: float) -> float:
    pole_height = pole_end_price - pole_start_price
    return breakout_price + pole_height
```

## Relationships

### Within Chapter 5

- **Versus [[Triangles]]**: pennants are essentially short triangles. The line is *time*: ≤3 weeks → pennant, longer → triangle.
- **Combines with [[Wide-Ranging Days]]**: the breakout bar is most reliable when wide-ranging.
- **Confirms [[Thrust Days|thrust day]] entries**: a thrust-day close beyond the flag is an ideal entry.

### Outside Chapter 5

- **[[Chapter 04 - Trading Ranges and Support and Resistance]]** — flags forming *near the top of a multi-month range* are a bullish breakout precursor. The longer the range, the more potent the flag.
- **[[Chapter 08 - Midtrend Entry and Pyramiding]]** — flags are the canonical mid-trend entry pattern: the prior trend tells you the direction; the flag is the timing vehicle.
- **[[Chapter 09 - Choosing Stop-Loss Points]]** — opposite extreme of the flag = natural stop.
- **[[Chapter 10 - Setting Objectives]]** — measured target = flagpole length projected from breakout.
- **[[Chapter 11 - The Most Important Rule]]** — a flag that breaks **counter to the prior trend** is one of Schwager's strongest reversal signals (a *failed continuation*). See his discussion of "counter-to-anticipated breakouts."

### When does this concept work well?

- **Best**: tight, short flags (≤2 weeks) inside a strong, established trend, ideally near a major prior breakout level. Volume should dry up inside the flag and surge on the breakout.
- **Worst**: loose, multi-week consolidations that are really small trading ranges; very late flags after a parabolic move (often these resolve *opposite* to expectation, which is itself a signal — see [[Chapter 11 - The Most Important Rule]]).

#chart-patterns #continuation-pattern #flags #pennants
