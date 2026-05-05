---
concept: "Putting Chart Patterns in Context"
chapter: 7
order: 4
tags: [multi-timeframe, context, synthesis, weekly-vs-daily, chapter-7]
source: "Schwager, Ch. 7, pp. 123-124"
---

# 4. Putting Chart Patterns in Context (Multi-Timeframe Analysis)

## Definition

**Putting chart patterns in context** means recognising that the meaning of a chart pattern depends on the **broader picture** it sits inside — most importantly, the **longer-timeframe chart** of the same instrument. A pattern that looks neutral or ambiguous on a daily chart can become decisively bullish or bearish when you zoom out to the weekly view.

Schwager illustrates this directly with the September 1992 Eurodollar (Figure 7.4): a daily chart showing what looks like a generic trading range becomes obviously bullish once the weekly continuous-futures chart reveals the market is sitting **near the top of a five-year range, with a flag pattern just formed** — a strongly bullish long-term setup. In context, only the **upside** breakout deserves to be taken seriously.

A more general formulation:

> The successful chart trader synthesises individual patterns with (a) the longer-timeframe chart, (b) recent volatility regime, (c) where price sits within multi-year levels, and (d) the broader market environment.

This is the concept that converts chart analysis from pattern-matching into **judgement**.

## Simple Analogy

Multi-timeframe context is like reading a single sentence vs. reading the whole paragraph. The sentence *"He picked up the knife"* could mean dinner is starting or a murder is about to happen — depending entirely on the surrounding paragraph. The *daily* chart is the sentence. The *weekly* chart is the paragraph. The *monthly* chart is the chapter. You can't interpret the sentence honestly without at least skimming the paragraph it lives in.

## Chart Illustration

![[04_context.png]]
*Top: weekly chart over ~6 years — market is in the upper part of a long-term range, suggesting a bullish bias. Bottom: the same period's daily chart, which in isolation looks like a neutral trading range. The weekly view tells you which side of the daily breakout to take.*

## Real Numeric Example — applying context to the Eurodollar trades

Recall the three trades from [[02_Risk_Control]]:

| # | Direction | P&L (pts) | Direction matches weekly bias (long)? |
|---|---|---|---|
| 1 | Long  | −0.50 | ✅ Yes (kept) |
| 2 | Short | −0.39 | ❌ No (filtered) |
| 3 | Long  | +2.05 | ✅ Yes (kept) |

Filtering by the long-term bullish bias would have removed the short trade entirely:

| Strategy | # Trades | Wins | Net (pts) | Net (USD) |
|---|---|---|---|---|
| All breakouts | 3 | 1 | +1.17 | +$2,913 |
| **Long-only (matches weekly bias)** | 2 | 1 | **+1.55** | **+$3,888** |

**+33% improvement in net P&L from a single piece of multi-timeframe information.** And the win rate jumps from 33% to 50%. This is the leverage of context.

## Code

```python
# Apply a long-term bias as a filter on already-generated trades
def filter_by_context(trades, bias):
    """bias = +1 (bullish weekly), -1 (bearish weekly), 0 (no filter)."""
    return [t for t in trades if bias == 0 or t.direction == bias]

# Build weekly view to derive the bias
def derive_weekly_bias(weekly_close, lookback=52):
    """Bullish if price > rolling 52-week mean of midpoint, else bearish."""
    mid = (weekly_close.rolling(lookback).max()
         + weekly_close.rolling(lookback).min()) / 2
    return +1 if weekly_close.iloc[-1] > mid.iloc[-1] else -1

bias  = derive_weekly_bias(df["close"].resample("W").last())
kept  = filter_by_context(trades, bias)
print(f"Bias={bias}, kept {len(kept)}/{len(trades)} trades, "
      f"net={sum(t.pnl_pts for t in kept):+.2f}pt")
```

Full source: [[ch7_master.py]]

## Relationships

### Within Chapter 7
- **Multiplies [[02_Risk_Control]]:** removes entire categories of bad trades before they're taken — fewer stops triggered, smaller drawdown.
- **More holistic than [[03_Confirmation_Conditions]]:** confirmation looks *forward* a few days from the signal; context looks *backward* across a much longer history.
- **Same logic as [[05_Knowledge_Of_Fundamentals]]:** both apply an *external filter* (one technical, one fundamental) to chart signals.
- **The art of [[07_Art_Vs_Science]]:** "synthesising the various components of the overall picture" is precisely the discretionary skill Schwager's conclusion celebrates.

### Outside Chapter 7
- [[Chapter_3_Trends]] — defining a trend on weekly bars before drilling into daily entries is the canonical multi-timeframe workflow.
- [[Chapter_4_Trading_Ranges]] — a daily trading range that sits at the top of a multi-year trading range carries a *very* different meaning.
- [[Chapter_5_Chart_Patterns]] — flags above the top of a trading range vs. flags inside one (Figures 5.26-5.29) are an explicit context-dependent interpretation.
- [[Chapter_8_Midtrend_Entry]] — entering "in the middle of a move" only makes sense by reading the longer-timeframe trend.
- [[Chapter_12_Real_World_Charts]] — many of the 19 trade case studies open by looking at a longer-timeframe chart first.
- **Outside the book:** Elliott Wave fractal nesting, Dow Theory's primary/secondary/minor trends, Wyckoff's "step back" — every major school teaches multi-timeframe.

### Common multi-timeframe pairings

| Trader type | Long-term frame | Trade-execution frame |
|---|---|---|
| Position trader | Monthly | Weekly |
| Swing trader | Weekly | Daily |
| Day trader | Daily | 15-min / 5-min |
| Scalper | 15-min | 1-min / tick |

The *ratio* between the two timeframes is roughly 4:1 to 6:1 — fine enough to act, coarse enough to provide independent information.

### When does context help vs. mislead?
| Situation | Effect of using long-term context |
|---|---|
| Strong long-term trend, daily noise | ✅ Excellent — filter daily counter-trend signals |
| Long-term sideways, daily breakout | ⚠️ Context offers little; trade the daily |
| Just-completed long-term trend reversal | ❌ "Context" is stale; it points the wrong way |
| Long-term and short-term agree | ✅ Highest-conviction setups |
| Long-term and short-term disagree | ⚠️ Reduce size or skip |

---

**Source:** Schwager (1999), Ch. 7, pp. 123-124, Figure 7.4.
**Tags:** #multi-timeframe #context #weekly-chart #synthesis #chapter-7
