# Implementation Plan — Event-Reaction Measurement System

**Spec:** `SRS_event_reaction.md` (v1.1, repo root) — APPROVED.
**Module dir (library):** `stock_microservices/event-reaction-lib/` (package `event_reaction`)
**Companion service:** `stock_microservices/services/event-reaction-service/`
**Test command:** `cd stock_microservices/event-reaction-lib && pytest tests/`
**Format:** PR-sized tasks, dependency order, one at a time. **Each task: write its failing
test(s) first, make them pass, show output, then STOP.** Do not start the next task without
being asked (module standing-rules: one task at a time).

> **Discipline (from the SRS / module CLAUDE.md):** the five stats stages
> (`align`, `surprise`, `returns`, `jumps`, `cross_section`) MUST NOT do I/O. Network/DB live
> ONLY in `ingest/`. All timestamps tz-aware UTC to the minute. Surprise is **observed**
> (consensus default; futures/Kuttner, odds alternates; `llm` deferred) — never modelled from
> the price series. Assert **properties** in tests, never the skeleton's illustrative numbers.

---

## SEQUENCING OVERVIEW

```
T0  module rules         CLAUDE.md  (FIRST — paste-in)
T1  scaffold             pyproject + package skeleton + types + exceptions + conftest
PURE-STATS STAGES (no data sources — build and test fully offline)
T2  align/        →  T3 surprise/   →  T4 returns/   →  T5 jumps/   →  T6 cross_section/
T7  orchestrator + no-leakage guard  (measure_event_reaction, assert_no_leakage)
ADAPTERS / SERVICE (I/O — last)
T8  ports + in-memory test adapters
T9  HttpPriceSource (ingest/ → stock-data-service)
T10 MySQL event store + repository (service)
T11 FastAPI service + compose/Traefik wiring (port 8012)
```

Stats stages T2–T7 depend on nothing outside the library and `chart-decomp`. Adapters T8–T11
come last so the core is proven before any network/DB is introduced.

---

## Task 0 — Module standing rules
- **Files:** `stock_microservices/event-reaction-lib/CLAUDE.md` (new)
- **Do:** Create the file from the contents the user pastes. Do **not** invent rules; this is a
  verbatim paste. Do **not** modify the root `CLAUDE.md`.
- **Tests:** none (doc task).
- **Done gate:** file exists at the module root with the pasted content.
- **Depends on:** none. **Do this first.**

