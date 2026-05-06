# Triple Tops and Bottoms

> Part of: [[Chapter_05_Chart_Patterns]] → Top and Bottom Formations

## Definition

A **triple top** is the same idea as a [[Double Tops and Bottoms|double top]], with one more failed rally — three peaks in roughly the same price area, separated by reaction lows. A **triple bottom** is the inverted form: three troughs at similar levels.

Triples are **rarer** than doubles, but interpretively identical. Confirmation: a close below the lowest of the intervening reaction lows (or above the highest reaction high for a triple bottom).

The repetition adds conviction — the market has tested resistance/support three times and failed each time. By the third failure, the case for reversal is very strong.

## Illustration

![[triple_top_bottom_illustration.svg]]

## Analogy — Three Strikes at the Same Pitch

A batter swings at the same fastball location three times and misses every time. After the third miss, the pitcher knows that pitch is a problem for him — and so does the batter. Either the pitcher keeps throwing it (and the batter changes), or the batter has to give up that part of the strike zone entirely.

A triple top works the same way. The market reaches up to the same level three times, and each time, the supply of sellers there is stronger than the demand of buyers. By the third failure, even the most committed bulls start to back off — the level is "respected" and the market drops away from it.

## Numeric Example

A weekly chart, stock making a triple top:

| Week | Peak / Trough | Price |
|---|---|---|
| W4  | First peak    | 145.20 |
| W11 | Reaction low  | 132.80 |
| W18 | Second peak   | 144.90 |
| W25 | Reaction low  | 134.20 |
| W34 | Third peak    | 145.50 |
| W42 | **Close below 132.80** → confirmed |  131.10 |

Calculations:
- Pattern height = 145.50 − 132.80 = 12.70
- Confirmation = 132.80
- **Measured target** = 132.80 − 12.70 = **120.10**

## Python Code

```python
import pandas as pd
import numpy as np

def detect_triple_top(df: pd.DataFrame,
                     similarity_pct: float = 0.03,
                     min_reaction_pct: float = 0.04,
                     window: int = 5) -> dict | None:
    """Three swing highs at similar levels with two reaction lows between them."""
    is_swing = df["high"] == df["high"].rolling(window * 2 + 1, center=True).max()
    swings = df[is_swing]
    if len(swings) < 3:
        return None

    p1, p2, p3 = swings.iloc[-3], swings.iloc[-2], swings.iloc[-1]
    peaks = [p1["high"], p2["high"], p3["high"]]
    if (max(peaks) - min(peaks)) / min(peaks) > similarity_pct:
        return None

    rxn1 = df.loc[p1.name:p2.name]["low"].min()
    rxn2 = df.loc[p2.name:p3.name]["low"].min()
    if (p2["high"] - rxn1) / p2["high"] < min_reaction_pct:
        return None
    if (p3["high"] - rxn2) / p3["high"] < min_reaction_pct:
        return None

    confirm_level = min(rxn1, rxn2)
    after = df.loc[p3.name:]
    confirmed = (after["close"] < confirm_level).any()

    return {
        "peaks": peaks,
        "reaction_lows": (rxn1, rxn2),
        "confirm_level": confirm_level,
        "confirmed": bool(confirmed),
        "target": confirm_level - (max(peaks) - confirm_level),
    }
```

## Relationships

### Within Chapter 5

- **Versus [[Double Tops and Bottoms]]**: a triple is just a double with one more attempt. Both have the same logic and target calculation; triples occur less often but with higher conviction.
- **Versus [[Head and Shoulders]]**: a head-and-shoulders has a *higher middle peak*; a triple top has all three peaks roughly equal.
- **Inside [[Chapter 04 - Trading Ranges and Support and Resistance]]** logic: three failed tests of resistance is essentially a confirmed range with a high probability that a *break of support* is meaningful.

### Outside Chapter 5

- **[[Chapter 04 - Trading Ranges and Support and Resistance]]** — three failures at the same level → strong resistance.
- **[[Chapter 10 - Setting Objectives]]** — projection method matches the double-top logic (height projected from breakdown).
- **[[Chapter 11 - The Most Important Rule]]** — penetration of a triple top in the original direction (price closes back above the highest peak after apparent confirmation) is a rare but very strong failed-signal pattern.

### When does this concept work well?

- **Best**: very long-term charts (weekly or monthly) where the three peaks are clearly separated by months. After a multi-year advance.
- **Worst**: trying to find triples on intraday charts — too much noise to label legitimate "peaks."

#chart-patterns #reversal-pattern #triple-top #triple-bottom
