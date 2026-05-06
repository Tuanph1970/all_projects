# Double Tops and Bottoms

> Part of: [[Chapter_05_Chart_Patterns]] → Top and Bottom Formations

## Definition

A **double top** is a two-peak formation where the market rallies, pulls back, rallies again to roughly the same area, and then turns back down. The two peaks need not be identical — only in the same general price vicinity.

A **double bottom** is the same idea inverted: two troughs in the same area separated by a relief rally.

**Confirmation rule**: The pattern is officially complete when price closes *below the reaction low between the two tops* (or *above the reaction high* between the two bottoms). When the intervening reaction is shallow, this confirmation is timely; when it's deep, the trader has surrendered too much profit waiting and must use other clues (like a [[Spikes|spike]] at the second peak or a [[Flags and Pennants|flag]] forming on the way down).

A double top/bottom that materializes *after a long, established trend* is a strong major-reversal signal.

## Illustration

![[double_top_bottom_illustration.svg]]

## Analogy — Two Failed Knock-on-the-Door Attempts

Imagine you're waiting for a friend to answer the door. You knock, wait, no answer. You walk back to your car, then think, "let me try once more" — you walk back, knock again, still no answer. Now you know they're not coming. You drive away.

The first peak is the first knock. The pullback is the walk back to the car. The second peak is the second knock at the same door — same height, same answer. The "confirmation" is when you start the engine and drive: that's price closing below the prior pullback low. After two clear failures at the same level, the path of least resistance is *away* from the door.

## Numeric Example

A stock making a double top:

| Day | High | Low | Close | Notes |
|---|---|---|---|---|
| Day 1 | **120.50** | 117.20 | 118.00 | First peak |
| Day 12 | 113.80 | **109.60** | 110.20 | Reaction low |
| Day 28 | **121.10** | 118.50 | 119.00 | Second peak (≈ first peak) |
| Day 41 | 110.80 | **109.40** | **109.10** | Closes below reaction low → **confirmed** |

Calculations:
- Pattern height = 121.10 − 109.60 = 11.50
- Confirmation level = 109.60
- **Measured target** = 109.60 − 11.50 = **98.10**
- Stop-loss for short entry = above the higher peak (121.10), or above the most recent shoulder retracement

## Python Code

```python
import pandas as pd
import numpy as np

def find_swing_highs(df: pd.DataFrame, window: int = 5) -> pd.Series:
    """A swing high is a bar that's the highest in a +/- window radius."""
    return df["high"] == df["high"].rolling(window * 2 + 1, center=True).max()


def detect_double_top(df: pd.DataFrame,
                     similarity_pct: float = 0.03,
                     min_reaction_pct: float = 0.05,
                     window: int = 5) -> dict | None:
    """
    Find the most recent two swing highs that:
      - are within similarity_pct of each other
      - have a meaningful reaction low between them
      - have a confirmed close below the reaction low afterward
    """
    swings = df[find_swing_highs(df, window)]
    if len(swings) < 2:
        return None

    last  = swings.iloc[-1]
    prev  = swings.iloc[-2]
    diff  = abs(last["high"] - prev["high"]) / prev["high"]
    if diff > similarity_pct:
        return None

    between = df.loc[prev.name:last.name]
    reaction_low = between["low"].min()
    pull = (prev["high"] - reaction_low) / prev["high"]
    if pull < min_reaction_pct:
        return None

    after = df.loc[last.name:]
    confirmed = (after["close"] < reaction_low).any()

    return {
        "first_peak":   prev["high"],
        "second_peak":  last["high"],
        "reaction_low": reaction_low,
        "confirmed":    bool(confirmed),
        "target":       reaction_low - (max(prev["high"], last["high"]) - reaction_low),
    }
```

## Relationships

### Within Chapter 5

- **Versus [[V Tops and Bottoms]]**: a V has no retest; a double top has a clear retest of the high. Doubles are slower but more reliable.
- **Versus [[Triple Tops and Bottoms]]**: triples are simply double tops/bottoms with one more attempt — rarer, but the same logic applies.
- **Versus [[Head and Shoulders]]**: a head-and-shoulders is asymmetric (middle peak is highest); a double top is roughly symmetric.
- **Confirmed by [[Spikes]] / [[Reversal Days]]** at the second peak.
- **Reaction-low breach is often a [[Wide-Ranging Days|wide-ranging]] / [[Thrust Days|thrust]] day** — that's the highest-conviction confirmation.

### Outside Chapter 5

- **[[Chapter 04 - Trading Ranges and Support and Resistance]]** — the two peaks define a *resistance* level; the reaction low defines a *support* level. The pattern is essentially a tiny trading range whose support gives way.
- **[[Chapter 10 - Setting Objectives]]** — measured-move target = pattern height projected from breakdown level.
- **[[Chapter 11 - The Most Important Rule]]** — *penetration* of a double top (price returns above both peaks after appearing to confirm) is one of Schwager's most powerful failed-signal indicators. It often precedes a much larger move.
- **[[Chapter 09 - Choosing Stop-Loss Points]]** — natural short stop above the higher of the two peaks.

### When does this concept work well?

- **Best**: after a *long* prior advance, with the two peaks 4–12 weeks apart, and with the reaction low tested only once before the breakdown.
- **Worst**: in a sideways market where every range high looks like the second peak of a "double top." Without a clear prior trend, the pattern is meaningless.

#chart-patterns #reversal-pattern #double-top #double-bottom
