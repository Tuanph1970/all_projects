# 15 Segmented Trade Analysis

**Step 7a — sub-tool of [[14 Personal Trading Analysis]]**

## Definition

**Segmented trade analysis** is the practice of partitioning a trade history along one or more dimensions and computing performance metrics — net P&L, win rate, average win, average loss, **expectancy** — for each partition separately.

The dimensions Schwager singles out:

| Dimension | Question it answers |
|-----------|--------------------|
| **Long vs short** | Am I biased? Does my edge work in both directions? |
| **By market** | Which symbols pay me? Which charge me tuition? |
| **By holding period** | Day trades, swings, position trades — am I best at one and worst at another? |
| **Aligned with system or against it** | Are my discretionary overrides helping or hurting? |
| **By time of day / day of week** | Is there a slot where my edge breaks down? |
| **By volatility regime** | Do I survive only the calm markets and bleed during noisy ones? |

The single most important metric per segment is **expectancy** — the average P&L per trade — because it tells you whether each segment, averaged across many samples, makes or loses money. A segment with expectancy of +$200 and 50 trades has reliably made $10,000; a segment with expectancy of -$80 and 50 trades has reliably lost $4,000. The aggregate result is the sum of these, which means **a small set of well-behaved segments can be funding a much larger set of bleeding ones**.

## Easy Analogy

A restaurant owner who only looks at the cash drawer at the end of the night sees a profit. The same owner who looks at item-level margins discovers the espresso bar is profitable, the sandwich counter breaks even, and the salad bar loses money on every plate. The "profitable restaurant" was three businesses, two profitable, one quietly subsidised by the others. Closing the salad bar adds 30% to the bottom line and nobody misses it.

Segmented analysis is the trader's item-level margin report.

## Numeric / Concrete Example

100 trades over the last quarter, segmented by holding period:

| Holding period | # | Win % | Avg Win | Avg Loss | Expectancy | Total P&L |
|---------------|---|-------|---------|----------|-----------|-----------|
| **< 1 day (intraday)** | 40 | 55% | $250 | $400 | **-$42** | -$1,680 |
| **1–5 days (swing)** | 35 | 48% | $1,400 | $700 | **+$308** | +$10,780 |
| **> 5 days (position)** | 25 | 60% | $2,800 | $1,100 | **+$1,240** | +$31,000 |

**Aggregate: +$40,100 across 100 trades.** Looks healthy.

But the segmentation is brutal:

- The intraday segment is **slightly negative expectancy**. It also occupies 40% of the trade count — meaning 40% of the trader's screen time, commissions, and emotional capital is producing **less than zero**.
- Position trades have 12× the expectancy of swing trades and 30× the headcount-adjusted contribution of intraday trades.

**Recommended action:** stop intraday trading entirely. Reallocate that screen time to identifying more position-trade candidates. Estimated improvement: cut commissions on 40% of trades, reduce emotional load, retain 100% of profits.

A trader who never segments would conclude: "I made $40k, I'll keep doing what I'm doing." That's the trap.

## Python Code

Implemented in [[04_trade_analysis.py]]:

```python
from collections import defaultdict
from statistics import mean

def segment_by_column(trades, key):
    """Group trades by a categorical key (e.g. 'direction', 'market', 'holding_bucket')."""
    out = defaultdict(list)
    for t in trades:
        out[t[key]].append(t)
    return dict(out)

def expectancy(trades):
    """Average P&L per trade. Sample-size matters — read alongside len(trades)."""
    return mean(t['net_pnl'] for t in trades) if trades else 0.0

# Composable: segment by direction, then by holding period within each.
for direction, ds in segment_by_column(all_trades, 'direction').items():
    for bucket, ts in segment_by_column(ds, 'holding_bucket').items():
        print(f"{direction:5s} {bucket:10s}  n={len(ts):3d}  E={expectancy(ts):+8.2f}")
```

A useful refinement: report a **standard error** alongside expectancy, since 8 trades with a positive expectancy is suggestive while 80 trades with the same expectancy is conclusive.

## Relationships

### Within Chapter 16
- One half of [[14 Personal Trading Analysis]]; the other half is [[16 Equity Chart]].
- Diagnoses the symptoms surfaced by the equity chart.
- Provides the evidence that drives changes to [[01 Trading Philosophy]] (drop a strategy), [[02 Market Selection]] (drop a market), or [[03 Risk Control Plan]] (cap exposure to a weak segment).
- Acts on the data structure of [[12 Traders Notebook]]; the qualitative explanations in [[13 Traders Diary]] often explain *why* a segment is broken.

### Outside Chapter 16
- **Chapter 15 — Testing Systems** — the same partition-and-measure technique used to evaluate a backtested system. A trader's live record is just a one-replication "system" to be analysed the same way.

## When This Concept Works Well
- When segments are defined **before** running the analysis, not chosen afterwards. Slicing post-hoc until a flattering number appears is the trader's version of p-hacking.
- When sample sizes per segment are reported alongside expectancy. Tiny segments produce noisy expectancies that look more meaningful than they are.
- When the analysis output produces **one specific rule change** per quarterly review, not a list of vague intentions.

## When It Fails
- When the trader segments only the losers — confirmation bias dressed up as analysis.
- When small-sample segments (n < 20) are treated with the same confidence as large-sample segments. A "winning intraday segment" with 7 trades is a coin-flip story.
- When a clearly losing segment is preserved because it's "the one I enjoy". Hobbies are fine; speculating on hobbies is expensive.
