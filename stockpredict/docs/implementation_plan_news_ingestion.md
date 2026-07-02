# Implementation Plan — News & Event Ingestion + Company-News Notification

**Spec:** `docs/SRS_news_ingestion.md` (v1.0) — APPROVED.
**New service:** `stock_microservices/services/news-service/` (port 8013, DB `stock_news`)
**Test command:** `pytest services/news-service/tests -v` (run from repo root with PYTHONPATH,
or inside the container), matching the per-service unit-test convention.
**Format:** PR-sized tasks, dependency order, **one at a time**. Each task: write its
failing test(s) first, make them pass, show output, then **STOP**. Do not start the next task
without being asked. Commit after each green task. Update `ROADMAP.xlsx` (Feature Inventory +
Sessions Log) as tasks land.

> **Discipline (from the SRS):** feeds/APIs only — **no HTML scraping** (EC-N1). Dedup by
> `news_id`, idempotent ingestion (EC-N2). Raw text/`raw_json` immutable (EC-N3). Reuse the
> notification stack (EC-N4) and the ai-insights classifier (EC-N5) — don't fork either.
> tz-aware UTC everywhere (EC-N6). Log-and-continue resilience (EC-N7). Notify good/bad only
> (EC-N8). Secrets via env (EC-N9). User fan-out stays in portfolio-service (EC-N10).

---

## SEQUENCING OVERVIEW

```
SHARED FOUNDATION
N1  scaffold service          FastAPI skeleton + config + health + metrics + package layout
N2  news_events store         SQLAlchemy NewsEvent + repository + ensure_schema + dedup (news_id)

STREAM B — company good/bad news + notifications  (BUILT FIRST)
N3  watch-set adapter         ingest/watch_source.py + additive read endpoints on portfolio & helper
N4  company-news adapter       ingest/company_source.py -> stock-data-service, NewsItem normalize
N5  classifier adapter         ingest/classifier.py -> ai-insights NewsAnalysis, closed vocab
N6  company poller + scheduler services/company_poller.py + notifier.py + scheduler.py (emit news.company)
N7  portfolio consumer          NotificationType.news_company + news.company consumer + email fan-out
N8  read API                    GET /news, GET /news/{id}, POST /ingest, POST /poll/{stream}
N9  compose/Traefik wiring       port 8013, DB stock_news, 6 labels; register consumer in portfolio
N10 frontend                     render news_company notifications in the React notification UI

STREAM A — macro/global events for ML + event-reaction bridge  (BUILT SECOND)
N11 macro feed adapters          ingest/macro_feeds.py (RSS/JSON registry) + tagging
N12 macro poller                 services/macro_poller.py -> tag -> store
N13 event-reaction bridge        ingest/event_bridge.py -> POST /events (idempotent, whitelist)

CLOSE-OUT
N14 docs + roadmap               ROADMAP.xlsx, MEMORY.md, end-to-end smoke
```

N1–N2 are the shared foundation. Stream B (N3–N10) delivers the visible win first. Stream A
(N11–N13) adds the ML corpus + bridge. Each task is independently shippable.

---

# SHARED FOUNDATION

## Task N1 — Scaffold the `news-service`
- **Files (new), under `stock_microservices/services/news-service/`:**
  - `app/main.py` — FastAPI app; lifespan creates the engine, calls `repo.ensure_schema()`
    (filled in N2), and starts/stops the scheduler (filled in N6/N12). `/health{,/live,/ready}`
    (unauthenticated live), `/metrics`. Router mounted under `/stock_helper/api/v2/news`.
  - `app/config.py` — pydantic-settings: `DATABASE_URL` (default sqlite, compose supplies
    `stock_news` MySQL), upstream URLs (`STOCK_DATA_SERVICE_URL`, `AI_INSIGHTS_SERVICE_URL`,
    `PORTFOLIO_SERVICE_URL`, `DECISION_HELPER_SERVICE_URL`, `EVENT_REACTION_SERVICE_URL`),
    RabbitMQ settings, toggles (`enable_company=true`, `enable_macro=false`,
    `enable_bridge=false`, `enable_email=false`), intervals, feed registry path, HTTP timeout
    (NFR-N5, EC-N9).
  - `app/exceptions.py` — `NewsIngestError`, `SourceUnavailableError`, `ClassificationError`
    (NFR-N3).
  - package skeleton: `app/{api,models,repositories,ingest,services}/__init__.py`.
  - `requirements.txt`, `Dockerfile` (copy `stock-common`, `pip install -e`, mirror an existing
    service Dockerfile).
  - `tests/test_health.py`.
