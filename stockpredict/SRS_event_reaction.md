# Software Requirements Specification

## Event-Reaction Measurement System

**Document version:** 1.1
**Date:** 2026-06-30
**Status:** Draft (Phase 1 — Design)
**Change note (1.1):** Reconciled with the module standing-rules doc
(`event-reaction-lib/CLAUDE.md`, provided after Phase 0). Surprise is now **observed/
external** (consensus default; futures/Kuttner and odds alternates; LLM deferred), data
contracts are **pandas**, and the package layout is **flat stage packages**. See §6 for the
full reconciliation list.

---

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements for an **event-reaction measurement system**: a
backend subsystem that quantifies how asset prices react to discrete, timestamped events
(central-bank rate decisions, tariff announcements, geopolitical shocks). Its founding
principle is that **markets price the surprise, not the event** — every reaction measured by
this system is built on a *surprise* (the deviation of the realised event outcome from what
the market expected just before the event), never on the raw occurrence of the event.

The system is intended for quantitative researchers and analysts who need to (a) attach a
defensible *surprise* magnitude to each event from a pre-event expectation, (b) measure the
asset's *abnormal* (market-adjusted) return reaction around the event, (c) test whether the
reaction is a statistically significant *jump* rather than ordinary volatility, and (d)
estimate the *cross-sectional exposure* of many assets to a common event — all under strict
anti-leakage discipline.

This SRS is written against `docs/event_reaction_gap_map.md` (Phase 0) and the module
standing-rules doc. It reuses, rather than re-implements, the price-loading and returns/
volatility machinery already in the repo, and mirrors the proven library + thin-service split
of the chart-decomposition subsystem.

> **Note on the reference skeleton.** A sketch `event_reaction_pipeline.py` (six stages:
> ingest → timestamp/align → featurize-to-surprise → market-model abnormal returns →
> Lee–Mykland jump test → cross-sectional exposure regression) will be supplied separately.
> It is a sketch of the **math**, not the target structure; when it arrives, its formulas are
> reconciled against §3 of this document, which takes precedence on organisation.

### 1.2 Scope

The system **shall**:

- Maintain an **event store** of discrete, timestamped events (FR-EVT), each carrying a kind,
  a tz-aware UTC timestamp (to the minute), an affected-asset scope, a realised outcome
  (`actual`), and a pre-event **consensus**; with optional auxiliary inputs (futures-implied
  expectation, market-implied odds).
- Construct, for each event, a **surprise from a pre-event expectation only** (FR-SURP):
  default `actual − consensus`, standardised; with **futures/Kuttner** and **odds**
  constructors as alternates.
- Compute **abnormal returns** (log returns) around each event via a market model whose
  parameters are estimated on an estimation window that strictly precedes the event window
  (FR-AR).
- Run a **Lee–Mykland jump test** (daily variant) deciding whether the event-window return is
  a significant jump versus the asset's local diffusive volatility (FR-JUMP).
- Estimate a **cross-sectional exposure regression** of abnormal returns on **surprise** (never
  the raw event) across many assets, with inference robust to same-day event clustering
  (FR-XS).
- Expose all of the above through a small public API consumed by a thin FastAPI service.

The system **shall not**:

- Provide live order placement or investment recommendations.
- Re-implement OHLC ingestion — it reuses `stock-data-service` (§6).
- Provide intraday high-frequency data in v1 — it operates on **daily** OHLC (EC5).
- Include the **LLM surprise constructor** in v1 — deferred to a later phase (it belongs to the
  chatbot subsystem); the pipeline reserves a hook for it (§3.3, §6).
- Forecast event *occurrence* or *outcomes*; it measures *reactions* to recorded outcomes.

### 1.3 Definitions, Acronyms, Abbreviations

