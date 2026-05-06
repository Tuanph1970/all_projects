# 14 Personal Trading Analysis

**Step 7 of the [[00 Chapter 16 Index|Planned Trading Approach]]**

![[12_personal_analysis.svg]]

## Definition

**Personal trading analysis** is the periodic, brutally honest review of one's own trading record. It has two complementary tools:

- [[15 Segmented Trade Analysis]] — slice the trade history by category (long/short, market, holding period, aligned-with-system or not, etc.) and compute P&L and expectancy per slice.
- [[16 Equity Chart]] — plot account equity over time as a price series and read it like any other chart, watching for danger signals.

The combination matters. The equity chart tells you **whether** something is going wrong; the segmented analysis tells you **what**. Either tool alone is half the diagnosis.

The reason this step is mandatory — even though it's tempting to skip after a good month — is that the data was already paid for. Every trade in the notebook represents real capital risked. Refusing to mine the data wastes a tuition that has already been spent.

## Easy Analogy

A coach reviewing game tape. The team won — the coach reviews the tape anyway. What plays worked, what plays got lucky, who was out of position even on a winning play. Without tape review, the coach can't tell whether the win was earned or borrowed against next week's loss. Trade analysis is game tape for traders.

## The Schwager Hypothesis

Schwager floats a striking claim that makes the case for this step stronger than any other: if every day trader honestly performed segmented analysis on their own results, the day-trading population would shrink by **roughly half overnight**. The implication is that a large fraction of active traders are persistently losing money in a category they could identify in 20 minutes of segmenting — and the only thing protecting them from that knowledge is their reluctance to look.

Whether the exact number is right or not, the point is that **the analysis is cheap, the data already exists, and the avoidance is psychological**.

## Numeric / Concrete Example

A trader reviews 200 trades over six months. Aggregate result: **+8% return**. Looks fine. Then segments:

| Segment | # | Win Rate | Avg Win | Avg Loss | Net |
|---------|---|----------|---------|----------|-----|
| **Trend trades, held > 5 days** | 60 | 48% | $2,400 | $900 | **+$36,400** |
| **Counter-trend, held < 2 days** | 90 | 52% | $400 | $850 | **-$15,800** |
| **News reactions** | 50 | 30% | $1,100 | $1,200 | **-$13,500** |

Aggregate +8% **hides a great strategy carrying two losing strategies on its back**. Drop the bottom two segments and the same trader earns +20% on a third the activity, with less stress and lower commissions. The segmentation didn't just diagnose the problem — it pointed to the precise improvement.

The equity chart for this trader would have shown an upward overall slope but with sharp 5–10% pullbacks every few weeks. Reading it side-by-side with the segmentation reveals each pullback corresponds to a cluster of news-reaction or counter-trend trades.

## Python Code

The full toolkit lives in [[04_trade_analysis.py]]:

```python
from trade_analysis import segment_by_column, expectancy, equity_curve, drawdown_series

# segmented view
for label, trades in segment_by_column(all_trades, key='strategy').items():
    print(f"{label:30s}  n={len(trades):3d}  E={expectancy(trades):+.2f}")

# equity-chart view
curve = equity_curve(all_trades, starting_equity=100_000)
dd = drawdown_series(curve)
print(f"Max drawdown: {dd.min():.1%}")
```

The two outputs answer the two questions:

- `expectancy()` per segment — **what is failing?**
- `equity_curve()` + `drawdown_series()` — **how bad is it, and is it getting worse?**

## Relationships

### Within Chapter 16
- This step is the **feedback engine** of the whole chapter. Findings here feed back into:
    - [[01 Trading Philosophy]] — drop strategies that don't work.
    - [[02 Market Selection]] — drop markets where the edge isn't there.
    - [[03 Risk Control Plan]] — tighten caps where the data shows them to be too loose.
- Triggered by signals in [[16 Equity Chart]], answered by [[15 Segmented Trade Analysis]].
- Consumes the data structure built by [[12 Traders Notebook]] and the explanations in [[13 Traders Diary]].

### Outside Chapter 16
- **Chapter 15 — Testing Systems** — the same analytical framework used to evaluate a system in backtest is now applied to the trader's own actual record. The trader is, in effect, a system whose performance is measured the same way.
- **Chapter 18 — Rule #11 (Discipline)** — the willingness to look at the equity chart on a losing month is itself a discipline test.

## When This Concept Works Well
- When done at fixed intervals — monthly is the typical cadence — regardless of recent performance. Looking only when things feel bad guarantees biased samples.
- When findings produce **specific changes** to specific rules, with a date stamp. "Be more disciplined" is not a finding; "stop taking news-reaction trades after 2 pm" is.

## When It Fails
- When the trader stops at the aggregate number and doesn't segment. A headline +8% can hide everything that matters.
- When losses are explained away ("that was an unusual month") instead of categorised. Every loser has a category.
- When the analysis is performed but the rules aren't updated — the loop never closes, and the same diagnoses recur every month.
