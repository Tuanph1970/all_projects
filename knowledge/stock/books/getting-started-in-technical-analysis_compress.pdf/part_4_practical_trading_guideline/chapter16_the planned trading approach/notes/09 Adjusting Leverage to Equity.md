# 09 Adjusting Leverage to Equity

**Element 6 of [[03 Risk Control Plan]]** · [[00 Chapter 16 Index]]

## Definition

Position size should track **current account equity**, not the original deposit. When equity grows, leverage scales up proportionally so dollar risk maintains the same percentage. When equity shrinks, leverage scales *down* — preventing a drawdown from spiraling into ruin.

Mechanically: if equity moves by X%, dollar risk per trade should move by approximately X% in the same direction.

## Easy Analogy

A long-distance runner adjusts pace to current heart rate, not to the heart rate they had at the starting line. If the heart rate climbs, they slow down to recover; if it drops back to baseline, they push again. Trying to keep the original pace through a heat wave will end the run prematurely. Equity is the trader's heart rate.

## Numeric / Concrete Example

Trader starts with **$100,000** at 2% risk per trade = **$2,000 per trade**.

| Equity | Risk % | Risk $ | Behavioural effect |
|--------|--------|--------|-------------------|
| $120,000 (+20%) | 2% | $2,400 | Slightly larger size, profits compound |
| $100,000 (start) | 2% | $2,000 | Baseline |
| $80,000 (-20%) | 2% | $1,600 | Smaller size, losses don't compound |
| $60,000 (-40%) | 2% | $1,200 | Defensive — recovery requires fewer winners |

**The math that matters:** if the trader keeps risking the original $2,000 after a drop to $60,000, that's now 3.3% per trade — and a string of losses snowballs much faster.

## Python Code

```python
def adjust_risk_dollar(starting_equity, current_equity, base_risk_pct):
    """Risk percent stays constant; risk dollar scales with equity."""
    return current_equity * base_risk_pct

# Use this AT THE TIME of every new trade — not once a month
adjust_risk_dollar(100_000, 80_000, 0.02)   # → 1600
adjust_risk_dollar(100_000, 120_000, 0.02)  # → 2400
```

See [[02_volatility_sizing.py]] for a fuller implementation.

## Relationships

### Within Chapter 16
- Combines with [[04 Maximum Risk Per Trade]]: the *percent* is fixed by Element 1; this rule ensures the *dollar amount* derived from that percent updates in real time.
- Different from [[10 Losing Period Adjustments]] — that one is psychological (cut size when confidence is shaken); this one is mathematical (cut size when equity is lower).

### Outside Chapter 16
- **Chapter 14** — when systems are evaluated, percent-of-equity returns and percent drawdowns implicitly assume this rule. Sizing in fixed dollars instead of percentages would produce different (and worse) compounding properties.

## When This Concept Works Well
- When the trader recalculates position size from current equity at the start of each trading day.
- When the rule is applied symmetrically — increasing size on the way up, not just decreasing on the way down.

## When It Fails
- When traders refuse to scale up after gains ("I don't want to give back profits") — this caps compound returns.
- When traders refuse to scale down after losses ("I need to make it back") — this is the most expensive mistake the rule exists to prevent.