- **Tests:** app imports; `GET /health/live` → 200 unauthenticated; `config` reads env with the
  documented defaults.
- **Done gate:** service boots under `TestClient`; health green.
- **Depends on:** none.

## Task N2 — `news_events` store + repository (FR-NEWS-STORE, FR-NEWS-DEDUP, EC-N2, EC-N3)
- **Files (new):** `app/models/domain.py` (`NewsEvent`, table `news_events` per SRS §4.1),
  `app/models/news_item.py` (`NewsItem` dataclass + `news_id()` derivation per §4.2),
  `app/repositories/news_repository.py` (`ensure_schema`, `upsert`, `exists`, `list_new`,
  `mark_classified`, `mark_notified`, `mark_bridged`, query helpers), `tests/test_repository.py`.
- **Do:** `news_id = stable_hash(source, guid|url|symbol+title+ts_date)` — pure, no clock/random
  (NFR-N2). `upsert` is a no-op on existing `news_id`. Raw fields immutable after insert;
  `mark_*` only touch stamps/classification columns (EC-N3).
- **Tests (MANDATORY — dedup):** identical source entry → identical `news_id` across runs;
  second `upsert` creates no duplicate row and reports "already seen"; different sources +
  same title → different ids; `mark_classified` leaves `title/body/raw_json` byte-identical
  (immutability, EC-N3). Runs on SQLite in-memory.
- **Done gate:** dedup + immutability tests green.
- **Depends on:** N1.

---

# STREAM B — COMPANY GOOD/BAD NEWS (BUILT FIRST)

## Task N3 — Watched-symbol set (FR-NEWS-WATCH, EC-N7, EC-N10)
- **Files (new):** `app/ingest/watch_source.py`, `tests/test_watch_source.py`.
  **Additive endpoints on existing services:**
  - `portfolio-service` — `GET /portfolio/watched-symbols` → `["ACB","FPT",…]` (`DISTINCT symbol`
    from `portfolio_holdings`, owned **and** `is_watchlist_only`). New route + repo method; no
    schema change.
  - `decision-helper-service` — `GET /helper/watched-tickers` → `[…]` (`DISTINCT ticker` from
    active `helper_watchlists`). New route + repo method.
- **Do:** `watch_source.resolve()` HTTP-fetches both and returns the **union** (uppercased,
  de-duped). If one upstream is down, log and use the other (EC-N7). Never enumerate users
  (EC-N10).
- **Tests:** mocked httpx → union of both sets; one upstream 5xx → still returns the other's
  symbols, error counted; empty union handled.
- **Done gate:** union + resilience tests green; both new endpoints return distinct symbols
  (per-service unit test).
- **Depends on:** N1.

## Task N4 — Company-news source adapter (FR-NEWS-COMPANY, EC-N1, EC-N3, EC-N6)
- **Files (new):** `app/ingest/company_source.py`, `tests/test_company_source.py`.
- **Do:** `fetch(symbol) -> list[NewsItem]` calls `stock-data-service`
  `GET /companies/{symbol}/news` (no vnstock import — EC-N1), normalizing each entry to a
  `NewsItem` with `stream="company"`, `symbol`, tz-aware UTC `ts_utc` (convert source-local —
  EC-N6), verbatim `raw_json` (EC-N3), `lang` best-effort. Timeout + retry via `stock-common`
  (EC-N7).
- **Tests:** mocked payload → `NewsItem`s with tz-aware UTC `ts_utc` and `raw_json` preserved
  byte-for-byte; a naive source time is converted, not stored naive; non-200/empty →
  `SourceUnavailableError` (caught by the poller later).
- **Done gate:** normalization + tz + raw-preservation tests green.
- **Depends on:** N2.

