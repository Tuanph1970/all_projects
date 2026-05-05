---
title: "Wide-Ranging Day Stop"
chapter: 9
concept_number: 6
tags: [concept/stop-placement, wide-ranging-day, one-day-pattern]
related: [[Flag and Pennant Stop]], [[Trading Range Stop]]
---

# Wide-Ranging Day Stop

## 📖 Definition
A **wide-ranging day** is a single bar whose high-to-low range is significantly larger than the recent average — a sign of strong directional conviction. After a breakout in the direction of such a bar, the **opposite extreme** of that bar (the *true low* for an up-day, the *true high* for a down-day) becomes a natural stop level. If the market reverses all the way through that single-bar extreme, the conviction implied by the bar has been negated.

> **True low / true high** (see Appendix in the book): the lower of the day's low and the prior day's close (and analogously for the high). Used because gaps shouldn't be ignored.

## 🖼️ Illustration
![[wide_ranging_day_stop.svg]]

## 🥚 Simple Analogy
A wide-ranging up day is like **a sprinter who suddenly bursts ahead of the pack**. If the next few minutes show them slipping back to the position they were in *before* the burst, the burst was a fluke — they're not actually faster. The starting line of the burst is the stop level.

## 🔢 Numeric Example
- Stock has been in a tight range averaging $1.50 daily true range
- Tuesday: stock prints high **$52**, low **$48** — a $4 wide-ranging up day (≈ 2.5× normal)
- Wednesday: stock continues higher to **$53** → enter long
- Stop = **true low** of Tuesday = $48 (or the prior day's close, whichever is lower)
- Risk per share = $5
- A close back below $48 invalidates the breakout day's signal

## 💻 Python Code
```python
# /code/wide_ranging_day_stop.py
"""Identify a wide-ranging day and compute the implied stop level."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class Bar:
    high: float
    low: float
    close: float

def true_range(today: Bar, prev_close: float) -> float:
    return max(today.high, prev_close) - min(today.low, prev_close)

def true_low(today: Bar, prev_close: float) -> float:
    return min(today.low, prev_close)

def is_wide_ranging(today: Bar, prev_close: float,
                    avg_range: float, multiple: float = 2.0) -> bool:
    return true_range(today, prev_close) >= multiple * avg_range


def long_stop_after_wrd(wrd: Bar, prev_close: float) -> float:
    """Stop = true low of the wide-ranging up day."""
    return true_low(wrd, prev_close)


if __name__ == "__main__":
    # 20-day average true range = $1.50
    avg_tr = 1.50
    prev_close = 49.20
    today = Bar(high=52.0, low=48.0, close=51.6)

    if is_wide_ranging(today, prev_close, avg_tr):
        stop = long_stop_after_wrd(today, prev_close)
        print(f"Wide-ranging day detected. Suggested long stop: ${stop:.2f}")
    else:
        print("Not a wide-ranging day; use a different stop technique.")
```

## 🔗 Within-Chapter Relationships
- Almost identical *logic* to the [[Flag and Pennant Stop]] — both say "if the breakout reverses through the opposite extreme of the signal pattern, the signal is invalidated." The difference is just the timeframe of the pattern (one bar vs several).
- Tighter than a [[Trading Range Stop]] because a single-bar low is closer than a multi-week range low.
- Often used as the **initial** stop on a freshly-triggered position; later upgraded to a [[Trailing Stop]] once the market makes new highs.

### When does this concept "work well"?
| Situation | Effective? |
|---|---|
| Wide-ranging breakout out of a clear range | ✅ Strong signal, clear stop |
| Wide-ranging day on a news event (earnings, Fed) | ⚠️ News can mean revert quickly — keep position size small |
| Several wide-ranging days in a row in opposing directions | ❌ Volatility regime — stops will whipsaw |
| Highly liquid future / large-cap stock | ✅ True low is meaningful |
| Low-volume stock with one freak bar | ❌ The bar may be noise, not signal |

## 🌐 Cross-Chapter Relationships
- **Chapter 5 — Chart Patterns** — formally introduces wide-ranging days as a one-day pattern.
- **Appendix** — defines *true high* / *true low* explicitly. This stop concept depends on those definitions when there's a gap.
- **Chapter 17 — Rule #18**: a sudden move far in excess of recent volatility *against* your position is grounds for immediate liquidation — the same logic applied from the *other* side.

## 📌 Key Takeaway
A wide-ranging day is a one-bar mini-trading-range. Treat its opposite extreme exactly like the opposite end of any other breakout pattern — that's where the signal dies.
