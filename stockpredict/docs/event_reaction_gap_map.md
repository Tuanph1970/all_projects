# Event-Reaction Subsystem — Phase 0 Gap Map

**Purpose.** Resolve every orientation item for the planned *Event-Reaction* subsystem
(measuring how asset prices react to discrete, timestamped events via the **surprise**,
never the raw event) to a REAL path/function in this repo, or mark it **new**. This is a
survey only — no design, no code. It is the handoff into Phase 1 (design).

**Surveyed:** HEAD, branch `main`, 2026-06-30.
**Backend root:** `stock_microservices/`
**Frontend root:** `stock_react_javascript/stock-react-app/`
**Closest precedent in-repo:** the chart-decomposition / pattern subsystem, split across
the library `stock_microservices/chart-decomp-lib/` (package `chart_decomp`) and the thin
FastAPI wrapper `stock_microservices/services/chart-decomp-service/`. This subsystem is
the template to mirror.

---

## 1. Package / service layout, test location, and the test command

### Service layout (the convention to follow)
`stock_microservices/services/` holds 11 services (`auth`, `stock-data`, `portfolio`,
`prediction`, `analysis`, `ai-insights`, `chatbot`, `journal`, `knowledge-qa`,
`decision-helper`, `chart-decomp`). Standard internal shape (e.g. `analysis-service`):

```
app/
  config.py                # get_settings(); pydantic-settings
  main.py                  # FastAPI app, lifespan, /health{,/live,/ready}, /metrics
  api/routes.py            # APIRouter, mounted under /stock_helper/api/v2/<area>
  api/schemas.py           # pydantic request/response
  models/  (domain.py, schemas.py)   # only if stateful
  repositories/            # only if stateful (DB access)
  services/                # business logic
tests/  (conftest.py, test_*.py)     # per-service tests; chart-decomp-service has NONE
```

`chart-decomp-service` is the **stateless** variant: no `models/`, no `repositories/`,
no `tests/` — `main.py` only smoke-tests that the `chart_decomp` library imported
(`services/chart-decomp-service/app/main.py:41-57`). All real logic + tests live in the
companion library.

### The library precedent (clean architecture)
`stock_microservices/chart-decomp-lib/` — installable package `chart-decomp`
(`chart-decomp-lib/pyproject.toml`), layered domain / application / factories /
infrastructure. Tests live in `chart-decomp-lib/tests/` (≈30 files: `test_decomp.py`,
`test_run_pattern_pipeline.py`, `test_null_fpr.py`, `test_causality.py`, …). This split —
**pure-compute library + thin stateless service** — is the model the event-reaction
subsystem should imitate.

### Where tests live (three places)
| Scope | Path | Run via |
|---|---|---|
| Repo-wide integration/e2e | `stock_microservices/tests/` | `scripts/run-tests.sh`, `quick-test.sh`, `test-service.sh` |
| Per-service unit | `services/<name>/tests/` | `pytest services/<name>/tests -v` |
| chart-decomp library | `chart-decomp-lib/tests/` | direct `pytest` (NOT covered by any script) |

Root `stock_microservices/pytest.ini`: `asyncio_mode=auto`, `testpaths=tests`,
markers `integration, e2e, performance, security, slow, auth, database`,
`addopts=-v --tb=short --strict-markers -ra`, `timeout=30`. Note `testpaths=tests`
scopes the repo runner to the repo-wide `tests/` dir only — **the chart-decomp library is
tested by pointing pytest at its own dir**, and `chart-decomp-lib` has no `pytest.ini`
of its own (only a `tests/conftest.py` with numpy fixtures: `rng`, `brownian`,
`ar1_series`, `sinusoidal`).

### Exact test command (the precedent the new lib will copy)
```bash
pip install -e "stock_microservices/chart-decomp-lib[dev]"   # one-time; brings pytest, fbm
cd stock_microservices/chart-decomp-lib && pytest tests/
```
`scripts/run-tests.sh` / `quick-test.sh` / `test-service.sh` do **not** target this kind of
library — they only run `tests/integration`. The new module follows the chart-decomp
pattern: its own `tests/` dir run with a direct `pytest`.

---

## 2. Price / OHLC time-series loading — can the event module reuse it?

**Partial reuse, over HTTP — there is NO shared price loader.** The OHLC loader is
**service-local to `stock-data-service`**, not a `stock-common` helper.

| Symbol | File | Signature |
|---|---|---|
| `StockRepository.get_historical_prices` | `services/stock-data-service/app/repositories/stock_repository.py:123` | `(company_id, start_date=None, end_date=None, limit=1000) -> List[StockPrice]` |
| `StockRepository.get_company_by_symbol` | `…/stock_repository.py:58` | symbol → company resolution |
| `StockService.get_historical_data` | `services/stock-data-service/app/services/stock_service.py:942` | `(symbol, start_date=None, end_date=None) -> HistoricalDataResponse`; DB first, vnstock fallback at `:997` |
| `StockPrice` model | `services/stock-data-service/app/models/domain.py:90` | table `stock_prices`, OHLCV keyed by `company_id`+`date` |
| HTTP route | `services/stock-data-service/app/api/routes.py:148` | `GET /stocks/{symbol}/history` |

