# 02 — Market Orders vs Limit Orders

## Definition

A **limit order** specifies a price at which you are willing to enter, and only fills if the market reaches that price. A **market order** instructs the broker to fill immediately at the next available price. Schwager's lesson from Figure 12.2: there is always a trade-off between **getting a better price** (limit) and **assuring the trade is implemented** (market). When a trade is *long-term* and *high-conviction*, market orders should be favored, because the cost of missing the trade dwarfs the cost of a few ticks of slippage.

The error in Figure 12.2 was not the *initial* limit at 117.00 — that was reasonable given the prevailing trading-range pattern. The error was **failing to convert to a market order once the price action made the rebound unlikely.**

## Illustration

![[02_market_vs_limit_order.png]]

The recommended sell at 117.00 was never touched. The level was lowered three times and never hit. Meanwhile the market made a large, rapid move in the anticipated direction. The trade was right; the order type made it un-takeable.

## Analogy

You're at a busy bus stop and you spot the right bus pulling up. You can either jump on now (market order) or wait for the next one because you noticed it has fewer people (limit order at a "better" price). If you wait, sometimes the next bus is indeed nicer. But sometimes the next bus is the *last* bus of the night, you don't realize it until it's gone, and now you're walking home in the rain. The skilled commuter knows when "good enough now" beats "perfect later that may never arrive."

## Numeric Example

| Approach | Sell trigger | Outcome |
|---|---|---|
| Limit @ 117.00 | Never touched (high was 116.50) | **Trade missed** — 0 P&L |
| Limit @ 116.50 (revised) | Never touched | Trade missed |
| Limit @ 116.00 (revised) | Never touched | Trade missed |
| **Market @ 113.00** (after rebound failed) | Filled instantly | **+8 points** as price reached 105 |

The "worse" market price of 113 produced 8 points of profit. The "better" limit prices produced zero.

## Python

```python
from chapter12_concepts import simulate_limit_buy, simulate_market_buy
import pandas as pd

# A market that pokes higher then collapses without retesting the limit.
df = pd.DataFrame({
    "open":  [115.0, 116.0, 116.4, 115.8, 114.0, 110.0, 106.0],
    "high":  [115.8, 116.4, 116.6, 116.0, 114.5, 110.5, 106.5],
    "low":   [114.5, 115.7, 115.9, 113.5, 109.0, 105.5, 102.0],
    "close": [115.6, 116.2, 116.1, 113.8, 109.5, 106.0, 103.0],
})

limit  = simulate_limit_buy(df, limit_price=117.00)   # never reached
market = simulate_market_buy(df, signal_index=2)      # fills at next open

print(f"Limit @ 117.00 → filled={limit.filled}")
print(f"Market @ next open → filled={market.filled}, price={market.fill_price}")
# Limit @ 117.00 → filled=False
# Market @ next open → filled=True, price=115.8
```

## Relationships

### Within Chapter 12

- **[[01_Primary_Premise_Violation]]** — the same logic in reverse for *exits*. On invalidation, never put a limit on the way out — exit at the market.
- **[[03_Stop_Placement_Quality]]** — stop orders are themselves a hybrid: triggered by price, then executed as a market order in the resulting direction.

### When is each best?

- **Limit order:** prices are inside a tight, well-defined range; fills near support/resistance offer materially better R:R; you can afford to miss the trade.
- **Market order:** breakout already in progress; long-term trade with large profit potential; news-driven move; reentering a missed trade where the original limit failed (this is the chapter's core lesson).

### Outside the chapter

- **Chapter 8 — Midtrend Entry.** Pyramiding into an existing trend almost always argues for market orders — by definition, you're chasing momentum already in motion.
- **Chapter 16 — Planned Trading Approach.** The trader's notebook records the order *type* used; reviewing missed-trade columns reveals whether limit-order discipline is actually costing money.
- **Chapter 17 — 82 Trading Rules.** "Don't try to pick a top or bottom" implicitly favors market orders on confirmation rather than limits at imagined turn levels.

## Source

- Schwager, *Getting Started in Technical Analysis*, Ch. 12, Figure 12.2 (p. 183–184)
- Code: [`chapter12_concepts.py → simulate_limit_buy(), simulate_market_buy()`](code/chapter12_concepts.py)
- Image: [`02_market_vs_limit_order.png`](images/02_market_vs_limit_order.png)
