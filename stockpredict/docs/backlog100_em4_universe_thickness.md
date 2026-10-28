# Backlog #100 — is EM-4's bottoms result an artefact of a thin universe?

**Part 1 is committed BEFORE the run.** Part 2 is appended later and may not
change a word of Part 1.

---

# Part 1 — pre-registration (committed 2026-10-28, before any output)

## The question

MEI is the percentage of a *universe* in a bullish major trend, and
`MIN_UNIVERSE = 10` admits a reading computed on ten symbols. `#87` flagged
that a reading off 11 charts "is not the same instrument as one off 92, and
Magee kept ~100". `#99` then settled EM-4's bottoms claim — fails 0 of 3, on a
phase-independent estimator — but on a series that still mixes both
instruments.

So: **does the verdict hold when only thick-universe readings are used?**

## Contamination disclosure, and it is worse here than in #99

I opened #100 because a sentence I was about to publish turned out false, and
the measurements that refuted it are measurements of *this* question. At h60,
on the 191-observation low arm:

| | |
|---|---|
| symbols classified at low observations | min 19, median 89, max 92 |
| observations on fewer than 30 symbols | 89 of 191 (47%) |
| thin/early half of the low arm | mean forward **+7.08%** |
| thick/late half | mean forward **+9.71%** |

**So I already know the direction a high threshold pushes the answer: toward
E&M.** Choosing a threshold now is exactly the hazard the register warned
about, and no disclosure makes that fully clean. Four constraints follow, and
the third is the one that actually protects the reader:

1. **The threshold is derived from a stated principle, not from the split.**
   See below — it is a fraction of the universe, fixed before any run, and it
   is not the 30 I happened to have measured.
2. **The criterion is inherited verbatim** from #87, via #99's estimator.
   Nothing about the test statistic or the significance bar is mine to choose
   here.
3. **A pass at the primary threshold alone will be reported as NOT ROBUST.**
   The full threshold sweep is reported beside it, so a result that exists at
   one cut-off and nowhere else is visible as such rather than as a headline.
   This is the guard against my knowing which direction flatters the claim.
4. **One run, reported whatever it says.**

## The threshold, and why this number

Magee's instrument was **~100 charts**. A reading taken on a minority of the
universe is not a thin version of that instrument, it is a different one — the
share of *ten* symbols trending tells you about ten companies, not about "the
market". The principled line is therefore a **majority of the universe**:

> **`MIN_CLASSIFIED = 46`** — half of the deep dump's 92 symbols.

Stated as a fraction of the universe so it carries over if the dump changes,
and deliberately **not** 30 (the figure I happen to have measured), nor 20
(the lowest observed), nor anything else chosen by looking at what it does to
n or to the edge.

Everything else is `#99`'s, unchanged: `DECILE = 10.0`, `WARMUP_POINTS = 250`,
the expanding trailing decile, every qualifying day, moving-block bootstrap at
`L = 2h` with `B = 2000` and seed `20261027`, and the 2004 vintage dump.

**How the filter is applied:** `compute_mei_series(bars, min_universe=46)`.
That is the production parameter itself, and it gates on exactly the field in
question (`classified`), so non-qualifying days are absent from the series and
the trailing decile is computed over qualifying readings only. The alternative
— keeping the full series for the percentile and sampling only thick days —
would measure a thick day against a threshold set by thin ones, which is a
different and less meaningful question.

## CRITERION, fixed before the run

Inherited from #87 and unchanged:

> 1. forward market return after a bottom-decile MEI reading is significantly
>    higher than the unconditional forward return (`t_boot > 1.96`,
>    directional); **and**
> 2. it holds at **more than one** horizon (10, 20, 60).

## POWER FLOOR, fixed before the run

Raising the threshold cuts n in the arm that was already binding. So:

* a horizon whose **low arm holds fewer than 30 observations** is reported as
  **underpowered**, not as evidence either way;
* if fewer than two horizons clear that floor, the whole test is reported as
  underpowered and the thin-universe caveat stays **open** rather than
  answered;
* a bootstrap discarding more than 10% of replicates is likewise reported as
  too thin to interpret, per #99.

## The readings, all pre-stated

* **Passes at 46, and the sweep shows it is not isolated** → EM-4's bottoms
  claim survives on a majority-universe instrument. That would reverse #99's
  null, and I commit now to then treating it as a *second instrument tried*,
  with the multiplicity stated, not as a clean confirmation.
* **Passes at 46 only, with the sweep failing around it** → reported as **not
  robust**, per constraint 3. Not a headline.
* **Fails, with n above the floor** → the null holds on the thick instrument
  too, and #87/#90's thin-universe caveat is **answered and closed**. This is
  the outcome that would make the caveat go away, which is worth as much as a
  pass.
* **Fails, with n below the floor** → uninformative. The caveat stays open and
  is recorded as unanswerable on this market's history, which is the same wall
  #90 and #99 hit.

## Expectations, recorded so they can be wrong

1. n_low will fall sharply — the 47% of the low arm below 30 symbols is
   pre-2010, so a 46 threshold likely removes roughly half of it.
2. The criterion will still fail, but with materially less power than #99's.
3. The edge will stay positive, as it has at every cut so far.

If (1) holds strongly enough, the honest answer to #100 may be "this market's
history cannot answer it" — and that is a legitimate result, not a failure to
measure.

## What this cannot settle

A threshold is a judgement. 46 is defensible and it is not unique; the sweep
is reported precisely because no single line is. And nothing here adds
information — it removes some, deliberately, to ask whether what remains says
the same thing.