## Task N5 — Classifier adapter (FR-NEWS-CLASSIFY, EC-N5, EC-N7, EC-N11)
- **Files (new):** `app/ingest/classifier.py`, `tests/test_classifier.py`.
- **Do:** `classify(item) -> (sentiment, category, score)` POSTs title+body+lang to
  `ai-insights-service` NewsAnalysis (reuse its `NewsAnalysisRequest`/`Response`; no model here
  — EC-N5) and maps the response into the **closed** vocab (SRS Appendix A):
  `sentiment ∈ {good,bad,neutral}`, company `category`, `score ∈ [-1,1]`. On error/timeout →
  raise `ClassificationError` (poller stores `sentiment=NULL`/`category="unclassified"` and
  retries — EC-N7).
- **Tests:** a good/bad/neutral ai-insights response each maps correctly; an unknown label →
  `neutral`+`other`; classifier 5xx → `ClassificationError`.
- **Done gate:** mapping + error tests green.
- **Depends on:** N2.

## Task N6 — Company poller + notifier + scheduler (FR-NEWS-COMPANY, FR-NEWS-NOTIFY emit side, FR-NEWS-SCHED, EC-N2, EC-N7, EC-N8)
- **Files (new):** `app/services/company_poller.py`, `app/services/notifier.py`,
  `app/services/scheduler.py`, `tests/test_company_poller.py`. Wire scheduler start/stop into
  `app/main.py` lifespan (NFR-N6).
- **Do:** `company_poller.tick()` = resolve (N3) → for each symbol fetch (N4) → dedup via
  `repo.exists` (N2) → classify new (N5) → `repo.upsert` (store all: good/bad/neutral) → for
  good/bad, `notifier.emit_news_company(item)` (RabbitMQ `news.company` via `stock-common`
  EventBus, SRS §4.3, **no user identity** — EC-N10) then `repo.mark_notified`. `neutral` never
  emits (EC-N8). Per-symbol/per-source failures logged and skipped; tick never crashes (EC-N7).
  Scheduler runs `tick` every `company_poll_interval`, non-overlapping (NFR-N6).
- **Tests (MANDATORY — pipeline + idempotency):**
  - Mocked watch `{ACB,FPT}`, mocked news, classifier → one `good` + one `neutral`: **both
    stored; exactly one `news.company` emitted (the good); zero for neutral** (EC-N8).
  - **Re-run the tick over identical news → zero new stores, zero new emits** (EC-N2 — the
    idempotency gate).
  - Classifier raises for one symbol → other symbol still stored, tick survives, error counter
    increments (EC-N7).
- **Done gate:** the three tests green (EventBus mocked).
- **Depends on:** N3, N4, N5.

## Task N7 — Portfolio-service consumer + notification type + email fan-out (FR-NEWS-NOTIFY consume side, EC-N4, EC-N9, EC-N10)
- **Files (edit, in `portfolio-service`):**
  - `app/models/domain.py` — add `NotificationType.news_company` to the enum.
  - `app/services/news_event_handler.py` (new) — subscribe to `news.company`; resolve users who
    own or watch `symbol` (holdings ∪ watchlist, from `portfolio_holdings`); per user create a
    `notifications` row (`type=news_company`, `source_event_id=news_id`, title/body from the
    event) via the existing notification path (dedup reused); if `enable_email`, enqueue email
    via the existing `email_consumer` (EC-N9 — no-op/log if SMTP unset).
  - Register the handler alongside `alert_event_handler` in the service startup.
  - `tests/test_news_event_handler.py`.
- **Do:** reuse existing best-effort, log-and-continue consumer machinery (EC-N4, EC-N7). Fan-out
  and user resolution live **here** (EC-N10).
- **Tests (MANDATORY — fan-out + dedup):** a `news.company` for `FPT` → one `notifications` row
  per user owning/watching `FPT`, `type=news_company`, `source_event_id=news_id`; **re-deliver
  same `news_id` → no duplicate per user**; email invoked per user only when `enable_email`.
- **Done gate:** fan-out + dedup tests green.
- **Depends on:** N6 (event contract).

