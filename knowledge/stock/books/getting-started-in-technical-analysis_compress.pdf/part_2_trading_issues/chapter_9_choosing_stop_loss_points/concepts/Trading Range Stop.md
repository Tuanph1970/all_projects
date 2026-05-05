---
title: "Trading Range Stop"
chapter: 9
concept_number: 4
tags: [concept/stop-placement, trading-range, breakout]
related: [[Trend Line Stop]], [[Flag and Pennant Stop]], [[Stop-Loss Liquidation Point]]
---

# Trading Range Stop

## 📖 Definition
After a position is entered on a **breakout** from a trading range, a **trading-range stop** places the protective stop somewhere inside the *opposite end* of that prior range. The reasoning: if the breakout is real, prices should not retreat deeply back into the range; a return all the way to the far side **invalidates** the breakout signal and transforms the technical picture.

A common refinement: place the stop between the **midpoint** and the more distant boundary, rather than at the nearest boundary — because shallow pullbacks into the near edge of the range are extremely common (and often a *good* re-entry zone, not a stop-out zone).

## 🖼️ Illustration
![[trading_range_stop.svg]]

## 🥚 Simple Analogy
A trading range is like a **swimming pool**. A breakout is the moment a kid finally jumps the wall and runs off into the yard. A small step back to the edge is normal — they might glance at the pool again. But if they fall *all the way back in*, the "they're done with the pool" theory was wrong. The far wall of the pool is your stop, not the near edge they just hopped over.

## 🔢 Numeric Example
- Multi-month trading range: **low $42 / high $48**
- Midpoint = $45
- Upside breakout closes at **$49**, position bought at **$49.50**
- Near-edge stop: $47.95 → too tight, nearly any pullback hits it
- Mid-range stop: **$45.00** → a balanced choice; risk = $4.50/share
- Far-edge stop: $42.00 → safest but biggest loss; risk = $7.50/share
- Pick the level whose risk fits within the [[Stop-Loss Liquidation Point#Numeric Example|2–3% rule]]

## 💻 Python Code
```python
# /code/trading_range_stop.py
"""Compute candidate trading-range stops and pick the tightest one
   that still satisfies the trader's max-risk-per-trade rule."""
from dataclasses import dataclass

@dataclass
class TradingRangeStop:
    range_low: float
    range_high: float
    entry_price: float
    account_equity: float
    max_risk_pct: float = 0.02

    @property
    def midpoint(self) -> float:
        return (self.range_low + self.range_high) / 2

    def candidate_stops(self, side: str = "long") -> dict:
        if side == "long":
            return {
                "near_edge": self.range_high,
                "midpoint":  self.midpoint,
                "far_edge":  self.range_low,
            }
        else:  # short on downside breakout
            return {
                "near_edge": self.range_low,
                "midpoint":  self.midpoint,
                "far_edge":  self.range_high,
            }

    def pick_stop(self, side: str = "long") -> tuple[str, float, int]:
        max_dollar_risk = self.account_equity * self.max_risk_pct
        chosen = None
        for label, stop in self.candidate_stops(side).items():
            risk = abs(self.entry_price - stop)
            if risk == 0:
                continue
            shares = int(max_dollar_risk // risk)
            # prefer tighter (smaller risk) stop, but skip 'near_edge' per Schwager
            if label == "near_edge":
                continue
            chosen = (label, stop, shares)
            if label == "midpoint":
                break  # midpoint is the recommended default
        return chosen


if __name__ == "__main__":
    trs = TradingRangeStop(
        range_low=42.0, range_high=48.0,
        entry_price=49.5, account_equity=100_000
    )
    label, stop, qty = trs.pick_stop()
    print(f"Chosen stop: {label} @ ${stop:.2f}  →  size {qty} shares")
```

## 🔗 Within-Chapter Relationships
- **Looser** than a [[Trend Line Stop]] — fewer whipsaws, but each loss is bigger.
- **Tighter** than a [[Money Stop]] in most cases, because the range boundary is usually closer than an arbitrary dollar amount.
- Same logic family as the [[Flag and Pennant Stop]] and [[Wide-Ranging Day Stop]] — all three say *"breakout invalidated when price returns to the opposite end of the pattern."*

### When does this concept "work well"?
| Situation | Effective? |
|---|---|
| Clear, well-defined multi-month range | ✅ Excellent |
| Range is very narrow | ⚠️ Risk per share is tiny, but signal is weak |
| Range is enormous (huge stop distance) | ⚠️ Use [[Money Stop]] instead, or pass on the trade |
| Recent false breakouts in the same name | ❌ Avoid; use confirmation filter first |

## 🌐 Cross-Chapter Relationships
- **Chapter 4 — Trading Ranges and Support/Resistance** — defines the range boundaries this stop technique relies on.
- **Chapter 5 — Chart Patterns** — bull/bear traps (failed breakouts that come back into the range) are exactly the events this stop is designed to detect.
- **Chapter 8 — Midtrend Entry** — when re-entering a trending market after a pullback to a former range, this same stop logic applies.

## 📌 Key Takeaway
After a range breakout, **don't put your stop at the near edge** — too many normal pullbacks reach it. Put it deep enough into the range that being hit means the breakout itself was a lie.
