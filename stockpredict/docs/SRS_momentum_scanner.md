# Software Requirements Specification

## Daily Momentum & Base Scanner (Qullamaggie discovery funnel)

**Document version:** 1.0
**Date:** 2026-11-09
**Status:** Draft (Phase 1 — Design)
**Source method:** `docs/Cam_nang_Giao_dich_Qullamaggie.pdf` — Part 2, *Quy Trình Lọc Cổ
Phiếu Hàng Ngày*. Part 1 (entry/stop/exit) is **not** in scope; see §1.3.
**Sibling docs:** `docs/implementation_plan_momentum_scanner.md` (the companion plan,
written in the next phase), `docs/SRS_edwards_magee_*.md` (the evaluation engine this
feeds).

---

## 1. Introduction

### 1.1 Purpose

Every signal surface in this platform today answers the same question: *given a ticker I
already care about, what should I do with it?* `POST /helper/scan` evaluates the user's
`HelperWatchlist`; the narrator narrates a symbol the user opened; the decision
orchestrator sizes a position in a symbol already named.

Nothing answers the prior question: **which tickers should be on the watchlist at all?**

This document specifies a **discovery funnel** — a nightly sweep that ranks the tradeable
universe by medium-term relative strength, keeps only the names that are *resting* in a
contracting base rather than extended, and emits a ranked candidate list with the
breakout level already computed. Its output is an input to the existing evaluation
engine, not a replacement for it.

### 1.2 Scope

The system **shall**:

- Resolve a **scan universe** from stored symbols, bounded by what has sufficient daily
  history (FR-SCAN-UNIV).
- Reject symbols failing a **liquidity floor** expressed in VND turnover (FR-SCAN-LIQ).
- Rank survivors by **multi-horizon momentum** over 21 / 63 / 126 trading bars
  (FR-SCAN-MOM).
- Apply a **trend template** — price above its longer moving averages, with a prior
  advance (FR-SCAN-TREND).
- Detect that the symbol is **based, not extended**: a sideways consolidation whose range
  and volume are contracting (FR-SCAN-BASE, FR-SCAN-SQUEEZE).
- Measure **short-MA proximity** — MA10/MA20 riding just under price (FR-SCAN-MA).
- Emit the **pivot level** (base resistance) a breakout would have to clear
  (FR-SCAN-LEVEL).
- Return a **ranked candidate list** and allow the user to push a candidate onto
  `HelperWatchlist` (FR-SCAN-OUT).
- Run **nightly after the close** and expose on-demand endpoints (FR-SCAN-SCHED,
  FR-SCAN-API).
- Refuse to rank a symbol whose history contains an **unrepaired price seam**
  (FR-SCAN-SEAM).

The system **shall not**:

- **Generate entries, stops, targets or position sizes** (EC-S6). That is the decision
  helper's job and it already does it. The scanner's output is a *candidate*, and the
  candidate is evaluated by `POST /helper/scan` exactly as a hand-added ticker is.
- **Own the watchlist.** `HelperWatchlist` stays owned by decision-helper-service; the
  scanner proposes, the user (or an explicit auto-add setting) disposes (EC-S6).
- **Introduce a new market-data provider or raise vnstock call volume** (EC-S2). It reads
  `stock_prices` that nightly ingestion already fills.
- **Re-implement pattern detection.** `ai-insights-service/app/services/patterns/` already
  has flag/pennant/triangle detectors; the scanner calls or ports them, never forks them
  (EC-S3).
- **Claim the method works on VN equities.** It makes the method *runnable* and
  *measurable*. Whether it has edge here is settled by §7, not by this document.

### 1.3 Why Part 1 is excluded

Qullamaggie's Part 1 (buy the breakout, stop 2–5% under, sell 1/3–1/2 into strength,
trail on MA10/MA20) is almost entirely already implemented, under different names and
from a different book: breakout confirmation with a penetration filter
(`confirmation/layer.py`), basing-point trailing stops (`risk/basing_point.py`),
partial-exit and target logic (`risk/target_module.py`), position sizing
(`risk/sizing_module.py`), failed-breakout detection (`signal/failed_signal.py`).
Specifying it again would duplicate a working subsystem. The **gap is Part 2**, and the
gap is real: §2 measures it.

**The mapping, verified by grep on 2026-11-09** (recorded because "implement Part 1" is
the obvious next thought after S-5a, and it is the wrong one):