## Task N8 — Read API (FR-NEWS-API)
- **Files (new):** `app/api/routes.py`, `app/api/schemas.py`, `tests/test_routes.py`.
- **Do:** `GET /news` (filters `stream,symbol,category,sentiment,since,until` + pagination),
  `GET /news/{news_id}` (incl. `raw_json`), `POST /ingest` (manual `NewsItem` →
  dedup→classify→store→notify), `POST /poll/{stream}` (trigger a tick). Map exceptions to HTTP
  via a `_handle` (`SourceUnavailableError`/`ClassificationError`→502, validation→422, else 500).
- **Tests:** filtered list returns only matches; `/news/{id}` includes `raw_json`; `/ingest`
  round-trips through the pipeline (mocked classifier/bus); `/health/live` 200 unauthenticated.
- **Done gate:** API tests green.
- **Depends on:** N2, N6.

## Task N9 — Compose / Traefik wiring + DB (port 8013, `stock_news`)
- **Files (edit):**
  - `stock_microservices/docker-compose.yml` — add a `news-service` block (mirror the
    event-reaction block `:813-849`): `expose: ["8013"]`, healthcheck, `networks`, env for all
    upstream URLs + RabbitMQ + `DATABASE_URL` (`stock_news`), and the 6 Traefik labels with
    `PathPrefix(/stock_helper/api/v2/news)` and `loadbalancer.server.port=8013`. Ensure the
    `news_event_handler` runs in `portfolio-service` (env toggle if needed).
  - `stock_microservices/mysql/init/*` — create DB `stock_news` (follow existing per-service DB
    creation).
- **Tests / done gate:** `docker compose config` validates; `./scripts/deploy.sh --health`
  shows `news-service` healthy; `GET /stock_helper/api/v2/news/health/live` via the gateway 200.
- **Depends on:** N8, N7.

## Task N10 — Frontend: render `news_company` notifications
- **Files (edit, React app):** the notification list/rendering components + any
  `NotificationType` mapping (icons/labels), and `src/constants/api.js` if a `NEWS_*` endpoint
  constant is needed for a "news" browse view. Follow the services/`httpClient` pattern — no
  direct axios in components (root `CLAUDE.md`).
- **Do:** render `news_company` notifications (title, symbol, good/bad badge, link) in the
  existing notification UI so ACB/FPT alerts show in-app. (Optional: a simple browse view over
  `GET /news`.) Rebuild the frontend Docker image to see it on the running screen
  (`project_frontend_docker_deploy`).
- **Tests:** component test rendering a `news_company` notification; manual smoke.
- **Done gate:** notifications render; image rebuilt.
- **Depends on:** N7, N9.

---

# STREAM A — MACRO/GLOBAL EVENTS (BUILT SECOND)

## Task N11 — Macro feed adapters + tagging (FR-NEWS-MACRO, EC-N1)
- **Files (new):** `app/ingest/macro_feeds.py`, a feed-registry config (SRS Appendix B),
  `tests/test_macro_feeds.py`. Add `feedparser` to `requirements.txt`.
- **Do:** registry-driven readers (`rss`|`json`) → `NewsItem`s with `stream="macro"`,
  `symbol=NULL`, tz-aware UTC `ts_utc` (EC-N6), verbatim `raw_json` (EC-N3). Rule/keyword
  tagging → macro `category` (`monetary,tariff,tax,trade,geopolitical,war,other`). **No
  scraping** (EC-N1). Keyed sources read keys from env (EC-N9).
- **Tests:** a saved RSS fixture → normalized items with correct category by rule; a JSON-API
  fixture likewise; naive feed time → tz-aware UTC.
- **Done gate:** normalization + tagging tests green (offline fixtures).
- **Depends on:** N2.

## Task N12 — Macro poller (FR-NEWS-MACRO, EC-N2, EC-N7)
- **Files (new):** `app/services/macro_poller.py`, `tests/test_macro_poller.py`. Wire into the
  scheduler behind `enable_macro`.
- **Do:** `tick()` = read each registry source (N11) → dedup (N2) → `repo.upsert`. No
  notification (Stream A is store + bridge). Per-source failure logged/skipped (EC-N7).
- **Tests:** mocked feeds → new items stored `stream=macro`; re-run → zero new (EC-N2); one
  source down → others still stored.
