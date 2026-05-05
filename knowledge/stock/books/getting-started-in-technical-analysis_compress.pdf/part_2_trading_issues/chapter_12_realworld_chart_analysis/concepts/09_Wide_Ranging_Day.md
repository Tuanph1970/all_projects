# 09 — Wide-Ranging Day

## Definition

A **wide-ranging day** is a single bar whose high-to-low range significantly exceeds the average range of recent trading days — i.e. its **true range >> recent ATR**. The book's glossary defines it as "a price bar that is significantly bigger than the days preceding it." The Appendix gives a quantitative form: the Volatility Ratio (VR) — today's true range divided by the average true range over the prior N days. A common threshold is VR ≥ 2.

In Chapter 12, wide-ranging days play three distinct roles depending on context:

1. **Trend-reversal warning** when they form **near an extended low** (wide-ranging *up* day) or **near an extended high** (wide-ranging *down* day) — Figures 12.7, 12.13, 12.17.
2. **Continuation-confirmation** when they form *with* the prevailing trend.
3. **Stop-placement reference** — return to the extremes of a wide-ranging day is itself a meaningful technical signal.

## Illustration

![[09_wide_ranging_day.png]]

A single bar dwarfing its neighbors at the bottom of an extended decline is one of Schwager's most-used early reversal signals.

## Analogy

A pond surface stays mostly flat with small ripples until something significant happens — a stone gets thrown in, a fish jumps, a sudden breeze. The size of the disturbance tells you about the energy that produced it. A series of tiny ripples, then one big splash, then ripples again: the big splash isn't noise, it's *something happened* worth investigating. A wide-ranging day is the chart equivalent — a sudden sharp departure from the prevailing rhythm that says forces just changed.

## Numeric Example

Suppose the last 14 bars have an average true range of 0.45. A bar that opens at 188.50, prints a high of 197.20, and a low of 187.80 has a true range of 9.40. The Volatility Ratio is 9.40 / 0.45 ≈ **20.9** — overwhelmingly wide. If this bar forms after a multi-week decline near major support, it is a textbook reversal warning.

| Bar | High | Low | Close | TR | ATR(14) | VR |
|---|---|---|---|---|---|---|
| t−2 | 189.0 | 188.4 | 188.7 | 0.6 | 0.45 | 1.3 |
| t−1 | 188.6 | 187.9 | 188.5 | 0.7 | 0.45 | 1.6 |
| **t (wide-range)** | **197.2** | **187.8** | **196.5** | **9.4** | 0.45 | **20.9** |
| t+1 | 197.5 | 195.0 | 197.0 | 2.5 | 1.0 | 2.5 |

## Python

```python
from chapter12_concepts import wide_ranging_day, true_range
import pandas as pd

# Build a series with one obvious outlier bar.
data = {
    "open":  [100.1, 100.2, 100.0, 99.8, 100.0, 99.5, 100.4, 100.0, 100.5, 100.8, 99.6, 100.2, 100.0, 99.7,  99.0, 105.0, 105.5],
    "high":  [100.5, 100.6, 100.4, 100.2, 100.3, 100.0, 100.7, 100.3, 100.9, 101.2, 100.0, 100.6, 100.4, 100.1, 99.5, 109.5, 106.0],
    "low":   [ 99.7,  99.8,  99.6,  99.4,  99.7,  99.1, 100.0,  99.7, 100.1, 100.4,  99.2,  99.8,  99.6,  99.3, 98.4, 104.0, 105.0],
    "close": [100.2, 100.3, 100.1,  99.9, 100.1,  99.6, 100.4, 100.0, 100.6, 100.9,  99.7, 100.3, 100.1,  99.8, 99.0, 109.0, 105.5],
}
df = pd.DataFrame(data)

flags = wide_ranging_day(df, lookback=14, k=2.0)
tr    = true_range(df)
print(f"Wide-ranging bars: {flags[flags].index.tolist()}")
print(f"True ranges:       {tr.round(2).tolist()}")
# Wide-ranging bars: [15] — the 5.5-point bar that dwarfs the prior 14
```

## Relationships

### Within Chapter 12

- **[[06_Bear_Trap]]** — Figure 12.13 explicitly stacks a wide-ranging up day onto a bear-trap low for confluence.
- **[[11_Island_Reversal_and_Spike_High]]** — Figure 12.17 lists "wide-ranging day" as one of *four* bearish patterns occurring on a single bar (along with bull trap, island reversal, spike high).
- **[[03_Stop_Placement_Quality]]** — return to either extreme of a wide-ranging day is a useful, defined level for placing stops or reversing trades.
- **[[08_Counter_to_Anticipated_Breakout]]** — a counter-breakout that *is itself* a wide-ranging day is a doubly-strong reversal signal.

### When does it work best?

Strongest as a **reversal** signal when:
- The bar forms at the **extreme of an extended trend**, not in the middle.
- The bar's direction is **opposite** the prevailing trend.
- A close near the bar's extreme (in the new direction) — i.e. not a doji-like wide-ranging day with a midway close.

As **continuation** confirmation, strongest when the bar forms on a fresh breakout from a consolidation.

### Outside the chapter

- **Chapter 5 — Chart Patterns.** Wide-ranging days are introduced there as one-day reversal patterns, alongside spike highs/lows and reversal days.
- **Chapter 11 — Failed Signals.** "Penetration of wide-ranging days" is a dedicated subsection (Figures 11.16–11.18) — return to the opposite extreme of a wide-ranging day flips its meaning.
- **Appendix.** The Volatility Ratio (VR) and Average True Range (ATR) provide the formal quantitative basis.
- **Chapter 9 — Stop-Loss Points.** Wide-ranging-day extremes are a Schwager-recommended stop reference.

## Source

- Schwager, *Getting Started in Technical Analysis*, Ch. 12, Figures 12.7, 12.13, 12.17
- Background: Ch. 5 — Chart Patterns; Ch. 11 — Penetration of Wide-Ranging Days; Glossary; Appendix (Volatility Ratio, ATR)
- Code: [`chapter12_concepts.py → wide_ranging_day(), true_range()`](code/chapter12_concepts.py)
- Image: [`09_wide_ranging_day.png`](images/09_wide_ranging_day.png)
