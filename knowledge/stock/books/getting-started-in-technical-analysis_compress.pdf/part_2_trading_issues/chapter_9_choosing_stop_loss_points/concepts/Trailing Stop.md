---
title: "Trailing Stop"
chapter: 9
concept_number: 9
tags: [concept/stop-placement, trailing-stop, profit-protection]
related: [[Stop-Loss Liquidation Point]], [[Relative High Low Stop]], [[Money Stop]]
---

# Trailing Stop

## 📖 Definition
A **trailing stop** is a protective stop that is *raised* (for longs) or *lowered* (for shorts) as the market moves in the direction of the trade. Its purpose is dual: limit losses while the trade is unprofitable, and **protect open profits** once the trade is winning.

Three common ways to define the "trailing rule":
1. **Pivot-based** — re-anchor the stop to each new [[Relative High Low Stop|relative low]] (or relative high) that forms.
2. **Fixed-dollar** — keep a constant dollar/percent distance below the highest closing price.
3. **Percentage** — keep the stop a fixed percentage below the highest close (e.g., 8 %).

**Iron rule:** a trailing stop is only ever **moved in one direction** — the direction that *reduces* risk. Loosening it is the [[CIC Anti-Pattern]].

## 🖼️ Illustration
![[trailing_stop.svg]]

## 🥚 Simple Analogy
A trailing stop is like the **safety harness on a rock-climber's rope**. As the climber goes up, they keep clipping into anchors *higher up the wall*, never lower. If they slip, they fall only as far as the *most recent* anchor — not all the way to the ground. They never unclip a higher anchor and reattach to a lower one; that would defeat the entire purpose.

## 🔢 Numeric Example
Long entry at $50, pivot-based trailing rule (relative low with N = 10 bars):

| Event | New high | New relative low | Trailing stop |
|---|---|---|---|
| Initial entry | $50 | (Oct low) $46 | **$46** |
| Dec rally to new highs | $58 | Dec low $52 | raised to **$52** |
| Mar rally to new highs | $65 | Mar low $58 | raised to **$58** |
| Apr rally to new highs | $72 | Apr low $64 | raised to **$64** |
| May decline below $64 | — | — | **stopped out at $64** ⇒ profit $14/share |

Without the trailing stop, the trader might have given back the entire move.

## 💻 Python Code
```python
# /code/trailing_stop.py
"""Pivot-based trailing stop for a long position."""
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TrailingStop:
    initial_stop: float
    n: int = 10                                # bars on each side defining a pivot
    current_stop: float = field(init=False)
    pivot_low_history: List[float] = field(default_factory=list)
    high_water_mark: float = field(default=float('-inf'))

    def __post_init__(self):
        self.current_stop = self.initial_stop

    def _is_relative_low(self, lows: List[float], i: int) -> bool:
        if i < self.n or i + self.n >= len(lows):
            return False
        window = lows[i - self.n : i + self.n + 1]
        return lows[i] == min(window) and window.count(lows[i]) == 1

    def update(self, lows: List[float], highs: List[float]) -> None:
        """Call after each new bar; only raises stop, never lowers it."""
        if highs:
            self.high_water_mark = max(self.high_water_mark, max(highs))
        for i in range(len(lows) - self.n - 1, len(lows)):
            if self._is_relative_low(lows, i):
                pivot = lows[i]
                if pivot > self.current_stop and self.high_water_mark > pivot:
                    self.current_stop = pivot
                    self.pivot_low_history.append(pivot)

    def stopped_out(self, current_close: float) -> bool:
        return current_close < self.current_stop


if __name__ == "__main__":
    # Synthetic up-trend with successively higher pivot lows
    lows  = [46,47,48,49,50,46,48,49,50,51,52,53,54,52,53,54,55,56,57,58,
             59,58,57,56,58,60,62,64,66,65,64,66,68,70,68,67,66,65,64,63]
    highs = [v + 2 for v in lows]
    ts = TrailingStop(initial_stop=46.0, n=5)
    ts.update(lows, highs)
    print("Pivot history:", ts.pivot_low_history)
    print(f"Current stop: ${ts.current_stop:.2f}")
    print("Stopped out today?", ts.stopped_out(current_close=lows[-1]))
```

## 🔗 Within-Chapter Relationships
- The **dynamic** counterpart to every static stop in this chapter: a [[Trend Line Stop]], [[Trading Range Stop]], or [[Relative High Low Stop]] is the *initial* anchor; once profits accumulate, those static levels are *replaced* by trailing levels.
- A [[Money Stop]] can also be trailed (fixed-dollar trailing stop), trading technical meaning for predictable risk.
- The opposite of the [[CIC Anti-Pattern]] — a trailing stop is the disciplined version of "managing the stop."

### When does this concept "work well"?
| Situation | Effective? |
|---|---|
| Strong trending market | ✅ Captures most of the move with limited drawdown |
| Choppy / range-bound market | ❌ Stop is hit by every reaction |
| After a major reward/risk milestone has been reached | ✅ Locks in profit while leaving upside open |
| Markets prone to sharp single-day reversals | ⚠️ Use closer trail or scale out partial profits |

## 🌐 Cross-Chapter Relationships
- **Chapter 10 — Setting Objectives** — Schwager argues trailing stops are usually *better than fixed objectives* for exiting profitable trades, because they let big winners run.
- **Chapter 17** — Rule #33: prefer trailing stops to objectives. Rule #32: convert a favorable gap into the next trailing stop level.
- **Chapter 14 — Trading Systems** — automated trend-following systems essentially codify a trailing stop as the trade-exit rule.

## 📌 Key Takeaway
The first job of a stop is to **limit losses**. The second job — equally important — is to **protect profits**. A trailing stop lets one rule do both jobs over the life of the trade.
