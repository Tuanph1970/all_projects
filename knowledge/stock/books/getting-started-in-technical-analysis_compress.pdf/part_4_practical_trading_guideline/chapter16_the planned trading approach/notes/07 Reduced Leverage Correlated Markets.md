# 07 Reduced Leverage Correlated Markets

**Element 4 of [[03 Risk Control Plan]]** · [[00 Chapter 16 Index]]

## Definition

When two or more markets in your portfolio are highly correlated, treating them as independent positions over-states diversification and under-states real risk. The cure is to **reduce leverage** — fewer shares or contracts in each — to bring the *aggregate* risk in line with what a truly diversified portfolio of the same size would carry.

Two textbook examples from Chapter 16:
- A futures portfolio of six currencies — they all move with the dollar.
- A "diversified" stock portfolio of six pharmaceutical names — they all move with FDA news, drug pricing rhetoric, and healthcare reform.

Both portfolios *look* like six positions but behave more like one or two.

## Easy Analogy

You're packing a backpack for a hiking trip and you've added six "different" emergency food bars. They all turn out to be the same brand of granola, just different flavours. If a bear gets into one, your gut probably can't trust the rest either — they have the same recipe. You need fewer bars and more variety: granola, jerky, dried fruit. That diversity is what makes the food supply resilient.

Same with markets: six positions that share a recipe (drivers) are not six positions of risk.

## Numeric / Concrete Example

Trader has $100,000, uses 2% risk per trade, and runs **six positions**:

**Scenario A — Truly diversified six markets** (corn, copper, ten-year notes, EUR/USD, S&P 500, gold):
- Total open risk = 6 × $2,000 = $12,000 (12% of equity).
- Pairwise correlations all under 0.4. Portfolio drawdown stays manageable.

**Scenario B — Six tech stocks** (AAPL, MSFT, GOOGL, META, AMZN, NVDA):
- Total open risk on paper = $12,000.
- Correlation often > 0.8 in selloffs.
- A 2% sector shock takes all six positions toward their stops simultaneously → real drawdown closer to $12,000 in one bad day.

**The correction:** in Scenario B, cut size by 50% (or more) so the *effective* risk is closer to a 2-3 position book.

## Python Code

A correlation-aware position adjuster:

```python
import numpy as np

def adjust_for_correlation(positions, returns_df, threshold=0.7, factor=0.5):
    """
    Cut shares for positions whose return is highly correlated with
    any *already-placed* position in the book.
    """
    placed = []
    for p in positions:
        corrs = [returns_df[p['symbol']].corr(returns_df[q['symbol']])
                 for q in placed]
        if any(abs(c) >= threshold for c in corrs):
            p['shares'] = int(p['shares'] * factor)
            p['note'] = 'cut for correlation'
        placed.append(p)
    return placed
```

## Relationships

### Within Chapter 16
- Direct corollary of [[06 Diversification]] — diversification's benefits assume independence; this rule corrects when independence is fake.
- Combines with [[08 Market Volatility Adjustments]] — the leverage cut here is on top of volatility-based sizing, not instead of it.

### Outside Chapter 16
- **Chapter 14** — diversifying across systems and parameter sets, not just markets, is the natural escape hatch when markets you want to trade are correlated.

## When This Concept Works Well
- When the trader checks rolling correlations (e.g., 60-day) before sizing — recent correlations matter more than long-run averages.
- When the cut factor is generous (50% or more) for the second and third correlated positions.

## When It Fails
- When correlations are estimated from calm-market data — they tend to spike to 1.0 during the very crisis the rule is meant to protect against.
- When traders selectively apply the cut only to losing trades, leaving winning correlated positions full-size — that's just rationalisation.
