---
title: "Money Stop"
chapter: 9
concept_number: 8
tags: [concept/stop-placement, money-stop, dollar-risk]
related: [[Stop-Loss Liquidation Point]], [[Trailing Stop]]
---

# Money Stop

## 📖 Definition
A **money stop** is a protective stop chosen purely on the basis of how much *dollar risk* the trader is willing to accept on a single trade — with no special technical significance to the price level itself. It's used when every reasonable technical reference point (trend line, range boundary, relative low, etc.) is too far away from the entry, implying a loss larger than the trader's risk-per-trade rule allows.

> The money stop is the **fallback**, not the default. It is used when patience for a deeper retracement isn't viable but a closer technical stop simply doesn't exist.

## 🖼️ Illustration
![[money_stop.svg]]

## 🥚 Simple Analogy
A money stop is the **drink limit** you set yourself before going out — *"I'm leaving after three, regardless."* It has nothing to do with the music being good or bad, who else is there, or whether the conversation is interesting. It's a budget. It exists because once the night is rolling, your *in-the-moment* judgment can't be trusted to call it.

## 🔢 Numeric Example
- Account size: **$50,000**, max risk per trade **2 %** = $1,000
- Trader believes a futures contract has just made a major top
- Nearest meaningful technical stop (the contract high) is *$15,000* away per contract — far too much risk
- Trader chooses a **money stop** of **$3 below entry**: a level with no technical meaning, sized so the dollar loss per contract = $1,500 (still too high → trader trades fewer contracts, or passes)
- For a stock trade with the same logic: enter at $80, money stop at $77.50, max loss = $2.50/share, position size = $1,000 ÷ $2.50 = **400 shares**

## 💻 Python Code
```python
# /code/money_stop.py
"""Decide whether to use a money stop, and if so, where to place it."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class StopDecision:
    entry_price: float
    technical_stop: Optional[float]   # nearest meaningful technical level (or None)
    account_equity: float
    max_risk_pct: float = 0.02
    money_stop_pct: float = 0.03      # default 3% money stop below entry

    @property
    def max_dollar_risk(self) -> float:
        return self.account_equity * self.max_risk_pct

    def technical_risk(self) -> Optional[float]:
        if self.technical_stop is None:
            return None
        return self.entry_price - self.technical_stop

    def decide(self) -> dict:
        tr = self.technical_risk()
        # If technical stop fits the risk budget, use it.
        if tr is not None and tr <= self.max_dollar_risk / 100:  # crude per-share test
            return {"type": "technical", "stop": self.technical_stop}
        # Else fall back to money stop sized to risk budget.
        money_stop = self.entry_price * (1 - self.money_stop_pct)
        return {"type": "money", "stop": money_stop}


if __name__ == "__main__":
    sd = StopDecision(
        entry_price=80.0,
        technical_stop=65.0,    # nearest support way too far below
        account_equity=50_000,
    )
    decision = sd.decide()
    print(f"Use {decision['type']} stop at ${decision['stop']:.2f}")
```

## 🔗 Within-Chapter Relationships
- The **fallback** when [[Trend Line Stop]], [[Trading Range Stop]], [[Flag and Pennant Stop]], [[Wide-Ranging Day Stop]], or [[Relative High Low Stop]] are all too far away.
- Frees the trader from being held hostage by a distant chart pattern, but at the cost of **no technical justification** for the exit level — the stop will sometimes fire when nothing on the chart says it should.
- Closely related to a fixed-dollar [[Trailing Stop]], which has the same trade-offs (known risk, but technically meaningless).

### When does this concept "work well"?
| Situation | Effective? |
|---|---|
| Nearest technical stop is unacceptably far away | ✅ Designed for this |
| Trader has a strong directional view but the chart is "messy" | ✅ Lets trader take the trade |
| Highly volatile market | ⚠️ Money stop will be hit on noise; widen *or* reduce size |
| Quiet, well-defined chart with clear support | ❌ Use a real technical stop instead |

## 🌐 Cross-Chapter Relationships
- **Chapter 16 — Planned Trading Approach** — the 2–3 % max-risk-per-trade rule is the calibration knob for *every* money stop.
- **Chapter 17** — Rule #13 ("decide on a specific protective stop point at trade entry") is satisfied by a money stop even when a chart-based stop isn't available.
- **Chapter 14** — system traders often use money stops *as* the primary exit because they simplify backtesting (a clear, mechanical rule).

## 📌 Key Takeaway
A money stop says **"I don't care what the chart says — this is how much I'm willing to lose."** Use it when no technical level fits your risk budget. Don't use it when one does.