## Task 1 — Scaffold the library package
- **Files (new):**
  - `event-reaction-lib/pyproject.toml` (mirror `chart-decomp-lib/pyproject.toml`: name
    `event-reaction`, deps `numpy,pandas,scipy,statsmodels` + `chart-decomp` (path/editable),
    `dev=[pytest,pytest-asyncio]`)
  - `event_reaction/__init__.py` (public-API re-exports, filled as stages land)
  - `event_reaction/types.py` (dataclasses `AlignedEvent`, `Surprise`, `AbnormalReturns`,
    `JumpTest`, `CrossSectionExposure`, `EventReaction`; `DEFAULTS` params object — values from
    SRS Appendix A)
  - `event_reaction/exceptions.py` (`EventReactionError`, `InsufficientDataError`,
    `AlignmentError`, `LeakageError` — mirror chart-decomp's hierarchy, NFR-3)
  - empty stage packages: `event_reaction/{ingest,align,surprise,returns,jumps,cross_section}/__init__.py`
  - `tests/conftest.py` (seeded RNG fixture; synthetic builders: `daily_prices`,
    `market_factor`, `event_row`, `clustered_panel`)
- **Tests (`tests/test_scaffold.py`):**
  - `import event_reaction` succeeds; all six stage subpackages import.
  - The four exception classes exist and subclass `EventReactionError`.
  - `DEFAULTS` exposes `L=120, g=5, k1=1, k2=1, jump_local_window=21, jump_level=0.01,
    n_surrogates=1000, seed=0` (SRS Appendix A).
- **Done gate:** package imports; defaults match the SRS.
- **Depends on:** T0.
- **Integration note:** the `chart-decomp` dependency is how T5 reuses `estimate_volatility` /
  surrogates (gap map §3). Add it here so later tasks can import `chart_decomp`.

---

# PURE-STATS STAGES (no I/O — NFR-1)

## Task 2 — `align/` : event clock, log returns, windows (FR-ALIGN, EC1, EC6)
- **Files:** `event_reaction/align/clock.py`, `tests/test_align.py`
- **Public signatures:**
  - `log_returns(prices: pd.Series) -> pd.Series`  (tz-aware UTC index preserved)
  - `resolve_event_day(ts_utc: pd.Timestamp, price_index: pd.DatetimeIndex) -> int`
  - `make_windows(t0_index: int, n: int, *, L=120, g=5, k1=1, k2=1) -> AlignedEvent`
- **Do:** Reject naive datetimes (`AlignmentError`). `t0` = first trading day on/after `ts_utc`
  (UTC). Build estimation `[t0-(L+g), t0-g]` and event `[t0-k1, t0+k2]` index bounds; raise
  `AlignmentError` if either extends beyond the series (no future padding — EC1).
- **Tests:**
  - Naive datetime → `AlignmentError`.
  - An event timestamped on a weekend resolves `t0` to the next trading day; an after-close
    UTC instant resolves to the correct session day (B5).
  - `est_window.end < t0_index` strictly, with exactly `g` days of gap.
  - Window past the data boundary → `AlignmentError`.
  - `log_returns` equals `np.log(p_t / p_{t-1})` (matches the repo formula,
    `prediction_service.py:80`); length `n-1`; index stays tz-aware UTC.
- **Done gate:** all above pass; module imports no I/O libs.
- **Depends on:** T1.

## Task 3 — `surprise/` : observed surprise constructors (FR-SURP, EC1, EC2)
- **Files:** `event_reaction/surprise/constructors.py`, `tests/test_surprise.py`
- **Public signatures:**
  - `make_surprise(event_row, prior_same_kind: pd.DataFrame, *, method="consensus",
    odds: pd.Series | None = None, futures: float | None = None) -> Surprise`
  - a small registry `CONSTRUCTORS = {"consensus":..., "futures":..., "odds":...}`
- **Do:**
  - `consensus` (default): `s_raw = actual − consensus`; `scale = std` of prior same-`kind`
    `(actual − consensus)` from events **strictly before `t0`**; `s = s_raw/scale`; `sign`.
  - `futures` (Kuttner): `expected` = pre-announcement futures-implied level; `s_raw =
    actual − expected`, scaled per Kuttner (2001).
  - `odds`: `expected` = last odds value **strictly before `t0`** (∈ [0,1]); `s_raw =
    realized − expected`.
  - `llm`: **NOT implemented** (deferred, B9) — registry raises `NotImplementedError` with a
    pointer to the chatbot phase.
- **Tests (MANDATORY — surprise sign/scale):**
  - **Sign/scale:** with `actual=1.0, consensus=0.5` and prior-surprise std `0.25`,
    `s == 2.0` and `sign == +1`; with `actual < consensus`, `sign == -1`. (the mandatory
    "standardized surprise has the right sign/scale" gate)
  - `odds` constructor recovers `realized − last_pre_event_odds`; an odds value **at or after**
    `t0` is never used (slice check).
  - `futures` constructor recovers `actual − futures_implied`.
  - `scale` uses only prior same-kind events (feed a later same-kind event with a wild surprise;
    assert it does not change the current `scale`).
  - short prior history → documented fallback (no crash; `scale` handling stated).
  - `method="llm"` → `NotImplementedError`.
- **Done gate:** sign/scale test green; no post-`t0` value influences any output.
- **Depends on:** T1 (uses `t0` from caller; pure).

## Task 4 — `returns/` : market-model abnormal returns + CAR (FR-AR, EC4)
- **Files:** `event_reaction/returns/abnormal.py`, `tests/test_returns.py`
- **Public signature:**
  - `abnormal_returns(asset_logret: pd.Series, market_logret: pd.Series,
    est_window: tuple[int,int], event_window: tuple[int,int]) -> AbnormalReturns`
- **Do:** OLS of `r_i` on `r_m` over the **estimation window only**; `AR_t = r_{i,t} −
  (α+β r_{m,t})` over the event window; `CAR = ΣAR`; `sigma_AR` = estimation-window residual
  std. Compute placebo-window CAR distribution (EC4 benchmark).
- **Tests (MANDATORY — known CAR recovered):**
  - On synthetic `r_i = α + β r_m + ε` with known `α,β`, recover them within tolerance.
  - **Inject a known abnormal bump** of size `δ` on the event day over a clean market model and
    assert recovered `CAR ≈ δ` within tolerance. (the mandatory "known CAR is recovered" gate)
  - `sigma_AR` > 0 and computed only from the estimation window (swap event-window values →
    `sigma_AR` unchanged).
  - placebo CAR distribution returned with the documented length.
- **Done gate:** known-CAR test green; estimation uses only pre-event window.
- **Depends on:** T2 (consumes windows), T1.

## Task 5 — `jumps/` : Lee–Mykland daily jump test (FR-JUMP, EC4, EC5)
- **Files:** `event_reaction/jumps/lee_mykland.py`, `tests/test_jumps.py`
- **Public signature:**
  - `jump_test_daily(asset_logret: pd.Series, t0_index: int, *, level=0.01,
    local_window=21) -> JumpTest`
- **Do:** Estimate local diffusive vol `σ̂` from a trailing daily-return window ending **before**
  `t0` (reuse `chart_decomp` `estimate_volatility` / `RealizedVolCalculator`, gap map §3). Form
  `L = r_{t0}/σ̂`; compare |L| to the extreme-value threshold; set `is_jump`. Compute `null_fpr`
  on non-event days / random-walk surrogates (`chart_decomp.make_surrogate`).
- **Tests (MANDATORY — injected jump detected):**
  - **Inject a large return** at `t0` on an otherwise calm series → `is_jump is True`. (the
    mandatory "injected jump is detected" gate)
  - A calm series at `t0` → `is_jump is False`.
  - **Null FPR (property):** on random-walk surrogates the empirical jump FPR ≈ `level`
    within tolerance (NOT a hardcoded magnitude — EC4).
  - `σ̂` uses only pre-`t0` data (mutate post-`t0` returns → `σ̂` unchanged).
- **Done gate:** injected-jump + null-FPR tests green.
- **Depends on:** T1; reuses `chart-decomp` (from T1 dep).

## Task 6 — `cross_section/` : exposure regression, clustering-robust (FR-XS, FR-CLUSTER, EC2, EC3)
- **Files:** `event_reaction/cross_section/exposure.py`, `tests/test_cross_section.py`
- **Public signature:**
  - `cross_sectional_exposure(panel: pd.DataFrame, *, cluster="event_date")
    -> CrossSectionExposure`  (panel columns: `asset, surprise, car, event_date`)
- **Do:** Regress `CAR_i = γ0 + γ1·surprise_i + u_i` — **regressor is the surprise, never the raw
  event (EC2)**. Inference robust to same-day clustering (EC3): default cluster-by-`event_date`
  SE (statsmodels); also provide the portfolio-aggregation route and a standardised
  cross-sectional (BMP/Kolari–Pynnönen) option. Report method + `n_event_dates`.
- **Tests (MANDATORY — exposure coefficient recovered + clustering):**
  - **Plant a panel** with known `γ1` and recover it within tolerance. (the mandatory "true
    exposure coefficient is recovered" gate)
  - **Clustering (EC3):** plant a common same-day factor so ARs are correlated; assert the **iid
    t-test over-rejects** (empirical size ≫ nominal across seeded replications) while the
    **cluster-robust / portfolio** route holds size near nominal.
  - passing raw `actual` instead of `surprise` is impossible by signature (regressor is named
    `surprise`); document EC2 in the docstring.
- **Done gate:** γ1-recovery + clustering tests green.
- **Depends on:** T1 (consumes the panel data structure; pure).

## Task 7 — Orchestrator + no-leakage guard (FR-NOLEAK, EC1)
- **Files:** `event_reaction/pipeline.py`, `tests/test_causality.py`,
  `tests/test_pipeline_e2e.py`
- **Public signatures:**
  - `measure_event_reaction(event_row, prices: pd.Series, market: pd.Series, *,
    params=DEFAULTS, odds=None) -> EventReaction`  (orchestrates align→surprise→returns→jumps)
  - `assert_no_leakage(event_row, prices, market, *, params=DEFAULTS) -> None`
- **Do:** Wire the four single-event stages into `EventReaction`. `assert_no_leakage` runs the
  measurement, mutates all **post-`t0`** prices/returns/outcomes with noise, re-runs, and asserts
  `surprise`, `α/β`, `σ_AR`, and `σ_local` are unchanged; raises `LeakageError` otherwise.
- **Tests (MANDATORY — no-look-ahead property):**
  - **No-leakage swap:** mutating post-`t0` data does NOT change the surprise (nor `α/β`,
    `σ_AR`, `σ_local`). (the mandatory "mutating post-event data must not change a surprise"
    gate; SRS §5.3)
  - **Look-ahead tripwire:** a deliberately non-causal variant (estimation/standardisation
    window includes `t0`+) produces absurdly inflated effects — regression guard.
  - **E2E:** synthetic multi-asset panel with a known event → `measure_event_reaction` returns a
    populated `EventReaction`; feeding its outputs into `cross_sectional_exposure` recovers the
    planted `γ1` (SRS §5.5).
- **Done gate:** no-leakage + tripwire + e2e green.
- **Depends on:** T2, T3, T4, T5 (and T6 for the e2e tie-in).

---

# ADAPTERS / SERVICE (I/O — last; NFR-1 keeps this out of the stats core)

## Task 8 — Ports + in-memory test adapters (§4.3)
- **Files:** `event_reaction/ingest/ports.py`, `event_reaction/ingest/memory.py`,
  `tests/test_adapters_memory.py`
- **Do:** Define `Protocol`s `EventSource.fetch(...) -> pd.DataFrame`,
  `PriceSource.history(symbol,start,end) -> pd.Series` (+ `intraday` stub for v2, EC5),
  `OddsSource.series(ref,start,end) -> pd.Series`. Provide in-memory implementations backed by
  fixtures so the whole core runs with **no network/DB**.
- **Tests:** in-memory adapters satisfy the protocols and emit valid contracts (events DataFrame
  has the SRS columns; prices/odds are tz-aware UTC; odds ∈ [0,1]).
- **Done gate:** core e2e (T7) runs end-to-end on in-memory adapters.
- **Depends on:** T1.

## Task 9 — HttpPriceSource adapter (`ingest/`, FR-EVT support)
- **Files:** `event_reaction/ingest/http_price_source.py`, `tests/test_http_price_source.py`
- **Do:** Implement `PriceSource` by calling `stock-data-service`
  `GET /stocks/{symbol}/history` and returning a tz-aware UTC daily `pd.Series` — reuse the
  prediction-service HTTP pattern (`prediction_service.py:36-54`); **do not import
  `StockRepository`** (gap map §2, B8). Network mocked in tests.
- **Tests:** mocked httpx response → correct tz-aware UTC `pd.Series`, sorted, gaps handled;
  non-200 / empty payload raises `InsufficientDataError`.
- **Done gate:** adapter returns the contract under a mocked transport; no real network in tests.
- **Depends on:** T8.
- **Integration point:** `stock-data-service` `GET /stocks/{symbol}/history`.

## Task 10 — MySQL event store + repository (service side)
- **Files (new, under the service):**
  `services/event-reaction-service/app/models/domain.py` (SQLAlchemy `EventRecord`, table e.g.
  `event_reactions_events`), `app/repositories/event_repository.py` (implements `EventSource`,
  materialises the events DataFrame), `tests/test_event_repository.py`
- **Do:** Repository CRUD + `fetch` returning the events DataFrame contract. Stateful, like
  `decision-helper-service` (gap map §4). Tests run against SQLite/in-memory or a mocked session
  (offline).
- **Tests:** round-trip persist→fetch yields the SRS events columns with tz-aware UTC `ts_utc`;
  upsert dedup policy on `(kind, ts_utc, asset_scope)`.
- **Done gate:** repository satisfies `EventSource` offline.
- **Depends on:** T8.
- **Integration point:** MySQL system of record (`host.docker.internal:3306`).

## Task 11 — FastAPI service + gateway wiring (port 8012)
- **Files (new):** `services/event-reaction-service/app/{main.py,config.py}`,
  `app/api/{routes.py,schemas.py}`, `app/services/event_reaction_service.py`,
  `services/event-reaction-service/{Dockerfile,requirements.txt}`,
  `services/event-reaction-service/tests/test_routes.py`
- **Edits to existing infra (call-outs):**
  - `stock_microservices/docker-compose.yml` — **add** an `event-reaction-service` block
    (mirror chart-decomp `:777-810`): `expose: ["8012"]`, healthcheck, `networks`, and the 6
    Traefik labels with `PathPrefix(/stock_helper/api/v2/event-reaction)` and
    `loadbalancer.server.port=8012`.
  - (deferred) `stock_react_javascript/.../src/constants/api.js` — add `EVENT_REACTION_*`
    endpoint constants when the UI phase starts. **Not in this plan.**
- **Do:** Mount the router under `/stock_helper/api/v2/event-reaction` (idiom:
  `chart-decomp-service/app/main.py:101-105`). Endpoints: `POST /events`, `GET /events`,
  `POST /measure`, `POST /cross-section`, plus `/health{,/live,/ready}`, `/metrics`. Map library
  exceptions to HTTP via a `_handle` (like `chart-decomp-service/app/api/routes.py:64`):
  `InsufficientDataError`→422, `AlignmentError`/`LeakageError`→422/400, else 500. Wire
  `MySqlEventRepository` + `HttpPriceSource` into the service layer.
- **Tests:** FastAPI `TestClient` with mocked sources — `/health/live` 200 (unauthenticated,
  per repo convention); `POST /measure` returns a populated `EventReaction` JSON; an
  alignment error maps to 422.
- **Done gate:** service tests green; compose block validates (`docker compose config`).
- **Depends on:** T7, T9, T10.
- **Integration points:** Traefik gateway (new router, port 8012); MySQL; stock-data-service.

---

## Mandatory test checklist (must exist and pass before "done")

| Test | Task | Why |
|---|---|---|
| Injected jump is detected; calm series is not | T5 | jump test works |
| Known CAR recovered from an injected bump | T4 | abnormal-return math is correct |
| True exposure coefficient `γ1` recovered | T6 | cross-sectional regression is correct |
| Standardized surprise has the right sign/scale | T3 | surprise construction is correct |
| No-look-ahead: mutating post-event data does NOT change a surprise | T7 | EC1 leakage guard (the #1 trap) |
| Clustering: iid t-test over-rejects, robust route holds size | T6 | EC3 (the #2 trap) |
| Jump null-FPR ≈ nominal on surrogates | T5 | EC4 benchmark gating |

All assertions test **properties**, never the spec's illustrative magnitudes.

---

## Integration points & refactors (summary)

- **Reuse (import, don't fork):** `chart_decomp.estimate_volatility`,
  `RealizedVolCalculator`, `make_surrogate`/`random_walk_surrogates` (T1 dep; used in T5).
- **Reuse over HTTP:** `stock-data-service` `GET /stocks/{symbol}/history` via `HttpPriceSource`
  (T9) — no cross-service import of `StockRepository`.
- **New infra:** compose block + 6 Traefik labels + port 8012 (T11). chart-decomp is absent
  from `docker-compose.prod.yml`/`.test.yml`; mirror that scope (local compose only) unless told
  otherwise.
- **No edits to existing service code** are required. The only existing file touched is
  `docker-compose.yml` (additive). Frontend (`api.js`, report component) is **deferred** to a
  later UI phase (gap map §5).
- **Root `CLAUDE.md` is never modified;** module rules live in `event-reaction-lib/CLAUDE.md`
  (T0).

---

## Verification checklist (final, before declaring the module done)

1. **Full suite green:** `cd stock_microservices/event-reaction-lib && pytest tests/` passes;
   service tests pass.
2. **No I/O in stats stages:** `align/ surprise/ returns/ jumps/ cross_section/` import no
   `httpx`/`requests`/`sqlalchemy`/socket/clock — verify by grep and by the offline-test runs
   (NFR-1, §3.10).
3. **Public API matches the SRS §4.2:** `measure_event_reaction`, `make_surprise`,
   `abnormal_returns`, `jump_test_daily`, `cross_sectional_exposure`, `assert_no_leakage` exist
   with the documented signatures and are re-exported from `event_reaction/__init__.py`.
4. **All seven mandatory tests** above exist and pass.
5. **tz-aware UTC end-to-end:** every contract rejects naive datetimes; the no-leakage and
   clustering tests are present (the two domain-bug gates).
6. Update `ROADMAP.xlsx` (Feature Inventory + Sessions Log) per the repo workflow.

## Reminders
- One task at a time: failing test → pass → show output → STOP.
- Surprise is observed (consensus/futures/odds); `llm` deferred. Never model it from prices.
- Regress on the surprise, never the raw event (EC2).
- Commit after each green task.
