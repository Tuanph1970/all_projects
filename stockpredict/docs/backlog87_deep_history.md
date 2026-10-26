# Backlog #87 — deep history, the real index, and what it changed

**Date:** 2026-10-20
**Code:** `stock-data-service` `HISTORY_YEARS`; `decision-helper-service/tests/deep_history_dump.py`
**Outcome:** the data task is done, EM-4's bottoms claim is now **testable**,
and **EM-4's quintile finding is overturned** — exactly as its own write-up
predicted.

---

## What was actually available

The 5-year limit was never the vendor's. It was ours — `DEFAULT_YEARS_HISTORY`,
inherited from the monolith. Probed before writing anything:

| | |
|---|---|
| FPT via VCI | 4,380 bars from **2009-03-27** |
| **VNINDEX** via VCI | 4,903 bars from **2008-02-18** — the real cap-weighted index |
| VN100 as the service defines it | **92 symbols**, close to Magee's ~100 charts |

So all three parts of #87 were obtainable, and the pull delivered **92 symbols,
320,237 bars, 2007-01-23 → 2026-10-13 — 19.7 years.** Against 32 symbols,
42,524 bars and 5.3 years before: **7.5× the data**, and for the first time the
right market proxy.

### What shipped

* `HISTORY_YEARS` in `stock-data-service` config — depth is a setting, not a
  literal.
* `tests/deep_history_dump.py` — a reproducible pull of a named universe plus
  the index, inheriting the vnstock guest throttle (~3.2 s spacing, so 92
  symbols costs about five minutes; `VNSTOCK_API_KEY` would raise it, Backlog
  `#49`).
* `em4_mei_study.py` now prefers the deep dump and the real index when
  present, and **prints which it used** — every EM-4 conclusion depends on
  that, and a study that silently swapped its inputs would be worthless.

---

## A defect in my own study, found by the new data

The first deep run reported **n = 0** low-MEI observations at the 60-session
horizon — *fewer than the 5.3-year data had found (2)*. More data cannot
produce fewer observations, so the sampler was wrong.

It walked a fixed stride (`range(warmup, n, horizon)`). That is a *systematic*
sample, and low-MEI episodes are short and clustered — a handful of bear
markets — so a stride can step straight over all of them, and did.

Fixed to consider **every** qualifying day and enforce non-overlap *within*
each arm by taking the earliest and skipping forward by the horizon. Sample
sizes went from 11/5/2 (shallow) and 20/10/0 (deep, broken) to **25/16/11**.

---

## E&M's bottoms claim is now testable, and falls just short

19.7 years, real VNINDEX, every episode used:

| horizon | n low | after low MEI | after others | edge | Welch t | |
|---|---|---|---|---|---|---|
| 10 | 25 | +2.82% | +0.35% | **+2.46%** | +1.88 | ns |
| 20 | 16 | +3.67% | +0.72% | **+2.95%** | +1.59 | ns |
| 60 | 11 | +14.74% | +2.17% | **+12.57%** | +1.73 | ns |

**Criterion fails: 0 of 3 significant.** But this is the strongest E&M result
in the whole workstream: every horizon positive, the edge growing with the
horizon, and t consistently 1.6–1.9 — just short, three times over. The
60-session edge of +12.57% is economically large.

> **CORRECTION, Backlog #90 (2026-10-26).** The verdict above stands — 0 of 3,
> at every sampling phase tested — but *"t consistently 1.6–1.9, just short,
> three times over"* does not. Those three numbers describe one phase of the
> non-overlap grid, not the data. `forward_returns` starts at `WARMUP_POINTS`
> as an **index**, so beginning the series a few readings earlier re-phases
> every selected observation. Deepening the pull to 2004 added 38 breadth
> readings — none of them a low-MEI day — and t fell to +1.22 / +0.88 / +1.09;
> trimming those 38 back reproduces the table above exactly. Sweeping the start
> by up to 44 readings moves t across +0.83–1.83 (h10), +0.53–1.71 (h20) and
> +0.93–1.67 (h60), so the figures here sit at the **top** of their own range.
> Read this table as "fails, and too unstable at n = 11–29 to call a near miss."
> See `docs/backlog90_deep_history_2004.md`; the sampler fix is Backlog #99 and
> must be pre-registered rather than tuned against this data.

