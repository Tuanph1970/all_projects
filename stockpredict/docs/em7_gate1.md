# EM-7 T2 / Gate 1 — the throwback is real, and small

**Date:** 2026-10-22
**Backlog:** `#67` (Gate 1 of two)
**Study:** `decision-helper-service/tests/em7_throwback_study.py`
**Verdict:** **PASS**, on both of E&M's claims, in **9 of 9** grid cells.

---

## The result

92 symbols, 320,237 bars, **85,623 breaks**. Clustered by symbol (92 clusters
— the `t` statistics are over symbols, not over breaks).

| band (ATR) | window | return | null | edge | t | overshoot Δ | t |
|---|---|---|---|---|---|---|---|
| 0.25 | 20 | 59.7% | 44.1% | **+15.6%** | +33.51 | **−0.14** | −6.16 |
| 0.25 | 60 | 72.9% | 61.1% | +11.8% | +22.67 | −0.21 | −7.17 |
| 0.25 | 120 | 79.0% | 70.9% | +8.1% | +14.76 | −0.24 | −7.80 |
| 0.50 | 20 | 72.8% | 58.2% | +14.6% | +34.91 | −0.16 | −6.64 |
| **0.50** | **60** | **82.3%** | **72.3%** | **+10.0%** | **+22.67** | **−0.23** | **−8.29** |
| 0.50 | 120 | 86.4% | 79.8% | +6.6% | +14.98 | −0.27 | −8.76 |
| 1.00 | 20 | 85.8% | 76.6% | +9.1% | +26.17 | −0.14 | −5.42 |
| 1.00 | 60 | 90.9% | 84.1% | +6.9% | +22.28 | −0.19 | −6.49 |
| 1.00 | 120 | 93.0% | 88.5% | +4.5% | +14.49 | −0.21 | −7.08 |

**Both of E&M's claims hold.** Ch 6 — the pullback is more frequent after a
break than after price merely sitting the same distance from the level
(+10.0pp at the primary setting). Ch 14 — it **stops more exactly at the old
line**, overshooting by 0.23 ATR *less* than the matched control.

The plan required sign robustness across the grid rather than a best cell, and
this is **9 of 9 on both halves** — which the 3-symbol smoke run was not
(three cells went the wrong way there).

## What the numbers do and do not say

**The effect is small and extremely consistent, not large.** A `t` of +22 on
92 clusters comes from low variance across symbols, not from a big effect: the
edge is **+10 points on a 72% base**. Those are different things and the `t`
flatters the first by reporting the second.

**The base rate is the headline.** Price returns to a level it sits half an
ATR from, within 60 bars, **nearly three times in four** — with no break
involved at all. That is what the null measures, and it is why the control had
to be built this carefully. The throwback's incremental information is the 10
points on top, and any trading rule has to earn its keep on that margin.

**The edge compresses as the band and window widen** — +15.6pp at
(0.25, 20) down to +4.5pp at (1.0, 120) — because both arms saturate toward
100%. That is the expected shape and a reassurance rather than a worry: an
artifact would not politely shrink as the measurement got easier for both
arms.

**And a high return rate is not unambiguously good news.** 82% of breaks pull
back to the level. That makes the "second chance" common — and it makes the
pullback that kills the original breakout common too. Gate 2 is where that
tension gets priced.

## The two pre-registered orderings

| | |
|---|---|
| **by level strength** | strong (3+ touches) **83.4%** vs weak (1–2) **81.1%** |
| **by break direction** | broken **downward 84.7%** vs **upward 80.2%** |

Strength points the way EM-2 would predict — touches are what carry
information about a level — but at **+2.3pp** it is a whisper, and EM-2's own
conclusion was that no elaboration beat simply counting touches.

The direction asymmetry is larger at **+4.5pp**: supports broken *downward*
pull back more often than resistances broken *upward*. That is consistent with
E&M's own Return-Line asymmetry and with the long/short asymmetry `#85`
observed and `#86` was logged to test. It is **not** a pre-registered
hypothesis about *profit*, and it must not become one on this data.

## The null, which was wrong first

Recorded because the first version passed spectacularly and was nonsense.

It required only that price be **at least** one band from the level. Over 19
years a level formed in 2010 sits hundreds of ATRs from 2024 prices, so those
draws could never return — while a real break sits, by definition, just past
the band edge. The arms were compared across different distance regimes, and
the study reported **+75 percentage points at t = +24.7**.

The implausibility is what exposed it. No market effect looks like that.

The null now matches the break's **own penetration distance** (the same ATRs
from the level, ±25%), so the only difference between arm and control is that
a break happened. This is EM-2's matched-distance construction — got wrong
once more here before being got right.

## Standing

| | |
|---|---|
| E&M Ch 6, frequency | **supported**, +10.0pp over a distance-matched null, 9/9 cells |
| E&M Ch 14, exactness | **supported**, −0.23 ATR overshoot, 9/9 cells |
| effect size | **small** (+10pp on a 72% base) and very consistent |
| level strength ordering | directionally right, **+2.3pp**, a whisper |
| break direction | **+4.5pp** favouring downward breaks; descriptive only |
| Gate 1 | **PASS** → proceed to `T3`, the detector |

What Gate 1 establishes is that **the phenomenon exists**. It says nothing
about whether trading it pays, which is `T4`'s question — and EM-2's standing
warning applies in full: on this data the levels were real, and every
elaboration on them failed to beat counting touches. A real phenomenon with a
10-point edge over chance is exactly the kind that can still lose money once
it has to pick entries and decline the rest.
