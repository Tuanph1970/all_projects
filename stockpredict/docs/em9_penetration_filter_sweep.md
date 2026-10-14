# EM-9 — re-calibrate the breakout penetration filter

**Recommendation: do not change it.** Three independent reasons, below.

Backlog #69. E&M master-list item 128 says **3% of price** for a stock (2% for
the averages); `confirmation/layer.py` uses **0.3–0.5%** by signal kind —
roughly an order of magnitude looser. The register called the divergence
"undocumented and unmeasured" and set a mandatory `C4` benchmark: a threshold
sweep on VN data reporting **hit rate and signal count** at each level.

Date: 2026-10-14. 32 symbols, ~1,030 evaluated bars each, full
signal → confirmation → stop/target/size replay through the existing backtest
harness (causal by construction: it only ever sees `bars_so_far`).

Reproduce with `tests/em9_penetration_sweep.py` and
`tests/em9_penetration_distribution.py`.

## Reason 1 — the filter does not change hit rate

| threshold | trades | hit rate | expectancy | net P&L | profit factor |
|---|---|---|---|---|---|
| shipped (0.3/0.5%) | 13,696 | 0.411 | −15.13 | −209,959 | 0.933 |
| 0.3% flat | 14,142 | 0.413 | −14.32 | −205,040 | 0.933 |
| 0.5% flat | 13,637 | 0.411 | −15.02 | −207,484 | 0.936 |
| 1.0% | 12,465 | 0.411 | −15.83 | −200,333 | 0.912 |
| 1.5% | 11,404 | 0.412 | −15.58 | −183,441 | 0.935 |
| 2.0% | 10,404 | 0.412 | −17.34 | −184,910 | 0.916 |
| **3.0% (the book)** | **8,908** | **0.419** | **−14.70** | **−132,783** | **0.975** |

**Hit rate moves from 0.411 to 0.419 across a tenfold change in the
threshold.** That is the benchmark the register asked for, and it answers the
question: the penetration filter is not selecting better signals at any level.

Net P&L does improve 37% at 3%. It improves because the strategy takes **35%
fewer trades**, not because the surviving trades are better — expectancy per
trade is flat (−15.13 → −14.70, inside the noise of the other rows). On a
negative-expectancy strategy *any* arbitrary restriction "improves" net P&L.
That is not evidence a filter works.

## Reason 2 — a single threshold is structurally wrong

The four signal kinds live on completely different penetration scales:

| signal kind | n | median | p90 | ≥0.5% | ≥3% (the book) |
|---|---|---|---|---|---|
| SR_BREAKOUT | 6,318 | **4.47%** | 12.77% | 100% | **75%** |
| MA_CROSS | 181 | 2.30% | 6.03% | 87% | 37% |
| N_DAY_BREAKOUT | 1,272 | 1.03% | 4.15% | 73% | 18% |
| SR_BOUNCE | 264 | **0.56%** | 2.00% | 52% | **3%** |

An **eightfold spread in median penetration**. So the book's 3% is two
different policies depending on which signal it meets: nearly inert for
`SR_BREAKOUT` (75% still pass) and nearly total for `SR_BOUNCE` (97%
eliminated).

This is the part the outcome table cannot show, and it is why "adopt the book's
number" is not a coherent change. E&M's 3% was a rule for judging *one* thing —
a penetration of a neckline or trendline drawn by hand. Applying it uniformly
to a moving-average cross, a Donchian breakout, and a bounce off support treats
four different measurements as one.

## Reason 3 — this backtest cannot arbitrate the question

Measured on 12 symbols:

| | trades | gross P&L | commission | net | bars per trade |
|---|---|---|---|---|---|
| shipped | 5,014 | −27,860 | **50,140** | −78,000 | **2.46** |
| 3% | 3,329 | −13,919 | 33,290 | −47,209 | 3.71 |

**Commission is 1.8× the size of the gross loss.** At a trade every 2.46 bars,
on 100,000 of equity with a flat 10 per trade, fees alone consume half the
starting capital. Whatever the sweep is measuring, it is mostly measuring
turnover against a fee schedule — not signal quality.

Gross P&L is negative too, so the signals do lose on their own merits. But the
margin is swamped, and a benchmark whose output is dominated by a cost model
cannot settle a threshold question. Logged as Backlog #80, because it blocks
more than this: the register proposes EM-3 (basing-point stops) as "A/B-able in
the existing backtest harness", and on this evidence it is not yet.

## Decision

`MIN_PENETRATION` is unchanged. The divergence from the book is now
**documented and measured** rather than merely inherited, which is what the
register actually asked for — it anticipated "possibly no behaviour change".

If the filter is revisited, the shape of the answer should be per-kind
thresholds expressed in units that mean the same thing across kinds — ATR
multiples, or a percentile of that kind's own penetration distribution — rather
than one percentage borrowed from a book that was judging a different
measurement. The distribution table above is the input for that.

What would make a future sweep decisive: fix the turnover and cost realism
first (#80), then re-run. A threshold study on a benchmark that loses 1.8× its
gross loss to fees cannot distinguish a good filter from a quiet one.
