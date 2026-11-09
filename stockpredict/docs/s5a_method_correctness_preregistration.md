# S-5a — Method-correctness study: PRE-REGISTRATION (Part 1)

**Date:** 2026-11-09
**Status:** Part 1 — parameters fixed. Written and committed **BEFORE**
`tests/s5a_method_correctness.py` exists.
**Scope:** `docs/SRS_momentum_scanner.md` §9, between S-4 and S-5.

---

## 0. Why this document exists before the code

The repo's own rule, from `tests/em4_universe_thickness.py`: *"Pre-registered in
docs/…, committed before this file was written. Nothing here may be tuned against
its own output."* Every threshold the scanner uses was chosen while looking at
2021–2026 data. A study of that same data can therefore prove very little unless
its **questions, metrics and cut-offs are fixed in advance** — otherwise the
first disappointing number invites a quiet adjustment, and the result becomes a
description of the adjusting rather than of the method.

So: the parameters below are final. The script may not change them, and a result
this document did not anticipate is reported as-is, not tuned away.

## 1. What is being tested, and what is not

**Being tested — correctness of the METHOD.** Does the scanner's output behave
the way a breakout-momentum strategy is supposed to behave?

**NOT being tested — correctness of the IMPLEMENTATION.** That is already
established: VT-1 (no future bar changes a past scan), VT-2 (byte-identical
reruns), VT-3 (the planted base is recovered at its true boundary), VT-4 (0.50%
on random walks against 3.1% live).

**NOT being tested — EDGE.** This study cannot estimate it and will not claim to.
Candidates arrive in bursts; the sample is a few hundred heavily overlapping
candidate-days over 5.5 years containing one bear market. VT-5 proper, on
accumulating live runs and/or a deepened universe, is where an edge claim could
come from. **Any return figure produced here is evidence about mechanism, not a
forecast**, and the script prints that beside every number.

## 2. Data and universe — unchanged from production

- The 93 symbols already in `stock_prices`, 2021-03-15 → 2026-11-06.
- `ScanConfig()` **defaults, unmodified**, with `seam_allowlist=KNOWN_PROVIDER_SEAMS`.
  No parameter in the funnel is re-fitted, swept or tuned by this study.
- Read-only. No database writes, no service changes, no scheduler changes.

## 3. Episodes, not candidate-days

A stock sits in its base for weeks, so daily scans re-observe the same setup.
Counting candidate-days would inflate n by an order of magnitude and make every
interval meaninglessly narrow.

**An EPISODE** = the first date a symbol becomes a candidate after **≥ 20 trading
bars** of not being one. Re-entry inside that window is the same episode.
`EPISODE_GAP_BARS = 20`.

## 4. Primary and secondary measures

Entry is assumed at the **close of the episode date** — a price that was actually
available. Not at the pivot: a breakout day can lock at trần with no fill, and
assuming that fill measures a market that does not exist. T+2.5 settlement means
no same-day exit, which the horizons below respect.

**PRIMARY — excess forward return.**
`excess = candidate_return(h) − mean(liquid_universe_return(h)) on the SAME date`,
for `h ∈ {5, 10, 20}` bars. Same-date differencing is deliberate: it removes the
market factor, which is the dominant source of correlation between candidates
appearing in the same burst.

**SECONDARY — pivot clearance.** Does any **close** in the next 20 bars exceed the
episode's pivot? Measured on close, not high, for the trần reason above. Compared
against the same rate for the benchmark arms. *This is the most direct test of
the mechanism: if base geometry means anything, a candidate should clear its own
pivot more often than a random liquid name clears a notional one.*

## 5. Benchmark arms (C4 — mandatory)

1. **ARM-LIQ** — every symbol passing the liquidity floor on that date. Isolates
   what momentum + base add over *"any liquid stock"*.
2. **ARM-RANDOM** — a same-size random draw from ARM-LIQ on that date, seeded
   `20261109`. Guards against a candidate count that is itself informative.

A result is reported for all three arms or not at all.

## 6. Regime split

Fixed in advance: a date is **BROAD** when more than **50%** of the ranked
universe closes above its own SMA200, otherwise **NARROW**. Breadth is computed
from the scan's own trend clauses — no new indicator, no market proxy.

Pre-registered expectation: **candidates should do visibly better in BROAD than
in NARROW regimes.** If forward returns are flat across the two, the trend
template is contributing nothing and that is a finding against the method.

## 7. Power floor and how a thin cell is reported

`MIN_EPISODES_PER_CELL = 10`. A cell below it prints **UNDERPOWERED (n=…)** and
no statistic. Reporting a mean off four episodes is how a study ends up quoted as
a result.

No significance test is run. With burst-correlated episodes a p-value would be
wrong in a direction that flatters the method, so the script reports **n, mean,
median and the interquartile range**, and states that the comparison is
directional.

## 8. Exclusions, fixed in advance

- An episode whose forward window runs past the last stored bar is **dropped**,
  not truncated to a shorter horizon.
- An episode whose forward window contains a price seam
  (`|overnight move| > 15%`) is **dropped** — a share-count event is not a return.
- Nothing else is excluded. No symbol, date or outlier is removed for being
  inconvenient.

## 9. What would count as the method failing

Stated now so it cannot be renegotiated later. Any of these is a finding against
the method, to be reported plainly:

- Pivot clearance for candidates **≤** ARM-LIQ.
- Mean excess 20-bar return **≤ 0** at adequate n.
- Forward returns **flat across BROAD and NARROW** regimes (§6).
- Candidates that hold MA20 performing **no better** than those that lose it
  — the method's own exit rule carrying no information.

## 10. Output

`docs/s5a_method_correctness.md` — Part 2, written from the script's output
after it runs. The numbers go there unedited, including the ones this document
hoped not to see.
