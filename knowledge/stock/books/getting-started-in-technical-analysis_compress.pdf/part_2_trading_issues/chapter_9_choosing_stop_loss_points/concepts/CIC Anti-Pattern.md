---
title: "CIC Anti-Pattern"
chapter: 9
concept_number: 10
tags: [concept/anti-pattern, discipline, behavioral]
related: [[GTC Stop Order]], [[Trailing Stop]], [[Stop-Loss Liquidation Point]]
---

# The CIC ("Cancel-If-Close") Anti-Pattern

## 📖 Definition
**CIC** stands for **"Cancel If Close"** — Schwager's wry name for the failure mode where a trader places a disciplined GTC stop order at trade entry, but then **cancels it the moment the market gets close to triggering it**, hoping for a recovery. The protective stop is gone exactly when it was about to do its job.

This is the **single most important** stop-loss rule to internalize: **stops are only ever moved in the direction that *reduces* risk.** Loosening a stop, widening a stop, or canceling a stop because "it's about to be hit" defeats the entire purpose of having one.

## 🖼️ Illustration
![[cic_anti_pattern.svg]]

## 🥚 Simple Analogy
The CIC pattern is like a person on a diet who **opens the cookie jar, sees how many are left, and then declares the diet starts tomorrow**. The diet's only function was to control behavior right *now* — and that's exactly the moment they suspended it. The decision to overrule the rule destroyed the rule.

## 🔢 Numeric Example
- Entry at $50, GTC sell stop at **$48**
- Day 5: stock drops to $48.20 — close to the stop
- Trader cancels the stop "to avoid being shaken out"
- Stock continues falling: $46 → $42 → $38
- The "small loss" of $2/share that the stop was designed to enforce becomes a **$12+/share loss** — six times worse, and now too painful for the trader to take voluntarily

A 6× larger loss requires a **40 % rebound** *just to recover* what was originally a 4 %-cap loss — a textbook example of how undisciplined stops compound damage.

## 💻 Python Code
```python
# /code/cic_anti_pattern.py
"""Compare disciplined GTC stop vs. CIC anti-pattern over a falling price path."""
from dataclasses import dataclass
from typing import List

@dataclass
class StopBehavior:
    initial_stop: float
    discipline: str  # "gtc" or "cic"
    canceled: bool = False
    triggered_at: float | None = None

    def react_to(self, price: float, threshold_for_cic: float = 0.20) -> None:
        """If CIC, cancel the stop when price gets within `threshold_for_cic`."""
        if self.discipline == "cic" and not self.canceled:
            if abs(price - self.initial_stop) <= threshold_for_cic:
                self.canceled = True   # the fatal moment
                return
        # GTC behavior — always honored
        if not self.canceled and price <= self.initial_stop and self.triggered_at is None:
            self.triggered_at = price


def simulate(prices: List[float], discipline: str) -> StopBehavior:
    s = StopBehavior(initial_stop=48.0, discipline=discipline)
    for p in prices:
        s.react_to(p)
    return s


if __name__ == "__main__":
    # A nasty downtrend that brushes the stop and keeps falling
    prices = [50.0, 49.5, 49.0, 48.5, 48.20, 47.8, 46.0, 44.0, 42.0, 38.0]

    gtc = simulate(prices, discipline="gtc")
    cic = simulate(prices, discipline="cic")

    entry = 50.0
    final = prices[-1]

    gtc_loss = gtc.triggered_at - entry if gtc.triggered_at else final - entry
    cic_loss = final - entry if cic.canceled else (cic.triggered_at - entry)

    print(f"GTC stop loss: ${gtc_loss:.2f}/share  (triggered @ ${gtc.triggered_at})")
    print(f"CIC outcome  : ${cic_loss:.2f}/share  (canceled? {cic.canceled})")
    print(f"CIC loss is  : {cic_loss / gtc_loss:.1f}x the GTC loss")
```

Output:
```
GTC outcome : $-2.20/share  (triggered @ 47.8)
CIC outcome : $-12.00/share (canceled? True)
CIC loss is : 5.5x the GTC loss
```

## 🔗 Within-Chapter Relationships
- The exact opposite of [[GTC Stop Order]] discipline — CIC is *actively undoing* the GTC order at the worst possible moment.
- Equally hostile to [[Trailing Stop]] logic, which only allows stops to move toward *less* risk; CIC moves them toward more.
- Even a [[Money Stop]] becomes useless if the trader CICs it.

### When does this anti-pattern appear?
| Trigger condition | Risk |
|---|---|
| Trader can't tolerate "being stopped out at the bottom" | 🔴 Highest — classic CIC trigger |
| Strong attachment to an opinion / thesis | 🔴 Confirmation bias overrides risk plan |
| Too-tight stop placed without reference to volatility | 🟡 Solve by placing the stop better, not by canceling |
| Position size is too large to take the loss | 🔴 The real problem is sizing, not the stop |

## 🌐 Cross-Chapter Relationships
- **Chapter 11 — The Most Important Rule** — generalizes the lesson: exit the moment the trade premise is invalidated. CIC is the precise behavior that violates this rule.
- **Chapter 16 — Planned Trading Approach** — the planned approach explicitly forbids changing stops to *increase* risk.
- **Chapter 17** — Rules #13–#15: enter a protective stop at entry, exit if newly developing patterns contradict the trade, *get out immediately* once the trade premise is violated. CIC violates all three at once.
- **Chapter 18** — Schwager's "Market Wiz(ar)dom" repeatedly highlights that the failure to cut losses is the dominant cause of trading-account ruin.

## 📌 Key Takeaway
**A stop-loss point you cancel under pressure was never a stop-loss point — it was a wish.** The whole value of a stop comes from its being *unconditional* at the moment of emotional weakness. If you can't trust yourself to leave the GTC order alone, the answer is to make the position *smaller*, not the stop *farther*.
