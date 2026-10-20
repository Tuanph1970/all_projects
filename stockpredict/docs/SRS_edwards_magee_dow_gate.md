# SRS — EM-6: Dow-Theory multi-index confirmation gate

**Version:** 1.0 (Phase 1 design)
**Date:** 2026-10-20
**Backlog:** `#66`
**Register:** `docs/implementation_plan_edwards_magee.md` § EM-6
**Study that settled the open question:** `decision-helper-service/tests/em6_witness_study.py`
**Status:** design only. Nothing is built. The gate's value is **not** established
by this document and is explicitly at risk — see §9.

---

## 1. What the book requires

E&M's tenet 8 is the one they call *most questioned, most durable*:

> **The Two Averages Must Confirm** — no valid trend-change signal from one
> average alone. They need not confirm on the same day.

With tenet 11 — *only closing prices used; any penetration, even 0.01, counts* —
and tenet 12, *a trend is assumed to continue until reversal is definitely
signalled*. The primary trend itself is read from **successively higher tops
and bottoms** (or lower ones): both, not one.

Bassetti's 9th-edition revision is the directly applicable part, because it
addresses our exact problem — a narrow index cannot represent an economy:

> Thirty stocks can no longer represent the economy. Read the broad trend from
> the **Dow Industrials + S&P 500 + NASDAQ Composite** together, requiring
> *"harmonic convergence"* among the three; **disagreement among them is itself
> a signal to hedge.**

Two parts, and they are different mechanisms: a **gate** (confirmation
required) and a **hedge signal** (disagreement is information, not merely the
absence of permission). Both are in scope.

## 2. Where it lands, and the state of the code

| | |
|---|---|
| today | **no market-level trend context reaches any signal.** `confirmation/layer.py` applies three checks — penetration, time-delay, oscillator — and all three are per-ticker. Verified: zero hits for `VNINDEX`/`VN30`/`HNX` anywhere in `decision-helper-service/app`. |
| integration point | a fourth check in `confirmation/layer.py`, plus a prior for the regime classifier |
| A/B switch | a `BacktestConfig` flag, the shape `#82` (`failed_signal_enabled`) and EM-3 (`trailing_stop_mode`) already use |

### 2.1 Data — no schema change, and one trap to avoid

**No DB migration is required.** `GET /stocks/{symbol}/history` falls through
to a live vendor fetch for any symbol with no rows in the DB
(`stock-data-service/app/services/stock_service.py:1137`), and index codes are
ordinary symbols to the vendor. `news-service` already relies on exactly this,
passing `index_symbol="VNINDEX"` into its `PriceHistorySource`
(`call_scorer.py`), so the path is in production use.

**The trap:** `market_indices` (`domain.py:141`) looks like the right table and
is **dead** — it has a reader (`stock_repository.py:293`) and an endpoint
(`routes.py:460`) but **no writer anywhere in the repo**. The register's claim
that "index data exists / is served" is true of the endpoint and false of the
data. EM-6 must **not** build on that table; populating it is a separate
tech-debt question (logged, not taken here).

**Caching is a requirement, not an optimisation.** Market context is
market-wide: one reading per index per day serves the entire universe. The
live fallback is per-request and sits behind the vnstock guest quota (20
req/min, `#49`), so a gate that re-fetched three index series per evaluated
symbol would exhaust the quota and make the orchestrator useless. See
`FR-EM-D7`.

## 3. The register's open question, settled by measurement

The register deferred one risk to this document:

> VNINDEX and VN30 share most of their weight, so they may confirm trivially;
> HNX / UPCOM or a breadth measure (EM-4) may be the real second witness. That
> question belongs in the Phase-1 SRS, not here.

It is answerable without building anything, so it was answered first. Criteria
were fixed before the first run. A witness is **usable** only if all three
hold on its common history with VNINDEX:

| | criterion | why |
|---|---|---|
| **W1** | daily-return correlation ≤ 0.95 | not substantially the same instrument |
| **W2** | the two disagree on ≥ 10% of days | the gate would actually bind |
| **W3** | median disagreement episode ≥ 5 bars | a trade held for weeks cannot be governed by a witness that changes its mind daily |

Measured on the full vendor history of five VN indices (22,318 bars; VNINDEX
5,672 bars from 2004-01-05), under **two** trend definitions so the conclusion
does not rest on one proxy — the shipped `compute_regime` (20/50 MA spread)
and a **Dow swing rule** (successive confirmed swing highs *and* lows, closing
prices only, 5% reversal threshold):

