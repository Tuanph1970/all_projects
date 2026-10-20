# Backlog #84 — EM-3's walk-forward confirmation and filter sweep

**Date:** 2026-10-20
**Study:** `decision-helper-service/tests/em3_walk_forward_study.py`
**Verdict:** **1 of 2 pre-registered conditions met. The default is not flipped.**
The failure is informative rather than flat, and the detail is the point.

---

## What a walk-forward means for this rule

Nothing in the basing-point rule is fitted. Three days clear, a 6 % filter and
a 3 % new-high threshold all come from Edwards & Magee, fixed a priori. So
this is **not** a test for parameter overfitting — there are no parameters to
overfit. It tests **temporal stability**: does the effect hold window after
window, or did yesterday's pooled result ride one lucky stretch?

Worth stating because the usual reason for running a walk-forward does not
apply, and a reader could otherwise assume it does.

## The criterion, fixed before the run

> Both of these, or EM-3 does not clear `C4`:
> 1. the basing-point arm wins a **majority of windows** on gross P&L per
>    trade, and the **sign test** on window wins is significant; and
> 2. the **paired mean difference** across windows is positive and significant.

Paired per window, because both arms run on the same window and the
between-period variance then drops out — a tighter statistic than yesterday's
pooled Welch t, and a direct read on stability.

---

## (a) Confirmation, at the book's 6 % filter

192 non-overlapping 180-day OOS windows across 32 symbols:

| arm | mean diff | paired t | windows won | sign z |
|---|---|---|---|---|
| basing point, rules 1–3 | **+37.82** | **+2.61** ✓ | 104 / 192 (54 %) | +1.08 ✗ |
| basing point + rule 4 | +29.86 | +2.72 ✓ | 106 / 192 (55 %) | +1.37 ✗ |

### Clustered by symbol — the conservative denominator, which turned out stronger

The 192 windows are **not independent**: roughly six come from each of 32
symbols, and windows from one symbol share its regime, liquidity and drift. A
paired t over all 192 treats them as independent draws, which understates the
standard error. So the same comparison with each symbol's windows averaged
first — 32 genuinely independent units:

| | n | mean diff | paired t | won | sign z |
|---|---|---|---|---|---|
| clustered by symbol | 32 | **+37.82** | **+3.39** ✓ | **21 / 32 (66 %)** | +1.59 ✗ |

I expected this to weaken the result and it strengthened it. Averaging within
a symbol removes the window-level noise, which was large, and reveals that the
effect is **consistent across the universe** (66 % of symbols, t = +3.39) even
though it is **inconsistent within any one symbol's six-month windows** (54 %).

## (b) Robustness across the filter — a sensitivity check, not a search

| filter | mean diff | paired t | windows won |
|---|---|---|---|
| 3.0 % | +22.54 | +1.87 ✗ | 51 % |
| 4.5 % | +30.35 | +2.23 ✓ | 52 % |
| **6.0 % (the book)** | **+37.82** | **+2.61 ✓** | 54 % |
| 8.0 % | +28.41 | +1.85 ✗ | 53 % |
| 10.0 % | +23.67 | +1.49 ✗ | 52 % |
| 12.0 % | +26.54 | +1.56 ✗ | 52 % |

**Every setting is positive**, from +22 to +38, which makes the *sign* robust.
But **only two of six reach significance**, and the book's own 6 % sits exactly
at the **peak**. That is either a nice confirmation of E&M's judgment or a
warning that significance is being read at a maximum. With t falling to 1.85
at 8 % and 1.49 at 10 %, it is fragile to a parameter nobody tuned.

The sweep is deliberately **not** used to pick a value. Choosing the maximum
after seeing the data is what this workstream has spent nine tasks avoiding.

---

## Verdict

**Condition 2 passes decisively** — +37.82 at paired t = +2.61 over windows,
and +3.39 clustered by symbol.

**Condition 1 fails** — the sign test never reaches significance, at either
level of aggregation (z = +1.08 over windows, +1.59 over symbols).

I pre-registered *both*, so **EM-3 does not clear `C4`**, and the default is
not flipped.

### But the failure says something specific

**The rule wins by magnitude, not by frequency.** It loses about as often as
it wins — 54 % of windows, 66 % of symbols — while its mean advantage is large
and significant. Its wins are simply bigger than its losses.

That is exactly what a wider stop *should* do, and it is E&M's own logic: a
stop placed where a probe cannot reach it gets taken out less often, so the
occasional large move survives to be captured. Yesterday's exit mix showed the
same mechanism from a different angle — stop-outs 76.9 % → 66.8 %, target-hits
22.6 % → 32.4 %.

It also means the edge sits in a tail. A trader running this would feel long
stretches of underperformance punctuated by a few large wins, and the sign
test is right to refuse to call that consistent.

### On my own criterion

Requiring the sign test was arguably the wrong choice for this rule: a sign
test deliberately discards magnitude, which is the one thing this rule
delivers. Had I framed condition 1 as "a majority of *symbols*", it would
have passed at 66 %.

But I pre-registered it, and the discipline is to report against what was
committed to rather than to drop the inconvenient half after seeing which way
it fell. The honest statement is that EM-3 is **strongly supported on
magnitude and unproven on consistency** — which is more useful than either a
bare pass or a bare fail.

---

## What shipped, besides the study

**A silent no-op bug fixed in `walk_forward.py`.** It copied `BacktestConfig`
field by field and had fallen **five fields behind**: EM-3's
`trailing_stop_mode`, `basing_point_filter_pct` and
`basing_point_new_high_rule`, plus F-043's `allow_pyramiding` and
`max_pyramid_fraction`, which predate this work.

So a walk-forward comparing two stop rules would have run the **default rule
in both arms** and reported no difference — the same class of failure as a
sweep that patches a bound default argument, and it would have read as "the
rule does not work out of sample" rather than "the harness never applied it".
This study would have returned a flat zero and I would have had to work out
why.

It now uses `dataclasses.replace`, so the copy cannot fall behind again, and a
test asserts every field survives a window.

---

## Recommendation

**Do not flip `trailing_stop_mode`.** Criterion-driven, not cautious.

The useful next question is not more backtesting of this rule. Because the
edge is **magnitude-driven**, the thing worth knowing is **where the magnitude
concentrates** — if it is in trending windows, the rule could be applied
conditionally, and `regime/classifier.py` already distinguishes TREND_UP /
TREND_DOWN / RANGE. That is a conditional analysis on data already collected,
not another sweep.

If that analysis finds the edge concentrated in trend regimes, a
regime-gated basing-point stop is a materially stronger proposal than the
unconditional one measured here — and it would be testable against the same
bench with the same criterion.
