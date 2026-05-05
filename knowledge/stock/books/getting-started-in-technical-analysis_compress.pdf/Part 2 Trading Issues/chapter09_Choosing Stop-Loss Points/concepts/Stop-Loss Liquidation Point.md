---
title: "Stop-Loss Liquidation Point"
chapter: 9
concept_number: 1
tags: [concept/stop-loss, risk-management, foundational]
related: [[GTC Stop Order]], [[Trailing Stop]], [[Money Stop]]
---

# Stop-Loss Liquidation Point

## 📖 Definition
A **stop-loss liquidation point** is the *predetermined* price at which a trader will exit a losing position. It is fixed **before** the trade is entered, and its purpose is to cap the maximum loss the trader is willing to absorb if the market moves against the position.

The guiding principle: a position should be liquidated at or before the price at which the technical picture that justified the trade has been invalidated.

## 🖼️ Illustration
![[stop_loss_liquidation_point.svg]]

## 🥚 Simple Analogy
Think of stop-loss like the **automatic shut-off on an electric kettle**. You set the temperature once — boiling — and the moment the water reaches that point, the kettle clicks off. You don't decide in the heat of the moment whether to keep heating; the decision was made when you flipped the switch. A trader who waits to "see how it feels" before exiting is like someone standing over a kettle, repeatedly resetting the shut-off because "it might cool down on its own." The water boils dry.

## 🔢 Numeric Example
- Account size: **$100,000**
- Maximum risk per trade: **2%** = $2,000
- Buy stock XYZ at **$50.00**
- Predetermined stop: **$48.00** (premise violated below this level)
- Risk per share: $50 − $48 = **$2**
- Max position size: $2,000 ÷ $2 = **1,000 shares**

If XYZ trades down to $48 → liquidate immediately, $2,000 loss. Trade is over. No "let me see if it bounces."

## 💻 Python Code
```python
# /code/stop_loss_liquidation_point.py
from dataclasses import dataclass

@dataclass
class StopLossPlan:
    entry_price: float
    stop_price: float
    account_equity: float
    max_risk_pct: float = 0.02   # 2% rule

    def risk_per_share(self) -> float:
        return self.entry_price - self.stop_price

    def max_position_size(self) -> int:
        risk_dollars = self.account_equity * self.max_risk_pct
        rps = self.risk_per_share()
        if rps <= 0:
            raise ValueError("Stop must be below entry for a long position.")
        return int(risk_dollars // rps)

    def should_liquidate(self, current_price: float) -> bool:
        return current_price <= self.stop_price


if __name__ == "__main__":
    plan = StopLossPlan(entry_price=50.0, stop_price=48.0, account_equity=100_000)
    print(f"Risk/share : ${plan.risk_per_share():.2f}")
    print(f"Max shares : {plan.max_position_size()}")
    print(f"Exit at $47.95? {plan.should_liquidate(47.95)}")
```

## 🔗 Within-Chapter Relationships
- **Foundation for the whole chapter.** Every other concept (trend-line stop, money stop, trailing stop, etc.) is just a *method for choosing where this point goes*.
- Pairs naturally with [[GTC Stop Order]] — the order mechanism that enforces the liquidation point automatically.
- The [[CIC Anti-Pattern]] is the failure mode of *having* a stop-loss point but not respecting it.

### When does this concept "work well"?
| Situation | Effective? |
|---|---|
| Discretionary trading on chart patterns | ✅ Essential — without it, losses can run unbounded |
| Mechanical trend-following systems | ⚠️ Optional — if the system auto-reverses, the reversal *is* the stop |
| Ultra-short-term scalping | ✅ Often automated as a hard stop |
| Buy-and-hold long-term investing | ❌ Different paradigm; usually replaced by rebalancing rules |

## 🌐 Cross-Chapter Relationships
- **Chapter 7** — establishes that win-rate < 50% is fine *if* losses are kept small. Stop-loss point is the mechanism that makes this true.
- **Chapter 11** ("The Most Important Rule") — generalizes the stop into a broader rule: exit whenever the trade premise is violated.
- **Chapter 16** — the 3%-of-equity max-risk rule **uses** the stop-loss point to size positions.
- **Chapter 17** — Rule #13: "Decide on a specific protective stop point at the time of trade entry."

## 📌 Key Takeaway
**Know where you're getting out before you get in.** A trade without a defined exit is a hope, not a plan.