| witness vs VNINDEX | corr | disagree (MA / Dow) | median episode | verdict |
|---|---|---|---|---|
| **VN30** | **0.965** | 14.4% / 13.2% | 2 / 15 | **unusable — W1 fails** |
| **HNXINDEX** | 0.469 | 27.5% / 36.3% | 5 / 34 | **usable** |
| HNX30 | 0.772 | 32.5% / 40.2% | 5 / 45 | usable |
| **UPCOMINDEX** | 0.451 | 46.8% / 37.5% | 12 / 42 | **usable** |

**The register's fear was exactly right about VN30 and wrong about the rest.**
VN30 is 0.965-correlated with VNINDEX — the same instrument wearing a second
name — and under the MA definition its disagreements have a median length of
**2 bars**, i.e. flicker. Its confirmation lag is **median 0 bars, 99% within
120 bars**: it confirms instantly and essentially always, which is the
definition of a trivial witness.

The full correlation matrix identifies the real structure:

| | VNINDEX | HNXINDEX | UPCOM | VN30 | HNX30 |
|---|---|---|---|---|---|
| **VNINDEX** | – | **0.469** | **0.451** | 0.965 | 0.772 |
| **HNXINDEX** | 0.469 | – | **0.461** | 0.775 | 0.887 |
| **UPCOMINDEX** | 0.451 | 0.461 | – | 0.537 | 0.520 |
| VN30 | 0.965 | 0.775 | 0.537 | – | 0.753 |
| HNX30 | 0.772 | 0.887 | 0.520 | 0.753 | – |

**VNINDEX + HNXINDEX + UPCOMINDEX are pairwise 0.45–0.47** — three different
exchanges (HOSE, Hanoi, the unlisted board), mutually near-independent. That
is a genuine three-witness set and a closer analogue to Industrials-vs-
Transports than VN30 could ever be: different *populations of companies*, not
a subset of the same one. VN30 and HNX30 are redundant subsets of their
parents (0.965 and 0.887) and are excluded by measurement.

**So EM-6 is not vacuous — but only via HNX and UPCOM.** Had the design
followed the register's phrasing and used VN30 as the second average, it would
have shipped a gate that passes everything.

### 3.1 The finding that most threatens EM-6's value

E&M allow the averages to confirm late. Measured, on VNINDEX trend changes:

| witness | turns | confirmed within 120 bars | median lag |
|---|---|---|---|
| HNXINDEX | 209 | **98%** | **2 bars** |
| UPCOMINDEX | 179 | 92% | 5 bars |
| VN30 | 152 | 99% | 0 bars |

**A witness that eventually confirms 98% of the time is not a veto — it is a
delay.** The gate's strictness is therefore almost entirely a property of the
lag window `k`, not of the witness:

* `k = 0` (same-day confirmation): blocks **21.7%** of VNINDEX TREND_UP days.
* `k → 120`: blocks about **2%** — very nearly inert.

And unanimity is expensive. Requiring all three to agree leaves only **37–48%**
of VNINDEX TREND_UP days standing; harmonic convergence holds on just
**37.1–42.0%** of days for the independent triple.

This is the central design tension and it is stated here rather than
discovered later: **EM-6 is a timing filter whose cost is known (a fifth to
two-thirds of long signals) and whose benefit is not.** §9 makes that the kill
criterion.

## 4. Functional requirements

**FR-EM-D1 — Market context provider.** A new module
(`decision-helper-service/app/services/market_context/dow.py`) computes, per
index code, a primary-trend state in `{TREND_UP, TREND_DOWN, UNDEFINED}` from
a bar series. Pure, no I/O, no side effects — the shape of
`backtest/market_features.py`, so the backtest can call it per bar.

**FR-EM-D2 — Trend definition is Dow's, not an MA proxy.** State turns UP only
when the latest confirmed swing high **and** swing low both exceed their
predecessors, DOWN only when both fall below, and otherwise **holds** (tenet
12). **Closing prices only** (tenet 11); no intraday extreme participates. The
swing confirmation threshold is a parameter, default 5%, which is the
discretisation of "secondary reaction" and is acknowledged as a choice E&M
leave to judgment.

**FR-EM-D3 — The witness set is fixed by measurement.** Lead = the index of
the symbol's own exchange (VNINDEX for the HOSE universe). Witnesses =
`HNXINDEX`, `UPCOMINDEX`. **VN30 and HNX30 are excluded** with the correlations
in §3 recorded in the code beside the constant, so the next reader does not
re-litigate it.

