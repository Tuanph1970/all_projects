---
title: "GTC Stop Order"
chapter: 9
concept_number: 2
tags: [concept/order-type, mechanism, discipline]
related: [[Stop-Loss Liquidation Point]], [[CIC Anti-Pattern]]
---

# GTC (Good-Till-Canceled) Stop Order

## 📖 Definition
A **GTC stop order** is a resting sell-stop (or buy-stop) order that remains active in the broker's order book until it is either filled or explicitly canceled by the trader — as opposed to a *day order*, which expires automatically at the close. The recommended workflow is to place the GTC stop at the **same moment** the position is opened, so the exit point is enforced by the broker rather than by the trader's nerve.

If the trader trusts their own discipline, they may keep the stop "mental" and convert it to a day order whenever the price approaches the stop level — but Schwager treats GTC as the default, more disciplined approach.

## 🖼️ Illustration
![[gtc_stop_order.svg]]

## 🥚 Simple Analogy
A GTC stop is like a **smoke detector** in your house. You install it once, you don't have to remember it, you don't need to be home — when smoke crosses the threshold, it goes off whether you're awake, asleep, or away on vacation. A "mental stop" is like saying *"I'll just sniff the air every few minutes."* Works fine — until the one night you fall asleep.

## 🔢 Numeric Example
- Buy 200 shares of XYZ at **$50.00**
- Immediately enter: **SELL 200 XYZ STOP $48.00 GTC**
- The order sits in the broker's system for weeks if needed
- Day 14: stock gaps down to $47.20 overnight on bad earnings
- Order triggers automatically at the open; fill near $47.20
- Loss = $2.80 × 200 = **$560** (vs. potential of much more if there was no stop)

## 💻 Python Code
```python
# /code/gtc_stop_order.py
"""Simulate a GTC vs. day-only stop order across a multi-day price series."""
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class GTCStopOrder:
    side: str            # "sell" or "buy"
    stop_price: float
    quantity: int
    active: bool = True
    fill_price: Optional[float] = None
    fill_day: Optional[int] = None

    def check(self, day: int, day_low: float, day_high: float) -> bool:
        """Return True if triggered on this day."""
        if not self.active:
            return False
        if self.side == "sell" and day_low <= self.stop_price:
            self.fill_price = min(self.stop_price, day_high)  # simple fill model
            self.fill_day, self.active = day, False
            return True
        if self.side == "buy" and day_high >= self.stop_price:
            self.fill_price = max(self.stop_price, day_low)
            self.fill_day, self.active = day, False
            return True
        return False


def simulate(prices: List[tuple], stop: GTCStopOrder):
    """prices = list of (low, high) tuples, one per day."""
    for day, (lo, hi) in enumerate(prices, start=1):
        if stop.check(day, lo, hi):
            print(f"Day {day}: STOP TRIGGERED at ${stop.fill_price:.2f}")
            return
    print("Stop never triggered, order still resting (GTC).")


if __name__ == "__main__":
    # 14 days, stock drifts and finally gaps down day 14
    series = [(49.5, 50.6), (49.8, 50.9), (49.0, 50.4), (48.9, 50.1),
              (49.1, 50.3), (48.8, 49.7), (48.5, 49.4), (48.3, 49.0),
              (48.4, 49.2), (48.6, 49.5), (48.2, 49.0), (48.0, 48.9),
              (48.1, 48.8), (47.20, 47.90)]    # gap-down day 14
    sell_stop = GTCStopOrder(side="sell", stop_price=48.00, quantity=200)
    simulate(series, sell_stop)
```

## 🔗 Within-Chapter Relationships
- The **mechanism** that enforces the [[Stop-Loss Liquidation Point]].
- Direct opposite of the [[CIC Anti-Pattern]] — a GTC stop sits there *waiting*; the CIC trader cancels it the moment it's about to do its job.
- Used by every other stop technique in this chapter as the order-placement vehicle: [[Trailing Stop]] is just a GTC stop that's repeatedly *raised* (never lowered).

### When does this concept "work well"?
| Situation | Effective? |
|---|---|
| Position trading (days–weeks) | ✅ Ideal |
| Trader cannot watch the screen all day | ✅ Essential |
| Markets that gap overnight (futures, earnings stocks) | ✅ Critical — protects against gap-throughs |
| Trader is highly disciplined and screen-bound | ⚠️ Mental stop acceptable, but riskier |
| Highly illiquid stock | ⚠️ Stop can fill far worse than stop price |

## 🌐 Cross-Chapter Relationships
- **Chapter 16** — the planned-trading approach explicitly recommends placing GTC orders at trade entry as part of the risk-control plan.
- **Chapter 17** — Rule #13 mandates a specific protective stop at trade entry. Rule #11 reinforces preferring market-style execution (which includes stop-market orders) over limit orders for risk-reduction exits.

## 📌 Key Takeaway
A stop-loss point you've decided on but **not entered as a GTC order** is half a stop. The order mechanism is what removes you — and your wishful thinking — from the loop.
