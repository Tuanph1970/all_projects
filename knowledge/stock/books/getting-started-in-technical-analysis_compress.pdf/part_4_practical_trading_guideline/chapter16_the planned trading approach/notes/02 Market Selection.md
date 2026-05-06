# 02 Market Selection

**Step 2 of the Planned Trading Approach** · [[00 Chapter 16 Index]]

![[03_market_selection.svg]]

## Definition

**Market selection** is the deliberate choice of which stocks, futures, or instruments to actively follow and trade. Time and capital are finite; you cannot competently track every market. The chapter offers three filters:

1. **Suitability** — does your trading approach work in this market historically?
2. **Diversification** — are the markets you've chosen driven by *different* underlying forces?
3. **Volatility** — is the dollar-volatility per contract/share compatible with your account size?

## Easy Analogy

Picking markets is like a chef stocking a small kitchen. You can't carry every ingredient, so you choose ingredients that:
- match the dishes you actually know how to cook (suitability),
- complement each other instead of overlapping (diversification — three kinds of basil isn't versatile),
- and fit on your shelves (volatility — that giant ham you can't fit in the fridge will spoil).

## Numeric / Concrete Example

A trader with $50,000 wants to build a 6-position portfolio.

**Bad list (high correlation, all tech):** AAPL, MSFT, GOOGL, META, AMZN, NVDA. When tech sells off (e.g., the 2022 rate-driven drawdown), every position bleeds together. Effective diversification ≈ 1 position.

**Better list (six different drivers):**

| Symbol | Sector | Beta to S&P | Driver |
|--------|--------|-------------|--------|
| AAPL | Tech | 1.2 | consumer demand, supply chain |
| JPM | Financials | 1.1 | rate spreads, credit cycle |
| XOM | Energy | 0.8 | oil price |
| JNJ | Healthcare | 0.6 | drug pipeline, defensive flows |
| PG | Consumer staples | 0.5 | inflation, FX |
| GLD | Commodity ETF | -0.1 | crisis hedge, real rates |

A bad week in any one driver rarely poisons the whole book.

## Python Code

A pragmatic correlation check before adding a market:

```python
import pandas as pd

def is_too_correlated(candidate_returns, existing_returns_df, threshold=0.7):
    """Return any existing market whose corr exceeds threshold."""
    corrs = existing_returns_df.corrwith(candidate_returns)
    return corrs[corrs.abs() >= threshold].to_dict()

# Example: about to add NVDA to a book that already holds AAPL, MSFT
# corrs = is_too_correlated(nvda_returns, df_existing[['AAPL','MSFT']])
# if corrs:  print('Skip — already covered by:', corrs)
```

## Relationships

### Within Chapter 16
- Each filter (suitability, diversification, volatility) ties into [[03 Risk Control Plan]]:
  - Diversification is itself element #3 of the risk-control plan ([[06 Diversification]]).
  - Volatility informs [[08 Market Volatility Adjustments]] for sizing.
- [[01 Trading Philosophy]] determines what counts as "suitable" — a trend-follower's "suitable" market is different from a mean-reverter's.

### Outside Chapter 16
- **Chapter 14** — extensively discusses why diversification across markets, systems, and parameter sets dampens equity drawdowns.
- **Chapter 1, Figures 1.1 & 1.2** (1979–1980 silver, 1994 coffee) — examples of giant moves you needed to be in *some* market to catch. Reinforces the case for trading many markets.

## When This Concept Works Well
- When you have ≥ 6 distinctly-driven markets in the book.
- When your suitability check uses 10+ years of data, not just last year's rip.

## When It Fails
- When "diversification" is cosmetic (six different bank stocks).
- When extreme-vol markets are added because they're "exciting" — they will dominate the book's risk.
