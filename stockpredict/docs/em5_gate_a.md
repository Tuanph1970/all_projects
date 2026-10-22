# EM-5 L3 / Gate A — slope does not earn anything, it subtracts

**Date:** 2026-10-23
**Backlog:** `#65` (Gate A, the only gate in Phase A)
**Study:** `decision-helper-service/tests/em5_gate_a_study.py`
**Verdict:** **FAIL, 0 of 3 horizons, at every penetration setting** — and the
horizontal comparison is **significantly better**, not merely equal.

---

## The result

92 symbols, penetration = **3%** (E&M's figure for a stock). Arm T is the
trendline's first decisive penetration; Arm H is the first break of the
**horizontal at `p₂`**, the most recent anchor price — same pivots, same bars,
slope the only difference.

| h | T | H | T − H | t | symbols where T wins | sign p |
|---|---|---|---|---|---|---|
| 10 | +0.965% | **+1.437%** | −0.471 | **−7.18** | 17 / 92 | 0.000 |
| 20 | +1.654% | **+2.163%** | −0.509 | −3.71 | 32 / 92 | 0.005 |
| 60 | +3.815% | **+4.713%** | −0.897 | −2.08 | 40 / 92 | 0.251 |

**Robust across the whole grid**, which is what the plan said to read rather
than a best cell:

| penetration | T beats H | H's margin at h=20 |
|---|---|---|
| 3% (the book, stock) | **0 / 3** | −0.509 (t = −3.71) |
| 2% (the book, averages) | **0 / 3** | −0.639 (t = −4.97) |
| 1.0 ATR (the declared alternative) | **0 / 3** | −0.652 (t = −5.61) |

The robustness arm agrees: **H-mid**, the horizontal at the anchors' *mean*,
also beats T — −0.414 at h=20 (t = −3.08). **Both** horizontals beat the
sloping line through the same pivots.

## This is not an underpowered null

| | |
|---|---|
| trendline events | **45,117** |
| horizontal events | 23,586 |
| observations after non-overlap | 17,843 / 13,694 at h=10 |
| clusters | 92 symbols |
| largest t | **−8.21** (1.0 ATR, h=10) |

The direction is consistent in **9 of 9** grid cells. A result this
one-sided, on this many events, is not a power problem.

## The event counts are themselves a finding

**Trendlines break nearly twice as often as the horizontals through the same
anchors** — 45,117 against 23,586. That is available at zero extra cost and it
points at the mechanism:

> A horizontal level sits **at a remembered price** — somewhere trades
> actually happened. A sloping line sits at an **extrapolation**, and the
> further it runs from its anchors the further it drifts from any price anyone
> transacted at. So it is crossed more often, and each crossing means less.

That reading also squares with EM-2, whose finding was that **touches** carry
the information about a level — i.e. the memory of a price. Slope discards
that memory in favour of a projection.

**It is a hypothesis, not a finding**, and it is labelled as one. It is
testable — does the T−H gap widen with |slope|? — and that test is not run
here, because Gate A has already decided the question Phase A existed to ask
and running it on the data that suggested it is how a mechanism gets
manufactured (the `#85` → `#86` discipline).

## Pre-registered consequence, applied

> **On failure: stop.** No `L4`, no Phase B, and EM-5 is recorded as what it
> would then be — a re-derivation of EM-2's levels with extra steps.

So **`L4` is not built** (the authority ordering — contacts ≫ duration >
angle), and **Phase B is not built**: no Three-Fan Principle, no return
line/channel, no authority wiring, no frontend overlay. The estimate for all
of that was 12–16 sessions; Gate A cost four.

**One thing Phase A delivers regardless**, and it was promised up front: the
first standalone, deterministic, causal trendline object in this codebase —
`admissible_lines`, `detect_penetration`, `count_contacts`, `amend_line`, 46
tests. The Three-Fan Principle and EM-7's deferred trendline throwback both
needed it before they could be measured at all. They can now be measured
cheaply if anyone wants to, with the knowledge that the line they rest on is
worse than a horizontal through its own anchors.

## What this means for the register

EM-5 was the **last** candidate. Seven have now been measured to a
conclusion, and the pattern is consistent enough to state as a result in its
own right:

| | |
|---|---|
| EM-1 volume validation | **shipped** |
| EM-9 penetration filter | recommended unchanged |
| EM-2 volume-weighted S/R | negative — levels real, no elaboration beat counting touches |
| EM-3 basing-point stops | real but tail-driven; default stayed ATR |
| EM-4 Magee Evaluative Index | measure ships; headline overturned by more data at `#87` |
| EM-6 Dow multi-index gate | negative — confirmation *removed* what little the raw regime had |
| EM-7 throwback entry | both claims confirmed, **tactic refuted** (adverse selection) |
| EM-8 measuring implications | two bug fixes, no feature; `MEASURED_MOVE` found dead |
| **EM-5 trendline engine** | **negative — slope is worse than no slope** |

**The structure E&M describe is real on this market; almost nothing built on
top of it pays.** EM-2 and EM-7 said it about levels. EM-5 now says it about
lines, and says something sharper: the sloping version of a level is *worse*
than the level.

Of nine candidates, **one shipped a feature** — and the workstream's larger
return was elsewhere: `#92` (a gap objective wrong twice over, ~70% of gap
targets unfounded), `#93` (a non-positive price crashing the live stop
module), `#94` (an AI review dead for five months), `#80`, `#82`, `#70`, `#52`,
and `MEASURED_MOVE`'s discovery. **Measuring the book's claims was worth more
for the bugs it exposed than for the claims it confirmed.**
