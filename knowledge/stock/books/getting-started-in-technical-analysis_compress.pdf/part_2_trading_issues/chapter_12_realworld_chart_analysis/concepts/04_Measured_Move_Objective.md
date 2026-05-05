# 04 — Measured Move Objective (MM)

## Definition

A **measured move** is a price-projection technique that assumes the *next* leg of a trend will be approximately the same size as the *prior* leg. After an up-leg from a swing low to a swing high, followed by a corrective pullback, the projected upside target is:

> `MM target = pullback low + (swing high − swing low)`

Schwager uses the MM as an **exit aid**, not a hard target. When price approaches an MM objective, two responses are appropriate:

1. **Tighten the stop** very close (Figure 12.8 — gold).
2. **Liquidate on the first sign of failure** (Figure 12.4 — British pound, Figure 12.14 — unleaded gas).

Multiple MM projections that **near-coincide** at the same price zone (Figure 10.3 in the book) make that zone a much higher-probability target.

## Illustration

![[04_measured_move_objective.png]]

The first leg's height is laid off from the pullback low to project where the second leg should reach. In Schwager's chapter-10 crude-oil example, three different measured moves all clustered just below the actual market top — high-conviction confluence.

## Analogy

You watch a child take a running jump from a curb and clear roughly two sidewalk squares. They land, brace, and run again from the same speed. A reasonable bet for the second jump is also about two squares — roughly equal effort, roughly equal distance. They might clear three squares (overshoot) or only one and a half (failure), but two is the natural anchor for what to expect. A measured move is the same: the market's prior leg is the running jump; the pullback is the brace; the projection is "about that far again."

## Numeric Example

September 1994 unleaded gas (Figure 12.14):

| Leg | From | To | Size |
|---|---|---|---|
| Up-leg A | 50.00¢ | 60.00¢ | +10.00¢ |
| Pullback | 60.00¢ | 56.00¢ | −4.00¢ |
| **MM projected target** | 56.00¢ | **66.00¢** | +10.00¢ |
| Actual | 56.00¢ | ~65.50¢ | reached MM zone, then failed |

When price reached 65.50¢ — within striking distance of the 66.00¢ MM target — a flag formed. The counter-to-anticipated breakdown of that flag triggered the exit very close to the high.

## Python

```python
from chapter12_concepts import measured_move_target

# Up-leg: 50 → 60. Pullback low: 56.
target_up = measured_move_target(
    swing_low=50.0, swing_high=60.0, pullback_low=56.0, direction="up"
)
print(f"Upside MM target: {target_up}")          # 66.0

# Multiple MMs forming a confluence zone
mms = [
    measured_move_target(50, 60, 56, "up"),       # 66.0
    measured_move_target(53, 62, 58, "up"),       # 67.0
    measured_move_target(55, 63, 59, "up"),       # 67.0
]
print(f"MM cluster: {mms}")
print(f"Confluence near: {sum(mms)/len(mms):.1f}")
```

## Relationships

### Within Chapter 12

- **[[03_Stop_Placement_Quality]]** — when an MM is reached, the typical action is to *tighten the stop dramatically* rather than exit outright (Figure 12.8).
- **[[08_Counter_to_Anticipated_Breakout]]** — the MM tells you *where* to be alert; the counter-breakout tells you *when* to act.
- **[[10_Trailing_Stop]]** — at the MM zone, the trailing distance can legitimately collapse to a tighter band.

### When does it work best?

Best in **trending markets with clean leg structure** — moves that have a clear push, a defined corrective pullback, and a resumption. It does **not** work well in choppy ranges where there is no real "leg" to measure, or after climactic blow-off moves where momentum overshoots dramatically.

### Outside the chapter

- **Chapter 5 — Chart Patterns.** Many patterns (flags, pennants, head-and-shoulders) carry their own measured-move rules. The general MM logic in Chapter 12 is a superset.
- **Chapter 10 — Setting Objectives.** This is where the MM concept is formally introduced. Chapter 12 shows it in live action.
- **Chapter 11 — Most Important Rule.** When an MM is reached and *fails* (counter-to-anticipated price action immediately follows), that failure is itself a high-quality reversal signal.

## Source

- Schwager, *Getting Started in Technical Analysis*, Ch. 12, Figures 12.4, 12.7, 12.8, 12.14
- Background: Ch. 10 — Setting Objectives
- Code: [`chapter12_concepts.py → measured_move_target()`](code/chapter12_concepts.py)
- Image: [`04_measured_move_objective.png`](images/04_measured_move_objective.png)
