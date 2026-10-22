# EM-7 — the throwback entry: a real phenomenon, an unprofitable tactic

**Date:** 2026-10-22
**Backlog:** `#67` — **closed**
**Design:** `SRS_edwards_magee_throwback.md` · **Plan:** `implementation_plan_em7_throwback.md`
**Gates:** `em7_gate1.md` (PASS) · `em7_gate2.md` (FAIL)
**Outcome:** the detector ships **`OFF`**. E&M's two descriptive claims are
**confirmed**; the tactic built on them **loses money**, and the reason is
adverse selection.

---

## The two gates, in one place

| | question | result |
|---|---|---|
| **Gate 1** | Is the throwback more than a coincidence? | **PASS** — return rate 82.3% vs a distance-matched null of 72.3% (**+10.0pp**, t = +22.67), and it overshoots the old line by **0.23 ATR less** (t = −8.29). **9 of 9** grid cells on both halves. |
| **Gate 2** | Is the second chance better than the first? | **FAIL** — **−0.375pp per opportunity** vs taking the break (t = −2.86), **30 of 92** symbols better, sign p = 0.001. Fails on magnitude *and* consistency. |

So **both of E&M's claims about the pullback are true on VN data** — it is
more frequent after a break than after price merely sitting the same distance
away (Ch 6), and it stops more exactly at the old line (Ch 14). And waiting
for it is still the wrong thing to do.

## Why the tactic loses: adverse selection

Measured rather than asserted, because *"the throwback misses the winners"* is
exactly the sort of satisfying mechanism that gets written up unverified.

BREAK return on the opportunities the throwback **declined**, minus those it
**filled**:

| horizon | difference | t |
|---|---|---|
| 10 | +9.56pp | +20.70 |
| 20 | **+14.17pp** | +19.09 |
| 60 | +22.55pp | +16.26 |

The **17.7% of breakouts that never come back are the ones that ran.** The
throwback is not a neutral filter that costs a few trades; it removes the best
breakouts systematically. The sharpest statement of the result:

> **The second chance is offered precisely when the first chance was not worth
> taking.**

And the number that would have sold it: the throwback's entry price is
**2.81% better**, on 82% of opportunities. The register's benchmark asks for
average entry price, and reporting it alone would have made EM-7 look like a
success. The plan recorded in advance that it is not evidence.

## What the design got right before measuring

**The anchor.** Phase 1 rejected pattern necklines for a broken S/R level, on
the grounds that ai-insights patterns cannot reach the backtest (no per-bar
HTTP) and `chart-decomp-lib` would have production and the backtest running
*different* detectors. EM-8's `M3` had just found `MEASURED_MOVE` dead for
exactly that dependency. Anchoring on the level also turned out to be *more*
faithful: Ch 13 says **"pattern resistance — the mechanism explains the
patterns"**, so the level is the cause and the pattern is a label on it.

**The metric.** Net P&L per *opportunity* with declines counted as zero. This
is the whole result.

**The null.** Matched on the break's own penetration distance. The first
version matched only a *minimum* distance and reported **+75pp at t = +24.7**
— a level from 2010 sits hundreds of ATRs from 2024 prices and can never
return, so the arms were compared across different distance regimes. The
implausibility is what exposed it.

## What shipped, and what did not

| | |
|---|---|
| `market_features.py` | `atr_series` (Wilder), `detect_level_breaks` (role-**alternating**), `effective_level_type`; `compute_sr_levels` now attaches `breaks`, `effective_type`, `broken_at`, `break_direction` — **additive** |
| `signal/trend/throwback.py` | the detector, four exclusive modes, **`OFF` by default** |
| `BacktestConfig.throwback_mode` | wired into `_run_signals`, default `OFF` |
| tests | 29 (T1) + 25 (T3) = **54**, plus two studies |
| **live behaviour** | **unchanged** — the detector is off and nothing consumes the new level fields |

`H-T8` is worth singling out: the in-process break logic is checked against
`analysis-service`'s shipped `detect_breaks` in a **subprocess** (both services
define a top-level `app` package, so a `sys.path` insert would shadow
decision-helper's own), with the same ATR series handed to both. They agree
exactly on all five fixtures. EM-6 D1 is why that was worth building — a
study's private copy of the swing rule was wrong there on 906 of 5,672 bars.

## Limitations, stated rather than buried

1. **E&M's 40% rule is untested, not refuted.** My `RETRACE_40` arm fills
   98.5% of the time with 0.21% better entry — the same trade a bar later —
   because the move is measured to the post-break extreme *so far*, so 40% of
   a tiny move is given back immediately. E&M intend a developed move: *"if
   the breakout continues for several days, compute the 40% on the whole
   move."* A faithful version needs a minimum-development condition and its
   own pre-registration.
2. **The trendline throwback was never in scope**, and it is the half E&M rate
   highest — *"pullbacks follow trendline breaks more frequently than pattern
   breaks and stop more exactly at the old line."* It needs EM-5 (`#65`). So
   this is a null on **pattern-boundary** throwbacks only.
3. **The break-direction asymmetry is descriptive.** Gate 1 found downward
   breaks pull back more often (84.7% vs 80.2%). It is not a profit
   hypothesis, and it must not become one on the data that produced it.

## Two of my own errors, for the record

**The null was wrong and it passed spectacularly** (+75pp, t = +24.7). I had
cited EM-2's matched-distance lesson *in the plan* and then got it wrong
anyway in a new place.

**And I reproduced a bug I had just fixed.** `#93` guarded non-positive prices
in `stop_module`; two tasks later my own `_net_return` guarded the entry price
and not the exit, and died on `e / x` with one of the 13 zero-price vendor
bars. Fixing a bug in one place does not fix the habit that produced it.

## Standing

| | |
|---|---|
| E&M Ch 6 — pullbacks are common | **confirmed**, +10.0pp over a matched null |
| E&M Ch 14 — they stop more exactly | **confirmed**, −0.23 ATR overshoot |
| the entry tactic | **refuted** on this market, −0.375pp/opportunity |
| mechanism | **adverse selection**, +14.17pp on declined opportunities |
| E&M's 40% rule | **untested** |
| the trendline throwback | **out of scope** — EM-5 (`#65`) |
| the detector | **`OFF`**, as pre-registered |

EM-7 closes the pattern this market keeps producing. EM-2: levels beat a
matched-distance null, and no elaboration beat counting touches. EM-7: the
throwback beats a matched-distance null on **both** of E&M's claims, and loses
money anyway. **The structure is real; the tactics built on it are not.**

The E&M register now has one candidate left — **EM-5 (`#65`)**, the trendline
engine — and it is where EM-7's deferred half lives.