| Qullamaggie Part 1 | Already implemented as |
|---|---|
| Buy the break of the base resistance | `confirmation/layer.py` (penetration filter, EM-9) + `signal/trend/n_day_breakout.py` |
| Stop under the day's low / the MA | `risk/stop_module.py` (chart → swing → ATR → money) |
| Trail on MA10 / MA20 | `risk/basing_point.py` (EM-3; the `/backtest` default since #101) |
| Sell part into strength | `risk/target_module.py` |
| Size from the 2–5% risk | `risk/sizing_module.py` |
| A breakout that fails | `signal/failed_signal.py` |

**What the same grep did expose is a missing handshake, not a missing feature.** Every
`pivot` reference in the risk modules is a *swing* pivot; the decision engine computes its
own levels and has never heard of `ScanCandidate.base.pivot`. So the scanner reports a
pivot at one price and the engine confirms a breakout at its own N-day high, and the two
surfaces can disagree in front of the user. Recorded as Backlog #140.

### 1.4 Definitions

| Term | Meaning here |
|---|---|
| **Bar** | One daily OHLCV row in `stock_prices`. |
| **Base** | A sideways range following an advance; Qulla's *vùng nền tích lũy*. |
| **Pivot** | The base's upper boundary — the level a breakout clears. |
| **Squeeze** | Range contraction + volume dry-up toward the right edge of the base. |
| **Extended** | Price far above the base/short MAs; the opposite of a valid setup. |
| **Seam** | A stored overnight move larger than the exchange band permits — an ingestion artefact, see FR-SCAN-SEAM. |

---

## 2. Current state — measured, not assumed

Measured on this machine, 2026-11-09, against the live `defaultdb`.

### 2.1 What already exists and is reusable

| Capability | Where | Verdict |
|---|---|---|
| Generic field screener + saved configs | `analysis-service` `POST\|GET /analysis/screener`, `analysis_service.py:896` | Reusable as a **UI pattern**, not as the engine: it filters a one-day price-board snapshot with no history behind it. |
| Liquidity assessment over N bars | `decision-helper-service/app/services/universe/liquidity.py` `assess_liquidity()` | **Directly reusable** — it already returns `avg_daily_value` and `avg_daily_volume`, strictly causal. Disabled by default (`MIN_AVG_DAILY_VALUE = 0.0`) and applied only to an existing watchlist. |
| Flag / pennant / triangle detection | `ai-insights-service/app/services/patterns/continuation.py` | **Directly reusable** for "resting in a flag, not parabolic". ATR-scaled pole, retrace cap, linearity floor. |
| Price-seam detection + repair | `stock_common.analytics.find_price_seams`; `stock-data-service` nightly sweep + `POST /stocks/{symbol}/repair-history` | **Directly reusable** as the data-integrity gate. |
| Watchlist store + evaluation | `decision-helper-service` `HelperWatchlist`, `POST /helper/scan` | The **consumer** of this scanner's output. |

### 2.2 What does not exist

- **No momentum or relative-strength ranking anywhere in the repository.** No 1M/3M/6M
  return, no RS rank, no cross-sectional comparison of any kind. This is the core of
  Qulla's Step 1 and it is absent.
- **No MA10.** `analysis-service` computes SMA20/50/200 only (`schemas.py:42-44`).
- **No volatility-contraction / volume-dry-up metric.** The flag detector caps retrace
  and requires tightness, but nothing measures *progressive* contraction toward the right
  edge, which is the squeeze Qulla actually waits for.
- **No market-wide sweep.** Every existing scan path is per-symbol or per-watchlist.

### 2.3 The universe problem — the decisive constraint (RESOLVED by S-0, 2026-11-09)

As first measured, before the backfill:

```
stock_prices : 43,370 rows | 32 distinct symbols | 2021-03-15 .. 2026-11-06
companies    : 32 rows, all exchange = HOSE
symbols with >= 126 bars : 32
stock_prices.value > 0   : 0 rows  (turnover column is empty on every row)
tbl_price_board : 92 distinct symbols (VN30 30, VN100 92, HOSE 30, HNX 30)
```

The groups are **hardcoded Python lists**, not a live listing:
`stock_service.py:2785` defines `STOCK_GROUPS["VN30"]` (30 symbols) and
`STOCK_GROUPS["VN100"]` (92 symbols). `HOSE` and `HNX` as served today return 30 names
each, not the exchange.

So the honest statement of scale is: **the scanner's universe today is ~92 symbols, of
which ~32 have usable daily history — not the ~1,600 listed Vietnamese tickers.**

Qullamaggie's funnel is a *selectivity* machine: thousands of names in, 10–20 out. At
n = 32 there is nothing to be selective about — a top-20 cut keeps 62% of the input, and
"top momentum decile" means three stocks. **Universe breadth is therefore a
prerequisite, not a later optimisation**, and §8-D1 is the decision that gates the whole
module.

`stock_prices.value` being NULL on all 43,370 rows means the VND liquidity floor must be
computed as `close × volume`, which is what `assess_liquidity` already does.

**S-0 ran on 2026-11-09. D1 was answered "backfill VN100" and the backfill is complete:**

```
companies    : 93 rows (92 VN100 + DPG), 91 HOSE + 2 HNX (IDC, PVS)
stock_prices : 122,914 rows | 93 symbols | 2021-03-15 .. 2026-11-06   (was 43,370 / 32)
symbols with >= 150 bars            : 93 / 93
symbols current to the last session : 93 / 93
```

61 symbols were created and synced (~1,300 bars each, 5 years, `HISTORY_YEARS = 5`) via
the existing `POST /stocks/{symbol}/ensure-and-sync`. Company rows were pre-seeded from a
single `GET /companies/all` listing (1,517 names) plus live
`GET /companies/group/{HOSE,HNX}` membership, specifically so `ensure_company_and_sync`
would take its "company found" branch and skip the **unpaced** `all_symbols()` call it
makes on the create path (`stock_service.py:1632`) — 61 of those would have blocked the
event loop and burned the quota for nothing.

Worth recording for D1 option 3: the live group endpoints return the **real** exchange
listing — HOSE 408, HNX 299, 707 names in total. Only the price-board path is limited to
the hardcoded 30, so a full-listing universe later is a data-volume question, not a
discovery one.

A top-20 cut over 93 names keeps 22% of the input — the funnel is now selective enough
that its output means something. §5's `SCAN_MAX_CANDIDATES = 20` default stands.

### 2.4 Correction to the Backlog #119 picture

Backlog #119 is closed more thoroughly than a reading of `adj_close` suggests, and the
root cause is not what the ticket title implies. `adj_close` **is** a byte-for-byte copy
of `close` — deliberately: vnstock/VCI returns an already back-adjusted series, so no
local adjustment is wanted. The fault was **our own incremental ingestion**:
`_top_up_prices` appends only bars after the last stored date, so when the provider
restates the whole history at a share-count event, the restated rows never land and the
old and new scales meet at a **seam** (`narrative.py:89-97`).

The remedy already shipped: `find_price_seams` in `stock-common`, a nightly scan-and-
repair in `stock-data-service` (`ENABLE_NIGHTLY_SEAM_SCAN`, capped at
`SEAM_SCAN_MAX_REPAIRS = 3`/night, bounded to `SEAM_SCAN_RECENT_DAYS = 30`), and a manual
`POST /stocks/{symbol}/repair-history`.

**The residual risk is exactly the one this module is most exposed to.** The 30-day
window is a deliberate loop guard, with the documented limitation that a seam older than
30 days is never auto-repaired. A 126-bar momentum ranking reads six months back — well
outside that window — so a stale seam does not merely mis-narrate one chart, it puts a
stock at the top or bottom of a cross-sectional rank for six months. Hence FR-SCAN-SEAM
is a hard gate, not a warning.

**Measured over the backfilled universe (S-0, 2026-11-09)** using `find_price_seams` at
its own `MAX_BELIEVABLE_DAILY_MOVE_PCT = 15.0`: **92 of 93 symbols clean, 1 flagged** —

```
VTP  2022-11-16   11.56 -> 13.54   +17.13%   ratio 0.854
```

and it is almost certainly a **false positive**, which matters more than the clean result:

- The symbol was re-pulled in full during S-0 (1,304 bars, 2021-08-05 onward, every row
  upserted). **The seam survived the re-pull.** A seam that survives a full re-fetch is
  provider data, not our ingestion artefact — §2.4's whole mechanism does not apply to it.
- The bar is internally consistent: previous session closes at its low (11.56), the next
  opens 11.78 and closes at its high (13.54). That is a limit-down day followed by a
  strong reversal, not a scale break.
- VTP traded on **UPCoM** in 2022 (it moved to HOSE in 2024), where the band is ±15% and
  reference-price resets widen it further. The detector's own docstring predicts exactly
  this: the flat 15% default is "the LOOSEST of the three" boards precisely because the
  board is not known per symbol at that layer.

**Refinement to FR-SCAN-SEAM, adopted here:** a seam that survives a full re-pull shall be
**classified, not excluded**. The gate excludes only seams the repair path can still fix.
The scanner shall therefore report `excluded_price_seam` and `flagged_price_seam` as two
distinct lists, and the per-exchange band (and the symbol's exchange *at the time of the
bar*, not today) is the input a later tightening needs. Excluding VTP outright on this
evidence would be the detector crying wolf — the failure mode the threshold comment was
written to avoid.

---

## 3. Functional requirements

### FR-SCAN-UNIV — Universe resolution
The scanner **shall** resolve its universe from symbols in `stock_prices` having at least
`MIN_BARS` (default 150) bars ending no earlier than the last completed trading session.
Symbols short of history are **excluded and counted**, never silently dropped: the
response carries `universe_total`, `excluded_insufficient_history`, and the exclusion
reason per symbol in verbose mode. A scanner that quietly ignores half the market is
indistinguishable from one that found nothing.

### FR-SCAN-LIQ — Liquidity floor
The scanner **shall** call `assess_liquidity()` over the last `LIQUIDITY_LOOKBACK_DAYS`
(default 50, matching Qulla's 50-session average) and reject symbols below
`SCAN_MIN_AVG_DAILY_VALUE` VND. The threshold **shall** be expressed in **turnover
(VND)**, not share count — Qulla's "300–500k shares" is meaningless across VN's price
range (EC-S4). Share-count floor is available but defaults to 0.

### FR-SCAN-MOM — Multi-horizon momentum ranking
For each surviving symbol the scanner **shall** compute total return over 21, 63 and 126
bars, and a composite rank. Requirements on the composite:

- Each horizon is ranked **cross-sectionally** (percentile within the scanned universe),
  then combined by configurable weights (default equal). Ranking percentiles rather than
  averaging raw returns prevents one volatile horizon from dominating.
- The number of symbols actually ranked **shall** be reported alongside the percentiles.
  A percentile over 32 names is not a percentile over 1,600 and the response must not let
  a reader confuse them.
- Returns **shall** be computed from `close`, strictly from bars at or before the scan
  date (EC-S1).

### FR-SCAN-TREND — Trend template
A candidate **shall** satisfy: `close > SMA50`, `close > SMA200`, `SMA50 > SMA200`, and a
prior advance of at least `MIN_PRIOR_ADVANCE_PCT` (default 30%) measured from the lowest
close in the last 126 bars. These restate Qulla's *"nằm trên MA50 và MA200, đã tăng 30–100%"*.
Each clause **shall** be reported individually as pass/fail, so a near-miss is visible
rather than collapsing to a single boolean.

### FR-SCAN-BASE — Base / consolidation detection
The scanner **shall** identify a base ending at the scan date: a window of
`BASE_MIN_BARS`..`BASE_MAX_BARS` (default 10..60) whose closes show no significant trend
and whose depth (high-to-low of the window) is at most `BASE_MAX_DEPTH_PCT` (default
25%). It **shall** reuse `FlagDetector`/`PennantDetector` from
`ai-insights-service/app/services/patterns/` for the flag-shaped case rather than
reimplementing them (EC-S3); the flat-base case is a new, narrower detector.

### FR-SCAN-SQUEEZE — Volatility contraction and volume dry-up
The scanner **shall** compute, over the detected base:

- **Range contraction**: ATR (or mean true range) of the base's last third divided by its
  first third. Lower is tighter; `< SQUEEZE_MAX_RATIO` (default 0.75) qualifies.
- **Volume dry-up**: mean volume of the last third divided by the base's own mean;
  `< DRYUP_MAX_RATIO` (default 0.80) qualifies.

Both **shall** be reported as numbers, not just booleans — the ratio is the thing a user
compares between candidates, and a hidden boolean cannot be calibrated later.

**On a FLAG window both denominators are the POLE, not the window** (Backlog #141,
measured — see §16). The cut-offs are unchanged; only what they are measured against
moves. A flag is 3–15 bars, so a "third" is one or two bars and the window's own mean is
computed over the same few quiet bars being judged — the flat denominators are
*degenerate* there rather than merely strict, and on a planted flag the window's first
third picks up the last pole bar, so the flat range ratio was partly measuring the pole it
was supposed to be compared against. The scanner **shall** therefore compute, for a FLAG:
last-third TR / mean pole TR `<= 0.75`, and last-third volume / mean pole volume `<= 0.80`.
Both pole-relative ratios **shall** also be reported as numbers, and **shall** be absent
(`None`) for a FLAT window, which has no pole — a flat base can then never be judged by a
flag's clause even by accident.

### FR-SCAN-MA — Short moving-average proximity
The scanner **shall** compute MA10 and MA20 (neither currently exists, §2.2) and report
`(close − MA10)/close` and `(close − MA20)/close`, plus whether both sit **below** price
within `MA_PROXIMITY_PCT` (default 8%). This encodes Qulla's *"MA10 và MA20 vắt chặt ngay
sát dưới đáy vùng nền"*.

**On a FLAG window the percentage ceiling does not apply; extension is bounded in ATR**
(Backlog #141, and the measurement says this was the *binding* clause — §16.2). Both
averages **shall** still sit below price: a flag whose MA20 is above it is not a pause in
an uptrend, and dropping the ceiling did not drop that requirement. What replaces the
ceiling is `(close − MA20) / ATR20 <= FLAG_MA_MAX_ATR` (default 5.0). The reason is
mechanical and was argued before any number was seen: a flag sits immediately after a
pole, which is exactly when price is **furthest** from its MA20, so a fixed percentage
bound asks a flag to look like a base whose averages have had weeks to catch up. What is
worth bounding there is *extension*, and extension scales with the stock's own volatility.
`(close − MA20)/ATR20` **shall** be reported alongside the two percentage distances.

### FR-SCAN-LEVEL — Pivot emission
For each candidate the scanner **shall** emit the pivot: the highest high of the detected
base, together with the distance from the current close in percent and in ATR. Where
`analysis-service`'s volume-weighted S/R (EM-2, `sr_volume.py`) returns a level within
`PIVOT_SR_TOLERANCE_PCT` of that high, the scanner **shall** report the S/R level's
strength beside it — a pivot confirmed by independent volume evidence is a different
object from one that is merely the window maximum.

### FR-SCAN-SEAM — Data-integrity gate
Before ranking, the scanner **shall** run `find_price_seams` over each symbol's scan
window. A symbol with an unrepaired seam **shall** be excluded from the ranking entirely
and reported in a dedicated `excluded_price_seam` list with the seam date and magnitude.
It **shall not** be silently repaired inline (that would re-pull history outside the
nightly quota budget, EC-S2); the response names the symbol so
`POST /stocks/{symbol}/repair-history` can be run against it. See §2.4 for why this is a
hard gate here and a warning elsewhere.

### FR-SCAN-OUT — Ranked output and watchlist hand-off
The scanner **shall** return candidates ordered by composite momentum rank, each carrying:
symbol, the three horizon returns and their percentiles, every trend-template clause,
base geometry (start/end, depth, length), squeeze and dry-up ratios, MA10/MA20 distances,
pivot level and distance, liquidity figures, and a flat list of the reasons it passed.
A candidate **shall** be pushable to `HelperWatchlist` through the existing
decision-helper API; the scanner does not write that table itself (EC-S6).

### FR-SCAN-SCHED — Nightly execution
The scanner **shall** run once per trading day after the close, after the nightly price
refresh and after the seam sweep (so it reads repaired data), modelled on the existing
`decision-helper-service` scheduler. Results **shall** be persisted per scan date so a
candidate list can be reconstructed as it stood on the evening it was produced — without
that, §7's forward evaluation is unfalsifiable.

### FR-SCAN-API — Endpoints
Under the existing `/stock_helper/api/v2` prefix and Traefik routing conventions:

- `POST …/scan/momentum` — run with an explicit parameter set, return ranked candidates.
- `GET …/scan/momentum?date=` — read back a persisted nightly run.
- `GET …/scan/momentum/{symbol}` — the full per-symbol diagnostic, including failed
  clauses, for a symbol that did *not* make the cut.

The third is not a convenience. Without it the scanner is unfalsifiable in daily use: a
user who expects a name to appear has no way to learn which clause rejected it.

---

## 4. Constraints

| ID | Constraint |
|---|---|
| **EC-S1** | **Strict causality.** Every figure for scan date *T* uses only bars ≤ *T*. No full-series computation then sliced. Mirrors the project-wide C1. |
| **EC-S2** | **No new provider, no extra quota.** Reads `stock_prices`. vnstock is at a 20 req/min client-side cap with no API key set (Backlog #49); a scanner that re-pulls history would starve the daily refresh. |
| **EC-S3** | **Reuse the existing detectors.** `patterns/continuation.py`, `universe/liquidity.py`, `sr_volume.py`, `find_price_seams`. New code only where §2.2 shows nothing exists. |
| **EC-S4** | **VND turnover, not share count,** for every liquidity threshold. |
| **EC-S5** | **Benchmark or it did not improve.** Per the project's C4: the candidate list is reported beside a null — see §7. |
| **EC-S6** | **Propose, do not dispose.** The scanner never writes `HelperWatchlist` and never emits entry/stop/size. |

---

## 5. Vietnamese-market adaptation

Qulla's parameters are US-equity parameters. Each adaptation below is a **decision with a
default**, not a translation.

| Qulla's rule | VN adaptation | Why |
|---|---|---|
| Price > $1–2 | Price ≥ `SCAN_MIN_PRICE` VND (default 10,000) and exchange ∈ {HOSE, HNX} | The US floor exists to exclude penny junk; in VN that role is played jointly by a price floor and by excluding UPCOM, where disclosure and liquidity differ in kind. |
| 50-day avg volume ≥ 300–500k shares | 50-day avg turnover ≥ `SCAN_MIN_AVG_DAILY_VALUE` VND (default 5×10⁹) | EC-S4. Also `stock_prices.value` is empty, so turnover is derived as close×volume. |
| Top % gainers, 1M/3M/6M | 21 / 63 / 126 **trading bars** | Calendar months drift against the Tết holiday, which moves every year and shifts the session count by up to a week. |
| Buy in the first 30–60 min | **Out of scope here** (Part 1), but flagged: VN's ATO auction, continuous session, lunch break and ATC make "the first hour" a different object | Recorded so the plan does not silently assume US intraday structure. |
| 2–5% stop | **Out of scope here**, but flagged as the deepest mismatch | T+2.5 settlement means the breakout day's position *cannot be sold that day*. The true day-1 risk is the full band, not 2–5%. Any Part-1 work must start here. |
| Breakout on heavy volume | Candidate generation only; the band (±7% HOSE / ±10% HNX) means a strong breakout can lock at trần with no fill | Affects §7's forward evaluation, which must not assume a fill at the pivot. |
| 10–20 names on the watchlist | `SCAN_MAX_CANDIDATES` default 20, but see §2.3 | At n = 32 this cut is not selective. The number is meaningful only once D1 is resolved. |

---

## 6. Non-functional requirements

- **NFR-S1 — Runtime.** A full nightly scan over the universe completes within 5 minutes
  at n ≤ 200 and within 30 minutes at n ≤ 1,800, reading only the database.
- **NFR-S2 — Determinism.** The same scan date and parameters over unchanged data produce
  an identical candidate list, byte for byte. Required for §7 to mean anything.
- **NFR-S3 — Explainability.** Every rejection is attributable to a named clause
  (FR-SCAN-API third endpoint).
- **NFR-S4 — Parameter surface.** Every threshold in §3 is configuration, not a literal,
  and every default is recorded in one place with its provenance.

---

## 7. Validation — how we find out whether this works here

Per EC-S5 and the project's standing C4, a scanner that only produces a list proves
nothing. The module ships with:

- **VT-1 — Causality (mandatory).** The no-leakage harness used elsewhere in this repo:
  perturb bars after *T*, assert the scan output for *T* is unchanged. Any failure here
  invalidates every other result.
- **VT-2 — Determinism.** Two runs, same date, identical output (NFR-S2).
- **VT-3 — Planted setup.** A synthetic series built to contain an advance, a contracting
  base and a pivot is detected, with base boundaries within tolerance.
- **VT-4 — Null false-positive rate.** Run the full funnel over random-walk series
  calibrated to VN daily volatility. Report the rate at which the funnel emits candidates
  from pure noise. A funnel that fires as often on noise as on real data has no content,
  and this number is reported *every time the candidate list is reported*.
- **VT-5 — Forward evaluation against a benchmark.** Over persisted nightly runs
  (FR-SCAN-SCHED), measure forward returns at +5/+10/+20 bars for candidates against two
  benchmarks: (a) all symbols passing liquidity only — isolating what momentum+base add
  over "any liquid stock"; (b) a same-size random draw from the liquid set. Report with
  significance, and report the band/T+ caveat from §5 explicitly — a backtest that fills
  at the pivot on a trần day is reporting fiction.

**VT-5 cannot run at module completion.** It needs months of persisted nightly scans. The
module is therefore *deliverable* at VT-1..VT-4 and *validated* only later; the SRS says
so here so that nobody later reads "shipped" as "proven". Until VT-5 reports, the honest
description of this feature to a user is *"a disciplined way to shortlist candidates"*,
never *"stocks likely to go up"*.

---

## 8. Open decisions (owner input required)

**D1 — Universe breadth. ✅ RESOLVED 2026-11-09 — option 2 chosen and executed; see §2.3.**
Original framing, kept because it is why the other options still exist: §2.3, today the funnel would run over ~32
symbols with history, out of a 92-symbol hardcoded list. Options:

1. **Scan what we have** (~32). Delivers the machinery now; the selectivity that makes
   the method work is absent. Useful as a working skeleton, not as a trading tool.
2. **Backfill VN100** (92 symbols × ~1,400 bars). Bounded, and the hardcoded list already
   exists. At a 20 req/min cap this is roughly an hour of ingestion. Makes a top-20 cut
   meaningfully selective (top 22%).
3. **Backfill the full HOSE+HNX listing** (~700 symbols). `stock.listing.all_symbols`
   exists in the codebase (`stock_service.py:646`). This is the configuration Qulla's
   method assumes, and a separate ingestion project with real quota cost — likely
   requiring `VNSTOCK_API_KEY` (Backlog #49) to be resolved first.

Chosen: **option 2**, executed in S-0 — 93 symbols, 122,914 bars, seam-swept. Option 3
(~707 HOSE+HNX names, the live listing confirmed reachable in S-0) remains the follow-on
and still wants Backlog #49 settled first.

**D2 — Exchange scope.** Include UPCOM? It roughly doubles the name count and contains
most of VN's genuine momentum outliers, but with a ±15% band and thinner disclosure.
Default in this draft: **excluded**.

**D3 — Auto-add to watchlist.** Should a top-ranked candidate be added to
`HelperWatchlist` automatically, or only on user confirmation? Default in this draft:
**confirmation only** (EC-S6).

**D4 — Service home. ✅ RESOLVED 2026-11-09 — `decision-helper-service`; S-1 built there.**
Original framing: Three defensible placements: `analysis-service` (owns the existing
screener and S/R), `decision-helper-service` (owns the watchlist, liquidity filter and
scheduler), or a new `scanner-service`. Recommendation: **`decision-helper-service`** — it
already owns `universe/`, the scheduler, and the destination table, and a new service
costs a compose entry, Traefik labels and a health contract for one nightly job.

**D6 — Where the scanner appears in the UI. ✅ RESOLVED 2026-11-09 — inside the existing
AI Insights menu, as a tab. No new nav entry, no new page.** Owner's call, and it is the
right one: `sidebar.ai_insights` already exists (`Sidebar.js:122`) and the page already
carries a tab control (`AIInsights.js:51`, parameters / charts), so the scanner becomes a
third tab rather than another top-level item.

One structural wrinkle to handle, not a reason to reopen the decision: `AIInsights.js` is
built around a **selected symbol** — the header and the six-column summary above the tabs
all describe it. The scanner is **market-wide** and has no symbol. The tab must therefore
suppress that header rather than show a stale one, and the natural flow is the reverse of
the page's current direction: pick a candidate from the scanner, which *sets* the symbol
and moves to Charts. Discovery feeding inspection, in one screen.

**D5 — MA10/MA20 home.** They do not exist (§2.2). Add to `analysis-service`'s indicator
set (visible everywhere, including the narrator) or compute locally in the scanner?
Recommendation: **`analysis-service`**, since Part-1 trailing-stop work will need MA10
too.

---

## 9. Phasing

| Phase | Content | Exit criterion |
|---|---|---|
| **S-0** ✅ | Resolve **D1**; backfill the chosen universe; verify seam-free via FR-SCAN-SEAM over the whole set | **DONE 2026-11-09** — 93 symbols, 122,914 bars, 1 seam (VTP, classified not excluded; §2.4) |
| **S-1** ✅ | Momentum ranking + liquidity + trend template (FR-SCAN-UNIV/LIQ/MOM/TREND) | **DONE 2026-11-09** — `app/services/scanner/` in decision-helper-service (D4), 42 tests incl. VT-1 and VT-2, CLI `tests/s1_momentum_scan.py`. See §11 |
| **S-2** ✅ | Base, squeeze, MA proximity, pivot (FR-SCAN-BASE/SQUEEZE/MA/LEVEL) | **DONE 2026-11-09** — 27 further tests; VT-3 recovers the planted boundary, VT-4 reported. See §12 |
| **S-3** ✅ | Persistence, scheduler, endpoints, watchlist hand-off (FR-SCAN-SCHED/API/OUT) | **DONE 2026-11-09** — two tables, three endpoints, nightly job at 09:15 UTC, verified live. See §13 |
| **S-4** ✅ | Frontend surface | **DONE 2026-11-09** — AI Insights third tab (D6), 17 tests, bilingual, built and deployed. See §14 |
| **S-5** | **Later, once data accumulates:** VT-5 forward evaluation | Benchmark comparison reported with significance |

---

## 10. Traceability to the source method

| Qulla Part 2 step | Requirement |
|---|---|
| Bước 1 — giá trên 1–2 USD | FR-SCAN-UNIV + §5 price floor |
| Bước 1 — KLGD TB 50 phiên ≥ 300–500k | FR-SCAN-LIQ (EC-S4) |
| Bước 1 — tăng trưởng % lớn nhất 1T/3T/6T | FR-SCAN-MOM |
| Bối cảnh — trên MA50/MA200, đã tăng 30–100% | FR-SCAN-TREND |
| Bước 2 — loại cổ phiếu tăng dốc đứng, giữ nền phẳng / lá cờ | FR-SCAN-BASE |
| Bước 2 — nến nhỏ, khối lượng kiệt quệ | FR-SCAN-SQUEEZE |
| Bước 2 — MA10/MA20 sát ngay dưới giá | FR-SCAN-MA |
| Kết quả — vẽ sẵn kháng cự ngang | FR-SCAN-LEVEL |
| Kết quả — watchlist 10–20 mã | FR-SCAN-OUT, `SCAN_MAX_CANDIDATES` |
| (implicit) chạy mỗi ngày sau khi đóng cửa | FR-SCAN-SCHED |

---

## 11. S-1 results (2026-11-09)

### 11.1 What was built

`decision-helper-service/app/services/scanner/` — `momentum.py` (FR-SCAN-MOM),
`trend.py` (FR-SCAN-TREND), `screen.py` (the funnel: FR-SCAN-UNIV, FR-SCAN-LIQ,
FR-SCAN-SEAM). 42 tests across three files; the whole service suite is 1,044 passed,
12 skipped. No HTTP endpoint and no UI, by design — `tests/s1_momentum_scan.py` is the
CLI, because the ranking has to be judged against real charts before FR-SCAN-API and a
nightly job get built on top of it.

### 11.2 Two corrections the tests forced

**The liquidity floor was wrong by a factor of 1,000, and it would have passed
everything silently.** vnstock/VCI quotes VN equities in **thousands of VND** and we
store that verbatim — VIC's close reads 233.69 for a 233,690 VND share. `assess_liquidity`
multiplies close by volume, so its `avg_daily_value` is in thousands too: VIC measures
875,755,182 over 50 sessions, which is 875 tỷ/day, not 876 triệu. Comparing that straight
against a VND threshold is off by three orders of magnitude *in the direction that admits
every symbol*, so nothing would have looked broken. `ScanConfig.price_unit_vnd` now makes
the conversion explicit and testable, and a source that one day stores real VND is a
one-line change rather than a silent re-calibration.

**`MIN_BARS = 150` (§3, FR-SCAN-UNIV) is below what the trend template needs.** SMA200
requires 200 bars, so a universe admitted at 150 would fail `close_above_sma200` for want
of *history* rather than want of *trend*, and the exclusion would be invisible in the
counts. `ScanConfig.effective_min_bars()` raises the configured floor to whatever the
stages actually need. The 150 default stays as documentation of intent; it is no longer
load-bearing.

### 11.3 The first real run — and it returns nothing

Over the 93-symbol universe at 2026-11-06, with a 5 tỷ/phiên floor:

```
universe 93 | required bars 200 | ranked 81
  illiquid                   12
  failed trend template      81
  QUALIFIED                   0
  seam flagged (VTP)          1   not excluded, per 2.4

why the rest failed (a name can fail several):
  prior_advance              79
  close_above_sma200         69
  sma50_above_sma200         64
  close_above_sma50          46
```

**This is a market reading, not a defect**, and it was checked as such before being
reported. Run at ten historical dates the same funnel tracks regime exactly as it should:

| as of | ranked | qualified | top names |
|---|---|---|---|
| 2022-03-31 | 25 | 1 | VIB |
| 2022-09-30 | 84 | 3 | BCM, HAG, NT2 |
| 2023-03-31 | 79 | 19 | VCI, VPB, SSI, LPB, VRE |
| 2023-09-30 | 85 | 17 | DGC, VTP, EVF, FRT, DGW |
| 2024-03-31 | 88 | 50 | VTP, GVR, TCB, SIP, PHR |
| 2024-09-30 | 89 | 7 | HDB, HCM, LPB, DPG, DCM |
| 2025-03-31 | 91 | 6 | VIC, SHB, SBT, VHM, GEX |
| 2025-09-30 | 93 | 31 | VIC, CII, LPB, GEX, VRE |
| 2026-03-31 | 90 | 9 | DCM, BVH, MIG, IDC, DPM |
| 2026-09-30 | 80 | 3 | PVT, SSB, VIC |
| **2026-11-06** | **81** | **0** | — |

A momentum funnel that returns nothing when 69 of 81 names are under their 200-day
average is behaving correctly. **An empty list is a valid and informative output of this
method and must stay one** — the temptation at S-2 will be to loosen `prior_advance` or
the liquidity floor until the screen has rows on it, and that would convert a working
regime filter into a decorative one. Any change to these defaults belongs to VT-5's
evidence, not to the wish for a populated list.

### 11.4 What S-1 deliberately does not do

A survivor here is *in a liquid uptrend with strong relative strength* — Qullamaggie's
**bối cảnh**, not his **setup**. There is no base, no squeeze, no MA10/20 proximity and no
pivot (all S-2). The list will contain extended names the full funnel would reject. It is
a shortlist to look at, never a buy list, and the CLI says so in its own header.

---

## 12. S-2 results (2026-11-09)

### 12.1 What was built

`app/services/scanner/base.py` — `detect_base` (FR-SCAN-BASE), `measure_squeeze`
(FR-SCAN-SQUEEZE), `measure_ma_proximity` (FR-SCAN-MA), `find_pivot` (FR-SCAN-LEVEL),
combined by `assess_base` into a four-clause verdict in the same reported-per-clause shape
as the trend template. `app/services/scanner/null_model.py` carries the VT-4 random-walk
null. 27 further tests; the service suite is 1,071 passed, 12 skipped.
`ScanConfig.require_base=False` reproduces the S-1 funnel exactly, which is what makes the
two phases comparable on the same data — §12.4 depends on it.

### 12.2 EC-S3 and the flag detectors — a sequencing choice, stated

§3 (FR-SCAN-BASE) says to reuse ai-insights' `FlagDetector`/`PennantDetector` and write
only the flat base. That reuse is **not** done in S-2, deliberately. This service does not
import ai-insights code — it consumes that service's pattern payload over HTTP and adapts
it (`signal/failed_signal.py::adapt_ai_insights_patterns`), and `tests/test_phase_k.py`
skips wholesale when the package is not importable. A nightly scan making one HTTP call
per symbol would also break the offline CLI and the determinism harness. So the
flat/consolidation base is local pure code and the flag-shaped case is left as an
injection seam for S-3, where the service surface exists. Forking `FlagDetector` into this
package would have been the real EC-S3 violation; not calling it yet is sequencing.

### 12.3 The detector was wrong twice, and tests found both

**A fixed drift limit cannot distinguish a base from a trend.** Drift shrinks with window
length, so *any* persistent trend has some window short enough to clear a fixed
percentage. A stock rising 0.5/bar for 300 bars produced a "45-bar base" at 14.9% drift —
under the 15% limit and not a base by any reading. The fix is depth-relative and
length-invariant: inside a consolidation price oscillates and finishes near where it
began, so net move is a small fraction of the range travelled; inside a trend the two are
nearly equal. `DEFAULT_BASE_MAX_DRIFT_OVER_DEPTH = 0.5`; that 45-bar window scored 0.96.

**"The longest admissible window" lets the threshold choose the answer.** Greedy
backward extension stops exactly when a cap trips, so on a planted 30-bar base it returned
43 bars at drift/depth 0.49 — it had swallowed 13 bars of the preceding advance and halted
on the 0.50 cap. Three unrelated fixture shapes all returned length 43 and a ratio of
0.49–0.50, which is the signature of a cap being measured rather than a pattern. Worse,
the contamination propagates: those run bars land in the squeeze's **first** third and
inflate it, so `range_ratio` reports a contraction the base never had. `detect_base` now
minimises drift/depth and breaks ties on length. The planted 30-bar base is recovered at
length 31, start index 259 against a true 260.

Measured base lengths on live candidates: 10 to 58 bars, median 14, with 17% at the 10-bar
floor. Mild short bias, not a systematic one — the 58-bar base was found where it existed.

### 12.4 VT-4, and what it says about S-1

30 random-walk universes of 93 symbols × 400 bars, VN-calibrated (2.405% daily log SD,
+0.0079%/day drift, measured over 122,820 returns), against live pooled pass rates at ten
half-year dates:

| funnel | live qualified / ranked | null (random walks) | enrichment |
|---|---|---|---|
| S-1 only (momentum + trend template) | 146 / 804 = **18.2%** | **22.69%** | **0.8×** |
| S-2 full funnel | 25 / 804 = **3.1%** | **0.50%** | **6.2×** |

**S-1's pass rate carries essentially no information.** It admits real VN symbols at the
rate it admits random walks — which is not a claim that it is *worse* than chance (the
comparison is not that clean: the null is always a fresh walk, while the live window spans
long bear stretches), but it does mean the momentum ranking plus trend template is a
**precondition, not a filter**. A random walk at 2.4% daily volatility reaches a 30%
126-bar advance and sits above its averages often enough that passing those clauses is
unremarkable. **This retrospectively qualifies §11.3**: S-1's shortlists were a reasonable
*starting* population and should never have been read as a selected one.

Selectivity lives entirely in the base stage. At the same thresholds, S-2 cuts noise 45×
(22.69% → 0.50%) and live names 6× (18.2% → 3.1%), leaving a 6.2× enrichment over noise.
On 2024-03-31 it cut 50 S-1 names to 16, rejecting 34 for `volume_dryup` (23),
`range_contraction` (20), `ma_hugging` (10) and `base_found` (3).

**What 6.2× does and does not establish.** It establishes that the full funnel is
selective against noise — necessary, and not sufficient. It says nothing about whether the
names it emits go up; that is VT-5, and it needs months of persisted live runs. One
further caution from the same table: a third of pure-noise universes still emitted at
least one candidate, so *seeing a name on the screen* is not evidence of anything. The
rate is the evidence, and it must be reported beside the list (C4 / EC-S5) — the CLI's
`--null` flag does this.

### 12.5 Today, still nothing

At 2026-11-06 the base stage receives zero inputs: all 81 ranked names fail the trend
template first. S-2 does not change today's answer and was never going to. Its value is at
the other end of the cycle — in March 2024 it was the difference between a 50-name list
and a 16-name one.

---

## 13. S-3 results (2026-11-09)

### 13.1 What was built

| Piece | Where |
|---|---|
| `scanner_runs`, `scanner_results` | `app/models/domain.py` |
| Fetch → scan → persist | `app/services/scanner/runner.py` |
| `POST /helper/scan/momentum` | run and persist |
| `GET /helper/scan/momentum?scan_date=` | read a stored run back |
| `GET /helper/scan/momentum/{symbol}` | the per-symbol diagnostic |
| Nightly job, 09:15 UTC | `scheduler.run_momentum_scan_job` + `main.py` |
| `MarketClient.fetch_universe()` | DB-backed `GET /companies`, **no vnstock quota** |

16 further tests; suite 1,090 passed, 12 skipped.

Two design points worth stating. **Rejections are persisted, not only winners** — the
per-symbol diagnostic exists so a user who expected a name can learn which clause rejected
it, and storing passes alone would make that endpoint a 404 for every question anyone
actually asks. **The scan is not per-user**: it is a property of the market, so one run
per `scan_date` serves everybody, and a re-run replaces rather than appends — "what did
the scanner say on the 6th" must have exactly one answer, or VT-5 gets to pick the variant
that supports it.

`fetch_universe` deliberately reads `GET /companies` (database) rather than
`/companies/all` or `/companies/group/{g}`, both of which call vnstock live. With Backlog
#134 open, a nightly 93-symbol scan on the live path would be unreliable *and* would spend
quota the price refresh needs.

### 13.2 Verified against the live stack

Rebuilt and redeployed, then driven through Traefik on :18004.

- **2026-11-06** — universe 93, ranked 81, 12 illiquid, **0 candidates**, 558 ms. The
  response carries `empty_reason`: *"81 of 81 ranked names failed the trend template, so
  none reached the base stage — the market is not offering this setup today."* That field
  exists because of #135: a blank screen that looks identical to a broken one is how a
  working filter gets loosened until it stops filtering.
- **2024-03-31** — 16 candidates with the null rate attached (10/30 universes, 0.50% of
  synthetic symbols), 3.2 s including the whole VT-4 computation.
- **`GET /scan/momentum/VIC`** returns `FAILED_TREND`, `failed_clauses: ["prior_advance"]`,
  and all four clauses with their numbers — VIC passed three (close 234.50 over SMA50
  233.69 and SMA200 198.85) and failed one: *"22.1% off the 126-bar low 192.00, need 30%"*.
  That is the endpoint doing the job it was specified for.
- An unknown symbol returns 404 with the reason, not an empty payload.

### 13.3 A reproducibility defect the live comparison caught

The API and the CLI returned the **same 16 candidates** at 2024-03-31 but swapped ranks 8
and 9. Cause: DPG and VHC both scored 0.74329501915708…, differing only in the last place
— 0.7432950191570881 against 0.7432950191570882. One ULP, arriving because the TSV path
and the JSON-over-HTTP path round-trip a float differently, jumped the sort past the
symbol tie-break that was supposed to settle exactly this.

The set never changed, so no candidate was gained or lost; but a stored *rank* that
depends on how the bars were transported is not a record VT-5 can rely on. `order_key` now
rounds the composite to 9 decimals before comparing. Nothing meaningful is merged: at
n = 88 the finest distinction a percentile can draw is 1/87 ≈ 0.0115, seven orders of
magnitude coarser. The persisted column is `DECIMAL(6,4)`, so ordering on more precision
than is stored would have meant the saved rank could not be re-derived from the saved
score.

**Two process failures are recorded with it, because both nearly let it through.** The
first fix was reported as applied when the edit had silently not landed — the host file
still held the old sort, and the container was never recreated. The second was a test that
passed for the wrong reason: it nudged a composite by `1e-16`, which is exactly `0.0` in
float64, so it asserted the tie-break while never exercising the rounding. The test now
uses the two real measured floats and asserts up front that they differ.

### 13.4 The watchlist hand-off (FR-SCAN-OUT, EC-S6)

No new endpoint. A candidate is pushed to `HelperWatchlist` through the existing
`POST /helper/watchlist`, and the scanner never writes that table. The separation is the
requirement, not an implementation detail: the scanner's job ends at *"this name is worth
looking at"*, and what a user does next is theirs.

### 13.5 Still open

The ai-insights `FlagDetector` injection seam (§12.2) is **not** wired. S-3 gave the
scanner a service surface but the flag-shaped base still has no detector behind it — the
flat/consolidation case carries the whole base stage today. That is the first thing S-4
should close, before any UI depends on the shape of the payload.

---

## 14. S-4 results (2026-11-09)

### 14.1 What was built

A third tab in the existing **AI Insights** page (D6) — no new route, no new nav entry.

| Piece | Where |
|---|---|
| `MomentumScannerPanel` | `src/components/common/MomentumScannerPanel.js` |
| Tab button + wiring | `src/components/Pages/AIInsights.js` (`activeTab === 'scanner'`) |
| 3 service methods | `src/services/helperService.js` |
| 2 endpoint constants | `src/constants/api.js` |
| 45 keys × 2 languages | `src/i18n/locales/{en,vi}.json` |

17 component tests; the whole frontend suite is 297 passed. Production build clean,
Docker image rebuilt, container recreated, both locales verified inside the deployed
bundle.

The symbol header and the Analyze button are hidden on this tab: every cell in that
summary describes the **selected symbol**, and the scanner is market-wide. Choosing a
candidate **sets** the symbol and jumps to Charts — discovery feeding inspection, which
reverses the page's usual direction.

### 14.2 The empty state is the primary state

`empty_reason` renders as a finding with the funnel counts beside it, plus a standing note
that an empty list is the honest output of a method that waits for stocks which have
already advanced. This is Backlog #135 made visible: a blank screen indistinguishable from
a broken one is how a working filter gets loosened until it stops filtering. Five of the
17 tests cover this state, including that a **404 reads as "nothing ran", never as
"nothing qualified"** — the two are different claims and the UI must not conflate them.

The VT-4 null rate renders beside the list whenever the stored run carries one (C4/EC-S5),
always with its caveat that it measures selectivity against noise and not edge. A test
asserts the caveat is present, and another asserts the figure is **omitted rather than
faked** when a run did not measure it.

### 14.3 One real defect, found by a test

`load` was wrapped in `useCallback(..., [t])`. `t` from `useTranslation` is a new function
on every render, so the callback changed identity every render, so the mount effect
re-fired — the test saw **8 calls** to `getMomentumScan` where it expected one. Against the
real i18n provider this may or may not have spun; in the test it plainly did.

The fix is not a narrower dependency array but a better pattern: the component now holds
message **codes** (`notice = 'no_run_yet'`, `serverError = {code} | {text}`) and translates
at render. That removes `t` from the fetch path entirely *and* fixes a second latent bug —
an already-translated string stored in state does not follow a language switch.

Two of the three remaining failures were the tests' fault, not the component's, and are
worth noting because both are easy to repeat: the Run button is relabelled while a fetch is
in flight, so it must be waited for rather than grabbed; and a `t` mock that echoes its key
has no `{{symbol}}` placeholder to interpolate into, so the interpolation assertion passed
over nothing. The mock now returns a real placeholder for that one key.

### 14.4 What a user sees today

Opening the tab on 2026-11-06 shows: scan date, 81/93 ranked, 0 candidates, the sentence
*"81 of 81 ranked names failed the trend template, so none reached the base stage — the
market is not offering this setup today"*, the funnel (12 illiquid, 81 failed trend,
93/93 accounted), and the symbol lookup. Typing `VIC` returns `FAILED_TREND` with all four
clauses and their arithmetic, the failing one reading *"22.1% off the 126-bar low 192.00,
need 30%"*. Setting the date to 2024-03-31 and pressing Run returns the 16-name list with
base length, depth, squeeze ratios, MA distances, pivot and turnover in tỷ.

---

## 15. The flag shape (2026-11-09)

### 15.1 Why a second shape was needed at all

`detect_base` requires `drift/depth ≤ 0.5` — price must finish near where it
began. **A flag finishes *down*, counter to its pole, by design.** So the very
test that separates a base from a trend is the test that hides a flag, and no
threshold adjustment fixes that: the two shapes are different objects.
`detect_flag_base` therefore runs as a **fallback**, only where no flat base
exists, so flags can only *add* names and never reclassify or remove one — a
property `test_scanner_base.py` asserts rather than assumes.

### 15.2 Relationship to ai-insights' `FlagDetector` (EC-S3)

The geometry mirrors it: a pole of ≥ 2×ATR that is mostly linear, then a channel
ending at the last bar whose highs **and** lows both slope down, retracing ≤ 50%
of the pole. It is not called directly because this service consumes ai-insights
over HTTP and never imports it, and a per-symbol HTTP call would break the
offline CLI and the VT-2 determinism harness. A skip-guarded cross-check test
asserts the two agree on a planted flag, so divergence is caught rather than
discovered. **If they ever disagree, lift the geometry into `stock-common`** the
way `find_price_seams` was lifted — do not patch one side.

Three deliberate divergences, each forced by a failing test:

1. **Retrace is measured from the peak of the move**, not across the flag window.
   `FlagDetector` uses `abs(fg_close[-1] - fg_close[0])`; because the flag must
   end at the last bar, that lets a 53%-retrace pullback read as 47% once the
   first bar's drop off the pole is excluded.
2. **Longest flag first, not shortest.** Shortest-first returned a 3-bar flag for
   every planted pullback from 6 to 10 bars. The flag *is* the whole pullback,
   and its length feeds the squeeze thirds and the pivot.
3. **The pole must end at its own top, and the flag's high must sit in its first
   third.** Without the first, the retrace cap is evadable by *shortening* the
   flag — `pole_end` is pinned to `flag_start − 1`, so a shorter flag pushes the
   pole window over the pullback's first bars, inflating `pole_move` and lowering
   the measured peak. Without the second, longest-first lets the flag swallow the
   pole: a planted 8-bar pole and 4-bar pullback came back as a 9-bar "flag"
   containing 5 pole bars, with the quiet pre-pole drift reinterpreted as the
   pole. Both are the same error in mirror image — a search order picking the
   answer — and the same error `detect_base` made before flattest-wins.

### 15.3 It works, it fires, and it changes almost nothing

> **SUPERSEDED 2026-11-10 by §16.** The counts below are correct as measured and
> are left as recorded, but the conclusion drawn from them — that the flag shape
> contributes ~0 candidates — no longer describes the scanner. Backlog #141 ran
> the pre-registered calibration this section called for, and the shape now
> admits 71 of 481 flag windows rather than 20. Read §15.3 and §15.4 as the
> statement of the problem; §16 is the resolution.

Measured over 242 sampled dates, on names that reached the base stage with **no
flat base**:

```
names with no flat base                     572
  of those, a bull FLAG is found             87   (15%)
  of those 87, what they then fail on:
     range_contraction + volume_dryup + ma_hugging   30
     range_contraction + volume_dryup                19
     ma_hugging                                      13
     range_contraction + ma_hugging                   9
     range_contraction                                6
     volume_dryup + ma_hugging                        4
     volume_dryup                                     4
     PASSES                                           2
```

**Two of 572.** Across the ten half-year dates used elsewhere in this document,
the flag shape added **zero** candidates — the two survivors fall on other dates.

### 15.4 The finding, which is not "flags are useless"

**The squeeze and MA-proximity thresholds were calibrated for flat bases and are
wrong for flags.** They reject 98% of the flags the detector finds, and the
reasons are structural rather than marginal:

- *Volume dry-up.* "Khối lượng giao dịch kiệt quệ" describes a base lasting weeks
  absorbing supply. A four-day pause after a sharp run does not dry up that way,
  and `dryup_max_ratio = 0.80` encodes the multi-week expectation.
- *MA proximity.* A flag sits immediately after a sharp pole, which is exactly
  when price is **furthest** from its MA20. `ma_proximity_pct = 8.0` was set for
  a base whose averages have had weeks to catch up.
- *Range contraction.* Measured over thirds of a 5-bar window, where a "third" is
  one or two bars.

**The thresholds are deliberately left alone.** Loosening them until flags
survive is precisely Backlog #135's trap — it would convert a working filter into
a decorative one and guarantee the screen always has rows. Shape-specific
thresholds are a *calibration* question requiring its own pre-registered
measurement, filed as Backlog #141, not a number picked today to make a feature
look productive.

So the honest status: the flag shape is implemented, tested from both sides of
every threshold, cross-checked against the existing detector, and **currently
contributes ~0 candidates** because the stages after it were not built for it.
That is a real result, and recording it is worth more than the feature.

**That status held for one day.** The calibration this section demanded was
pre-registered, run and adopted on 2026-11-10 — §16. The paragraph above is kept
because it is what the evidence supported at the time, and because the sequence
matters: the feature was recorded as unproductive *before* anyone was allowed to
tune it, which is the only reason the tuning that followed can be believed.

---

## 16. The #141 calibration (2026-11-10)

Resolves what §15.4 filed. Pre-registered in
`docs/backlog141_flag_calibration_preregistration.md` (commit `f3cecc5f`, written
before the study script existed), measured in `docs/backlog141_flag_calibration.md`
(`f2d003db`), adopted in `b617afe1`.

### 16.1 Why this is not §135's trap

The temptation §15.4 named was real: loosen three numbers until flags survive, and
a filter becomes decoration. What was done instead is a different act. **Two of the
three clauses kept their production cut-offs exactly — 0.75 and 0.80 — and changed
only their denominator.** "Quieter than the thrust it is pausing after" is what
range contraction and volume dry-up always meant; measuring a 4-bar pause against
its own 4-bar mean cannot express that, and produces a ratio near 1 whatever the
stock did. Re-specifying a measure that cannot work on a short window is not the
same act as relaxing a threshold that can.

Only `ma_hugging` had a bound genuinely replaced, and only after the measurement
identified it as the binding one.

### 16.2 What the measurement found

1,186 scan dates, 2021-03-15 → 2026-11-09, 93 symbols, **481 flag windows**. This
cross-checks §15.3: 87 over 242 sampled dates scales to ≈426, against 481 on the
full calendar.

```
production (PPP)                      20 of 481 admitted   (4%)
arms carrying shape-specific ma_hugging    48-74 admitted
arms without it                            18-28 admitted
```

**The fixed 8% MA bound was the binding clause, not the squeeze ratios.** That was
argued from mechanism in the pre-registration before any number was seen, which is
precisely what the eight diagnostic arms were run to test — and why only one of
them (`SSS`) was ever adoptable.

### 16.3 The held-out result, and which part of it is real

TEST period 2024-07-01 → 2026-11-09, n = 35 flag episodes. All four pre-committed
conditions passed, so the rule said adopt and was honoured as written.

| condition | result | verdict |
|---|---|---|
| n ≥ 20 flag episodes | 35 | pass |
| pivot clearance ≥ ARM-FLAT | **57.1% vs 40.9%** | pass |
| mean excess 20-bar ≥ 0 | +0.46% (median **−2.37%**) | pass |
| mean excess 20-bar ≥ ARM-RANDOM | +0.46% vs +0.29% | pass |

**Only the second line is evidence.** Pivot clearance is the mechanism test — a
flag admitted by these clauses clears its own pivot more often than the flat bases
the screen already produces, out-of-sample. The fourth passes by 0.17pp at n=35
against n=35, which is noise. The third passes on a mean whose median is negative:
the central episode *lost*, and the mean is carried by a tail. Had the rule
pre-registered the median, the study would have said KEEP.

This is **not an edge claim.** S-5a's limits apply unchanged.

### 16.4 What was adopted, and the proof flat verdicts did not move

Flag-only, switched on `window.shape` in `assess_base`. FR-SCAN-SQUEEZE and
FR-SCAN-MA above carry the normative statements.

Verified empirically rather than asserted: production over all 1,186 scan dates
gives **FLAT = 861 rows, sha256 `c580bca5`, identical before and after**, while
FLAG goes **20 → 71**, matching the adopted arm's measured count exactly. Nine unit
tests assert the two shapes are judged by disjoint rule sets — the risk was never
"flags pass more often", it was a loosened flag clause leaking onto the flat path.

### 16.5 What #141 does not resolve

- The flag shape is still a **small** contributor: 71 symbol-days. It adds names;
  it does not change the screen's character.
- **§11.3 and Backlog #135 still stand.** A funnel returning nothing on today's
  market is still returning the correct answer, and this is not licence to
  revisit the liquidity or advance floors.
- **S-5a's primary finding is unchanged.** Buying the base still does not pay.
- The successor is **VT-5 on accumulating live runs**, not another sweep of the
  same 5.5 years.

---

## 17. The decision-engine handshake (Backlog #140, 2026-11-10)

FR-SCAN-LEVEL emits a pivot. Until 2026-11-10 **nothing read it.** Every `pivot`
reference in the risk modules is a *swing* pivot, and nothing in `confirmation/`,
`risk/`, `signal/` or `decision/` touched `ScanCandidate.base.pivot`. The
user-visible consequence: the Scanner tab said "GVR, pivot 35.0", the user added
GVR to the watchlist, and `/helper` then judged a breakout against its own 20-day
high. Two surfaces, two levels, no stated relationship — a missing handshake, not
a missing feature.

S-5a made it load-bearing: selection has content but buying the base does not pay,
so whatever edge exists has to come from the breakout trigger, and the trigger was
not connected to the level the screen advertised.

### 17.1 The coupling is one-directional, and that is EC-S6

`scanner/runner.py::load_scanner_pivot` returns the most recent CANDIDATE pivot at
or before `bar_date`; `detect_n_day_breakout` takes it as `reference_level` and
**adopts it only when it is at or above the N-bar high.** A lower pivot is ignored.

Honouring a lower pivot would fire a breakout the engine's own rule would refuse —
the scanner *loosening* the engine's standard, which EC-S6 forbids it from doing.
The scanner proposes: it may make the trigger stricter, never easier. The emitted
evidence carries `level_source`, `n_day_level` and `reference_level` so a reader
comparing the two surfaces sees why they agree or differ, rather than discovering
a silent substitution.

`confirmation/layer.py` needed no change: `_extract_trigger_level` reads
`evidence["breakout_level"]`, so penetration and the K-bar delay inherit the
handshake.

### 17.2 `PIVOT_LOOKBACK_DAYS = 30` is measured, not chosen

Recorded here because it was previously justified only in a docstring.

**A pivot is not a same-day fact.** Measured over 40 scan dates: on the day a
candidate first closes *above* its pivot it is never still a candidate — **0 of
8** — because the breakout lifts the window's drift and the base stops qualifying.
Matching `scan_date == bar_date` therefore guarantees the pivot is gone exactly
when the engine needs it, which is what made the first cut of this handshake
decorative.

A trader draws the line when the base forms and leaves it drawn until the breakout
resolves. Thirty calendar days is that, bounded: a pivot older than this describes
a base the market has moved on from.

### 17.3 What is verified, and what is not

Verified live after deployment: `reference_level` comes back as the stored pivot
(VGC 52.99, KBC 36.3, PAN 18.45), so the lookup works end-to-end through the
deployed endpoint. **Not yet observed in the wild:** a LONG adoption in which the
pivot actually *replaces* the N-bar high. All three live cases were short
breakdowns, where the pivot is correctly ignored. The branch is unit-tested and the
lookup is proven; the two have not been exercised together on live data, because
the latest persisted candidates are 2024-03-31 and today's market yields none
(§11.3). Stated rather than rounded up.
