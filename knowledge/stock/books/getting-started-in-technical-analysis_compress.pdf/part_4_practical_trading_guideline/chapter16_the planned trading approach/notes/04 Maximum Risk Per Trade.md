# 04 Maximum Risk Per Trade

**Element 1 of [[03 Risk Control Plan]]** · [[00 Chapter 16 Index]]

![[05_max_risk_per_trade.svg]]

## Definition

The **maximum risk per trade** is the cap on the dollar amount you will lose if a single trade hits its stop. Expressed as a percentage of total account equity, this is the most important number in any risk plan.

The chapter's guidance:
- **Ideal:** ≤ 3% of equity per trade.
- **Acceptable:** modestly higher with strong methodology.
- **Above 7%:** the trader should reconsider whether they are financially suited to trading at all.

This single number, combined with the entry-to-stop distance, determines position size.

## Easy Analogy

Imagine you walk into a casino with $1,000 of "fun money". You decide ahead of time you will not bet more than $20 on any single hand. Even if you lose 30 hands in a row (extraordinary bad luck), you still walk out with $400 — bruised, but able to come back tomorrow. Without the rule, one big confident bet of $500 wipes out half your stake on a single coin flip.

Trading is the same casino, except the hands keep coming forever and the size of your bet (your position) is something *you* control on every hand.

## Numeric / Concrete Example

Account equity: **$100,000**. Risk cap: **3%**.

| Trade | Entry | Stop | Risk/share | Max shares | Capital deployed |
|-------|-------|------|------------|------------|------------------|
| TSLA long | $200 | $190 | $10 | 300 | $60,000 |
| KO long | $60 | $58 | $2 | 1,500 | $90,000 |
| GLD long | $190 | $185 | $5 | 600 | $114,000 *(too big — cut to fit margin)* |

In every case, the dollar loss if the stop hits is approximately **$3,000 = 3% of equity**.

### The drawdown math
| Risk per trade | Loss after 10 consecutive losses | Gain needed to recover |
|----------------|----------------------------------|------------------------|
| 1% | -10% | +11% |
| 2% | -18% | +22% |
| 3% | -26% | +35% |
| 5% | -40% | +67% |
| 10% | -65% | +186% |
| 15% | -80% | +400% |

Above ~5% per trade, recovery becomes mathematically punishing.

## Python Code

The position sizing formula:

```python
def shares_for_risk(equity, risk_pct, entry, stop):
    return int((equity * risk_pct) // abs(entry - stop))

# Example:
shares_for_risk(100_000, 0.03, 200, 190)  # → 300
shares_for_risk(100_000, 0.03, 60, 58)    # → 1500
```

Full implementation with cumulative checks: see [[01_position_sizing.py]].

## Relationships

### Within Chapter 16
- Sets the foundation for [[05 Stop-Loss Strategy]] — without a stop you cannot compute risk.
- Combines with [[08 Market Volatility Adjustments]]: in volatile markets the stop distance grows, so shares shrink, but the dollar risk stays fixed at this percentage.
- Used together with the cumulative cap recorded in [[12 Traders Notebook]] (rule of thumb: total open implied risk ≤ 25-35% of equity).

### Outside Chapter 16
- **Chapter 18 — Rule #9** echoes this with even tighter guidance: never risk more than 1-2% per trade.
- **Chapter 15** — testing and optimisation always reports drawdown as a % of equity, the same currency as this rule.

## When This Concept Works Well
- When the % is enforced *before* every trade is opened, computed from current equity (not original deposit).
- When the trader rounds DOWN to fit the rule (better to be slightly under than slightly over).

## When It Fails
- When traders compound rule violations: a 5% trade plus another 5% trade on a correlated stock = 10% real exposure to one shock.
- When a "high-conviction" trade gets the rule waived. The next 15 such trades will average to break-even, but the one large loss won't be averaged away.
