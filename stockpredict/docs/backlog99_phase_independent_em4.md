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