`stock-common/stock_common/database/` has only a generic `BaseRepository[T]`
(`database/repository.py:22`) — no `StockPrice`, no OHLC query. `StockRepository` is not
importable across service boundaries.

**Reuse path for the event module (precedent already exists):** prediction-service does
not import a loader — it fetches prices over HTTP. See
`services/prediction-service/app/services/prediction_service.py:36`
`_fetch_historical_data(symbol, days=365)` → `httpx` GET
`STOCK_DATA_SERVICE_URL/.../stocks/{symbol}/history` (`:42-54`) → sorted DataFrame;
`_get_current_price` (`:59`) hits `/quote`. **The event-reaction module should source OHLC
the same way: an HTTP call to stock-data-service's `/history`.** (chart-decomp-lib never
loads prices — its endpoints take the raw `series` array in the request body.)

---

## 3. Returns / log-returns / stats helpers

**Scattered; no shared stats module in `stock-common`.** Two reusable clusters:

**(a) Inline in prediction-service** (`prediction_service.py:74-129`, not exposed as
functions — they live inside `_prepare_features` over a DataFrame):
- `df["returns"] = df["close"].pct_change()` (`:79`)
- `df["log_returns"] = np.log(df["close"]/df["close"].shift(1))` (`:80`)
- rolling-std `volatility_20/5` (`:88-89`); SMA/EMA, RSI, MACD, Bollinger, lags (`:83-117`)

**(b) Reusable utilities in `chart-decomp-lib`** (importable from `chart_decomp`):
| Symbol | File | What |
|---|---|---|
| `RealizedVolCalculator.compute` | `chart_decomp/infrastructure/realized_vol/rv_calculator.py:23` | `(returns, annualization=252) -> (rv, vol, log_rv)`; facades `chart_decomp.realized_variance`/`realized_vol` |
| `estimate_volatility` | `chart_decomp/infrastructure/validation/surrogates.py:64` | `std(diff(x))` per-step vol |
| `make_surrogate` | `…/surrogates.py:74` | `(returns, method='shuffle'\|'gaussian')` surrogate path via cumsum |
| `random_walk_surrogates` | `…/surrogates.py:19` | RW null paths |
| `PatternDetectorBase.{linfit,line_at,rel_diff,within_tol,series_range,clamp01}` | `chart_decomp/infrastructure/patterns/base.py:31-69` | least-squares slope, symmetric rel-diff, tolerance, range, clamp |
| Hurst (returns-based) | `chart_decomp/infrastructure/long_memory/wavelet_hurst.py` (facade `chart_decomp.hurst_wavelet`) | long-memory on returns |

**No general z-score helper exists** anywhere (pattern code uses scale-robust `rel_diff`
instead of z-scores). A surprise/standardization helper for event-reaction would be **new**
— but `estimate_volatility` and the surrogate/null tooling are directly reusable for the
benchmark/null-FPR side.

---

## 4. API pipeline / registry, and module-vs-service recommendation

### The dispatch/registry idiom (to imitate, not necessarily share)
`chart_decomp/factories/pattern_detector_factory.py` is a Registry + Composite:
- `PatternDetectorRegistry` (`:22`) — `name -> detector` dict; `register` (`:33`),
  `detect(skeleton, x, detectors="all", params)` (`:50`) runs/aggregates/sorts, assigns
  `detection_id`.
- module-level `default_registry` (`:94`) + `register_detector` (`:97`) /
  `detect_patterns` (`:102`) facade; built-ins registered at import (`:133-145`).
- Sibling factories follow the same idiom: `DecomposerFactory` (`decomposer_factory.py:43`)
  and `forecaster_factory.py`.
- Orchestrator: `RunPatternPipelineUseCase.execute(x, …)`
  (`chart_decomp/application/run_pattern_pipeline_usecase.py:69`) = denoise → swings →
  `detect_patterns` → right-edge confirm → null-FPR. **It takes a raw 1-D float array — no
  dates, no event store, no persistence.**

### Gateway routing (what a service needs)
Traefik routes one router per service under `/stock_helper/api/v2/<area>`
(`docker-compose.yml`). chart-decomp's block (`:777-810`): `expose: ["8011"]`, healthcheck,
and 6 labels (`:804-810`) — `traefik.enable`, `traefik.project=stock`, router `rule=
PathPrefix(/stock_helper/api/v2/chart-decomp)`, `entrypoints=web`, `priority=10`,
`loadbalancer.server.port=8011`. Ports in use: 8001/8004/8005/8010/8011 → **next free 8012**.
chart-decomp is absent from `docker-compose.prod.yml`/`.test.yml` (incomplete coverage — a
decision point for any new service).

