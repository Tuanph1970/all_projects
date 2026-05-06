# Head and Shoulders

> Part of: [[Chapter_05_Chart_Patterns]] → Top and Bottom Formations

## Definition

The **head-and-shoulders top** is a three-peak reversal formation in which the middle peak ("head") is *higher* than the peaks on either side ("shoulders"). The "neckline" connects the two reaction lows between the peaks.

The mirror image is the **head-and-shoulders bottom**: three troughs with a deeper middle trough, and a neckline connecting the two reaction highs.

**Two essential requirements**:
1. **The pattern is not complete until the neckline is broken.** Until then, it's just an unfinished shape.
2. **A meaningful prior trend must exist.** A "head and shoulders" that forms in choppy, sideways action is meaningless.

A common rookie mistake is to call the pattern early — to spot the shoulder-head-shoulder shape and short before the neckline breaks. Schwager warns against this: many such patterns dissolve back into trend continuation.

## Illustration

![[head_and_shoulders_illustration.svg]]

## Analogy — A Bouncing Ball Losing Energy

Drop a tennis ball. The first bounce is high. The second bounce is the *highest* — wait, that doesn't work physically. Try this instead:

A bouncing ball is the *opposite* shape of an H&S top. So flip it: imagine you're throwing the ball *upward* against a low ceiling. First throw, you barely reach the ceiling (left shoulder). Second throw, you pound it (head). Third throw, your arm is tired and you can only barely tap it again (right shoulder). After three throws, you stop — and the ball stays on the ground.

The **neckline break** is when the ball, instead of staying on the ground, gets stomped into the floorboards. The ceiling (head) was the peak strength of your effort; the right-shoulder height tells you how much energy is left; and the broken neckline means you don't even have the strength to keep the ball at floor-level anymore.

## Numeric Example

A H&S top in a stock:

| Stage | Date | Price | Notes |
|---|---|---|---|
| Left shoulder | Jan | 142.00 | Peak |
| Reaction low 1 | Feb | 130.50 | Neckline anchor 1 |
| Head | Mar | 152.00 | New high |
| Reaction low 2 | Apr | 131.20 | Neckline anchor 2 |
| Right shoulder | May | 141.80 | Lower than head; close to LS |
| **Neckline break** | Jun | close < 130.50 | Pattern confirmed |

Calculations:
- Neckline level (avg of the two reaction lows) ≈ 130.85
- Pattern height = 152.00 − 130.85 = 21.15
- **Measured target** = 130.85 − 21.15 = **109.70**
- Stop-loss for short = above the right shoulder (141.80)

## Python Code

```python
import pandas as pd
import numpy as np

def detect_head_and_shoulders(df: pd.DataFrame,
                             window: int = 5,
                             shoulder_tolerance: float = 0.05) -> dict | None:
    """
    Identify the most recent H&S top:
        LS_high < Head_high  AND  RS_high < Head_high
        |LS_high - RS_high| / LS_high <= shoulder_tolerance
    Returns details and whether the neckline has been broken.
    """
    is_high = df["high"] == df["high"].rolling(window * 2 + 1, center=True).max()
    is_low  = df["low"]  == df["low"].rolling(window * 2 + 1, center=True).min()

    highs = df[is_high]
    lows  = df[is_low]
    if len(highs) < 3 or len(lows) < 2:
        return None

    ls, head, rs = highs.iloc[-3], highs.iloc[-2], highs.iloc[-1]
    if not (head["high"] > ls["high"] and head["high"] > rs["high"]):
        return None

    asym = abs(ls["high"] - rs["high"]) / ls["high"]
    if asym > shoulder_tolerance:
        return None

    # Find reaction lows between LS-Head and Head-RS
    rxn1 = df.loc[ls.name:head.name]["low"].min()
    rxn2 = df.loc[head.name:rs.name]["low"].min()
    neckline = (rxn1 + rxn2) / 2

    after = df.loc[rs.name:]
    confirmed = (after["close"] < neckline).any()

    return {
        "left_shoulder":  ls["high"],
        "head":           head["high"],
        "right_shoulder": rs["high"],
        "neckline":       neckline,
        "confirmed":      bool(confirmed),
        "target":         neckline - (head["high"] - neckline),
    }
```

## Relationships

### Within Chapter 5

- **Versus [[Double Tops and Bottoms]]**: a double top is symmetric (two equal peaks); H&S is asymmetric (taller middle peak). H&S patterns *contain* a built-in trend-failure signal: the right shoulder forming below the head shows the buyers are weakening even before the neckline cracks.
- **Versus [[Triple Tops and Bottoms]]**: triples have three equal peaks; H&S has an asymmetric middle.
- **Confirmed by [[Wide-Ranging Days]] / [[Thrust Days]]** breaking the neckline.

### Outside Chapter 5

- **[[Chapter 03 - Trends]]** — the right shoulder being below the head is the first violation of the "higher highs" rule of an uptrend.
- **[[Chapter 10 - Setting Objectives]]** — the standard measured target uses pattern height projected down from neckline.
- **[[Chapter 11 - The Most Important Rule]]** — failed H&S patterns are common and powerful: when price retraces past the *most recent* shoulder after appearing to confirm, the pattern is invalidated and a strong move in the original-trend direction often follows. Schwager treats this explicitly as a separate signal.
- **[[Chapter 09 - Choosing Stop-Loss Points]]** — stop just above the right shoulder; if violated, the pattern has failed.

### When does this concept work well?

- **Best**: after a long, mature trend; with the head clearly above both shoulders; with a downward-sloping neckline (more bearish version) on a top; and confirmed by a high-volume neckline break.
- **Worst**: in choppy, range-bound markets where any sequence of three peaks superficially resembles H&S. Always require a meaningful prior trend.

#chart-patterns #reversal-pattern #head-and-shoulders