> **⚠️ D4 and D5 COMPOSED AT PHASE 2.** As written below, `FR-EM-D4`
> confirms a *turn* (an event) while `FR-EM-D5` checks a *state* — two
> mechanisms, with no statement of how they relate. The plan resolves it into
> one: **the witness governs how a lead turn is *adopted*; the gate then
> checks a signal against the adopted trend**, and an unconfirmed turn leaves
> the previous trend standing, which is tenet 12 rather than a special case.
> `confirmed_primary_trend(lead, witnesses, k)` is the single primitive. See
> `docs/implementation_plan_em6_dow_gate.md` §1.

**FR-EM-D4 — Confirmation with a lag window.** A lead trend change at day *t*
is *confirmed* if a witness holds the same state at any day in `[t, t+k]`.
`k` is a parameter (default provisional, §9). This implements *"they need not
confirm on the same day"* literally.

**FR-EM-D5 — Gate modes.** `OFF` (**default**), `CONFIRM_2` (lead + at least
one witness), `UNANIMOUS_3` (all three). Off by default because an unmeasured
gate must not change live behaviour — the discipline `#82` established after
the failed-signal override shipped on by default and distorted every exit
statistic.

**FR-EM-D6 — Disagreement is a signal, not only an absence.** When the
witnesses disagree with the lead, apply a **confidence penalty** rather than a
veto, in the style of the existing oscillator rule, and emit a reason step
naming the disagreeing indices. This is Bassetti's *"disagreement is itself a
signal to hedge"*; a veto would discard it.

**FR-EM-D7 — One reading per index per day, shared.** Market context is
computed once per `(date, index)` and reused across every symbol in the
evaluation pass. Required by the quota, per §2.1.

**FR-EM-D8 — Strict causality (C1).** Context for day *t* is computed from
bars up to and including *t* and nothing later. The swing rule is incremental
by construction; a swing point becomes *confirmed* only once the reversal has
happened, which is backward-looking confirmation and therefore legitimate.

**FR-EM-D9 — Integration.** `confirm()` gains an optional market-context
argument; absent, behaviour is byte-identical to today. `BacktestConfig` gains
`dow_gate_mode` and `dow_gate_lag_bars` for the A/B.

**FR-EM-D10 — Every default here is provisional** pending the §8 measurement,
as `FR-EM-V11` reserved for EM-1. The numbers in §3 describe index agreement,
**not** signal profitability, and must not be quoted as the latter.

## 5. Edge cases

| ID | case | required behaviour |
|---|---|---|
| **EC-D1** | witness series unavailable, too short, or `UNDEFINED` | **fail OPEN** — accept as if the gate were off, and record `SKIP` with the reason. A data outage must never silently suppress every signal; that failure would look exactly like a quiet market. |
| **EC-D2** | HNX/HOSE trading calendars differ | align on dates present in the witness; if the witness has no bar for day *t*, carry its last known state and **bound the staleness** (reject as stale beyond a limit rather than trusting an old reading) |
| **EC-D3** | lead index has < `slow`/2-swing history | `UNDEFINED` → gate skips, per EC-D1 |
| **EC-D4** | universe widens beyond HOSE | the lead must be the symbol's **own** exchange index; a HOSE lead for an HNX-listed symbol is a silent category error |
| **EC-D5** | index code is also a valid ticker | address indices by an explicit allow-list constant, never by string heuristics |

## 6. Harnesses (built with the code, not after)