### Recommendation: a NEW library + NEW thin service (mirror chart-decomp) — NOT a module inside chart-decomp
Deciding facts:
- chart-decomp is **stateless, DB-less, array-only**. Its library has no time/date types,
  no event calendar, no persistence. An event-reaction subsystem is inherently
  **timestamped and stateful**: it needs an event store (event + expected vs. actual →
  *surprise*), joins to OHLC, and reaction windows around event timestamps. Forcing that
  into the stateless univariate-array service is a poor fit.
- The registry's open/closed benefit only applies to detectors expressible as
  `PatternDetectorBase`-style plugins over a swing skeleton — event-reaction measurement
  is not that shape.
- A new module inside chart-decomp = edit ~3 files (`schemas.py`, `decomp_service.py`,
  `routes.py`) + a lib subpackage, zero infra. Cheap, but wrong altitude.
- A new service = a `services/<name>-service/` dir (Dockerfile with the two stock-common
  touchpoints: editable-install `Dockerfile:12-13` + `assert_no_placeholder_secrets` in
  `config.py:40-42`), `requirements.txt`, full `app/` tree, a compose block with the 6
  Traefik labels (and ideally prod/test/ha compose entries), and a new port (8012). More
  boilerplate, but matches the one-router-per-domain topology and allows a DB/event store
  like `decision-helper-service` (`app/models/`, `app/repositories/`, `app/messaging/`).

**Therefore:** create `event-reaction-lib/` (pure-compute: surprise construction, reaction
measurement around an event timestamp, benchmarks/null) + `services/event-reaction-service/`
(stateful: event store in MySQL, OHLC via HTTP to stock-data-service §2). **Reuse**
`chart-decomp-lib`'s `estimate_volatility`, `make_surrogate`/`random_walk_surrogates`, and
`RealizedVolCalculator` for the returns/volatility and null-benchmark machinery — import the
package; do not duplicate. The nested module `CLAUDE.md` (added later, per ground rules)
lives in the new lib/service dir.

---

## 5. Frontend — is the Detection Report table reusable for an event-reaction report?

**Found, but low reusability — expect a sibling component.**
- The "Detection Report" table is bespoke inline JSX inside `PatternTab`,
  `stock_react_javascript/stock-react-app/src/components/Pages/ChartDecomp/index.js:945`.
  Single-scale table at `index.js:1358-1408`; multi-scale variant via `renderMulti()` from
  `index.js:1087`.
- It takes **no props** and reads the local `dets` array (`index.js:1168`, from
  `result.detections`); columns are a fixed i18n key list (`index.js:1367`:
  `col_pattern,col_start,col_end,col_score,col_confirmed,col_null_pct`) with
  detection-specific cell logic (`d.pattern`, `(d.score*100)%`, `✓`/`Edge?`, noteworthy `★`,
  `PATTERN_COLORS`). It does **not** use the generic `components/ui/DataTable.js`.
- Data flow: `PatternTab.run()` (`index.js:962-982`) → `services/chartDecompService.js`
  (`patternPipeline` :57 / `patternMultiScale` :77) → endpoints in `constants/api.js`
  (`CHART_DECOMP_PAT_PIPELINE` :397, `CHART_DECOMP_PAT_MULTISCALE` :400).

**Assessment:** the card/styling shell is copy-pasteable, but columns/rows are not
parameterized. Reusing it for an "events vs. price-reaction" report means **building a new
sibling component** (matching the existing per-tab pattern: each tab owns its table), or
optionally refactoring toward `ui/DataTable.js` for shared styling. Mark the event-reaction
report UI **new**. (Frontend is out of scope until a later phase; recorded here only to
answer the report question.)

---

## Summary table

| Item | Resolution |
|---|---|
| Service/lib layout | Mirror chart-decomp: `chart-decomp-lib` + `chart-decomp-service` |
| Test location | New `event-reaction-lib/tests/` (like `chart-decomp-lib/tests/`) |
| Test command | `cd stock_microservices/event-reaction-lib && pytest tests/` |
| OHLC loading | Reuse over HTTP: stock-data-service `GET /stocks/{symbol}/history` (no shared loader) |
| Returns/log-returns | Inline in prediction-service; reusable vol/surrogate utils in chart-decomp-lib |
| Stats helpers | `estimate_volatility`, `make_surrogate`, `RealizedVolCalculator` reusable; z-score/surprise = **new** |
| API registry/pipeline | `PatternDetectorRegistry` + `RunPatternPipelineUseCase` are the *pattern* to imitate, not share |
| Module vs service | **New microservice + new library** (event-reaction is stateful/timestamped; chart-decomp is stateless/array-only) |
| Frontend report table | `PatternTab` Detection Report is bespoke → build a **new sibling component** |

```
MODULE_DIR = stock_microservices/event-reaction-lib   (companion service: stock_microservices/services/event-reaction-service)
TEST_CMD   = cd stock_microservices/event-reaction-lib && pytest tests/
```
