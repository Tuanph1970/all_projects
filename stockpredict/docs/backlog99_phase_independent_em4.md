# Backlog #99 — a phase-independent EM-4 estimator

**Part 1, the pre-registration, is committed BEFORE the estimator is written or
run.** The git history is the evidence for that ordering; it is the only thing
that makes the rest of this document worth reading. Part 2 is appended in a
later commit and may not change a word of Part 1.

---

# Part 1 — pre-registration (committed 2026-10-27, before any output)

## Why this item exists

`forward_returns` enforces non-overlap by taking the earliest qualifying day
and skipping forward by `horizon`. The set it selects is therefore fixed by
*which index comes first* — and `WARMUP_POINTS = 250` is an index into the
series, not a date. Begin the series a few readings earlier and the whole
harvest grid re-phases onto largely different days.

Backlog #90 measured the consequence rather than suspecting it: shifting the
start by up to 44 readings — changing nothing whatever about the market — moves
Welch t across **+0.83…+1.83 (h10), +0.53…+1.71 (h20), +0.93…+1.67 (h60)**.
#87's published 1.88 / 1.59 / 1.73 sat at the top of all three ranges, which is
why its "directionally supported, just short three times over" reading had to
be withdrawn.

The verdict held at every phase tested, so this is **not an attempt to rescue
the claim**. It is that a statistic this sensitive to an arbitrary offset
cannot support *any* characterisation, favourable or not.

## Disclosure: I am not a naive observer

I ran that phase sweep. I therefore know, before designing this estimator,
roughly where the per-phase statistics sit and that EM-4 fails at every phase I
looked at. **This is not a clean pre-registration and I will not claim it is
one.** Three constraints are adopted specifically to limit what that knowledge
can buy:

1. **The decision criterion is inherited verbatim, not chosen.** It is #87's,
   fixed before any of this data existed. I am not free to pick a threshold
   that suits what I have seen.
2. **The classification of a reading as low is untouched** — same expanding
   trailing decile, same `DECILE = 10.0`, same `MIN_UNIVERSE = 10`, same
   `WARMUP_POINTS = 250`. Only the *sampling* changes. So any movement in the
   result is attributable to the sampler and nothing else.
3. **One run, reported whatever it says.** No second estimator if the first is
   unflattering. If I later believe a different estimator is better, that is a
   new pre-registered item, not an edit to this one.

What I genuinely do not know, and cannot infer from the sweep, is the value of
the statistic defined below: it is a different estimator with a different
standard error, computed on all ~4,600 readings rather than 11–29 of them.

## What changes, and what does not

| | |
|---|---|
| MEI construction | unchanged |
| `DECILE`, `MIN_UNIVERSE`, `WARMUP_POINTS` | unchanged |
| low-vs-other classification | unchanged (expanding trailing decile, no hindsight) |
| data vintage | unchanged — the 2004 dump adopted by #90 (5,667 index bars from 2004-01-05; 92 symbols; 322,650 rows) |
| **the sample** | **every qualifying day, instead of a skip-forward grid** |
| **the inference** | **moving-block bootstrap, instead of Welch on a pseudo-independent sample** |
| the criterion | unchanged, inherited from #87 |

The existing `forward_returns` is **kept, not deleted**, so #87's and #90's
published tables stay reproducible. A result nobody can re-derive is not a
record.

## The estimator

**Point estimate.** For each horizon h ∈ {10, 20, 60}: take *every* index
i ∈ [`WARMUP_POINTS`, len(series) − h), classify it low or other exactly as
now, and compute the forward index return over h sessions. The statistic is

    edge(h) = mean(forward return | low) − mean(forward return | other)

No stride, no skip-forward, no phase — there is nothing left for an offset to
move. This is also the maximally precise point estimate available from the
data, which is the secondary reason to prefer it.

**Why not average the old statistic over all h phases.** That was the register's
other suggestion. It is rejected because the mean of t-statistics has no null
distribution to test against, so it would produce a number with no criterion
attachable to it. Averaging the *edge* over all phases is defensible, but it
converges to the all-observations difference in means above — so the estimator
below is that limit, taken directly.

## The inference

Using every day makes the point estimate precise and the naive standard error
**meaningless**: consecutive forward returns overlap by h−1 bars, and low-MEI
days are clustered into a handful of bear markets. Hundreds of low days may
carry only three or four independent episodes. This is exactly the trap #79
documented — and note that #87's "non-overlapping" sample did **not** escape
it either: 11 observations drawn from 3–4 bear markets are not 11 independent
draws. The old design paid for that illusion by discarding 99% of the data.

So: **moving-block bootstrap**, which prices the dependence instead of
pretending it away.

