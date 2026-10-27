# Backlog #90 — deepening the EM-4 history to 2004, and what it showed

**Task:** `deep_history_dump.py` set `START = "2008-01-01"`. Lower it, re-pull, and
re-run the EM-4 bottoms test on the longer history — keeping #87's pre-registered
criterion rather than inventing a new one after seeing the data.

**Outcome:** the data task is done and the extra history is real, but it is far smaller
than the register assumed, and the re-test still **fails the criterion, 0 of 3**. The
finding worth keeping is not the verdict — that did not change — it is *why* the numbers
moved: **EM-4's near-miss was a sampling-phase artefact.**

---

## The register's premise was wrong in two ways

#90 said the dump "MISSES 2004-2008 — which contains the entire 2006-07 VN bubble AND
ITS MARCH-2007 TOP". Measured on the preserved 2008-vintage file:

| | claimed | actual |
|---|---|---|
| index start | 2008-02-18 | **2007-01-19** |
| bars dated 2007 | none | **235** |
| March-2007 top | missing | **present — max close 1170.67 on 2007-03-12** |
| 2009 bottom | — | present — 235.50 on 2009-02-24 |

So the old dump already held the top *and* the whole crash to 235.50. What was missing
was the bubble's **ascent** (2004-01-05 → 2007-01-18), not a bottom — and E&M's claim is
about bottoms.

The second error is subtler and matters more: the binding constraint was never the index
history. It is the **constituent** history, because MEI is the percentage of a *universe*
in a bullish major trend and `MIN_UNIVERSE = 10`.

## The vendor does serve more, but the universe does not

VCI returns bars **earlier than the requested start**, which is why the old file begins
2007-01-19 despite asking for 2008 — and why the limit was easy to miss. Probed directly
before changing anything:

| symbol | in the 2008 dump | with `start=2004` |
|---|---|---|
| ACB | 2007-02-02 | 2006-11-21 |
| SSI | 2007-01-23 | 2006-12-15 |
| FPT | 2007-02-06 | 2006-12-13 |
| VNM | 2007-02-06 | 2006-01-19 |
| REE | 2007-02-06 | **2002-12-04** |

VNINDEX itself runs from **2004-01-05** (5,667 bars); asking for 2000 returns the same,
so that is the vendor's floor.

What the re-pull actually gained:

| | 2008 vintage | 2004 vintage | gain |
|---|---|---|---|
| index bars | 4,903 from 2007-01-19 | 5,667 from 2004-01-05 | **+764** |
| symbol rows | 320,237 | 322,650 | **+2,413 (+0.75%)** |
| earliest symbol bar | 2007-01-23 | 2002-12-04 | |
| **MEI readings** | 4,857 from 2007-04-24 | 4,895 from **2007-03-01** | **+38** |

The universe reaches ten listed names only on **2006-12-13**, so three extra years of
index history buy **38 extra breadth readings** — about two months. The thin-early-universe
caveat #87 raised does get worse, exactly as predicted: those 38 readings are computed
off a **10–11 symbol** universe.

## The re-test: still 0 of 3, and every t weaker

Criterion, fixed in `em4_mei_study.py` before any of this work and left untouched:

> 1. forward market return after a bottom-decile MEI reading is significantly higher
>    than the unconditional forward return; **and**
> 2. it holds at **more than one** horizon (10, 20, 60).

The 2008 baseline was reproduced first, exactly, so the comparison is attributable to the
data and nothing else:

| horizon | n (2008 → 2004) | edge (2008 → 2004) | Welch t (2008 → 2004) |
|---|---|---|---|
| 10 | 25 → 29 | +2.46% → **+1.55%** | +1.88 → **+1.22** |
| 20 | 16 → 18 | +2.95% → **+1.71%** | +1.59 → **+0.88** |
| 60 | 11 → 12 | +12.57% → **+8.49%** | +1.73 → **+1.09** |

**Criterion fails, 0 of 3** — as before, but from further away.

## The 38 readings are the entire cause, and they contain no bottoms

Two checks pin this down.

**None of the added readings is a low-MEI day.** 0 of 38 sit at or below 10%. They are
the March-2007 top, at *maximum* breadth:

```
  date         MEI  classified  idx close   fwd60d
  2007-03-01  100.0%       10    1123.07   -4.02%
  2007-03-13  100.0%       11    1158.27  -10.15%
  2007-03-19   90.9%       11    1133.34   -7.51%
  2007-04-16   36.4%       11     983.00   +3.33%
```

So the deterioration is not new bottom evidence arriving. Yet `n_low` *rose*, 25 → 29.