- **Done gate:** store + idempotency tests green.
- **Depends on:** N11.

## Task N13 — Event-reaction bridge (FR-NEWS-BRIDGE, EC-N2, EC-N6)
- **Files (new):** `app/ingest/event_bridge.py`, `tests/test_event_bridge.py`. Wire into the
  macro poller behind `enable_bridge`.
- **Do:** for a macro item recognized as a **numeric release** with parseable `actual` +
  pre-event `consensus` and a whitelisted category (Appendix A: `monetary→rate_decision`,
  `tariff→tariff`, `tax→tax`), POST `event-reaction-service` `POST /events` with
  `{event_id: news_id, ts_utc, kind, actual, consensus, asset_scope}`; `mark_bridged`.
  `event_id = news_id` makes re-posts idempotent (event store upserts by `event_id`). Free-text
  items post nothing.
- **Tests:** a numeric-release fixture posts exactly one event with `event_id == news_id`
  (mocked event-reaction); re-run posts the same `event_id`; a free-text geopolitical item posts
  nothing.
- **Done gate:** bridge + idempotency tests green.
- **Depends on:** N12; integrates event-reaction `POST /events`.

---

# CLOSE-OUT

## Task N14 — Docs, roadmap, smoke
- **Do:** update `ROADMAP.xlsx` (Feature Inventory: add "News Ingestion" rows; Sessions Log:
  append what landed + where left off); add a `MEMORY.md` pointer for the news subsystem; run an
  end-to-end smoke: watched `{ACB,FPT}` → a planted "good" company item flows to an in-app
  notification; a macro numeric release bridges to event-reaction.
- **Done gate:** roadmap current; smoke passes.
- **Depends on:** all.

---

## Mandatory test checklist (must exist and pass before "done")

| Test | Task | Why |
|---|---|---|
| Same source entry → same `news_id`; re-`upsert` no-op | N2 | dedup foundation (EC-N2) |
| Raw `title/body/raw_json` immutable after `mark_*` | N2 | ML corpus integrity (EC-N3) |
| Company poller: good emits one event, neutral emits none | N6 | notify good/bad only (EC-N8) |
| Re-run company tick → zero new stores/emits | N6 | idempotency (EC-N2 — the #1 trap) |
| `news.company` fan-out: one notif per watching user, deduped | N7 | delivery correctness (EC-N4, EC-N10) |
| Bridge posts `event_id == news_id`, idempotent; free-text posts nothing | N13 | bridge correctness (FR-NEWS-BRIDGE) |
| Poller survives a down upstream (watch/source/classifier) | N3/N6 | resilience (EC-N7) |

---

## Integration points & edits (summary)

- **Reuse (call over HTTP / event bus, don't fork):** `stock-data-service`
  `/companies/{symbol}/news` (N4); `ai-insights-service` NewsAnalysis (N5); portfolio-service
  notification/email stack via `news.company` (N6/N7); event-reaction `POST /events` (N13);
  decision-helper scheduler idiom (N6).
- **Additive edits to existing services (no schema change except an enum value):**
  portfolio-service gains `GET /portfolio/watched-symbols`, a `news.company` consumer, and
  `NotificationType.news_company` (N3, N7); decision-helper gains `GET /helper/watched-tickers`
  (N3).
- **New infra:** `news-service` (port 8013), DB `stock_news`, compose block + 6 Traefik labels,
  `feedparser` dep (N9, N11).
- **Frontend:** render the new notification type; rebuild the image (N10;
  `project_frontend_docker_deploy`).
- **Root `CLAUDE.md` untouched; no nested module `CLAUDE.md`** (this is a straightforward
  ingestion service — SRS §6).

---

## Reminders
- One task at a time: failing test → pass → show output → STOP. Commit after each green task.
- Feeds/APIs only — never scrape (EC-N1). Two dedup layers — never emit before the store
  confirms "new" (EC-N2, D1). Raw corpus immutable (EC-N3). Notify good/bad only (EC-N8).
- Reuse the classifier and the notification stack; user fan-out stays in portfolio-service.
- Email is behind `enable_email` and needs portfolio-service SMTP; in-app works regardless.
