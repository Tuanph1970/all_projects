# V Tops and Bottoms

> Part of: [[Chapter_05_Chart_Patterns]] → Top and Bottom Formations

## Definition

A **V top** is a sharp, "turn-on-a-dime" reversal at the end of an advance: the chart prints a steep up-leg, an apex of one or two bars, and then an equally steep down-leg. A **V bottom** is the mirror image at the end of a decline.

These patterns are *fast* — there is essentially no consolidation, no warning shoulder, no gradual rounding. The market simply changes its mind in a day or two.

The drawback: a V is **hard to distinguish in real time from a sharp pullback** that's about to resume the trend. Schwager argues you should only trust a V if there's an additional confirming feature at the apex:

- A prominent [[Spikes|spike]]
- A meaningful [[Reversal Days|reversal day]] (preferably the strong version)
- A wide [[Gaps|gap]] in the opposite direction
- A [[Wide-Ranging Days|wide-ranging day]] with a contrary close

Without one of these confirmations, a V is a *guess*; with one, it's a structured signal.

## Illustration

![[v_tops_bottoms_illustration.svg]]

## Analogy — The Dropped Tray

You're carrying a stack of plates up a staircase. Step by step you've gone up — until on the very next step your foot catches and the whole stack tips. There's no warning, no wobble — one moment up, the next moment everything's coming down.

A V top is that fall. There was no rounded shoulder, no triple-checking your balance — just a sudden flip. And the only way you know it really happened (and isn't just a stumble you'll recover from) is some unambiguous evidence at the moment of the flip: a crash sound, a plate breaking, a clear sign that something gave way. Without that evidence, you might just be tripping briefly.

## Numeric Example

Stock rallies from 60 → 95 over three months. Then:

| Day | High | Low | Close |
|---|---|---|---|
| T−1 | 94.50 | 93.20 | 94.30 |
| **T (apex — spike high)** | **96.80** | 93.40 | 93.55 |
| T+1 | 93.80 | 91.20 | 91.40 |
| T+2 | 91.60 | 89.50 | 89.80 |
| T+3 | 90.20 | 87.00 | 87.20 |

The apex day:
- Spike high (96.80 vs neighbor highs ~94.50 and 93.80) ✓
- Strong reversal day (close 93.55 below T−1 low of 93.20) ✓
- Following sharp 8-pt drop in 3 days

Three confirmation features stacked → high-conviction V top.

## Python Code

```python
import pandas as pd

def detect_v_top(df: pd.DataFrame, run_length: int = 20,
                drop_length: int = 5, min_run_pct: float = 0.10,
                min_drop_pct: float = 0.07) -> pd.Series:
    """
    Mark V-top apex bars: large advance into a peak, then sharp decline,
    with peak occurring within 1-2 bars.
    """
    closes = df["close"]
    is_v = pd.Series(False, index=df.index)

    for i in range(run_length, len(df) - drop_length):
        run_low_idx  = closes.iloc[i - run_length:i].idxmin()
        run_low      = closes.loc[run_low_idx]
        peak         = df["high"].iloc[i]
        if (peak - run_low) / run_low < min_run_pct:
            continue

        post_low = df["low"].iloc[i + 1 : i + 1 + drop_length].min()
        if (peak - post_low) / peak < min_drop_pct:
            continue

        is_v.iloc[i] = True
    return is_v


def confirm_v_with_spike_or_reversal(df: pd.DataFrame, v_idx: int) -> bool:
    """Require at least one of: spike, strong reversal day, large gap."""
    h, l, c = df["high"].iloc[v_idx], df["low"].iloc[v_idx], df["close"].iloc[v_idx]
    prev_h  = df["high"].iloc[v_idx - 1]
    prev_l  = df["low"].iloc[v_idx - 1]
    next_h  = df["high"].iloc[v_idx + 1] if v_idx + 1 < len(df) else h

    spike    = h > prev_h * 1.02 and h > next_h * 1.02
    rev_day  = h > prev_h and c < prev_l                   # strong reversal
    gap_down = df["high"].iloc[v_idx + 1] < l if v_idx + 1 < len(df) else False
    return spike or rev_day or gap_down
```

## Relationships

### Within Chapter 5

- **Strengthened by [[Spikes]]**, [[Reversal Days]], [[Gaps]], [[Wide-Ranging Days]] — see the apex confirmation list above.
- **Versus [[Double Tops and Bottoms]]**: a double top has a *retest* between the two peaks; a V has none. Doubles are more reliable but slower; Vs are faster but riskier without confirmation.
- **Versus [[Rounded Tops and Bottoms]]**: a V is the *opposite* of a rounded top in shape — instant turn versus gradual transition. Rounded patterns are far more reliable.

### Outside Chapter 5

- **[[Chapter 03 - Trends]]** — a V is essentially a trend-reversal point with zero transition. Once confirmed, the prior trendline is broken.
- **[[Chapter 11 - The Most Important Rule]]** — V tops/bottoms that *fail* (price retakes the apex) signal continuation of the original trend with high conviction.
- **[[Chapter 09 - Choosing Stop-Loss Points]]** — apex extreme = natural stop.

### When does this concept work well?

- **Best**: with multiple confirmation features stacked at the apex, in a market that has just finished a parabolic, accelerated move.
- **Worst**: as a stand-alone pattern without confirmation — too easy to mistake for a normal pullback that resumes.

#chart-patterns #reversal-pattern #v-tops #v-bottoms
