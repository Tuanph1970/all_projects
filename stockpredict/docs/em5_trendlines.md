# EM-5 — the trendline engine: slope is worse than no slope

**Date:** 2026-10-23
**Backlog:** `#65` — **closed**
**Design:** `SRS_edwards_magee_trendlines.md` (Phase A) · **Plan:** `implementation_plan_em5_trendlines.md`
**Gate:** `em5_gate_a.md` (FAIL)
**Outcome:** Phase B not built. The engine ships as apparatus, consumed by
nothing. **EM-5 was the last candidate in the register.**

---

## What was asked, and what came back

Phase A asked one question, chosen because the previous five candidates had
circled it without ever asking it directly:

> **Does the slope earn anything?** A trendline is a *sloping level* through
> the same swing pivots EM-2's horizontal levels come from. Does breaking it
> tell you anything a horizontal through the same anchors does not?

| h | trendline | horizontal at `p₂` | difference | t |
|---|---|---|---|---|
| 10 | +0.965% | **+1.437%** | −0.471 | **−7.18** |
| 20 | +1.654% | **+2.163%** | −0.509 | −3.71 |
| 60 | +3.815% | **+4.713%** | −0.897 | −2.08 |

**0 of 3 horizons, at all three penetration settings** (3%, 2%, 1.0 ATR),
direction consistent in **9 of 9** grid cells, on **45,117** trendline events
against 23,586 horizontal ones across 92 symbols. The robustness arm — the
horizontal at the anchors' *mean* — beats the trendline too.

So the answer is not "slope adds nothing". It is **slope subtracts**.

## The mechanism, offered as a hypothesis

Trendlines break **nearly twice as often** as the horizontals through their own
anchors (45,117 against 23,586). That number came free with the event counts
and it suggests why:

> A horizontal level sits at a **remembered price** — somewhere trades actually
> happened. A sloping line sits at an **extrapolation**, drifting further from
> any transacted price the longer it runs. So it is crossed more often, and
> each crossing means less.

That squares with EM-2, whose finding was that **touches** carry the
information about a level. Slope discards that memory in favour of a
projection.

**It is not tested.** It is testable — does the gap widen with |slope|? — but
running that on the data which suggested it is how a mechanism gets
manufactured (`#85` → `#86`).

## What the scoping bought

Full EM-5 was five deliverables and **12–16 sessions**. Phase A cost **four**,
and the gate arrived at task 4 of 6 because `L1`'s measurement corrected the
plan: authority *ordering* belonged behind the gate, but contact *counting*
did not, since E&M's own amendment rules make three contacts a **validity
threshold** rather than a score.

**Not built:** the Three-Fan Principle, the return line and channel, authority
scoring, the frontend overlay.

**Built and kept**, as promised before the gate ran: the first standalone,
deterministic, causal trendline object in this codebase.

| | |
|---|---|
| `market_context/trendline.py` | `admissible_lines`, `candidate_pair_count`, `Trendline` |
| `market_context/trendline_breaks.py` | `count_contacts`, `is_confirmed`, `detect_penetration`, `amend_line` |
| tests | **46** |
| consumed by | **nothing** — no signal, no default changed |

The Three-Fan Principle and EM-7's deferred trendline throwback both needed
this before they could be measured at all. They can be measured cheaply now —
knowing the line they would rest on is worse than a horizontal through its own
anchors.

## What the design got right before measuring

* **Closes, not extremes.** E&M say it outright — *"closing prices often make a
  better trendline than extreme lows, especially in thin erratic stocks"* — so
  the engine shares a vocabulary with `dow.py` instead of inventing a second.
* **The price-track constraint does the pruning, not a cap.** Measured: it
  removes **81.6%** of candidate pairs, and zero tolerance never prunes to
  nothing (0 of 1,992 bars had no admissible line). Had a cap been doing the
  work, every number downstream would have been measuring the cap.
* **Returning a ranked set, not a line.** E&M's method is explicitly plural —
  *"draw every line the action permits, lightly; erase the useless"* — so
  total enumeration plus a hard rule is both faithful and deterministic.
* **The comparison was fixed in the plan**, not at measurement time, because
  "a horizontal through the same anchors" is ambiguous and the ambiguity would
  otherwise have been resolved under pressure.

## And three errors of mine, recorded

1. **A test ending in `... or True`** — a tautology left in while drafting,
   exactly the vacuous assertion I criticise elsewhere.
2. **Guard fixtures that could not fail.** Twice: a "quiet" fixture that was
   not quiet *relative to its level*, and a contact fixture whose closes sat
   *exactly* on the line, so any tolerance passed. The pattern across L1 and
   L2 is consistent and worth naming.
3. **A flaw in my mutation-checking method.** Python served **stale bytecode**
   when a mutation and its restore were the same byte size inside one
   filesystem mtime second. The dangerous direction is the mirror image — a
   mutation that never loads looks as though it *survived* — so both
   previously recorded survivors were re-verified with the cache cleared.
   Every check since clears `__pycache__`.

`EC-L5` in my own SRS also turned out ambiguous, with the code right:
admissibility is a property of the anchor segment, fixed in the past, so a
later crossing is a *penetration* and not a retroactive invalidation — which
is precisely why E&M can speak of a throwback to the **projected** trendline.

---

## The register is closed. Nine candidates.

| | outcome |
|---|---|
| **EM-1** volume validation | **shipped** |
| EM-9 penetration filter | recommended unchanged |
| EM-2 volume-weighted S/R | negative — levels real, no elaboration beat counting touches |
| EM-3 basing-point stops | real but tail-driven; default stayed `ATR` |
| EM-4 Magee Evaluative Index | measure ships; headline overturned by more data at `#87` |
| EM-6 Dow multi-index gate | negative — confirmation *removed* what the raw regime had |
| EM-7 throwback entry | both claims confirmed, **tactic refuted** (adverse selection) |
| EM-8 measuring implications | two bug fixes, no feature; `MEASURED_MOVE` found dead |
| **EM-5** trendline engine | negative — **slope is worse than no slope** |

**One of nine shipped a feature.** Read alone that looks like a poor return.
It isn't, for two reasons.

**First, the negatives are load-bearing.** The system does not now carry a
volume-weighted S/R score, a Dow confirmation gate, a throwback entry, a
measured-move target path, an exposure governor, or a trendline engine wired
into anything — and each of those absences is backed by a number rather than
by taste. EM-2, EM-7 and EM-5 together say something consistent and useful:
**the structure E&M describe is real on this market, and almost nothing built
on top of it pays.**

**Second, the measurement found bugs the features never would have.** Across
the workstream: `#92` (a gap objective wrong twice over — ~70% of gap targets
unfounded), `#93` (a non-positive price crashing the live stop module), `#94`
(an AI review dead five months), `#80` (half-reported commission), `#82`,
`#70`, `#52`, `MEASURED_MOVE` found to be dead code, and — chasing a dashboard
of N/A — `#95` (a vendor period vocabulary silently returning quarterly data).
**Measuring the book's claims was worth more for the bugs it exposed than for
the claims it confirmed.**

What remains of the register is `#86` (EM-3's long/short hypothesis, logged so
it can be tested on evidence it did not come from) and `#90` (EM-4's history
starting four years late). Both are small, both are pre-registered, and
neither is a feature.
