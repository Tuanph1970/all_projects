# 08 Market Volatility Adjustments

**Element 5 of [[03 Risk Control Plan]]** · [[00 Chapter 16 Index]]

![[08_volatility_equity_adjust.svg]]

## Definition

**Volatility-based sizing** is the rule that the *number* of shares or contracts traded in any market should fall as the market's volatility rises. Two layers:

1. **Across markets** — fewer units in volatile markets than in calm ones, given the same dollar risk budget.
2. **Within a single market over time** — as a market's volatility expands or contracts, position size adapts dynamically.

The result is a portfolio where every position carries roughly the same dollar risk — even though one might be 1,500 shares of a quiet utility and another might be 50 shares of a momentum tech name.

## Easy Analogy

When you fill a glass with water, you tilt it slowly because the water's surface is calm. Pouring soda is the same volume but the foam means you tilt less and pour slower — the same "amount poured" comes out of fewer glugs. Wild markets are foamy. Calm markets are flat. The pour (your dollar risk) is constant; the technique (your share count) adjusts.

## Numeric / Concrete Example

Same risk budget ($3,000), same trader, two different markets:

| Market | Last close | ATR(14) | Stop = 2×ATR | Risk/share | Max shares | Capital used |
|--------|-----------|---------|---------------|------------|------------|--------------|
| KO (calm) | $60 | $1 | $2 | $2 | 1,500 | $90,000 |
| TSLA (wild) | $250 | $10 | $20 | $20 | 150 | $37,500 |

If you sized purely by *capital*, you might buy $50,000 of each — but the TSLA position would be wagering $5,000 on a typical 2-ATR move, while KO would only wager $1,667. The trader unknowingly takes on 3× the risk in TSLA. Volatility sizing equalises that.

## Python Code

```python
import pandas as pd

def atr_position_size(df, equity, risk_pct=0.02, atr_mult=2.0, period=14):
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([high - low,
                    (high - close.shift()).abs(),
                    (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean().iloc[-1]
    stop_dist = atr_mult * atr
    return int((equity * risk_pct) // stop_dist)
```

Full implementation: [[02_volatility_sizing.py]].

## Relationships

### Within Chapter 16
- Inseparable from [[04 Maximum Risk Per Trade]] — this rule is *how* you keep dollar risk constant when the markets aren't.
- One of three filters in [[02 Market Selection]] — extreme-volatility markets may simply be excluded for small accounts.
- Defines the stop distance used by [[05 Stop-Loss Strategy]] when an ATR-based approach is preferred over a chart-based stop.

### Outside Chapter 16
- **Chapter 9** — discussions of stop placement around volatility envelopes feed directly into the multiplier choice here.
- **Chapter 14** — moving average bands and other volatility-derived signals share the underlying ATR concept.

## When This Concept Works Well
- When traders rebalance position size whenever ATR shifts meaningfully (say, by 30%+).
- When the volatility window matches the holding period — short-term traders use shorter ATR periods, swing traders longer.

## When It Fails
- When traders only adjust *up* (in calm markets) but forget to adjust *down* in volatile ones.
- When ATR is computed on too short a window — sizing becomes jittery and trades get scaled in and out unnecessarily.