* Resample contiguous blocks of `(low_flag, forward_return)` pairs *jointly*,
  with replacement, preserving within-block order, until the replicate has as
  many observations as the original; recompute `edge` on each replicate.
* **Block length L = 2h** (primary). Forward returns are h−1-dependent by
  construction, so the block must comfortably exceed h; 2h adds slack for real
  market autocorrelation on top of the mechanical overlap.
* **Pre-registered sensitivity: L = h and L = 3h**, reported alongside. Fixed
  now so that it is a robustness report and not a search.
* **B = 2000 replicates, seed 20261027**, fixed now.
* Test statistic: `t_boot(h) = edge(h) / SE_bootstrap(h)`, the literal
  translation of the inherited `t > 1.96`, and directly comparable to the Welch
  t that #87 and #90 published.
* Also reported, as a cross-check and **not** a second criterion: the 2.5th
  percentile of the bootstrap distribution of `edge`.
* Replicates containing fewer than 2 low observations are discarded, and the
  discard count is reported. If more than 10% are discarded the bootstrap is
  too thin to interpret and I will say so rather than quote the number.

## The decision criterion — inherited, unchanged

> 1. forward market return after a bottom-decile MEI reading is significantly
>    higher than the unconditional forward return (`t > 1.96`, directional, as
>    E&M's claim is directional); **and**
> 2. it holds at **more than one** horizon (10, 20, 60).

`t_boot` replaces the Welch t. Nothing else moves.

## A falsifiable prediction about the fix itself

The point of #99 is phase-independence, so that must be *demonstrated*, not
asserted. I will re-run #90's sweep — dropping the first k ∈ {0, 5, 15, 20, 30,
40} readings — against the new estimator.

**Prediction: the t spread collapses to well under half of the old
1.00 / 1.18 / 0.75.** Dropping k readings now removes ≈k observations from a
sample of thousands instead of re-selecting the entire grid, so the residual
movement should be small and monotone-ish rather than erratic.

**If the spread does not collapse, #99 has failed** and I will report it as a
failure rather than redefining success. That is the one outcome that would
invalidate the estimator itself rather than merely answering EM-4.

## Expectations, recorded so they can be wrong

Stated to be checkable, not because they carry any weight:

1. **`t_boot` will be lower than #87's Welch t at most or all horizons** — the
   bootstrap prices episode clustering that Welch-on-11-points ignored. If it
   comes out *higher*, that is a genuine surprise and I should suspect the
   block length before believing it.
2. **The criterion will still fail, 0 of 3.** Every phase tested in #90 failed,
   and a correct standard error should not rescue it.
3. **The edge will stay positive at all three horizons** — that part was stable
   across every phase.

A null here is worth more than the three nulls before it, because for the first
time it would be a null that an arbitrary offset cannot flip.

## What this cannot settle

Nothing here adds data or power. If EM-4 fails, the honest reading remains
#90's: n in the tail is the binding constraint. A better estimator makes the
answer *trustworthy*, not *favourable*, and no amount of statistics manufactures
bear markets that Vietnam has not had.

---

# Part 2 — the result (appended 2026-10-27, after the run)

Part 1 above is unedited. Data: the 2004 vintage adopted by #90 — 92 symbols,
322,650 rows, VNINDEX 5,667 bars from 2004-01-05, MEI 4,895 readings from
2007-03-01.

**The legacy sampler was reproduced first, exactly** — n = 29/18/12 and Welch
t = +1.22 / +0.88 / +1.09, identical to #90 — so sharing the classifier
between the two samplers (`low_flags`) changed nothing, and every difference
below is attributable to the sampler and the inference.

## The pre-registered estimator

| horizon | n low | n other | edge | SE boot | **t_boot** | 2.5th pct | discarded |
|---|---|---|---|---|---|---|---|
| 10 | 211 | 4,396 | +0.72% | 1.58 | **+0.46** | −1.78% | 0 |
| 20 | 208 | 4,387 | +1.75% | 3.16 | **+0.55** | −2.86% | 0 |
| 60 | 191 | 4,367 | +6.24% | 7.92 | **+0.79** | −0.69% | 0 |

**Criterion fails, 0 of 3.** Not one horizon approaches 1.96, and the 2.5th
percentile of the edge is negative at all three. Zero replicates discarded, so
the bootstrap is not thin. All three pre-registered expectations held: t_boot
below #87's Welch t, criterion failed, edge positive everywhere.

This is the strongest form of the null the workstream has produced. It uses
every observation, there is no offset left to choose, and the standard error
prices the dependence rather than assuming it away.

## The finding that matters more than the verdict

I also computed the **naive Welch t on exactly the same all-observations
sample** — the statistic a reasonable person would reach for after deciding to
use all the data:

