# EM-7 T4 / Gate 2 — the second chance is offered when the first was worth taking

**Date:** 2026-10-22
**Backlog:** `#67` (Gate 2 of two)
**Study:** `decision-helper-service/tests/em7_gate2_study.py`
**Verdict:** **FAIL.** The throwback gets a better price on four of five
opportunities and makes **less than half** the money. The detector stays `OFF`.

---

## The result

92 symbols, **85,033 opportunities** (every decisive break of a level), all
three arms holding the same horizon and paying the same 0.40% round trip.

| horizon | BREAK | THROWBACK | diff | t | symbols better | sign p |
|---|---|---|---|---|---|---|
| 10 | +0.391% | +0.030% | −0.361 | −3.97 | 31/92 | 0.002 |
| **20** | **+0.710%** | **+0.335%** | **−0.375** | **−2.86** | **30/92** | **0.001** |
| 60 | +2.778% | +1.523% | −1.255 | −4.83 | 22/92 | 0.000 |

| | THROWBACK |
|---|---|
| fill rate | **82.3%** — Gate 1 predicted 82.3%, which is a clean internal check |
| entry price better by | **+2.81%** |
| net P&L per opportunity | **less than half** of entering at the break |

**It fails on magnitude *and* consistency.** Unlike EM-3 (`#84`) and EM-8's
`M3`, where magnitude held and consistency did not, here both go the same way:
only 22–31 symbols of 92 favour waiting, at sign-test p ≤ 0.002. There is no
tail-driven ambiguity to argue about.

## Why: adverse selection, measured rather than asserted

The register's warning was *"a better average entry price must not be paid for
with a materially lower fill rate."* The real cost turns out not to be the
fill rate at all — it is **which** opportunities go unfilled.

Comparing the BREAK return on the opportunities the throwback **declined**
against those it **filled** (25 symbols):

| horizon | declined − filled | t |
|---|---|---|
| 10 | **+9.56pp** | +20.70 |
| 20 | **+14.17pp** | +19.09 |
| 60 | **+22.55pp** | +16.26 |

The 17.7% of breakouts that never come back are the ones that **ran**. At the
20-session horizon, entering at the break on a declined opportunity returned
**14 percentage points more** than on a filled one.

So the throwback is not a neutral filter that costs a few trades. It is a
filter that **systematically removes the best breakouts** — and that is the
sharpest form of this negative: *the second chance is offered precisely when
the first chance was not worth taking.*

Both of E&M's descriptive claims survive this (Gate 1: 82% return, stopping
0.23 ATR more exactly). What does not survive is the **tactic** built on them.
The pullback is real; waiting for it is not profitable here.

## A limitation that must not be read as a refutation

**The `RETRACE_40` arm does not faithfully test E&M's 40% rule.** It fills
**98.5%** of the time with only **0.21%** better entry — essentially the same
trade as BREAK, a bar or two later — and lands within noise of it (+0.062 at
t = +0.31 at horizon 20; −0.10 and −0.34 at the other two).

The cause is in my implementation, not in E&M. I measure the move from the
level to the post-break extreme **so far**, so one bar after the break the
"move" is tiny and 40% of a tiny move is given back immediately. E&M clearly
intend the move to have developed — *"if the breakout continues for several
days, compute the 40% on the whole move."* A faithful version needs a
minimum-development condition, which is a design change requiring its own
pre-registration.

**So E&M's 40% rule is untested here, not refuted.** Logged rather than
claimed.

## Two bugs of mine, both worth recording

**The study crashed on the same defect I had just fixed in shipped code.**
`#93` guarded non-positive prices in `stop_module`; my `_net_return` guarded
the entry price and not the exit, so `e / x` divided by zero on one of the 13
zero-price vendor bars. Fixing a bug in one place does not fix the habit that
produced it.

**And the mechanism was nearly a story rather than a finding.** "The throwback
misses the winners" was my immediate explanation, and it is the kind of
plausible mechanism that gets written up unverified. It took one extra column
to measure, and it came back at t ≈ +19.

## Standing

| | |
|---|---|
| Gate 1 — the phenomenon | **PASS**: +10.0pp return rate, 0.23 ATR less overshoot |
| Gate 2 — the tactic | **FAIL**: −0.375pp per opportunity, 30/92 symbols, p = 0.001 |
| mechanism | **adverse selection**, +14.17pp on declined opportunities (t = +19.09) |
| entry price | better by 2.81% — the number that looks most persuasive and means least |
| E&M's 40% rule | **untested**, not refuted; my arm fires too early |
| the detector | **stays `OFF`**, as the plan pre-registered |

EM-7 joins EM-2 in the pattern this project keeps finding on this market: the
**level** is real, and the **tactic** built on it is not. EM-2 closed with
levels beating a matched-distance null while no elaboration beat counting
touches. EM-7 closes with the throwback beating a matched-distance null on
both of E&M's claims, and losing money anyway.
