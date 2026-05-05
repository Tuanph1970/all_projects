# 10 — Trailing Stop

## Definition

A **trailing stop** is a stop-loss level that **moves in the direction of the trade as the position becomes profitable**, but never against. For a long, the stop ratchets *up* with each new high; it never moves down. For a short, it ratchets down with each new low. The result is that profits are locked in progressively while the position remains free to capture additional gains as long as the trend holds.

Schwager calls trailing stops "among the least glamorous, but most sensible" methods of determining trade exits (Chapter 11). In Chapter 12 they appear as the actual exit mechanism in Figure 12.13 (the crude-oil long that captured the bulk of a major rally) and as the protective tool referenced for trade management throughout. Two practical refinements appear:

1. After a measured-move objective is achieved, the trail can legitimately tighten dramatically to lock in the bulk of profits (Figure 12.8).
2. To avoid premature exits, **don't tighten the trail closer than break-even for the first ~2 weeks** of the trade (Figure 12.16 lesson).

## Illustration

![[10_trailing_stop.png]]

The stop line stair-steps upward beneath the rising price, never retreats, and finally clips a deep pullback — by then the bulk of the move has been banked.

## Analogy

You're hiking up a mountain trail and you keep dropping small flagged sticks behind you, but you never move one *back* down — only forward as you climb higher. If you slip and fall, you slide only as far as the most recent flag, not all the way to the trailhead. The flags don't help you climb, but they bound your downside while letting you go as far up as your legs can take you.

## Numeric Example

Long entered at 22.00. Trailing distance set at 1.50 points.

| Day | Close | Running max | Trailing stop | Action |
|---|---|---|---|---|
| 1 | 22.00 | 22.00 | 20.50 | Hold |
| 5 | 24.00 | 24.00 | 22.50 | Stop ratchets up |
| 10 | 26.00 | 26.00 | 24.50 | Locks in profit |
| 14 | 25.50 | 26.00 | 24.50 | Stop **does not** move down |
| 18 | 28.00 | 28.00 | 26.50 | Locks in more |
| 22 | 26.40 | 28.00 | 26.50 | **Stop hit** — exit at 26.50 |

Net: entered at 22.00, exited at 26.50 → +4.50 points captured automatically without any subjective exit decision.

## Python

```python
from chapter12_concepts import trailing_stop
import pandas as pd

prices = pd.Series([22, 22.4, 23.0, 23.6, 24.0, 24.5, 25.2, 25.8,
                    26.0, 25.6, 25.4, 26.2, 27.0, 27.8, 28.0,
                    27.5, 26.8, 26.4])

stop_line = trailing_stop(prices, distance=1.5, side="long")
hit = (prices < stop_line)
exit_idx = hit.idxmax() if hit.any() else None

print(stop_line.round(2).tolist())
print(f"Exit on bar {exit_idx} at price {prices.iloc[exit_idx]} "
      f"with stop {stop_line.iloc[exit_idx]:.2f}")
```

## Relationships

### Within Chapter 12

- **[[03_Stop_Placement_Quality]]** — the same too-tight risk applies to trails. The 2-week-no-tighter-than-breakeven rule is the chapter's compromise.
- **[[04_Measured_Move_Objective]]** — when an MM is reached, a previously generous trail can rationally collapse to near the most recent swing.
- **[[01_Primary_Premise_Violation]]** — a trail is one mechanism; premise-violation exits are another. They coexist: take whichever fires first.

### When does it work best?

Best in **strong, sustained trends** with low whipsaw — long-duration moves in trending instruments. Worst in **range-bound markets**, where every routine pullback hits the stop before any meaningful profit can accumulate. The volatility regime matters more than the specific trail formula.

### Outside the chapter

- **Chapter 9 — Choosing Stop-Loss Points.** Trailing stops are introduced and detailed there.
- **Chapter 10 — Setting Objectives.** The chapter explicitly contrasts trailing stops vs. fixed objectives — the trail "comes closest to the ideal of letting a profitable trade run its course."
- **Chapter 14 — Trading Systems.** Most trend-following systems have a trailing-stop component (e.g. Chandelier exit, parabolic SAR, channel exits).
- **Appendix — ATR.** ATR-based trail distance is a standard adaptive form: trail = recent_high − k·ATR.

## Source

- Schwager, *Getting Started in Technical Analysis*, Ch. 12, Figures 12.13, 12.16
- Background: Ch. 9 — Stop-Loss Points; Ch. 10 — Setting Objectives
- Code: [`chapter12_concepts.py → trailing_stop()`](code/chapter12_concepts.py)
- Image: [`10_trailing_stop.png`](images/10_trailing_stop.png)