| horizon | naive Welch t | t_boot | inflation |
|---|---|---|---|
| 10 | +1.26 | +0.46 | 2.8× |
| 20 | **+2.01 → SIG** | +0.55 | 3.6× |
| 60 | **+2.83 → SIG** | +0.79 | 3.6× |

**That reads 2 of 3 significant. It PASSES the criterion.** Switching to the
full sample without pricing the dependence would have produced the
workstream's first "confirmed" E&M result — a headline that E&M's bottoms
claim reproduces on 19.6 years of Vietnamese data, at two horizons, with a
+6.24% sixty-session edge.

It would have been an artefact. 211 low-MEI days are not 211 independent
events; they are a handful of bear markets sampled daily, and consecutive
60-session forward returns share 59 of their 60 bars. The block bootstrap
deflates t by 2.8–3.6× and the claim fails.

This is the #79 trap, and it is worth recording that **#87 did not escape it
either.** Its 11 "non-overlapping" observations removed the mechanical overlap
but not the episodic clustering — 11 days drawn from three or four bear
markets were still treated by Welch as 11 independent draws. The old design
paid 99% of the data for an independence it never actually obtained.

The pre-registration is the only reason this is a footnote rather than a
false positive. The inference method was fixed in Part 1, in a commit that
landed before the estimator was written. Had I chosen it after seeing
+2.01 and +2.83, no amount of after-the-fact reasoning would have made the
choice credible — including to me.

**Is the bootstrap merely too conservative?** The fair counter-question, and
the answer is no, it is still generous. At L = 2h = 120 a replicate is built
from 38 blocks, so the SE behaves as though the series held ~38 independent
pieces. Vietnam has had three or four genuine bear markets in 19.6 years. An
episode-level count would be harsher than this, not kinder. Two further
checks: the pre-registered block sweep barely moves the answer —

| horizon | L = h | L = 2h | L = 3h |
|---|---|---|---|
| 10 | +0.49 | +0.46 | +0.43 |
| 20 | +0.60 | +0.55 | +0.55 |
| 60 | +0.68 | +0.79 | +0.82 |

— and re-seeding the bootstrap moves the SE by ~3.5%, far too little to
matter against a 1.96 threshold.

## The pre-registered test of the fix FAILED

Part 1 predicted the k-sweep spread would collapse to "well under half" of
#90's — under 0.50 / 0.59 / 0.375. It did not:

| horizon | new t range | new spread | old spread | required | verdict |
|---|---|---|---|---|---|
| 10 | +0.46 … +1.19 | 0.74 | 1.00 | < 0.50 | **fail** |
| 20 | +0.55 … +1.26 | 0.70 | 1.18 | < 0.59 | **fail** |
| 60 | +0.79 … +1.49 | 0.70 | 0.75 | < 0.375 | **fail** |

h20 improved by 41%, h10 by 26%, and **h60 is essentially unchanged.** Reported
as a failure, as Part 1 committed to.

### Why it failed, measured rather than argued

I predicted dropping k readings would now remove ≈k observations from a sample
of thousands. The count was right and the reasoning was wrong — it matters
*which arm* they come from. At h60, k = 40 drops 37 observations, and:

* **34 of the 37 (92%) are low-MEI days** — 18% of the entire low arm;
* their mean forward return is **−23.65%**, against +8.47% for the low arm as a
  whole.

They are mid-2008: breadth had collapsed, and the market then fell another
quarter over the next sixty sessions. They are the single strongest piece of
counter-evidence to E&M's claim in the series, and the sweep deletes them. Of
course t rises — it rises from +0.79 to +1.49 as the data that contradicts the
claim is removed.

So the residual movement is not re-selection. It is a small number of real,
highly informative observations leaving the sample, which is a legitimate
sensitivity rather than an artefact. The new sweep is correspondingly orderly
where the old one jumped around — it rises on 13 of 15 steps against the old
sampler's 9 of 15, and every rise has the mechanism above behind it.

### The honest reading of that failure

**My pre-registered test was mis-specified, and I will not use that to dodge
the result.** Two distinct properties got conflated in Part 1:

1. *Phase-independence* — no arbitrary grid offset can reselect the sample.
   This **is** achieved, by construction: nothing is skipped, so there is no
   phase parameter to vary. It is asserted in
   `tests/test_em4_estimator.py::test_every_eligible_day_is_used_and_order_is_preserved`,
   and that test dies when the stride is reintroduced.
2. *Insensitivity to where the sample starts* — which I used as a proxy for
   (1) and which is **not** achievable and should not have been predicted,
   because moving the start genuinely changes the data.

The lesson is about test design, not about EM-4: a proxy measurement was
pre-registered as though it were the property itself. Recorded here because
Part 1 is what I will be held to, and it says this outcome means #99 failed.

