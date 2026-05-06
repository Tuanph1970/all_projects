# Island Reversals

> Part of: [[Chapter_05_Chart_Patterns]] → Top and Bottom Formations

## Definition

An **island top** forms when, after an extended advance, prices **gap higher** to a new high, trade for one or more days at that elevated level *without filling the gap*, and then **gap lower** to leave the entire elevated range visually disconnected — a small "island" of bars surrounded by empty space on the chart.

An **island bottom** is the inverse: a downside gap, a brief stay at low prices, and then an upside gap that strands the bottom bars on their own.

The "island" can be one bar (a single isolated day) or several weeks of trading at the elevated/depressed level. What matters is that *both* gaps remain unfilled, so the cluster is fully bracketed by empty space.

Island reversals are essentially [[Spikes|spike]]-and-[[Reversal Days|reversal-day]] formations supercharged by gaps on both sides — and they are among the more reliable major-reversal signals.

## Illustration

![[island_reversal_illustration.svg]]

## Analogy — A Stranded Hiker

Imagine a hiker who jumps across a small ravine to reach a small rocky outcrop, spends a few hours there, and then jumps *back* across in a different direction — but this time the ravine on the return side is wider, and the outcrop is left behind, surrounded by empty air on both sides.

That isolated outcrop is an island top. The two jumps are the two gaps. Once the hiker is on the new side and the outcrop is stranded, you know they're not coming back: the previous high ground has been abandoned, and the only relevant price terrain is below it.

## Numeric Example

Daily bars on a stock that's been in an uptrend:

| Day | High | Low | Close | Notes |
|---|---|---|---|---|
| T−1 | 88.40 | 87.20 | 88.10 | Last bar before island |
| T (gap up) | 91.50 | 90.20 | 90.80 | Low (90.20) > prior high (88.40) → up-gap |
| T+1 | 92.10 | 90.40 | 91.30 | Stays elevated |
| T+2 | 91.80 | 90.30 | 90.50 | Stays elevated |
| T+3 (gap down) | 87.00 | 85.40 | 85.80 | High (87.00) < prior low (90.30) → down-gap |
| T+4 | 86.20 | 84.50 | 84.80 | Confirmation |

The bars on T, T+1, T+2 are the "island": fully isolated by the up-gap at T and the down-gap at T+3. Both gaps are unfilled.

Calculation guide:
- Pattern reference high = 92.10 (top of island)
- Pre-gap reference high = 88.40
- A natural stop on a short entry = above 88.40 (or above the bottom of the upper gap, 90.20)
- Initial target: at minimum, retracement of the most recent advance leg

## Python Code

```python
import pandas as pd

def detect_island_top(df: pd.DataFrame, max_island_bars: int = 10) -> dict | None:
    """
    Walk through bars looking for:
        - up-gap on day T: low[T] > high[T-1]
        - bars T..T+k all hold above high[T-1] (gap unfilled)
        - down-gap on day T+k+1: high[T+k+1] < low[T+k]
    """
    h, l = df["high"].values, df["low"].values
    for t in range(1, len(df) - max_island_bars - 1):
        if l[t] <= h[t - 1]:
            continue                        # no up-gap

        gap_floor = h[t - 1]
        for k in range(max_island_bars):
            island_end = t + k
            if island_end + 1 >= len(df):
                break
            if l[island_end] <= gap_floor:  # gap got filled
                break
            if h[island_end + 1] < l[island_end]:
                return {
                    "island_start": t,
                    "island_end":   island_end,
                    "up_gap_floor": gap_floor,
                    "down_gap_ceiling": l[island_end],
                    "island_high":  max(h[t : island_end + 1]),
                }
    return None


def detect_island_bottom(df: pd.DataFrame, max_island_bars: int = 10) -> dict | None:
    h, l = df["high"].values, df["low"].values
    for t in range(1, len(df) - max_island_bars - 1):
        if h[t] >= l[t - 1]:
            continue                        # no down-gap

        gap_ceiling = l[t - 1]
        for k in range(max_island_bars):
            island_end = t + k
            if island_end + 1 >= len(df):
                break
            if h[island_end] >= gap_ceiling:
                break
            if l[island_end + 1] > h[island_end]:
                return {
                    "island_start": t,
                    "island_end":   island_end,
                    "down_gap_ceiling": gap_ceiling,
                    "up_gap_floor":     h[island_end],
                    "island_low":       min(l[t : island_end + 1]),
                }
    return None
```

## Relationships

### Within Chapter 5

- **Built from [[Gaps]]**: an island is literally bracketed by two gaps in opposite directions. It is the most powerful gap-based signal in the chapter.
- **Often contains [[Spikes]] / [[Reversal Days]]**: the bars *inside* the island frequently include a spike or reversal day at the apex.
- **Versus [[V Tops and Bottoms]]**: an island is a V with the additional requirement that *gaps* mark the entry and exit. Islands are stronger than plain Vs.
- **Confirms an [[Gaps|exhaustion gap]]**: if a runaway-looking gap is followed within days by a counter-direction gap that traps it, the original gap is retroactively classified as an exhaustion gap, and the island confirms the reversal.

### Outside Chapter 5

- **[[Chapter 11 - The Most Important Rule]]** — *filling* either of the bracketing gaps invalidates the island and converts it into a failed signal, often a strong continuation indicator.
- **[[Chapter 10 - Setting Objectives]]** — the island's vertical span gives a rough projection magnitude; broader projections use the height of the prior trend leg.
- **[[Chapter 09 - Choosing Stop-Loss Points]]** — the natural stop is *across the gap* (the level that would fill the bracketing gap on the opposite side).

### When does this concept work well?

- **Best**: after a long, accelerated trend, when the opening up-gap (or down-gap) coincides with a news catalyst or is visibly larger than recent volatility, and the down-gap (or up-gap) closing the island is itself wide-ranging.
- **Worst**: in low-liquidity names where overnight gaps are routine; the "island" loses meaning when gaps form daily.

#chart-patterns #reversal-pattern #island-reversals #gaps
