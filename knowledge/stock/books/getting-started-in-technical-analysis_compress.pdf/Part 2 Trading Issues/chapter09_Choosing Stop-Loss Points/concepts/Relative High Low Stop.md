---
title: "Relative High Low Stop"
chapter: 9
concept_number: 7
tags: [concept/stop-placement, swing-point, pivot]
related: [[Trailing Stop]], [[Trend Line Stop]], [[Money Stop]]
---

# Relative High / Relative Low Stop

## 📖 Definition
A **relative low** is a bar whose low is below the lows of the *N* bars before it and the *N* bars after it (the mirror definition holds for a relative high). For a long position, the **most recent relative low** is a natural stop point: a close beneath that swing pivot says the structure of higher-lows is broken.

The choice of *N* is somewhat arbitrary, but a sensible range is roughly **5–15 bars on each side**. Smaller *N* finds more (smaller) pivots; larger *N* finds fewer (more meaningful) pivots.

## 🖼️ Illustration
![[relative_high_low_stop.svg]]

## 🥚 Simple Analogy
Climbing a staircase, you can always glance back at **the last step you stood on**. As long as you're above it, you're still going up. The moment your foot drops back below that last step, the climb has paused — or reversed. The most recent relative low is just "the last step you stood on."

## 🔢 Numeric Example
- Stock makes successive higher relative lows at **$45, $48, $51** as it rallies
- After printing $51, price moves up to $56 — current position is long from $54
- Most recent relative low = **$51**
- Stop = a close below $51, with N=10 bars on each side
- Risk per share = $54 − $51 = **$3**
- If $51 breaks on a closing basis, the higher-low structure has failed and the long is exited

## 💻 Python Code
```python
# /code/relative_high_low_stop.py
"""Detect relative lows / highs and produce a stop level for a long position."""
from typing import List, Optional

def find_relative_lows(lows: List[float], n: int = 10) -> List[int]:
    """Return indices of bars that are relative lows with n bars on each side."""
    pivots = []
    for i in range(n, len(lows) - n):
        window = lows[i - n : i + n + 1]
        if lows[i] == min(window) and window.count(lows[i]) == 1:
            pivots.append(i)
    return pivots

def most_recent_relative_low(lows: List[float], n: int = 10) -> Optional[int]:
    pivots = find_relative_lows(lows, n=n)
    return pivots[-1] if pivots else None

def stop_level(lows: List[float], n: int = 10,
               buffer_pct: float = 0.002) -> Optional[float]:
    idx = most_recent_relative_low(lows, n=n)
    if idx is None:
        return None
    return lows[idx] * (1 - buffer_pct)


if __name__ == "__main__":
    # Synthetic uptrending series with 3 visible swing lows
    lows = [50, 49, 47, 46, 45, 46, 47, 48, 49, 50, 51, 52, 51, 50,
            48, 49, 50, 51, 52, 53, 54, 53, 52, 51, 53, 55, 57, 58,
            59, 60, 58, 57, 56]
    idx = most_recent_relative_low(lows, n=5)
    print(f"Most recent relative low: index {idx}, price {lows[idx]}")
    print(f"Suggested stop: ${stop_level(lows, n=5):.2f}")
```

## 🔗 Within-Chapter Relationships
- The natural building block of a [[Trailing Stop]]: each new relative low becomes the next *higher* stop.
- More objective and more **discrete** than a [[Trend Line Stop]] — pivots are defined by an algorithm; trend lines are subjective.
- More technically grounded than a [[Money Stop]], which is purely dollar-based.
- When the nearest relative low is *too far below entry* to satisfy the trader's max-risk-per-trade rule, fall back to a [[Money Stop]].

### When does this concept "work well"?
| Situation | Effective? |
|---|---|
| Smooth, stair-stepping trend | ✅ Excellent |
| Choppy market with no clean pivots | ❌ Pivots are noise |
| When a clear *most recent* relative low exists close to current price | ✅ Tight, meaningful stop |
| Just after a pivot was set (next pivot is far away) | ⚠️ Risk may grow before the next pivot forms |

## 🌐 Cross-Chapter Relationships
- **Chapter 3 — Trends** — defines relative highs and relative lows; an uptrend is essentially a *sequence of higher relative lows*.
- **Chapter 5 — Chart Patterns** — double bottoms, head-and-shoulders, etc. are all defined in terms of relative highs/lows.
- **Chapter 10 — Setting Objectives** — relative highs are also used to set *upside* objectives, the mirror of using relative lows as stops.
- **Appendix** — defines the *N*-bar relative high/low formally.

## 📌 Key Takeaway
In a healthy uptrend, every new relative low is *higher* than the last. The moment that pattern breaks, you have permission to leave. The most recent relative low is your line in the sand.
