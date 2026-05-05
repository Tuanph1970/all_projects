# 05 — Bull Trap

## Definition

A **bull trap** is an upside breakout above a prior trading range or chart pattern that **fails almost immediately**, with prices reversing back into and then below the range. The breakout traps late buyers (who bought the breakout) and triggered short-stops, but **uncovers no additional buying** — a clear indication that the underlying technical picture is weak. Schwager treats confirmed bull traps as **among the most reliable indicators of major tops**.

Confirmation conditions (from Chapter 11, applied in Chapter 12):

- **Initial price confirmation** — pullback to the median of the prior consolidation.
- **Strong price confirmation** — pullback to or beyond the *opposite* (lower) boundary of the consolidation.
- **Time confirmation** — failure to revisit the breakout high within a specified time window (e.g. 4 weeks).

## Illustration

![[05_bull_trap.png]]

Figure 12.8 (October 1993 gold): a "confirmed bull-trap top" was Schwager's headline entry reason for going short, alongside a sustained downside gap, a wide-ranging down day, and a flag consolidation after the downswing. The trade rode a major decline.

## Analogy

A crowded elevator hits the top floor, the doors open into a flashy lobby, everyone surges forward — and the lobby is empty, the lights are off, and the floor is a thin sheet of ice. A few people slip in, then everybody scrambles back into the elevator and rides it down hard. The "top floor" looked like the destination, but the absence of anyone *being there* (no follow-through buying) tells you the entire trip up was the bait, not the goal.

## Numeric Example

October 1993 T-bond (Figure 11.2 / Figure 12.8 context):

| Event | Price | Read |
|---|---|---|
| Trading range over 7 weeks | 117.00 – 120.00 | Resistance |
| Mid-October breakout to record highs | **121.50** | Apparent bullish breakout |
| Within 5 trading days | back to 119.00 | Inside range — **initial confirmation** |
| Within 2 weeks | 116.50 | Below range low — **strong confirmation** |
| Six months later | 102.00 | Major bear market underway |

A short entered on the strong confirmation at 116.50 with a stop above 121.50 risks 5 points to make 14+ — a 1:3 R:R that won.

## Python

```python
from chapter12_concepts import detect_bull_trap
import pandas as pd

# A market that breaks out above 120 then collapses back through 117.
df = pd.DataFrame({
    "open":  [119.5, 120.2, 121.0, 121.4, 120.0, 118.0, 116.5, 115.0],
    "high":  [120.0, 120.8, 121.6, 121.8, 120.4, 118.5, 117.0, 115.5],
    "low":   [119.0, 119.5, 120.5, 120.0, 117.5, 115.5, 115.0, 113.0],
    "close": [119.8, 120.4, 121.5, 120.5, 118.0, 116.5, 115.5, 113.5],
})

traps = detect_bull_trap(df, range_high=120.0, range_low=117.0, lookforward=5)
print(traps.tolist())
# bar 2 (close 121.5) flagged — break above 120 followed by close below median 118.5
```

## Relationships

### Within Chapter 12

- **[[06_Bear_Trap]]** — exact mirror image at market bottoms.
- **[[01_Primary_Premise_Violation]]** — a bull trap is, from the long's perspective, a definitive premise violation.
- **[[08_Counter_to_Anticipated_Breakout]]** — same family of "failed signal" trades; the bull trap is specifically a failed *range* breakout, while counter-to-anticipated typically describes flag/pennant failures.
- **[[09_Wide_Ranging_Day]]** — a wide-ranging *down* day immediately after a new high greatly strengthens the bull-trap reading (Figure 12.8 explicitly stacks both signals).

### When does it work best?

Most reliable when:
1. The prior trading range is **broad and well-established** (multiple weeks).
2. The breakout occurs into **record highs** or after an extended advance.
3. The reversal back into the range is **fast** (days, not months).

Less reliable on small intraday range breaks where noise dominates structure.

### Outside the chapter

- **Chapter 11 — The Most Important Rule.** Bull traps are the flagship example of Schwager's "failed signals are the most reliable signals" thesis.
- **Chapter 4 — Trading Ranges and Support/Resistance.** Bull traps are conceptually the *failure mode* of standard range breakouts. Understanding the latter is required to recognize the former.
- **Chapter 17 — 82 Trading Rules** (rule 56): "A breakout to new highs or lows followed within the next week or two by a gap back into the range is a particularly reliable form of a bull trap or bear trap."

## Source

- Schwager, *Getting Started in Technical Analysis*, Ch. 12, Figures 12.2, 12.8
- Background: Ch. 11 — Bull and Bear Traps (Figures 11.1–11.5)
- Code: [`chapter12_concepts.py → detect_bull_trap()`](code/chapter12_concepts.py)
- Image: [`05_bull_trap.png`](images/05_bull_trap.png)
