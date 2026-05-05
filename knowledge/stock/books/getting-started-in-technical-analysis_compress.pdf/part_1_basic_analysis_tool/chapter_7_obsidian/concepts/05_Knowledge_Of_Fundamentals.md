---
concept: "Knowledge of Fundamentals"
chapter: 7
order: 5
tags: [fundamentals, hybrid-analysis, filter, edge, chapter-7]
source: "Schwager, Ch. 7, p. 124"
---

# 5. Knowledge of Fundamentals (Filtered Signals)

## Definition

Schwager's fifth defence of chart analysis is that a trader who **also has skill in fundamental forecasting** can use the fundamental view as a *filter* on technical signals. Specifically:

- If the long-term fundamental forecast is **bullish** → only act on **buy** chart signals.
- If the long-term fundamental forecast is **bearish** → only act on **sell** chart signals.
- If the fundamental projection is **neutral** → take both buy and sell signals.

This requires only that the trader's fundamental forecasting accuracy is **better than 50/50** — a low bar, but a meaningful one. The point is that fundamentals and technicals are **orthogonal sources of information**: combining them eliminates a class of trades that look fine technically but conflict with what the fundamentals are saying about the longer term.

The crucial framing: this is **not** "fundamentals vs. technicals" — it's **fundamentals as a directional filter on technical signals**.

## Simple Analogy

This is like **looking at the weather forecast before deciding whether to bring the umbrella you packed**. You always pack the umbrella (the chart skill is always there). But on the morning you see the forecast says clear blue skies all day, you confidently leave the umbrella by the door — even if a few clouds appear at lunch (a bearish chart signal). The forecast (fundamentals) doesn't tell you whether it's currently raining at this exact second; the chart does. But the forecast tells you which direction to lean when the chart is ambiguous.

## Chart Illustration

![[05_fundamentals.png]]
*The same Eurodollar series with all three breakout signals marked. The bullish fundamental view (in this period: declining short-term rates → higher Eurodollar prices) keeps the two long entries (highlighted) and filters out the short trade (faded).*

## Real Numeric Example — Eurodollar with bullish fundamental bias

In the early 1990s, the Fed was actively easing — fundamentals supported lower yields and therefore *higher* Eurodollar prices (Eurodollar futures price = 100 − yield). A trader holding a bullish fundamental view would filter the trades:

| Strategy | # Trades | Wins | Net (pts) | Net (USD) |
|---|---|---|---|---|
| All technical breakouts | 3 | 1 | +1.17 | +$2,913 |
| **Filtered by bullish fundamentals** | 2 | 1 | **+1.55** | **+$3,888** |
| Naive fundamentals only (always long, hold) | 1 | 1 | ~+1.5 | ~+$3,750 |

The hybrid approach captures **+33% more profit** than chart-only and avoids the short trade that fought the fundamentals. Note: a *pure* fundamentalist who simply went long Eurodollars in March 1991 would have done well too — but would have endured large mark-to-market drawdowns during the May–August chop. The hybrid trader sits out the chop and re-enters cleanly.

### Decision matrix in numbers

| Fundamental view | Chart signal | Action | Why |
|---|---|---|---|
| Bullish | Buy | **Take** | Both align — highest-conviction trade |
| Bullish | Sell | **Skip** | Conflicting signals — wait for clarity |
| Bearish | Buy | **Skip** | Conflicting signals — wait for clarity |
| Bearish | Sell | **Take** | Both align — highest-conviction trade |
| Neutral | Buy or Sell | **Take** | Charts are the only input available |

## Code

```python
def filter_by_fundamental(trades, bias):
    """bias = +1 bullish, -1 bearish, 0 neutral. Keep trades whose direction
       agrees with the bias (or all if neutral)."""
    if bias == 0:
        return list(trades)
    return [t for t in trades if t.direction == bias]

# Bullish fundamental view → keep only longs
kept = filter_by_fundamental(trades, bias=+1)
net  = sum(t.pnl_pts for t in kept)
print(f"Filtered: {len(kept)} trades, net {net:+.2f}pt = ${net*2500:+,.0f}")
# Filtered: 2 trades, net +1.55pt = $+3,888
```

Full source: [[ch7_master.py]]

## Relationships

### Within Chapter 7
- **Same mechanism as [[04_Patterns_In_Context]]:** both apply a directional filter to raw chart signals. Context uses the *long-term chart* as the filter; this concept uses the *fundamental forecast*. They can be used together (and often agree).
- **Independent of [[02_Risk_Control]]:** filtering reduces *number* of trades; risk control caps *loss per trade*. Both shrink drawdown via different routes.
- **Different from [[06_Failed_Signals]]:** failed signals exploit *opposite-direction* moves *after* a chart pattern. Fundamentals filter signals *before* entry.

### Outside Chapter 7
- [[Introduction_Fundamental_vs_Technical]] — the entire opening of the book is the great fundamental-vs-technical debate. Chapter 7 §5 is Schwager's resolution: **use both**.
- [[Chapter_1_Charts_Forecasting_Or_Folklore]] — Ms. Trend in the dialogue agrees that "the price chart provides an unambiguous and immediate summary of the net impact of all fundamental and psychological factors." Concept #5 inverts this: even so, *explicit* fundamentals add information.
- [[Chapter_16_Planned_Trading_Approach]] — formalises the "trading philosophy" step: most successful traders combine multiple input streams.
- [[Chapter_18_Market_Wizdom]] — the Market Wizards interviewed (Druckenmiller, Soros) are famously hybrid: they use fundamentals to identify the *direction* and charts to identify the *timing*.
- **Outside the book:** Druckenmiller's "fundamentals tell you what to trade, charts tell you when"; Soros's reflexivity as a fundamental-driving-technical feedback loop.

### When does fundamental filtering work well vs. poorly?
| Situation | Effect of fundamental filter |
|---|---|
| Trader has genuine fundamental edge | ✅ Excellent — orthogonal information adds real value |
| Trader has *zero* fundamental skill | ❌ No better than random; may hurt by adding noise |
| Long-horizon trades (weeks-months) | ✅ Fundamentals dominate longer horizons |
| Day trading / scalping | ⚠️ Fundamentals slow to update; minimal benefit |
| Commodity supply shock | ⚠️ Charts react first; fundamentals lag |
| Macro turning points | ⚠️ Fundamentals are last to confirm; delayed entry costly |

### Edge math (why >50% accuracy is the bar)

If your fundamental view is right with probability p > 0.5, and chart signals are also slightly profitable, the **AND** of two independent positive-edge signals has higher expectancy than either alone — even if neither is impressive on its own. This is the same logic as ensemble methods: independent, individually-mediocre signals combine into one robust signal.

---

**Source:** Schwager (1999), Ch. 7, p. 124.
**Tags:** #fundamentals #hybrid-analysis #filtered-signals #chapter-7
