# Gaps

> Part of: [[Chapter_05_Chart_Patterns]] → One-Day Patterns

## Definition

A **gap** is a price bar where today's low is above yesterday's high (an *up-gap*), or today's high is below yesterday's low (a *down-gap*). The result is a visible empty area on the chart — a region in which no trade ever printed.

Schwager identifies **four types**, each with a different meaning:

| Type | Where it occurs | Signal value |
|---|---|---|
| **Common gap** | Inside a trading range | Low — usually noise |
| **Breakaway gap** | Beyond the edge of a long-standing range | **High** — one of the most reliable signals if not filled within a few days |
| **Runaway gap** | Mid-trend, when a trend accelerates | Confirms strength; can occur in clusters |
| **Exhaustion gap** | Late in an extended move, just before reversal | Identifiable only in hindsight; precedes [[Island Reversals]] |

The honest difficulty: a runaway gap and an exhaustion gap *look identical when they form* — the difference is what happens next.

## Illustration

![[gaps_illustration.svg]]

## Analogy — The Crowded Elevator

Imagine you're watching people get on and off an elevator floor by floor. Most days, traffic at each floor is roughly continuous — someone gets on, someone gets off. That's the normal price tape.

A **gap** is when the elevator skips a floor entirely — doors don't even open. Why? Something out there made everybody change their mind at once.

- **Common gap** = the elevator skips the mezzanine because nobody works there anyway. No big deal.
- **Breakaway gap** = the elevator suddenly starts at floor 5 because the building manager just announced floors 1–4 are closed forever. New regime.
- **Runaway gap** = the elevator is in express mode going up — it skips floor after floor because everyone wants to get to the top.
- **Exhaustion gap** = the elevator skips one last floor going up and then everyone realizes nobody's at the top. It comes right back down.

## Numeric Example

A stock's daily bars:

| Day | Open | High | Low | Close |
|---|---|---|---|---|
| Mon | 100.00 | 102.00 | 99.50 | 101.80 |
| Tue | **104.00** | 106.20 | **103.50** | 105.90 |

Tuesday's low (103.50) is **above** Monday's high (102.00) → an up-gap of **1.50** (the empty zone between 102.00 and 103.50).

If Monday was the upper boundary of a 3-month range and the gap doesn't fill (price doesn't trade back into 102.00–103.50) within a few days → **breakaway gap** → strong long signal.

## Python Code

See [[gaps_detector.py]] for the full module.

```python
import pandas as pd

def detect_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect gap days. df must have columns: high, low, close.
    Returns the input df with new columns: gap_type ('up'/'down'/None) and gap_size.
    """
    prev_high = df["high"].shift(1)
    prev_low  = df["low"].shift(1)

    up_gap   = df["low"]  > prev_high
    down_gap = df["high"] < prev_low

    df = df.copy()
    df["gap_type"] = None
    df.loc[up_gap,   "gap_type"] = "up"
    df.loc[down_gap, "gap_type"] = "down"

    df["gap_size"] = 0.0
    df.loc[up_gap,   "gap_size"] = df["low"]  - prev_high
    df.loc[down_gap, "gap_size"] = prev_low   - df["high"]
    return df


def is_filled(df: pd.DataFrame, gap_idx: int, lookahead: int = 5) -> bool:
    """
    A gap is 'filled' if price re-enters the empty zone within `lookahead` bars.
    """
    row = df.iloc[gap_idx]
    if row["gap_type"] is None:
        return False
    end = min(gap_idx + 1 + lookahead, len(df))
    window = df.iloc[gap_idx + 1 : end]

    if row["gap_type"] == "up":
        gap_top    = row["low"]                 # bottom of price today
        gap_bottom = df.iloc[gap_idx - 1]["high"]
        return (window["low"] <= gap_bottom).any()
    else:
        gap_bottom = row["high"]
        gap_top    = df.iloc[gap_idx - 1]["low"]
        return (window["high"] >= gap_top).any()
```

## Relationships

### Within Chapter 5

- **Component of [[Island Reversals]]**: an island is literally bracketed by two gaps in opposite directions.
- **Combines with [[Wide-Ranging Days]]**: a wide-ranging day that *also* gaps is doubly significant.
- **Compare with [[Spikes]]**: both mark abrupt sentiment shifts, but a spike is a *single bar's shape*, while a gap is a *relationship between two bars*.

### Outside Chapter 5

- **[[Chapter 04 - Trading Ranges and Support and Resistance]]** — breakaway gaps from long-standing ranges are the most reliable kind. The range provides the context.
- **[[Chapter 11 - The Most Important Rule]]** — a *filled* gap is itself a powerful "failed signal" indicating the breakout was a fake-out and the opposite move is likely.
- **[[Chapter 09 - Choosing Stop-Loss Points]]** — a natural stop on a breakaway-gap entry is "fill of the gap" → close below the bottom of the gap zone.

### When does this concept work well?

- **Best**: breakaway gaps after multi-month consolidation, in liquid markets, with rising volume on the gap day.
- **Worst**: in thinly-traded names or after-hours moves where gaps are common noise rather than signal.

#chart-patterns #one-day-pattern #gaps
