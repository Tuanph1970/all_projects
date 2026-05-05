# 08 — Counter-to-Anticipated Breakout

## Definition

A **counter-to-anticipated breakout** is a breakout from a continuation pattern (flag, pennant, narrow consolidation) that goes in the **opposite direction** of the move that preceded the pattern. Because flags and pennants are *expected* to resolve in the direction of the prior thrust, a breakout in the wrong direction is a strong **failed-signal** event. Schwager treats counter-to-anticipated breakouts as both:

1. **Exit signals** for trades whose premise was the expected continuation (Figures 12.5, 12.6, 12.9, 12.10, 12.14, 12.15, 12.18).
2. **Reversal-entry signals** in the opposite direction (Figure 12.7 — counter-break of a bear consolidation triggers a long; Figure 12.13 — failure of the prior short triggers a long).

This is the live application of Chapter 11's "the most important rule": the failure of a high-probability signal is itself a higher-probability signal.

## Illustration

![[08_counter_to_anticipated.png]]

A narrow consolidation forming after a steep downswing should resolve down. When it instead breaks *up*, the original trade premise is dead and a new opposite-direction premise is born.

## Analogy

You're at a dinner party where someone keeps telling a long anecdote that's clearly building toward a punch line. You can predict the rhythm of the joke. Then the storyteller stops, sets down the wine glass, and admits "actually, that's not what happened at all" — and the real story is the opposite. The unexpected reversal is more informative than any confirmation of the predicted ending would have been: it tells you the *whole framing* you were holding was wrong, and the new framing is now the operative reality.

## Numeric Example

March 1995 deutsche mark (Figures 12.6 → 12.7):

| Sequence | Setup | Action | Outcome |
|---|---|---|---|
| Initial trade | Narrow consolidation after steep down-move | **Short** at consolidation low ~64.0 | Entry premise = continuation |
| Counter-breakout | Prices break **up** out of consolidation | **Cover short** + **reverse to long** at ~64.5 | Same event closes one trade and opens another |
| Subsequent | Wide-ranging up day forms near the relative low | Confirms reversal | Long ridden to MM target |

The same price tick (the upside breakout) was simultaneously: (a) the stop on the short, (b) the premise violator, and (c) the entry for the long. **One event, three roles.**

## Python

```python
from chapter12_concepts import detect_flag, counter_to_anticipated_breakout
import pandas as pd

# Down-pole then a tight consolidation, then a counter-to-anticipated upside break.
poles = [70, 68.5, 67.0, 66.0, 65.0, 64.5, 64.2, 64.0]            # bear pole
flags = [64.2, 64.5, 64.0, 63.8, 64.2, 64.6, 64.4, 64.5]          # tight flag
df = pd.DataFrame({
    "open":  [p - 0.1 for p in poles + flags],
    "high":  [p + 0.3 for p in poles + flags],
    "low":   [p - 0.3 for p in poles + flags],
    "close": poles + flags,
})
flag = detect_flag(df, pole_bars=8, flag_bars=8, pole_min_pct=0.04, flag_max_pct=0.03)
print("Detected flag:", flag)

# Now a new bar closes ABOVE the flag's high → counter-to-anticipated breakout
latest_close = (flag["flag_high"] + 0.5) if flag else None
signal = counter_to_anticipated_breakout(flag, latest_close)
print(f"Latest close {latest_close:.2f} → signal: {signal}")
# Detected flag: {'direction': 'down', ...}
# Latest close ~65.x → signal: counter_breakout_up
```

## Relationships

### Within Chapter 12

- **[[01_Primary_Premise_Violation]]** — the counter-breakout *is* the premise violator for any continuation-based trade.
- **[[05_Bull_Trap]]** / **[[06_Bear_Trap]]** — same family of failed-signal events; traps fail *range* breakouts, counter-to-anticipated fails *flag/pennant* breakouts.
- **[[07_Flag_and_Pennant_Continuation]]** — this concept is the failure mode of that one. They are unintelligible apart.
- **[[09_Wide_Ranging_Day]]** — when the counter-breakout *is itself* a wide-ranging day, the signal is meaningfully strengthened.

### When does it work best?

Strongest when:
1. The flag/pennant formed at a **structural extreme** — near a major support or resistance, or after an extended trend (the move is overdue to fail).
2. The **counter-breakout is decisive** — a clean close beyond the opposite boundary, ideally with size (a wide-ranging day).
3. A **measured move had already been achieved or nearly achieved** before the counter-break (Figure 12.14).

Less reliable on continuation patterns formed in the middle of clean, young trends — those usually do continue.

### Outside the chapter

- **Chapter 11 — The Most Important Rule.** This concept is given a full section there (Figures 11.19–11.21).
- **Chapter 5 — Chart Patterns.** You must understand the *expected* breakout direction (Chapter 5) to recognize the *unexpected* one (Chapter 11/12).
- **Chapter 14 — Confirmation Rules.** A "counter-to-anticipated" rule is the inverse of a confirmation rule — both insist on real penetration before acting.
- **Chapter 17 — Trading Rules.** "When the market doesn't behave as expected, get out" — and, frequently, reverse.

## Source

- Schwager, *Getting Started in Technical Analysis*, Ch. 12 — Figures 12.6, 12.7, 12.9, 12.10, 12.14, 12.15, 12.18
- Background: Ch. 11 — "Counter-to-Anticipated Breakout of Flag or Pennant" (Figures 11.19–11.21)
- Code: [`chapter12_concepts.py → counter_to_anticipated_breakout()`](code/chapter12_concepts.py)
- Image: [`08_counter_to_anticipated.png`](images/08_counter_to_anticipated.png)