| ID | harness |
|---|---|
| **H-D1** | **Causality.** Append future bars; every past context reading must be unchanged. The EM-4 pattern (`test_mei.py`). |
| **H-D2** | **Fail-open.** With witnesses unavailable, the accept/reject decision and final confidence must equal gate-off **exactly**, signal for signal. |
| **H-D3** | **Vacuity guard.** On real data the gate must change the decision on a material share of signals. A gate that changes nothing is a bug, not a conservative default — this is the lesson of VN30 in §3, encoded as a test. |
| **H-D4** | **Determinism.** Repeated runs identical. |
| **H-D5** | **Bound-default guard.** Parameters must be read at call time, not captured in default arguments. This project has paid for that trap five times (EM-1 S2, `#78`, `W1`, `#84`, and `#87`'s `HISTORY_YEARS`), and `compute_regime(bars, fast=20, slow=50)` is itself an instance. Mutation-checked, as `#87` did. |
| **H-D6** | **Planted agreement/disagreement.** Synthetic index pairs constructed to agree, and to disagree for a known span, must be classified accordingly — the detector-level analogue of the planted-pattern test. |

## 7. Deliberately out of scope

* **Populating `market_indices`.** Dead table; EM-6 routes around it.
* **The MEI as a fourth witness.** EM-4's breadth measure is a genuinely
  different construction and Bassetti explicitly urges running the MEI across
  all three indices. But `#87` has just shown that breadth *level* carries
  nothing about forward index returns, so adding it as a witness now would be
  building on a measured null. Deferred, with that reason.
* **Frontend.** No UI until the gate is shown to pay.
* **Hedging mechanics.** `FR-EM-D6` emits the hedge *signal*; acting on it
  (short the index, size down) is portfolio-level work and belongs with EM-4's
  unbuilt governor.

## 8. Mandatory benchmark (C4)

Gate `OFF` vs `CONFIRM_2` vs `UNANIMOUS_3` on the **same universe and window**
through `backtest/harness.py`, reporting gross and net P&L per trade, hit
rate, trade count, and the suppressed-signal count — because a gate that
improves hit rate while destroying trade count has not necessarily helped.

Out-of-sample, with the `#84` machinery: walk-forward windows, **clustered**
significance by symbol, and a sign test for consistency across symbols —
`#84`'s lesson being that magnitude and consistency are separate claims and
EM-3 won the first while losing the second.

## 9. Pre-registered kill criterion

Fixed now, before implementation, because §3.1 already shows the cost:

> The gate ships enabled **only if** `CONFIRM_2` improves net P&L per trade
> out-of-sample with clustered significance (p < 0.05), **and** the
> improvement survives the suppression — i.e. total net P&L must not fall
> while per-trade P&L rises. Failing that, the gate stays `OFF` and EM-6 is
> recorded as a measured negative, as EM-2 was.

A second, independent kill criterion:

> If `H-D3` shows `CONFIRM_2` with the chosen `k` changes the decision on < 5%
> of signals, the gate is inert and must not ship at all, whatever its P&L
> point estimate.

**The honest prior is unfavourable.** A 98%-eventual-confirmation witness, a
cost of a fifth to two-thirds of long signals, and this project's record —
EM-2 closed negative, EM-3 confirmed on magnitude but not consistency, EM-4's
headline finding overturned by more data at `#87` — all argue that EM-6 is
more likely to be a measured negative than a shipped feature. It is worth
measuring anyway, because tenet 8 is the single most-cited rule in the book
and a null on it is a publishable result for this project. It is **not** worth
pre-committing to.

## 10. Open questions for the Phase-2 plan

> **All four were settled in `docs/implementation_plan_em6_dow_gate.md`:** (1)
> `k` is swept at D6; (2) both trend rules are built behind a `trend_rule`
> parameter and measurement decides; (3) the modes are made **mutually
> exclusive**, so the penalty and the gate cannot hide each other; (4) the
> swing threshold is swept on `{3, 5, 8}%` reading sign robustness, not the
> peak. The plan also adds a trap the SRS missed — a market-wide gate is **one
> treatment on shared dates**, so significance must cluster by **date**, not
> by symbol as `#84` correctly did for a per-symbol rule.

1. **`k`, the lag window.** §3.1 makes this the parameter that *is* the design.
   Sweep it; expect the familiar shape where the sign is robust and
   significance is fragile (`#84`'s filter sweep).
2. **Which trend definition the gate ships with.** `FR-EM-D2` chooses Dow's
   rule because it is the book's. But the Dow rule produces only **15–29 state
   changes in 20 years** on VNINDEX, so the gate state is extremely
   persistent, and the MA proxy may be the more useful instrument even though
   it is not E&M's. Decide by measurement, not by fidelity.
3. **Whether the penalty in `FR-EM-D6` and the gate in `FR-EM-D5` interact.**
   `#83` found exactly this class of bug: capping severities made `#82`'s
   override structurally unreachable. If a disagreeing witness both penalises
   confidence and blocks the signal, the penalty is unobservable. Scope them
   explicitly.
4. **The 5% swing threshold.** Unmeasured. Sweep with `k`.

---

## Appendix — a data gap found while probing, not fixed here

The vendor serves **VNINDEX from 2004-01-05 (5,672 bars)**. `#87`'s
`deep_history_dump.py` set `START = "2008-01-01"` and so captured 4,903 bars
from 2008-02-18 — missing **2004–2008, which contains the entire 2006–07 VN
bubble and its March-2007 top** (VNINDEX ~1170 → 235 by February 2009).

That is a live gap in the EM-4 bottoms re-test, which concluded on 19.7 years
and could have had 22.8, including one more complete bubble-and-crash cycle —
the exact event class the claim is about. Logged as its own backlog item
rather than folded in here, since EM-6 is the task in hand and the EM-4 re-run
is a separate measurement with its own pre-registered criterion.