**Trimming them back reproduces the old numbers exactly.** Same bars file, same 5,667-bar
index, series truncated to the old start date:

| series | h10 | h20 | h60 |
|---|---|---|---|
| 2004 full (4,895 readings) | n=29, t=+1.22 | n=18, t=+0.88 | n=12, t=+1.09 |
| trimmed to 2007-04-24 (4,857) | n=25, **t=+1.88** | n=16, **t=+1.59** | n=11, **t=+1.73** |

Identical to #87. The +764 index bars and +2,413 symbol rows change nothing; **the 38
readings change everything.**

The mechanism is in `forward_returns`: `WARMUP_POINTS = 250` is an *index* into the
series, and non-overlap is enforced by taking the earliest qualifying day and skipping
forward by `horizon`. Start the series 38 readings earlier and the harvest grid re-phases,
selecting largely different days. (It is not the decile cutoff — at the 2009-02-24 bottom
that is 0.00% in both vintages.)

## The headline: the near-miss was phase-dependent

Dropping the first *k* readings changes nothing about the market, only where the grid
starts:

| k | series starts | t₁₀ | t₂₀ | t₆₀ |
|---|---|---|---|---|
| 0 | 2007-03-01 | +1.22 | +0.88 | +1.09 |
| 5 | 2007-03-08 | +0.83 | +0.53 | +0.93 |
| 15 | 2007-03-22 | +1.63 | +1.71 | +1.03 |
| 20 | 2007-03-29 | +1.81 | +1.53 | +1.08 |
| 30 | 2007-04-12 | +1.73 | +0.84 | +1.11 |
| 40 | 2007-05-02 | +1.83 | +1.52 | +1.67 |

| horizon | t range | spread |
|---|---|---|
| 10 | +0.83 … +1.83 | 1.00 |
| 20 | +0.53 … +1.71 | 1.18 |
| 60 | +0.93 … +1.67 | 0.75 |

#87's published 1.88 / 1.59 / 1.73 sit at the **top** of their own phase range. The
verdict is robust — no phase reaches significance — but the *characterisation* is not:
"t consistently 1.6–1.9, just short three times over" describes one grid phase, not the
data. Across phases t is typically 0.9–1.5.

This does not refute E&M's claim either. It says the statistic is too unstable at
n = 11–29 to support the "directionally supported, just short" reading #87 recorded, and
that **n remains the binding constraint — not history depth.** Three more years of index
bars could not help, because breadth has no constituents to measure there.

## Decisions

* **`START` stays at 2004-01-01.** More complete data, adopted even though it makes the
  EM-4 figure *worse* — picking the vintage that flatters a result is how a workstream
  stops being evidence. The trimmed-reproduces-old check is what makes it safe to adopt:
  nothing else moved.
* **`MIN_UNIVERSE`, `WARMUP_POINTS` and the criterion are untouched.** Changing any of
  them now, having seen the data, is precisely the post-hoc fiddling #90 warned against.
* **The sampler weakness is registered, not fixed** (Backlog #99). Averaging over all
  phases — or using every overlapping observation with a block bootstrap — would give a
  phase-independent statistic. That has to be pre-registered and run once, not tuned
  against this data.

> **OUTCOME, Backlog #99 (2026-10-27).** Done, pre-registered in a commit that landed
> before the estimator was written. Every qualifying day plus a moving-block bootstrap
> gives t = **+0.46 / +0.55 / +0.79** — fails 0 of 3, and no window tested reaches
> +1.50, so the near miss is unavailable at any phase. Two things this session found
> that are worth more than the verdict: a **naive** Welch t on the same full sample
> reads +1.26 / +2.01 / +2.83 and would have *passed* the criterion 2 of 3 (the
> bootstrap deflates it 2.8–3.6×), and the phase sweep's residual movement is **not**
> re-selection — at h60, k=40 drops 37 observations of which 34 are low-MEI days
> averaging −23.65%, i.e. 18% of the low arm and the strongest counter-evidence in the
> series. #99's own pre-registered prediction (that the sweep spread would collapse)
> **failed**, and is reported as failed. See `docs/backlog99_phase_independent_em4.md`.

## Reproducing

```bash
cd stock_microservices/services/decision-helper-service
PYTHONPATH=. python3 tests/deep_history_dump.py /tmp/deep_bars.tsv /tmp/deep_index.tsv
PYTHONPATH=. python3 tests/em4_mei_study.py
```

~5–6 minutes for 92 symbols at the 20 req/min guest quota (Backlog #49 would cut it to
a third). Both vintages were kept side by side during this work via `EM4_BARS` /
`EM4_INDEX`, which is what made the trim check possible.
