# 06 Diversification

**Element 3 of [[03 Risk Control Plan]]** · [[00 Chapter 16 Index]]

![[07_diversification.svg]]

## Definition

**Diversification** in this context is the practice of spreading trading risk across multiple sources of return so that no single adverse event dominates the account's outcome. Three flavours appear in the chapter:

1. **Multiple markets** — different stocks, sectors, or asset classes
2. **Multiple systems** — trend-following + countertrend + breakout, etc.
3. **Multiple parameter sets** — e.g., breakout systems with N=10, N=20, N=40

Diversification reduces the probability that all positions lose at the same time. Beyond risk reduction, it raises the chance of catching a major trend somewhere in the portfolio.

## Easy Analogy

A backyard with one tomato plant either gives you a great year or no tomatoes at all. A backyard with tomatoes, peppers, herbs, beans, and squash gives you *something* every season — drought hits the squash, frost hits the basil, but never all of them at once. The total harvest is more reliable, even though no single plant outperforms a champion tomato.

Trading without diversification is the one-tomato garden.

## Numeric / Concrete Example

The book offers a clean illustration: trader with $20,000, system with $3,000 average drawdown per market.

| Setup | Average drawdown | % of equity |
|-------|------------------|-------------|
| 2 contracts of GOLD | $6,000 | 30% |
| 1 GOLD + 1 SOYBEANS | < $6,000 (often ~$4,500) | ~22% |
| 1 GOLD + 1 SOYBEANS + 1 BONDS + 1 EUR + 1 CRUDE + 1 SUGAR | typically < $9,000 across all six | < 45% combined |

The drawdowns *can only* equal $6,000 in the two-market case if losses are exactly synchronized, which is statistically unlikely. Adding inversely correlated markets (like bonds vs equities in a flight-to-quality) can actually reduce drawdown below what a single market produces.

## Python Code

Quick check on the average drawdown reduction from adding markets:

```python
import numpy as np

def average_drawdown(returns_df):
    eq = (1 + returns_df).cumprod()
    peak = eq.cummax()
    return ((eq - peak) / peak).mean()

# Suppose two return series with identical individual stats but different timing
np.random.seed(0)
gold = np.random.normal(0.0005, 0.012, 1000)
beans = np.random.normal(0.0005, 0.012, 1000)

import pandas as pd
single = pd.Series(gold).cumsum()
combined = pd.Series((gold + beans) / 2).cumsum()  # equal-weight

# Diversified series shows materially smaller drawdowns
```

## Relationships

### Within Chapter 16
- Diversification is one of the **three filters** in [[02 Market Selection]] — picking unrelated markets is upstream of this rule.
- When markets are nominally diverse but actually correlated, [[07 Reduced Leverage Correlated Markets]] applies.
- The benefits compound with [[08 Market Volatility Adjustments]] — smaller positions in volatile markets PLUS spreading them across uncorrelated names = much smoother equity.

### Outside Chapter 16
- **Chapter 14** — discusses three benefits of diversification at the *system* level: dampened equity retracements, ensuring participation in major trends, and "bad luck insurance" against isolated abnormal results.
- **Chapter 15** — average parameter set performance across many parameter sets is an extension of the diversification idea applied to system optimisation.

## When This Concept Works Well
- When markets are chosen for *low correlation* of returns, not just different tickers.
- When the trader has enough capital to size each position correctly without breaking [[04 Maximum Risk Per Trade]].
- When countertrend + trend systems are mixed — one tends to thrive when the other suffers.

## When It Fails
- "Diworsification" — adding mediocre markets just to have more entries. Diluting the edge without dampening the risk.
- Hidden correlation — six different bank stocks look diversified on the surface but move as one in a banking crisis.
- Diversification across parameter sets only, while staying in one market — still concentrated.
