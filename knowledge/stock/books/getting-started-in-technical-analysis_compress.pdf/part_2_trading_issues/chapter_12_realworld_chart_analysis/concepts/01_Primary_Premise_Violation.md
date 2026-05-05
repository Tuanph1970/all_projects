# 01 — Primary Premise Violation

## Definition

A **primary premise** is the specific technical reason for entering a trade — for example, *"prices broke out above a triangular consolidation, implying continuation of the bull move."* A **primary premise violation** occurs when subsequent price action contradicts that reason. Schwager's rule is absolute: **once the primary premise of a trade is violated, the position must be liquidated** — regardless of whether you currently have a profit, a loss, or a stop-loss order in place.

The premise is not "I think it's going up." The premise is the chart structure that *makes* it go up. When the structure breaks, your reason is gone.

## Illustration

![[01_primary_premise_violation.png]]

Schwager's Figure 12.1 shows a December 1993 T-bond trade entered on a triangle breakout. When prices broke meaningfully *below* the lower triangle boundary, the original breakout signal became invalid and the trade had to be liquidated immediately.

## Analogy

You buy an umbrella because the forecast says rain. Halfway to the bus stop, the sun comes out, the radar app shows clear skies for the rest of the day, and you're still carrying it. The right move is not to keep walking with the umbrella in case it rains again — it's to put it back in the bag. **The reason you grabbed it has disappeared.** Holding a position after its premise is violated is the same: you're carrying weight for a forecast that no longer exists.

## Numeric Example

| Step | Price | Action |
|---|---|---|
| Triangle range | 101.5 – 104.5 | Pattern forms |
| Upside breakout | 105.0 | **Buy long** at 105 — premise = breakout continuation |
| Pullback | 103.5 | Still inside upper triangle area — premise intact |
| Breakdown close | **101.0** | Premise **violated** — exit at 101 |
| Loss | **−4 points** | Small loss locked in |
| Continuing decline | 92.0 | Procrastination would have cost −13 points |

A 4-point loss vs. a 13-point loss is the entire difference between staying in business and not.

## Python

```python
from chapter12_concepts import premise_violated
import pandas as pd

# Long entered on a breakout above the 104.5 triangle high.
# Invalidation: a daily close below the lower triangle boundary at 101.5.
prices = pd.DataFrame({
    "open":  [105.0, 104.2, 103.8, 103.5, 102.0, 100.8, 100.0],
    "high":  [105.5, 104.8, 104.0, 103.9, 102.4, 101.5, 100.5],
    "low":   [104.5, 103.5, 103.0, 102.2, 100.6,  99.8,  99.0],
    "close": [104.8, 103.9, 103.2, 102.5, 101.0, 100.0,  99.2],
})

violated = premise_violated(prices, invalidation_level=101.5, direction="long")
exit_idx = violated.idxmax() if violated.any() else None
print(f"Exit on bar {exit_idx} at close {prices.loc[exit_idx, 'close']}")
# Exit on bar 4 at close 101.0
```

## Relationships

### Within Chapter 12

- **[[02_Market_vs_Limit_Orders]]** — once the premise is violated, never use a limit exit; the market doesn't owe you a better price.
- **[[03_Stop_Placement_Quality]]** — the stop should sit just beyond the level whose break would invalidate the premise. They are two sides of the same coin: the premise tells you *where* the stop must go.
- **[[06_Bear_Trap]]** / **[[05_Bull_Trap]]** — a trap is, by definition, a premise violation of someone else's breakout trade.
- **[[08_Counter_to_Anticipated_Breakout]]** — the canonical premise violator for flag/pennant trades.

### When does it work best?

Best on trades with **a single, sharp invalidation level** (triangle break, flag boundary, prior swing low). Works less cleanly on trades whose premise is diffuse — e.g. "prices look overextended" — because there is no precise level to anchor to.

### Outside the chapter

- **Chapter 11 — Failed Signals.** A failed signal *is* a premise violation observed from the other side. Failed breakouts, false trend-line breaks, and traps are all premise-violation events.
- **Chapter 9 — Stop-Loss Points.** Schwager's "logical stop placement" is exactly the price level that, if hit, says the premise is wrong.
- **Chapter 16 — Planned Trading Approach.** The trader's diary forces you to *write the premise down at entry*, which is what makes premise-violation discipline possible.
- **Chapter 18 — Market Wizardry.** "When the market goes against you, get out" is the same rule expressed at the personal-discipline level.

## Source

- Schwager, *Getting Started in Technical Analysis*, Ch. 12, Figure 12.1 (p. 181–182)
- Code: [`chapter12_concepts.py → premise_violated()`](code/chapter12_concepts.py)
- Image: [`01_primary_premise_violation.png`](images/01_primary_premise_violation.png)