| Term | Definition |
|---|---|
| Event | A discrete, timestamped occurrence (rate decision, tariff, shock) with a realised outcome |
| Surprise | Standardised deviation of the realised outcome from the **pre-event expectation**; the quantity markets price |
| Consensus | Pre-event expected value (survey/published), the default expectation; a column in the events contract |
| Futures/Kuttner surprise | Surprise inferred from the change in a related futures price across the release (Kuttner, 2001); expectation = pre-announcement futures-implied level |
| Odds series | Pre-event market-implied probability in `[0,1]` (e.g. policy-decision odds), tz-aware UTC |
| Estimation window | Trailing window `[t₀−(L+g), t₀−g]` on which market-model params are fit; ends `g` days before the event |
| Event window | `[t₀−k₁, t₀+k₂]` days around the event over which abnormal returns are accumulated |
| Gap `g` | Days between the end of the estimation window and the event (analogue of the chart system's `edge_lag`) |
| AR / CAR | Abnormal Return / Cumulative Abnormal Return (log returns) |
| Market model | `r_i = α_i + β_i·r_m + ε_i`; abnormal return = realised − fitted |
| Lee–Mykland test | Jump test comparing a return to local realised volatility (Lee & Mykland, 2008) |
| Cross-section | Many assets reacting to one common event (the unit of FR-XS) |
| Same-day clustering | Multiple events sharing a date → cross-sectionally correlated ARs → the iid event-study t-test is invalid |
| tz-aware UTC | Every timestamp carries an explicit UTC timezone to the minute; naive datetimes are rejected |
| No-leakage test | Mutate post-event data with noise; assert pre-event-derived quantities do not change |

### 1.4 References

1. MacKinlay, A. C. (1997). *Event Studies in Economics and Finance*. JEL.
2. Kuttner, K. N. (2001). *Monetary Policy Surprises and Interest Rates: Evidence from the Fed
   Funds Futures Market*. Journal of Monetary Economics.
3. Lee, S. S., & Mykland, P. A. (2008). *Jumps in Financial Markets: A New Nonparametric Test
   and Jump Dynamics*. Review of Financial Studies.
4. Boehmer, E., Musumeci, J., & Poulsen, A. (1991). *Event-Study Methodology under Conditions
   of Event-Induced Variance*. Journal of Financial Economics.
5. Kolari, J., & Pynnönen, S. (2010). *Event Study Testing with Cross-Sectional Correlation of
   Abnormal Returns*. Review of Financial Studies.
6. `docs/event_reaction_gap_map.md` — Phase 0 gap map (this repo).
7. `event-reaction-lib/CLAUDE.md` — module standing rules (provided separately).
8. `SRS_chart_decomposition.md` — sibling SRS whose causality discipline (C1) this document
   extends to the event-study setting.

### 1.5 Document Overview

§2 gives the module boundary, package layout, and integration points. §3 specifies the six
stages as modules with data contracts and the structural anti-bug requirements. §4 defines the
pandas data contracts, the public API, and the ports-and-adapters split. §5 is the validation/
test plan. §6 records reuse + reconciliation decisions. Appendices give defaults and traps.

---

## 2. Overall Description

### 2.1 Product Perspective, Module Boundary, and Package Layout

The system is a **new microservice + companion pure-compute library**, mirroring the
chart-decomposition split (gap map §1, §4):

- **`stock_microservices/event-reaction-lib/`** (package `event_reaction`) — the pure-stats
  core. Per the module standing-rules doc, the package is laid out as **flat stage packages**
  (not the chart-decomp `domain/application/infrastructure` layering):

  ```
  event_reaction/
    types.py          # shared dataclasses / type aliases for results & params
    ingest/           # ADAPTERS ONLY — network/DB I/O lives here and nowhere else
                      #   prices (HTTP→stock-data-service), events (MySQL store), odds (prediction-market)
    align/            # UTC event clock, log returns, estimation/event window resolution   (pure)
    surprise/         # surprise constructors: consensus (default), futures/Kuttner, odds   (pure)
    returns/          # market-model abnormal returns + CAR                                 (pure)
    jumps/            # Lee–Mykland jump test (daily variant)                               (pure)
    cross_section/    # CAR-on-surprise exposure regression, clustering-robust              (pure)
  ```
  **The five stats stages (`align`, `surprise`, `returns`, `jumps`, `cross_section`) MUST NOT
  perform I/O.** All network/DB access is confined to `ingest/`.

- **`stock_microservices/services/event-reaction-service/`** — a FastAPI service mounting the
  library under `/stock_helper/api/v2/event-reaction`. It is **stateful**: it owns an **event
  store in MySQL** (`app/models/`, `app/repositories/`) like `decision-helper-service`. The
  MySQL repository is the `ingest/` **events adapter** that *materialises* the `events`
  DataFrame (§4.1); the stats core only ever sees that DataFrame.

A nested **`event-reaction-lib/CLAUDE.md`** carries the module's standing rules. **This SRS
does not modify the root `CLAUDE.md`.**

#### Integration points (cited from the gap map)

| Integration | Real anchor (gap map) | How this module plugs in |
|---|---|---|
| OHLC price loading | `stock-data-service` `GET /stocks/{symbol}/history`; consumed over HTTP by `prediction-service` `_fetch_historical_data` (`prediction_service.py:36`) | `ingest/` prices adapter makes the same HTTP call; stats core never touches DB/vnstock |
| Returns / log-returns | inline in `prediction_service.py:79-80`; reusable utils in chart-decomp-lib | Reuse log-return formula; centralise in `align/` (see §6) |
| Volatility / null baseline | `RealizedVolCalculator.compute` (`rv_calculator.py:23`); `estimate_volatility` (`surrogates.py:64`); `make_surrogate`/`random_walk_surrogates` (`surrogates.py:19,74`) | Local vol for the jump test; surrogates for the random-walk null (EC4) |
| Gateway routing | Traefik one-router-per-service, `/stock_helper/api/v2/<area>`; chart-decomp at 8011 (`docker-compose.yml:777-810`) | New router `stock-event-reaction`, prefix `/event-reaction`, next free port **8012**, same 6-label set |
| Service mount | `chart-decomp-service/app/main.py:101-105` | Same mount idiom; stateful `lifespan` ensures event tables exist |
| Frontend report | bespoke "Detection Report" table in `PatternTab` (`ChartDecomp/index.js:1358-1408`) | **New sibling React component** (out of scope until a later UI phase; §6) |
| Test location/command | `chart-decomp-lib/tests/` run by direct `pytest` (gap map §1) | `event-reaction-lib/tests/`, `cd stock_microservices/event-reaction-lib && pytest tests/` |

### 2.2 Product Functions

1. Ingest and persist events (tz-aware UTC, asset scope, `actual`, `consensus`).
2. Align each event to the daily price grid: resolve the event day from the minute-resolution
   UTC release timestamp; derive estimation/event windows on the trading calendar.
3. Construct a **standardised surprise** from a pre-event expectation (consensus default;
   futures/Kuttner or odds alternates).
4. Compute abnormal returns / CAR (log returns) over the event window via a strictly-pre-event
   market model.
5. Run the daily Lee–Mykland jump test on the event-window return.
6. Regress abnormal returns on **surprise** across assets (exposure), with clustering-robust
   inference.

### 2.3 User Classes and Characteristics

- **Quant researcher** — runs event studies; needs causal hygiene, observed-surprise
  constructors, and benchmark gating.
- **Backend developer** — calls the public API (§4.2) or the service endpoints; needs stable,
  typed pandas contracts and mockable data sources.
- **Frontend developer** — consumes service JSON to render an event-reaction report (future).

### 2.4 Operating Environment

Python ≥ 3.10. Library depends on numpy/pandas/scipy/statsmodels (§7) plus the in-repo
`chart-decomp` package for reuse. The service adds FastAPI/uvicorn, SQLAlchemy + MySQL (system
of record at `host.docker.internal:3306`), `httpx` for the price adapter. Deployed behind
Traefik on port 8012.

### 2.5 Design and Implementation Constraints

**EC1. Strict causality / no look-ahead (extends chart-system C1).** Every quantity attached
to an event uses **only data timestamped strictly before the event**. The surprise's
expectation (consensus/futures/odds) is a **pre-event** value; the market-model parameters
(FR-AR) are fit on an estimation window ending a gap `g ≥ 1` trading days before the event day.
No full-series quantity is computed then sliced around the event. Estimators take
`(data_up_to_t⁻)`, never a precomputed full-panel matrix.

**EC2. Surprise, not the raw event.** No reaction is regressed on, or attributed to, the raw
event occurrence or the raw `actual`. Every reaction model (especially FR-XS) takes a
**surprise** measure as its regressor. Constructing the surprise is mandatory upstream of any
reaction estimate.

**EC3. Event-induced cross-sectional correlation.** When events cluster on the same day,
abnormal returns are cross-sectionally correlated and the classical iid event-study t-test
over-rejects. The cross-sectional module **shall not** use the iid t-test; it uses a
clustering-robust procedure (§3.8).

**EC4. Benchmark gating (analogue of chart-system C4).** A reaction is reported as
"significant" only if it beats a stated null **out-of-window**: (a) a random-walk / placebo-
window null for the surprise→AR link, and (b) a non-event-window distribution for the jump
test. The benchmark is reported beside every effect.

**EC5. Daily-frequency limitation, explicitly documented.** v1 operates on **daily** OHLC. The
Lee–Mykland test is a **daily variant** (local realised vol from a trailing daily-return
window); its reduced power versus the intraday original is documented (Appendix B). The
intraday `PriceSource` port is specified (§4.3) but not implemented in v1.

**EC6. Timezone discipline, to the minute.** All timestamps — events, price index, odds index —
are **tz-aware UTC to the minute**. The event release timestamp is the **join key**. Naive
datetimes are rejected at the boundary (FR-ALIGN). Resolution to the daily trading grid is
explicit and tested.

**EC7. Reproducibility.** Every stochastic routine (surrogate nulls, bootstrap, sampling)
accepts a seed.

### 2.6 Assumptions and Dependencies

- Daily OHLC for each asset and a market proxy (index) are available via `stock-data-service`.
- Each event's `consensus` is the **pre-event vintage** (not a later-revised value); `actual`
  is recorded post-event. Futures/odds inputs, where present, are pre-event quotes.
- The trading calendar is derivable from the price index (no separate holiday source in v1).
- Missing data within a window is handled per FR-ALIGN's documented policy, not silently.

---

## 3. Specific Requirements

The six skeleton stages map to modules 3.1–3.6. §3.7–3.8 are the structural anti-bug
requirements; §3.9 lists non-functional requirements; §3.10 states the I/O-isolation rule.

### 3.1 Stage 1 — Event Ingestion (FR-EVT) — `ingest/`

- **Input:** events from the `EventSource` adapter (MySQL store); prices from the `PriceSource`
  adapter (HTTP→stock-data-service); optional odds from the `OddsSource` adapter.
- **Behaviour:** validate each event has a non-null `kind`, a **tz-aware UTC** `ts_utc` (EC6),
  an asset scope, a realised `actual`, and a `consensus` (the default expectation). Futures/odds
  references are optional.
- **Output:** a validated, de-duplicated `events` DataFrame (§4.1) plus the aligned price/odds
  series. Duplicate `(kind, ts_utc, asset_scope)` rows are upserted per a documented policy.
- **Constraint:** ingestion is the **only** stage permitted I/O (§3.10). It performs no return
  or surprise computation.

### 3.2 Stage 2 — Timestamp / Alignment (FR-ALIGN) — `align/` (pure)

- **Input:** a validated event row, a daily price `pd.Series` (tz-aware UTC index), optional
  odds `pd.Series`.
- **Method:** reject naive datetimes (EC6). Resolve the **event day** `t₀` = first trading day
  on or after `ts_utc` (UTC). Compute **log returns** from prices. From the trading calendar
  implied by the price index, derive the **estimation window** `[t₀−(L+g), t₀−g]` and the
  **event window** `[t₀−k₁, t₀+k₂]`. Reject events whose required windows extend beyond available
  data (no padding with future data — EC1).
- **Output:** an `AlignedEvent` with integer index bounds for both windows, resolved `t₀`, and a
  `coverage` flag for in-window gaps.
- **Constraint:** pure index arithmetic on tz-aware data; no value smoothing; **no I/O**.

### 3.3 Stage 3 — Surprise Constructors (FR-SURP) — `surprise/` (pure)

Surprise is **observed/external**, never modelled from the price series. `surprise/` exposes a
small **constructor registry** keyed by name, defaulting to `consensus`. Each constructor is a
pure function over inputs already materialised by `ingest/`, using **only pre-event values**
(EC1).

- **`consensus` (default):** raw surprise `s_raw = actual − consensus`. Standardised surprise
  `s = s_raw / σ_kind`, where `σ_kind` is the dispersion of past `(actual − consensus)`
  surprises **of the same `kind`** computed from events strictly before `t₀`. Sign convention
  documented (positive = hawkish/larger-than-expected).
- **`futures` / Kuttner:** expectation = the pre-announcement futures-implied level; surprise =
  realised − implied, scaled per Kuttner (2001). Uses only the pre-event futures quote and the
  recorded outcome.
- **`odds`:** for binary/level outcomes with a market-implied probability series, surprise =
  realised outcome − the **last odds value strictly before `t₀`** (odds ∈ `[0,1]`).
- **`llm` (DEFERRED, v2):** an LLM-derived expectation/score. Out of scope for v1 (chatbot
  subsystem). The registry reserves the name; **its network call would live in `ingest/`** (it
  must not be invoked from the pure `surprise/` stage), materialising a column the constructor
  then consumes.
- **Output:** a `Surprise` object: `method`, `s_raw`, `s` (standardised), `expected` (the
  external expectation used), `scale` (`σ_kind`), and `sign`.
- **Constraint (EC1):** every input is timestamped strictly before `t₀`; `σ_kind` uses only
  prior same-kind events. This is the primary leakage surface, covered by §5.3.

### 3.4 Stage 4 — Market-Model Abnormal Returns (FR-AR) — `returns/` (pure)

- **Input:** asset daily **log** returns, market-proxy daily log returns, the aligned
  estimation and event windows.
- **Method:** estimate `α_i, β_i` by OLS of `r_i` on `r_m` over the **estimation window only**
  (ends `g` days before `t₀`, EC1). `AR_t = r_{i,t} − (α_i + β_i r_{m,t})` over the event
  window; `CAR = Σ AR_t`. Report estimation-window residual std `σ_AR` for standardisation
  (`SAR_t = AR_t / σ_AR`).
- **Benchmark (EC4):** also compute CAR over placebo windows from non-event periods to
  characterise the null distribution of CAR.
- **Output:** `AbnormalReturns`: `AR[]`, `CAR`, `alpha`, `beta`, `sigma_AR`, `est_window`,
  `event_window`, placebo-CAR summary.

### 3.5 Stage 5 — Lee–Mykland Jump Test, daily variant (FR-JUMP) — `jumps/` (pure)

- **Input:** asset daily log returns and the resolved event day `t₀`.
- **Method:** estimate local diffusive volatility `σ̂_t` from a trailing daily-return window
  ending **before** `t₀` (reusing `estimate_volatility` / `RealizedVolCalculator` where
  applicable). Form `L_{t₀} = r_{t₀} / σ̂_{t₀}` and compare its magnitude to the extreme-value
  threshold to flag a jump at a stated level.
- **Benchmark / null (EC4):** report empirical false-positive rate on **non-event** days and/or
  random-walk surrogates (`make_surrogate`), so a flagged jump is interpretable vs the
  random-walk null.
- **Output:** `JumpTest`: `statistic`, `threshold`, `is_jump`, `sigma_local`, `null_fpr`.
- **Constraint (EC5):** documented daily-variant with reduced power; intraday original deferred.

### 3.6 Stage 6 — Cross-Sectional Exposure Regression (FR-XS) — `cross_section/` (pure)

- **Input:** for one common event (or event-kind), a panel
  `{asset → (surprise sᵢ, CARᵢ, event_date)}`.
- **Method:** regress `CARᵢ = γ₀ + γ₁·sᵢ + uᵢ` across assets — **the regressor is the surprise,
  never the raw event (EC2)**. `γ₁` is the exposure (reaction per unit surprise). Inference uses
  a **clustering-robust** procedure (EC3, §3.8) — never the iid event-study t-test.
- **Output:** `CrossSectionExposure`: `gamma0`, `gamma1`, robust SEs, the clustering method,
  `n_assets`, `n_event_dates`, R².
- **Constraint:** when all assets share one event date, report the calendar-time / portfolio-
  aggregated estimate (§3.8) rather than treating assets as independent draws.

### 3.7 Structural prevention of look-ahead leakage (FR-NOLEAK) — addresses domain bug (a)

1. **Window contract.** Alignment (§3.2) guarantees `estimation_window.end ≤ t₀ − g`; the
   surprise's expectation and `σ_kind` use only data before `t₀`. The event window may include
   `t₀`+, but no *fitting/standardising* code sees it.
2. **`data_up_to_t` signatures.** Surprise standardisation (FR-SURP) and the market model
   (FR-AR) are functions of pre-event slices, mirroring the chart system's
   `(data_up_to_t) -> features` rule (`SRS_chart_decomposition.md` Appendix B1). No full-panel
   matrix is precomputed and sliced.
3. **Mandatory no-leakage test (EC1, §5.3).** For each event, replace all post-`t₀` data with
   noise and assert the surprise, `α/β`, `σ_AR`, and local jump vol are **unchanged**. A
   deliberately non-causal variant is included as a tripwire and must show absurdly inflated
   effects.

### 3.8 Robust cross-sectional inference under clustering (FR-CLUSTER) — addresses domain bug (b)

When events cluster on the same day, ARs are cross-sectionally correlated and the iid t-test is
invalid (EC3). The module **shall** provide, and default to, at least one of:

- **Cluster-robust standard errors** on the §3.6 regression, clustered by **event date**.
- **Calendar-time portfolio aggregation:** collapse same-day events into a single portfolio
  observation (equal/value-weighted CAR) before inference.
- **Standardised cross-sectional test** (Boehmer–Musumeci–Poulsen / Kolari–Pynnönen) that
  estimates the cross-sectional variance of standardised ARs directly.

The chosen method and the count of distinct event dates are reported with every estimate. The
mandatory clustering test (§5.4) plants a common same-day factor and asserts the iid t-test
over-rejects while the robust procedure does not.

### 3.9 Non-Functional Requirements

- **NFR-1 Purity.** The five stats stages have no network/DB/file/clock dependency; time and
  data enter through `ingest/` adapters (§4.3). (Enables EC1 and offline tests.)
- **NFR-2 Determinism.** Same inputs + seed ⇒ bit-stable outputs.
- **NFR-3 Typing & errors.** Typed dataclasses for results/params; a small exception hierarchy
  (`EventReactionError`, `InsufficientDataError`, `AlignmentError`, `LeakageError`) mirroring
  chart-decomp's, so the service `_handle` maps them to HTTP codes.
- **NFR-4 Performance.** A single-event end-to-end on ≤ 2000 daily bars completes well under
  1 s; a 200-asset cross-section within a few seconds.
- **NFR-5 Observability.** `/health{,/live,/ready}` + `/metrics` like every repo service.

### 3.10 Separation of concerns (I/O only in `ingest/`)

The five stats stages are pure functions over in-memory pandas/numpy contracts. Data
acquisition (events from MySQL, prices from `stock-data-service` over HTTP, odds from a
prediction-market source) happens only in `ingest/` adapters behind ports (§4.3). The
orchestrator receives data through ports and passes plain Series/DataFrames to the stats core.

---

## 4. Data Models and Interfaces

### 4.1 Core Data Contracts (pandas; tz-aware UTC)

Per the module standing-rules doc, inputs are **pandas** with tz-aware UTC, to the minute (EC6).

```python
# events: one row per event. ts_utc is the join key (tz-aware UTC, minute resolution).
events: pd.DataFrame  # columns:
#   event_id : str
#   ts_utc   : datetime64[ns, UTC]   (naive -> rejected)
#   kind     : str                   ("rate_decision" | "tariff" | "geopolitical" | ...)
#   actual   : float                 (realised outcome, recorded post-event)
#   consensus: float                 (pre-event expected value — default surprise input)
#   [optional] futures_implied: float    # for the Kuttner constructor (pre-event)
#   [optional] odds_ref: str             # handle to an odds series (pre-event)
#   [optional] asset_scope: object       # symbol | list[symbol] | sector tag

prices: pd.Series   # tz-aware UTC monotonic-increasing index; values = (adj) close; gaps handled
market: pd.Series   # market-proxy prices, same index convention
odds:   pd.Series   # values in [0,1], tz-aware UTC index   (optional)
```

Result objects are lightweight dataclasses (illustrative; implementation matches repo style):

```python
@dataclass(frozen=True)
class AlignedEvent:
    event_id: str
    t0_index: int                  # event day t0 in the price series
    est_window: tuple[int, int]    # [t0-(L+g), t0-g], end strictly < t0
    event_window: tuple[int, int]  # [t0-k1, t0+k2]
    coverage: str                  # "full" | "partial:<reason>"

@dataclass(frozen=True)
class Surprise:
    method: str                    # "consensus" | "futures" | "odds"
    s_raw: float
    s: float                       # standardised
    expected: float
    scale: float                   # sigma_kind
    sign: int

# AbnormalReturns, JumpTest, CrossSectionExposure: see §3.4-3.6

@dataclass(frozen=True)
class EventReaction:
    aligned: AlignedEvent
    surprise: Surprise
    abnormal: AbnormalReturns
    jump: JumpTest
```

### 4.2 Public API (Illustrative)

```python
# Single-event end-to-end (orchestrates align -> surprise -> returns -> jumps over adapter data)
measure_event_reaction(event_row, prices, market, *, params=DEFAULTS,
                       odds=None) -> EventReaction

# Individual stages (pure core; each takes only the data it needs)
make_surprise(event_row, prior_same_kind, *, method="consensus",
              odds=None, futures=None) -> Surprise                  # FR-SURP
abnormal_returns(asset_logret, market_logret, est_window, event_window) -> AbnormalReturns  # FR-AR
jump_test_daily(asset_logret, t0_index, *, level=0.01,
                local_window=21) -> JumpTest                        # FR-JUMP

# Cross-sectional (stage 6) over a panel of single-event results — regressor is the SURPRISE
cross_sectional_exposure(panel, *, cluster="event_date") -> CrossSectionExposure  # FR-XS

# Causality guard exposed for tests/CI
assert_no_leakage(event_row, prices, market, *, params) -> None     # FR-NOLEAK
```

### 4.3 Ports and Adapters

**Ports (library, e.g. `typing.Protocol`):**

```python
class EventSource(Protocol):
    def fetch(self, kind=None, since=None, until=None) -> pd.DataFrame: ...  # the events contract

class PriceSource(Protocol):
    def history(self, symbol, start, end) -> pd.Series: ...     # daily in v1
    # def intraday(self, symbol, start, end) -> pd.Series: ...  # specified, v2 (EC5)

class OddsSource(Protocol):                                     # optional
    def series(self, ref, start, end) -> pd.Series: ...         # values in [0,1]
```

**Adapters (in `ingest/` / the service, not the stats core):**

- `MySqlEventRepository` implements `EventSource` against the owned MySQL event store
  (SQLAlchemy models in `app/models/`, repository in `app/repositories/`, lifespan ensures
  tables — like `decision-helper-service`) and materialises the `events` DataFrame.
- `HttpPriceSource` implements `PriceSource` by calling `stock-data-service`
  `GET /stocks/{symbol}/history` (the prediction-service pattern, gap map §2).
- **Test adapters:** in-memory sources backed by fixtures, so the entire stats core and
  orchestration are testable with **no network or DB** (NFR-1).

### 4.4 Service Endpoints (thin wrapper)

Mounted under `/stock_helper/api/v2/event-reaction` (port 8012). Indicative: `POST /events`
(ingest), `GET /events`, `POST /measure` (single event), `POST /cross-section`, plus
`/health{,/live,/ready}` and `/metrics`. Library exceptions map to HTTP via a `_handle` like
`chart-decomp-service/app/api/routes.py:64`.

---

## 5. Validation and Test Requirements

Tests live in `event-reaction-lib/tests/`, run with
`cd stock_microservices/event-reaction-lib && pytest tests/` (gap map §1). All fixtures are
deterministic and seeded; stats stages run fully offline; data adapters are mocked.

### 5.1 Unit / Recovery Tests (one per stat stage)

- **Surprise:** known `(actual, consensus, σ_kind)` → known standardised `s` with the right
  **sign and scale**; the `odds` and `futures` constructors recover their defined surprises;
  short prior-history handling is documented and tested.
- **Alignment:** event `ts_utc` → correct `t₀` across DST/weekends; naive datetime rejected;
  windows past data raise `AlignmentError`; log returns match the reference formula.
- **Abnormal returns:** on synthetic `r_i = α + β r_m + ε`, recover `α, β` within tolerance;
  **known CAR recovered**.
- **Jump test:** an **injected jump** on an otherwise calm series is detected; a calm series is
  not.
- **Exposure:** on a planted cross-section with **known `γ₁`**, recover the coefficient within
  tolerance.

### 5.2 Statistical Validation

- **Surprise standardisation:** standardised surprise has unit scale (within tolerance) and
  uses pre-event dispersion only.
- **Jump-test null FPR (EC4):** on random-walk surrogates, empirical jump FPR ≈ nominal level —
  a *property*, not the skeleton's illustrative numbers.
- **CAR null (EC4):** placebo-window CAR distribution brackets the observed CAR as expected.

### 5.3 Causality / No-Leakage Tests (mandatory — EC1, FR-NOLEAK)

- **No-leakage property test:** mutate all post-`t₀` data with noise; assert the surprise,
  `α/β`, `σ_AR`, and local jump vol are **unchanged**. (Direct analogue of
  `SRS_chart_decomposition.md` §5.3; matches the module doc's property-test requirement.)
- **Look-ahead tripwire:** a deliberately non-causal variant (estimation/standardisation window
  includes `t₀`+) must produce absurdly inflated effect sizes.

### 5.4 Cross-Sectional Clustering Test (mandatory — EC3, FR-CLUSTER)

Plant a common same-day factor across many assets so their ARs are correlated. Assert the **iid
event-study t-test over-rejects** (empirical size ≫ nominal) while the **clustering-robust
procedure** (cluster-by-date SE / portfolio aggregation / standardised cross-sectional test)
holds size near nominal. This is the executable statement of EC3.

### 5.5 End-to-End Test

Generate a multi-asset daily panel with a common factor and a known event with a known
surprise→AR mapping; run ingest → align → surprise → returns → jumps → cross_section and check:
(a) recovered exposure `γ₁` within tolerance of the planted value; (b) the no-leakage mutation
leaves all pre-event quantities unchanged; (c) the clustering-robust test's size is near
nominal where the iid test's is not.

---

## 6. Reuse & Reconciliation Decisions

### 6.1 Reuse (from the gap map)

| Concern | Decision | Anchor |
|---|---|---|
| OHLC loading | **Reuse over HTTP** via `ingest/` `HttpPriceSource` → `stock-data-service` `GET /stocks/{symbol}/history`; do not import `StockRepository` cross-service | gap map §2; `prediction_service.py:36-54` |
| Returns / log-returns | Reuse the log-return formula; centralise in `align/` rather than re-deriving inline | gap map §3 (`prediction_service.py:79-80`) |
| Volatility / null | Reuse `RealizedVolCalculator.compute`, `estimate_volatility` (local vol); `make_surrogate`/`random_walk_surrogates` (random-walk null, EC4) | gap map §3 (`rv_calculator.py:23`, `surrogates.py:19,64,74`) |
| Service shape | New stateful service (MySQL event store) like `decision-helper`; thin router mount like `chart-decomp-service` | gap map §1, §4 |
| Frontend report | **New sibling React component** — `PatternTab`'s table is bespoke; out of scope until a later UI phase | gap map §5 (`ChartDecomp/index.js:1358-1408`) |
| Module rules | Nested `event-reaction-lib/CLAUDE.md`; root `CLAUDE.md` untouched | §2.1 |

### 6.2 Reconciliation with the module standing-rules doc (v1.0 → v1.1)

| Item | v1.0 (superseded) | v1.1 (module doc governs) |
|---|---|---|
| Package layout | chart-decomp `domain/application/infrastructure` layering | **Flat stage packages** `ingest/ align/ surprise/ returns/ jumps/ cross_section/` (§2.1) |
| Data contracts | numpy-array dataclasses | **pandas** `events` DataFrame, `prices`/`market`/`odds` `pd.Series` (§4.1) |
| Surprise source | module-estimated AR(1)/RW baseline (default) | **Observed/external**: `consensus` default; `futures`/Kuttner, `odds` alternates; **`llm` deferred** (§3.3) |
| Event-vs-surprise | implied | **Explicit EC2**: never regress on the raw event (§2.5, §3.6) |
| Timestamp resolution | "tz-aware UTC" | **to the minute; release ts is the join key** (EC6) |
| MySQL event store | stateful service | unchanged — now framed as the `ingest/` events adapter materialising the DataFrame (§2.1, §4.3) |

> **Note:** the gap map (`docs/event_reaction_gap_map.md`) required **no changes** — it is a
> survey of real paths/reuse and its findings still hold.

---

## 7. Dependencies

| Dependency | Used for |
|---|---|
| `numpy` | array math across stages |
| `pandas` | tz-aware UTC contracts, trading-calendar indexing, panel handling (the primary data type) |
| `scipy` | OLS/statistics, extreme-value thresholds for Lee–Mykland, distributions |
| `statsmodels` | market-model OLS, cluster-robust / HAC standard errors for FR-XS (EC3) |
| `chart-decomp` (in-repo) | reused volatility & surrogate helpers (§6) |
| service-only | `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, MySQL driver, `httpx`, `prometheus-client` |

Optional-extras pattern mirrors `chart-decomp-lib/pyproject.toml` (`dev = [pytest, ...]`).

---

## Appendix A — Default Parameters

| Parameter | Default | Notes |
|---|---|---|
| Estimation window length `L` | 120 trading days | Market-model fit window |
| Gap `g` | 5 trading days | Estimation ends `g` days before `t₀` (EC1; analogue of chart `edge_lag`) |
| Event window `(k₁, k₂)` | (1, 1) | One day pre/post `t₀`; CAR over the window |
| Surprise constructor | `consensus` | Default; `futures`/Kuttner and `odds` are alternates; `llm` deferred |
| Surprise scale `σ_kind` | per-kind, pre-event | Dispersion of prior same-kind `(actual − consensus)` surprises |
| Jump local window | 21 trading days | Trailing daily-return window for `σ̂_local` (EC5) |
| Jump test level | 0.01 | Extreme-value threshold |
| Cross-section clustering | `event_date` | Cluster-robust SE default (EC3) |
| Null surrogates | 1000 | Random-walk null replications (EC4) |
| Seed | 0 | Reproducibility (EC7) |

Magnitudes are defaults, **not** expected test values; tests assert properties (EC4, §5).

---

## Appendix B — Known Limitations and Implementation Traps

**B1. Look-ahead leakage is the #1 trap.** Using any at/after-`t₀` data in the surprise's
expectation, its standardisation scale, or the market model silently inflates every reaction.
Structurally prevented by the window contract and `(data_up_to_t)` signatures (§3.7); enforced
by the mandatory no-leakage mutation test (§5.3).

**B2. Same-day event clustering breaks the iid t-test.** The #2 trap and the reason
EC3/FR-CLUSTER exist. Treating N same-day assets as N independent observations over-rejects;
always use cluster-by-date / portfolio aggregation / standardised cross-sectional inference
(§3.8, §5.4).

**B3. Surprise sign and standardisation must be explicit.** A surprise is comparable across
events only once standardised by a *pre-event* per-kind scale; mixing raw and standardised
surprises, or flipping the sign convention, silently corrupts the exposure regression.

**B4. Daily Lee–Mykland has reduced power (EC5).** The daily variant cannot separate a true
jump from a large diffusive day as cleanly as the intraday original. Report `is_jump` beside its
non-event-day FPR (EC4) and treat it as indicative until intraday data exists.

**B5. Event timestamp ≠ trading day.** Events fire at a wall-clock instant (often after the
local close, in another timezone). The minute-resolution UTC→trading-day resolution (FR-ALIGN)
is where off-by-one bugs live; it is tz-aware and explicitly tested (§5.1).

**B6. The market proxy matters.** `β` and the abnormal return depend on the chosen index; the
proxy symbol is a reported parameter, not a hidden constant.

**B7. Surprise is observed, not modelled — and must use the pre-event vintage.** The expectation
(consensus/futures/odds) must be a value known **before** the event: the pre-event consensus
vintage (not a later revision), the pre-announcement futures-implied level, or the last odds
quote before `t₀`. Never substitute a post-event or revised value, and never fall back to a
value derived from the price reaction itself (that would re-introduce leakage and defeat EC2).

**B8. Reuse, do not fork, the price loader.** OHLC must come through the `ingest/` `PriceSource`
adapter to `stock-data-service`; copying `StockRepository` into this module would duplicate
schema ownership and drift from the system of record (gap map §2).

**B9. The LLM surprise constructor is deferred and is an I/O concern.** When added (v2), its
model call lives in `ingest/`, materialising a column the pure `surprise/` constructor consumes
— it must never be invoked from a stats stage (NFR-1, §3.10).

---

*End of document.*
