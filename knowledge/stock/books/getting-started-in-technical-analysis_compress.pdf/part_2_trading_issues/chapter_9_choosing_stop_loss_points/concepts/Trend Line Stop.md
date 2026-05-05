---
title: "Trend Line Stop"
chapter: 9
concept_number: 3
tags: [concept/stop-placement, trend-line]
related: [[Stop-Loss Liquidation Point]], [[Trading Range Stop]], [[Trailing Stop]]
---

# Trend Line Stop

## 📖 Definition
A **trend line stop** places the protective stop just *beyond* a relevant trend line — below an uptrend line for a long position, above a downtrend line for a short position. The reasoning: the trend line is the lowest-cost early-warning signal that the trend itself may have ended. Penetrating it triggers an exit before the move has fully developed against you.

The trade-off: trend lines are cheap to violate. False signals are common, and trend lines are frequently redrawn during a real bull or bear move (see Chapter 3). So the stop is *responsive* but **prone to whipsaws**.

## 🖼️ Illustration
![[trend_line_stop.svg]]

## 🥚 Simple Analogy
A trend line stop is like the **handrail** on a flight of stairs. If your hand is sliding along it as you go up, the moment it leaves the rail something has changed — you're either at the top, or you've stumbled. The rail gives you the *earliest* warning, but it'll also yell every time you let go for a sip of water that wasn't actually a fall.

## 🔢 Numeric Example
- Stock has risen along an uptrend line connecting lows: $40 (Jan), $44 (Mar), $48 (May)
- Trend-line slope ≈ +$2/month
- Today is July → trend line projects to **$52**
- Buy at $58
- **Sell stop = $51** (just below where the trend line is "today")
- Risk per share = $7
- If the line is broken, the technical premise is invalidated → exit

## 💻 Python Code
```python
# /code/trend_line_stop.py
"""Compute a stop-loss level just below a fitted uptrend line."""
import numpy as np
from dataclasses import dataclass

@dataclass
class TrendLineStop:
    pivot_dates: list[int]    # day indices of lows used to build the line
    pivot_prices: list[float] # corresponding low prices
    buffer: float = 0.005     # 0.5% buffer below line

    def slope_intercept(self):
        x = np.array(self.pivot_dates, dtype=float)
        y = np.array(self.pivot_prices, dtype=float)
        # least-squares fit (works even with >2 points)
        slope, intercept = np.polyfit(x, y, 1)
        return slope, intercept

    def line_value(self, day: int) -> float:
        m, b = self.slope_intercept()
        return m * day + b

    def stop_for(self, day: int) -> float:
        return self.line_value(day) * (1 - self.buffer)


if __name__ == "__main__":
    # Lows on day 10, 70, 130 of a rising trend
    tl = TrendLineStop(
        pivot_dates=[10, 70, 130],
        pivot_prices=[40.0, 44.0, 48.0],
    )
    today = 190
    print(f"Trend line at day {today}: ${tl.line_value(today):.2f}")
    print(f"Suggested stop:           ${tl.stop_for(today):.2f}")
```

## 🔗 Within-Chapter Relationships
- **Most sensitive** of the technical stops in this chapter — exits earliest, but with the highest false-signal rate.
- Compared to a [[Trading Range Stop]] (which waits for a much larger move) it surrenders far less open profit but whipsaws more often.
- Often *replaced* mid-trade by a [[Trailing Stop]] that ratchets up as new pivot lows form.
- A [[Money Stop]] is the fallback when a trend line is too far away to give acceptable risk.

### When does this concept "work well"?
| Situation | Effective? |
|---|---|
| Cleanly trending market with multiple touches on the line | ✅ Strong |
| Choppy, sideways market | ❌ Constant whipsaws |
| Very long-term trend (months/years) | ✅ But supplement with money stop |
| Brand-new trend with only 2 points on the line | ⚠️ Line not yet validated; treat tentatively |

## 🌐 Cross-Chapter Relationships
- **Chapter 3 — Trends** — defines uptrend and downtrend lines, internal trend lines. This stop technique is impossible without that chapter's groundwork.
- **Chapter 7** — discusses why simple chart signals (including trend-line breaks) generate false signals frequently; motivates layering with confirmation rules.
- **Chapter 14** — confirmation conditions and filter rules can be added on top of a trend-line stop to reduce whipsaws.

## 📌 Key Takeaway
Trend-line stops are the **fastest** to fire and the **most likely** to be wrong. Use them when the trend is clean and well-defined, and be ready to re-enter if the break turns out to be a false alarm.
