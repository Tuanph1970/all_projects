# 07 — Flag and Pennant Continuation

## Definition

A **flag** is a tight, short-duration price consolidation (typically 1–3 weeks) that forms after a sharp directional move — the "pole." It usually drifts slightly *against* the prior trend (a flag pointing down after an up-move). A **pennant** is the same idea with **converging** boundaries instead of parallel ones — a small symmetric triangle. Both are **continuation patterns**: in the great majority of cases, the breakout from the flag/pennant is in the **same direction** as the pole.

Schwager's Chapter 12 leans heavily on flags as both **entry triggers** (buy near the flag's lower boundary in an uptrend) and **structural anchors** for stops, exits, and reversal logic. The flag's two boundaries, plus the pole's measured-move projection, define the entire trade.

## Illustration

![[07_flag_pennant.png]]

The pole is the strong directional thrust; the flag is the brief consolidation; the continuation is the next leg, which typically projects roughly the size of the pole from the flag's breakout point.

## Analogy

A sprinter mid-race takes a shallow breath without breaking stride — the rhythm pauses, the body decelerates fractionally, the legs reset, then the same speed resumes. The pause is not weakness; it is recovery inside an existing motion. A flag is exactly that visible-on-chart breath: prices tighten, hold, and then resume the same direction at the same intensity.

## Numeric Example

September 1994 unleaded gas (Figure 12.14):

| Element | Value |
|---|---|
| Pole low → pole high | 50.0¢ → 60.0¢ |
| Pole size | +10.0¢ |
| Flag range (sideways consolidation) | 56.0¢ – 60.0¢ |
| **Entry near flag low** | 56.5¢ |
| Stop just below flag low | 55.0¢ (risk = 1.5¢) |
| Continuation projection | 56.5¢ + 10.0¢ ≈ 66.5¢ |
| Reward potential | +10.0¢ |
| Risk:Reward | **1 : 6.7** |

This is the asymmetric payoff that makes flag-buying viable even at win rates near or below 50%.

## Python

```python
from chapter12_concepts import detect_flag
import pandas as pd

# Pole 50→60, then a sideways flag at ~57.
n_pole, n_flag = 8, 8
poles = [50, 51.5, 53, 54.5, 56, 57.5, 59, 60]
flags = [59.5, 58.8, 57.5, 57.3, 57.8, 58.0, 57.2, 57.6]

df = pd.DataFrame({
    "open":  [p - 0.1 for p in poles + flags],
    "high":  [p + 0.4 for p in poles + flags],
    "low":   [p - 0.4 for p in poles + flags],
    "close": poles + flags,
})

flag = detect_flag(df, pole_bars=n_pole, flag_bars=n_flag)
print(flag)
# {'direction': 'up', 'flag_high': ~59.9, 'flag_low': ~56.8, 'pole_size': 10.0}
```

## Relationships

### Within Chapter 12

- **[[03_Stop_Placement_Quality]]** — flags evolve and tolerate one-day spikes; stops must sit *meaningfully* beyond the flag boundary, not on it.
- **[[04_Measured_Move_Objective]]** — every flag implies an MM target equal to the pole, projected from the flag's breakout point.
- **[[08_Counter_to_Anticipated_Breakout]]** — when a flag breaks out *opposite* to the pole, the trade premise is invalidated and the *failure* itself becomes the new signal, often a major reversal.
- **[[12_Expected_Gain_per_Trade]]** — Figure 12.9 explicitly uses flag-near-range-low as the example pattern that needs only to capture occasional big winners to be net profitable.

### When does it work best?

Best when:
- **Flag forms near a structural extreme** — flag near top of broad range = bullish; flag near bottom = bearish (rules 49, 52, 57 in Chapter 17).
- **Pole was strong and recent** — sharp, well-defined thrust; not a drift.
- **Flag is short** — under ~3 weeks; longer consolidations behave more like ranges than flags.
- **Volume contracts during the flag** (not directly in this chapter but standard).

Less reliable when the prior move was choppy or the flag drags on for many weeks.

### Outside the chapter

- **Chapter 5 — Chart Patterns.** Flags and pennants are formally introduced there as continuation patterns.
- **Chapter 11 — Failed Signals.** "Counter-to-anticipated breakout of flag or pennant" gets its own dedicated section; Chapter 12 is full of these in action (Figures 12.6/12.7, 12.9, 12.14, 12.15, 12.18).
- **Chapter 17 — Trading Rules.** Rules 49, 52, 57 codify the flag-near-extreme-of-range pattern.

## Source

- Schwager, *Getting Started in Technical Analysis*, Ch. 12 — appears in Figures 12.5, 12.10, 12.11, 12.14, 12.18, 12.19
- Background: Ch. 5 — Chart Patterns
- Code: [`chapter12_concepts.py → detect_flag()`](code/chapter12_concepts.py)
- Image: [`07_flag_pennant.png`](images/07_flag_pennant.png)