The three horizons are **not independent** — the same episodes measured over
different windows — so their p-values cannot be combined as if they were, and
the consistency is weaker evidence than it looks.

What remains the constraint is still n. 19.7 years of VN data contains perhaps
three or four genuine bear markets; the decile flags hundreds of days, and
non-overlap collapses them to 11 at the 60-session horizon.

### A descriptive note that is hard to ignore

The VNINDEX's three lowest closes are 2009-02-24, 02-26 and 03-03 — the GFC
bottom, index at 235.5. **MEI read 0.0% on all three.** E&M's claim landing
exactly, on the largest bottom in the series.

**Caveat on the early years, stated because it bounds that:** in 2007–09 only
**11 of the 92** symbols had listed and were classifiable. Those 0.0% readings
are *0 of 11*, not 0 of 92. `MIN_UNIVERSE = 10` admits them, which is right —
withholding the GFC would be worse — but a reading off 11 charts is not the
same instrument as one off 92, and Magee kept ~100.

---

## EM-4's quintile finding is overturned

EM-4 reported forward return **monotone decreasing** across breadth quintiles —
Q1 +11.10% down to Q5 −3.88%, top-vs-bottom −14.99% at t = −2.08 — on 17
observations with **n = 3 per bucket**, and concluded the register's
pro-cyclical exposure governor was *contra-indicated*.

Re-run on 19.7 years with the real index:

| | 20 sessions (n=45/bucket) | 60 sessions (n=15/bucket) |
|---|---|---|
| Q1 (lowest breadth) | +0.73% | +1.59% |
| Q2 | +0.31% | +4.45% |
| Q3 | +1.21% | −3.49% |
| Q4 | +0.54% | +4.08% |
| Q5 (highest) | +1.68% | +4.12% |
| top vs bottom | **+0.95%, t = +0.59 ns** | **+2.53%, t = +0.68 ns** |

**The sign flipped and the monotonicity is gone.** It is noise in both
directions.

EM-4's own write-up predicted this: *"a monotone pattern across five tiny
buckets is exactly the shape that does not survive more data."* It did not.

**So I withdraw EM-4's warning.** The pro-cyclical governor is **not
contra-indicated** — it is simply **unsupported**, like the contrarian version.
Breadth *level* carries nothing about forward index returns in either
direction.

### The two results together tell a coherent story, and it is E&M's

* The **tail** — extreme low readings — looks like it carries something
  (+12.57% at 60 sessions, t = 1.73).
* The **level** — where breadth sits in its range — carries nothing.

That is exactly what E&M claimed and no more. The 1985 market letter says
*major bottoms correspond with extremely low readings*; it never says breadth
linearly predicts returns. The quintile framing was **my** generalisation of
their claim, and it is the half that does not survive.

---

## The guard, because nothing had ever asserted the depth

No test anywhere checked the history window. That is *why* it sat at five
years for the life of the project without anyone noticing — the value was
correct-looking, consumed once, and unasserted. So two tests ship with the
setting:

* the requested span is `365 × HISTORY_YEARS` wide and ends today, asserted as
  a property over 1/5/20 years rather than against a fixed date;
* **the depth is read at call time, not frozen at import** — two patched
  depths must produce two different spans.

The second is there because this project has paid for the bound-default trap
four times (EM-1 S2, `#78`, `W1`, `#84`). Mutation-checked by briefly
reintroducing it as `_years: int = settings.HISTORY_YEARS`: three of the four
cases fail — and the one that still **passes is `years=5`**, the frozen
default. That is the trap's exact signature, and the reason a sweep over a
bound parameter reads as "flat, so the parameter doesn't matter."

---

## Standing

| | |
|---|---|
| data depth | **done** — 19.7 years, 92 symbols, real VNINDEX, depth configurable |
| E&M's bottoms claim | **testable at last**; 0/3 significant. ~~directionally supported~~ — withdrawn by #90: the near-miss is sampling-phase dependent (see the correction above) |
| breadth *level* → returns | **nothing**, in either direction; EM-4's finding overturned |
| the exposure governor | still **not built** — now because it is unsupported, not contra-indicated |
| EM-6 (Dow multi-index gate) | **unblocked** — the real VNINDEX now exists locally |

Nothing new consumes the MEI. What changed is that the next person to ask can
get an answer, and two of the three caveats EM-4 carried are gone.