What the sweep *does* establish is worth more than what I asked of it: across
every window tested, t_boot spans +0.46 to +1.49 and **never approaches
1.96.** Under the old estimator the top of the range was +1.83 — close enough
that #87 called it a near miss. That characterisation is now unavailable at
any window.

## Verdict on EM-4

| | |
|---|---|
| E&M's bottoms claim, best estimator available | **fails, 0 of 3**, at every window tested |
| the "near miss" of #87 | gone — max t_boot across all windows is +1.49 |
| would the full sample have "confirmed" it? | **yes, 2 of 3 — and that result would have been false** |
| binding constraint | unchanged from #90: episodes in the tail, not history depth |
| sign of the edge | positive at all horizons, at every window |

The edge stays positive and economically large (+6.24% over sixty sessions),
and it remains indistinguishable from noise once the three or four bear markets
behind it are counted as three or four events. Vietnam has not yet produced
enough bottoms to test a claim about bottoms. No estimator fixes that, and
#99 was never going to.

## Decisions

* **The phase-dependent `forward_returns` is kept, not deleted.** #87's and
  #90's published tables stay re-derivable; a result nobody can reproduce is
  not a record. Its docstring now says which of the two is primary.
* **`block_bootstrap` is now tested, with the study's first real test file.**
  17 tests in `tests/test_em4_estimator.py`, calibrated against the analytic
  SE on iid data and against a knowably-wrong per-observation SE on clustered
  data. The function is load-bearing — it is the 2.8–3.6× between a false
  positive and a null — and it was previously asserted nowhere.
* **Nothing is re-tuned.** `DECILE`, `MIN_UNIVERSE`, `WARMUP_POINTS`, the
  criterion and the data vintage are all untouched, as Part 1 fixed them.
* **One successor item IS opened — Backlog #100 — because I checked a claim I
  was about to assert and it was false.** The sentence I had drafted here read
  "#99's answer does not turn on `MIN_UNIVERSE`, because the 2008
  counter-evidence sits on a full universe." Measured, at h60:

  | low-arm composition (n = 191) | |
  |---|---|
  | symbols classified at the low observations | min **19**, median 89, max 92 |
  | observations with fewer than 30 symbols | **89 (47%)**, mean forward +7.13% |
  | observations with fewer than 20 symbols | 5 (2.6%), mean forward **−36.97%** |
  | dated before 2010 | 90 (47%), mean forward +7.08% |
  | 2010 and later | 101, mean forward +9.71% |

  Nearly **half the low arm is measured off fewer than 30 of the 92 symbols**,
  and the five most extreme counter-observations — the mid-2008 ones driving
  the whole sweep result above — sit on the *thinnest* universe in the series,
  not a full one. The opposite of what I was about to write.

  Two things follow. `MIN_UNIVERSE = 10` is *not* the binding knob — no low-arm
  observation is taken on fewer than 19 symbols, because `WARMUP_POINTS = 250`
  already pushes the window start to 2008-03-04. But universe *thickness* is
  material, and the two halves differ (+7.08% thin/early against +9.71%
  thick/late), so a thickness threshold could plausibly move the answer **in
  either direction**, including toward a pass.

  That is precisely why it is registered rather than run. **I have now seen
  those conditional means, which contaminates me for #100** — the item says so
  explicitly, and says the threshold must be fixed, in writing, before the run.

## A note on the mutation checks, because one survived

Four mutations were applied to the estimator. Three died immediately. The
fourth — admitting each reading into **its own** trailing decile history, i.e.
hindsight — **passed all 15 tests**, on a fixture of 650 uniform random
readings, because the decile rank almost never shifts onto a different value
when every value is distinct.

I predicted coarse MEI values (0.0, 9.1, 18.2 … off an 11-symbol universe)
would catch it. **Measured: they do not either.** What catches it is a
constructed boundary case — a 259-value ascending history where the cutoff
rank moves from 24 to 25 the moment the reading is admitted. Both tests are
kept; the coarse one's docstring states plainly that it makes no kill.

Worth recording because the previous commit on this branch was
`56a3f21b test(frontend): #71 — 18 green tests that proved nothing`. A green
suite is a claim, not evidence, and here the strongest-sounding test in the
file was the one that could not see the most serious possible bug.

## Reproducing

```bash
cd stock_microservices/services/decision-helper-service
PYTHONPATH=. python3 tests/deep_history_dump.py /tmp/deep_bars.tsv /tmp/deep_index.tsv
PYTHONPATH=. python3 tests/em4_mei_study.py          # both tables, sensitivity, sweep
PYTHONPATH=. python3 -m pytest tests/test_em4_estimator.py -q
```
