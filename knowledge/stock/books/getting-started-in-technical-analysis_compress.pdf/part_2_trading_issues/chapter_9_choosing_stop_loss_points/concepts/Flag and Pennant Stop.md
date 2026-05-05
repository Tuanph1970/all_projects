---
title: "Flag and Pennant Stop"
chapter: 9
concept_number: 5
tags: [concept/stop-placement, continuation-pattern, flag, pennant]
related: [[Trading Range Stop]], [[Wide-Ranging Day Stop]]
---

# Flag / Pennant Stop

## 📖 Definition
After a breakout from a **flag** (parallel-bounded short consolidation) or **pennant** (small symmetrical-triangle consolidation), a return of price back to the *opposite end* of the pattern — or beyond — is treated as a reversal signal. The stop is therefore placed at (or just past) that opposite boundary. Flags and pennants are continuation patterns; if they "fail backward," the assumed continuation is no longer valid.

## 🖼️ Illustration
![[flag_pennant_stop.svg]]

## 🥚 Simple Analogy
A flag pattern is like **a runner pausing to retie their shoelaces mid-race**. Once they stand back up and start sprinting again (the breakout), you expect them to keep running. If, instead, they sit *back down* on the curb in the exact spot they were tying their shoes — something is wrong, the race is over for them. The curb is your stop.

## 🔢 Numeric Example
- Stock rallies from $30 → $40 (the "flag pole")
- Consolidates in a tight downward-sloping flag: high $40, low **$38.50**
- Upside breakout, position bought at **$40.30**
- Sell stop placed at **$38.40** (just below the flag's lower boundary)
- Risk per share = $1.90 — small because flags are small patterns

## 💻 Python Code
```python
# /code/flag_pennant_stop.py
"""Detect a simple flag (parallel channel) and emit a breakout entry plus stop."""
import numpy as np
from dataclasses import dataclass

@dataclass
class FlagStop:
    flag_high: float
    flag_low: float
    flagpole_start: float   # where the flagpole began
    flagpole_top: float     # where the flag began

    def is_valid_flag(self) -> bool:
        # Flag should retrace only a small fraction of the pole
        pole = self.flagpole_top - self.flagpole_start
        retracement = self.flagpole_top - self.flag_low
        return 0 < retracement / pole < 0.50  # < 50 % retrace = healthy flag

    def upside_entry(self) -> float:
        return self.flag_high * 1.001       # break + tick

    def upside_stop(self) -> float:
        return self.flag_low * 0.999        # opposite end

    def risk_per_share(self) -> float:
        return self.upside_entry() - self.upside_stop()


if __name__ == "__main__":
    f = FlagStop(flag_high=40.0, flag_low=38.5,
                 flagpole_start=30.0, flagpole_top=40.0)
    if f.is_valid_flag():
        print(f"Entry  : ${f.upside_entry():.2f}")
        print(f"Stop   : ${f.upside_stop():.2f}")
        print(f"Risk/sh: ${f.risk_per_share():.2f}")
    else:
        print("Not a healthy flag; skip the trade.")
```

## 🔗 Within-Chapter Relationships
- Same logical family as [[Trading Range Stop]] and [[Wide-Ranging Day Stop]]: *"if the breakout reverses all the way back, the breakout was wrong."*
- Tighter than a [[Trading Range Stop]] because flags/pennants are small patterns.
- More structured than a [[Money Stop]] — it pegs to *meaningful* price levels.
- Often morphs into a [[Trailing Stop]] once the post-flag move makes new highs.

### When does this concept "work well"?
| Situation | Effective? |
|---|---|
| Strong, fast prior trend with a brief consolidation | ✅ Ideal — the textbook case |
| Long, drifting consolidation (>4 weeks) | ❌ It's not a flag any more — treat as a range |
| Flag whose retracement is >50% of the pole | ⚠️ Likely a reversal, not a continuation |
| Very volatile stock | ⚠️ Stop will be hit on noise; widen or pass |

## 🌐 Cross-Chapter Relationships
- **Chapter 5 — Chart Patterns** — defines flags and pennants as continuation patterns.
- **Chapter 8 — Midtrend Entry** — flag breakouts are explicitly mentioned as a valid midtrend entry trigger; this stop technique is the matching exit logic.
- **Chapter 12 — Real-World Chart Analysis** — illustrative trades show flag/pennant stops in practice.

## 📌 Key Takeaway
Flags are *promises of continuation*. The flag's opposite boundary is where that promise breaks. Place your stop there.
