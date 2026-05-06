# 03 Risk Control Plan

**Step 3 of the Planned Trading Approach** · [[00 Chapter 16 Index]]

![[04_risk_control_plan.svg]]

## Definition

A **risk control plan** is the codified set of rules that prevents any single trade — or any unlucky sequence of trades — from doing permanent damage to the account. The chapter prefers the term "risk control" over the more common "money management" because the priority is rigid loss limitation, not optimisation of position size for return.

The plan has **seven elements**:

1. [[04 Maximum Risk Per Trade]] — cap on dollars at risk per individual trade
2. [[05 Stop-Loss Strategy]] — pre-defined exit on the losing side
3. [[06 Diversification]] — spreading bets across uncorrelated markets, systems, parameter sets
4. [[07 Reduced Leverage Correlated Markets]] — adjustment when chosen markets do correlate
5. [[08 Market Volatility Adjustments]] — sizing inversely with market volatility
6. [[09 Adjusting Leverage to Equity]] — sizing scales up/down with current equity
7. [[10 Losing Period Adjustments]] — temporary cutback (discretionary traders only)

## Easy Analogy

Risk control is the seatbelt, the airbag, the crumple zone, AND the speed limit on a car. None of them prevents accidents — but together they ensure that an accident doesn't end the journey forever. A trader without a risk control plan is driving a sports car at 100 mph with no seatbelt. The car still might get them home... once or twice.

## Numeric / Concrete Example

A trader with $100,000 implements all seven elements:

| Element | Rule |
|---------|------|
| 1. Max risk per trade | 2% = $2,000 |
| 2. Stop-loss | Always pre-set, GTC, before opening the trade |
| 3. Diversification | At least 6 markets, < 0.7 correlation pairwise |
| 4. Correlated cuts | If two positions correlate > 0.7, halve the smaller |
| 5. Volatility adjust | Stop = 2 × ATR; size = $2,000 / stop distance |
| 6. Equity-linked | Risk % scales: equity at 80% → risk per trade at 1.6% |
| 7. Losing-period | After a 15% drawdown, halve all sizes for 30 days |

These seven rules make catastrophic loss arithmetically very difficult.

## Python Code

The risk-control plan is essentially a chain of guard checks before a trade fires:

```python
def pre_trade_risk_checks(trade, account, open_book):
    checks = [
        ("max risk per trade",   trade.risk_dollar <= account.equity * 0.02),
        ("cumulative risk cap",  open_book.total_risk + trade.risk_dollar
                                  <= account.equity * 0.30),
        ("not over-correlated",  not is_too_correlated(trade, open_book)),
        ("volatility-adjusted",  trade.shares * trade.atr * 2 <= trade.risk_dollar * 1.05),
        ("equity-scaled",        trade.risk_pct <= account.current_risk_pct()),
    ]
    failed = [name for name, ok in checks if not ok]
    return (not failed, failed)
```

Implementations of each individual check live in:
- [[01_position_sizing.py]] — element 1 & cumulative risk
- [[02_volatility_sizing.py]] — elements 5 & 6

## Relationships

### Within Chapter 16
- Sits at the dead centre of the seven steps. Steps 1-2 generate trade ideas; this plan vets them before they hit the market; Steps 4-7 monitor and improve.
- [[12 Traders Notebook]] enforces this plan by tracking every column needed to compute the seven rules in real time.

### Outside Chapter 16
- **Chapter 9** — mechanics of stop-loss placement (referenced by element 2).
- **Chapter 14** — diversification benefits at the system-design level (elements 3 & 4).
- **Chapter 18 — Rule #9 (Money Management and Risk Control):** Schwager reports that great traders consistently rate risk control as *more important than the trading method itself*.

## When This Concept Works Well
- When the rules are written down and visible at the trading desk — not held in memory.
- When the trader uses a checklist before every entry.

## When It Fails
- When the rules are bent "just this once" for a high-conviction trade. That trade is statistically the same as any other, and its outsize loss is the one that breaks the account.
- When discipline weakens after a long winning streak (overconfidence inflates position size).
