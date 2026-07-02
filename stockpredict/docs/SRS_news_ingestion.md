# Software Requirements Specification

## News & Event Ingestion + Company-News Notification System

**Document version:** 1.0
**Date:** 2026-07-02
**Status:** Draft (Phase 1 — Design)
**Sibling docs:** `SRS_event_reaction.md` (the module this bridges into),
`docs/implementation_plan_news_ingestion.md` (the companion plan).

---

## 1. Introduction

### 1.1 Purpose

This document specifies a **news & event ingestion subsystem** with two independent
ingestion streams that share one persistent corpus:

- **Stream A — Macro/global events.** Poll structured feeds/APIs for economic and
  political events (monetary policy, tariffs, tax, geopolitical, war), tag and persist
  them as an immutable corpus for future machine-learning use, and — where a release
  carries a numeric outcome and consensus — **bridge** it into the existing
  event-reaction event store (`POST /events`) so it becomes a *measurable surprise*.
- **Stream B — Company good/bad news.** Poll per-ticker company news for the symbols a
  user **owns or watches** (e.g. ACB, FPT), classify each item as **good / bad / neutral**
  with a category (new product, new technology, management/policy change, regulatory…),
  persist it, and **notify** the affected users through the platform's existing
  in-app + email notification stack.

The founding principle differs per stream. Stream A exists to *record* events losslessly
for later modelling; nothing is discarded. Stream B exists to *alert* a user to material
news about assets they care about, cheaply and without duplicates.

### 1.2 Scope

The system **shall**:

- Maintain a single **`news_events` store** (FR-NEWS-STORE) holding both streams'
  items with raw title/body and the full source payload (`raw_json`) preserved for ML.
- Resolve the **watched-symbol set** = union of owned/watched tickers across
  `portfolio_holdings` (owned + watchlist) and `helper_watchlists`, obtained over HTTP
  from the owning services (FR-NEWS-WATCH).
- Poll **company news per watched symbol** from `stock-data-service`
  `GET /companies/{symbol}/news` (which wraps vnstock) — no scraping (FR-NEWS-COMPANY).
- **Classify** each new item via the existing `ai-insights-service` LLM path
  (`NewsAnalysisRequest`/`Response`) into `sentiment ∈ {good,bad,neutral}` + `category`
  + `sentiment_score` (FR-NEWS-CLASSIFY).
- **Deduplicate** items by a stable `news_id` so re-polls never re-store or re-notify
  (FR-NEWS-DEDUP).
- **Notify** users of `good`/`bad` company news (never `neutral`) via the existing
  `portfolio-service` notification stack — **in-app** (`notifications` table) **and email**
  (FR-NEWS-NOTIFY), fanned out per user by that service (which owns the user↔ticker map).
- Poll **macro feeds/APIs** on a schedule, tag each item into a macro `category`, and
  persist it (FR-NEWS-MACRO).
- **Bridge** macro releases that carry a numeric `actual`/`consensus` into the
  event-reaction service's `POST /events` (FR-NEWS-BRIDGE).
- Expose **read endpoints** for the stored corpus (FR-NEWS-API) and run on a scheduler
  modelled on `decision-helper-service` (FR-NEWS-SCHED).

The system **shall not**:

- **Scrape arbitrary HTML sites.** Only structured RSS/APIs are used (EC-N1). A site
  without a feed/API is out of scope until a feed is available.
- **Re-implement classification.** It calls `ai-insights-service`; it does not host its
  own LLM (EC-N5).
- **Re-implement notifications/email/push.** It emits a RabbitMQ event that the existing
  `portfolio-service` consumers act on (EC-N4).
- **Own the user↔ticker mapping.** `portfolio-service` owns it and performs the per-user
  fan-out; this service is user-agnostic at the ingestion layer (§2.1, EC-N10).
- Notify on macro/global events in v1 — Stream A is **store + bridge only** (the user
  requested notifications for company news only).
- Forecast, trade, or recommend. It records and alerts; it does not act.

### 1.3 Definitions, Acronyms, Abbreviations

| Term | Definition |
|---|---|
| Stream A / macro | Global economic & political events from public feeds; store + bridge, no notify |
| Stream B / company | Per-ticker company news for watched symbols; classify + notify |
| `news_events` | The shared MySQL corpus persisting both streams (system of record for news) |
| Watched-symbol set | Union of distinct tickers a user owns or watches (holdings ∪ watchlist ∪ helper watchlist) |
| `news_id` | Deterministic dedupe key = stable hash of `(source, url ‖ guid ‖ title+ts)` |
| Sentiment | `good` \| `bad` \| `neutral` label + `sentiment_score ∈ [-1,1]` from the classifier |
| Category | Coarse topic tag: company (`new_product`,`new_tech`,`management`,`regulatory`,…) or macro (`monetary`,`tariff`,`tax`,`geopolitical`,`war`,…) |
| Bridge | Forwarding a numeric macro release to event-reaction `POST /events` as `{kind, ts_utc, actual, consensus, asset_scope}` |
| Feed adapter | A source-specific reader (RSS or JSON API) producing normalized `NewsItem`s |
| Poller | A scheduled coroutine that drives a stream end-to-end for one tick |
| `news.company` | RabbitMQ event emitted per good/bad company item; consumed by portfolio-service |
| tz-aware UTC | Every stored/emitted timestamp carries explicit UTC (consistency with event-reaction, EC-N6) |

### 1.4 References

1. `SRS_event_reaction.md` — the event store this bridges into (`POST /events`, the
   `events` contract, `kind`).
2. `docs/event_reaction_gap_map.md` — service-shape / integration precedents.
3. `stock-data-service` `GET /companies/{symbol}/news` — the vnstock company-news source
   (`app/services/stock_service.py:580`, route `app/api/routes.py:218`).
4. `ai-insights-service` `NewsAnalysisRequest`/`NewsAnalysisResponse`
   (`app/models/schemas.py:47-52`) — the classification path.
5. `portfolio-service` notification stack — `notifications`, `push_subscriptions` tables
   (`app/models/domain.py:98-148`), `notification_consumer.py`, `email_consumer.py`,
   `NotificationType` enum.
6. `decision-helper-service/app/services/scheduler.py` — the scheduled-poller pattern to
   copy (FR-NEWS-SCHED); `helper_watchlists` (`app/models/domain.py:78-89`).
7. `portfolio_holdings` (`portfolio-service/app/models/domain.py:40-58`) with the
   `is_watchlist_only` flag — owned vs. watched tickers.
8. Root `CLAUDE.md` — gateway/prefix/service-name conventions this subsystem follows.

### 1.5 Document Overview

§2 gives the module boundary, service layout, and integration points. §3 specifies the
functional requirements per stream plus the shared store, classification, dedup, and
notification requirements. §4 defines the data model, the `NewsItem` contract, the RabbitMQ
event, and the service endpoints. §5 is the test plan. §6 records reuse decisions.
Appendices give defaults, the source registry, and traps.

---

## 2. Overall Description

### 2.1 Product Perspective, Service Boundary, and Layout

The subsystem is a **new microservice** — `news-service` — following the standard service
shape (root `CLAUDE.md` §"Service shape"). Unlike event-reaction it needs **no companion
pure-compute library**: there is no heavy in-process statistics; the only "computation"
(classification) is delegated to `ai-insights-service`. The service is **stateful** (owns
the `news_events` MySQL store) and **schedule-driven** (two pollers), like
`decision-helper-service`.

```
stock_microservices/services/news-service/
  app/
    main.py            # FastAPI app, lifespan (ensure_schema + start pollers), /health, /metrics
    config.py          # pydantic-settings: DB URL, upstream service URLs, feed registry, poll intervals, API keys
    api/
      routes.py        # read endpoints (GET /news, GET /news/{id}) + POST /ingest (manual/test)
      schemas.py       # pydantic response models
    models/
      domain.py        # SQLAlchemy NewsEvent (table `news_events`)
      news_item.py     # the normalized NewsItem dataclass/schema (source-agnostic)
    repositories/
      news_repository.py  # persist / fetch / dedup-by-news_id / mark_notified
    ingest/            # ADAPTERS ONLY — all external I/O lives here
      company_source.py   # HTTP -> stock-data-service /companies/{symbol}/news
      watch_source.py     # HTTP -> portfolio-service + decision-helper watched-symbol set
      classifier.py       # HTTP -> ai-insights-service NewsAnalysis
      macro_feeds.py      # RSS/JSON feed readers (registry-driven)
      event_bridge.py     # HTTP -> event-reaction-service POST /events
    services/
      company_poller.py   # Stream B pipeline: resolve -> fetch -> dedup -> classify -> store -> emit
      macro_poller.py     # Stream A pipeline: read feeds -> tag -> store -> bridge
      notifier.py         # emit `news.company` RabbitMQ event (thin)
      scheduler.py        # async scheduler driving both pollers (copy decision-helper idiom)
```

**Ownership boundaries (EC-N4, EC-N10):**

- `news-service` owns the **news corpus** and the **ingestion/classification pipeline**.
  It is **user-agnostic** for company news: it stores per-*symbol* items and emits
  per-*symbol* events. It never writes to `notifications` and never reads the user↔ticker map.
- `portfolio-service` owns the **user↔ticker map** and the **notification/email delivery**.
  It consumes `news.company`, resolves which users own/watch the symbol, and creates one
  in-app notification + email per user (deduped by `news_id`).

#### Integration points

| Integration | Real anchor | How this module plugs in |
|---|---|---|
| Company news source | `stock-data-service` `GET /companies/{symbol}/news` (`stock_service.py:580`) | `ingest/company_source.py` calls it over HTTP; no vnstock import here |
| Classification | `ai-insights-service` `NewsAnalysis*` (`schemas.py:47-52`) | `ingest/classifier.py` posts news text, reads sentiment/category |
| Watched-symbol set | `portfolio_holdings` (`domain.py:40-58`), `helper_watchlists` (`domain.py:78-89`) | `ingest/watch_source.py` calls **new additive read endpoints** on those services (§4.5); no cross-service DB reads |
| Notification delivery | `portfolio-service` `notification_consumer.py`, `email_consumer.py`, `NotificationType` | Emit RabbitMQ `news.company`; add `NotificationType.news_company` + a consumer there |
| Event bridge | `event-reaction-service` `POST /events` (`SRS_event_reaction.md` §4.4) | `ingest/event_bridge.py` posts numeric macro releases |
| Scheduler | `decision-helper-service/app/services/scheduler.py` | `services/scheduler.py` mirrors the custom async idiom |
| Gateway routing | Traefik one-router-per-service, chart-decomp 8011 / event-reaction 8012 | New router `stock-news`, prefix `/news`, next free port **8013**, same 6-label set |
| DB | MySQL system of record; per-service DB (`stock_event_reaction`, …) | New DB **`stock_news`** |

### 2.2 Product Functions

1. Persist a de-duplicated, ML-friendly `news_events` corpus for both streams.
2. Resolve the union watched-symbol set over HTTP.
3. Poll company news per watched symbol; classify; store; notify on good/bad.
4. Poll macro feeds; tag; store; bridge numeric releases to event-reaction.
5. Serve the stored corpus via read endpoints.

### 2.3 User Classes

- **End user (investor)** — receives in-app + email alerts for good/bad news on owned/
  watched tickers; browses stored news in the app.
- **ML/quant researcher** — consumes the `news_events` corpus (raw text + `raw_json`) as
  a future model input; consumes bridged surprises via event-reaction.
- **Backend developer** — operates the pollers, configures the feed registry and API keys.

### 2.4 Operating Environment

Python ≥ 3.10, FastAPI/uvicorn, SQLAlchemy + MySQL (`stock_news` DB), `httpx` for all
upstream calls, an RSS/Atom parser (`feedparser`) for Stream A, `aio-pika` (via
`stock-common` `EventBus`) for the `news.company` event. Deployed behind Traefik on port
**8013**. Depends at runtime on `stock-data-service`, `ai-insights-service`,
`portfolio-service`, `decision-helper-service`, `event-reaction-service`, RabbitMQ.

### 2.5 Design and Implementation Constraints

**EC-N1. No HTML scraping — feeds/APIs only.** Every external source is a structured RSS/
Atom feed or JSON API declared in the config-driven **source registry** (Appendix B).
Adding a source is a config change, not a new parser per site.

**EC-N2. Idempotent ingestion (dedup).** Re-running a poller over the same window must not
create duplicate rows or duplicate notifications. Dedup is by `news_id` at store time
(FR-NEWS-DEDUP) and by `source_event_id = news_id` at notification time in
portfolio-service.

**EC-N3. Lossless, immutable corpus for ML.** Raw `title`, `body`, `url`, `lang`, and the
full source payload `raw_json` are stored verbatim and never mutated after insert.
Classification writes only add `sentiment`/`category`/`score`/`classified_at`; the raw text
is append-only.

**EC-N4. Reuse the notification stack — don't fork it.** Delivery (in-app, email, dedup,
read/unread) stays in `portfolio-service`. This service only *emits* `news.company`.

**EC-N5. Reuse the classifier — don't fork it.** Sentiment/category come from
`ai-insights-service`. This service holds no model and no prompt logic beyond shaping the
request/response.

**EC-N6. tz-aware UTC timestamps.** All stored/emitted timestamps are tz-aware UTC, matching
the event-reaction contract so bridged events (FR-NEWS-BRIDGE) align cleanly. Source-local
times are converted at the adapter boundary.

**EC-N7. Resilience — log-and-continue.** A single source or upstream being down must not
crash a poll tick or block other sources/symbols. Failures are logged (structlog) and
counted (Prometheus); the poller proceeds. External calls use timeouts + the `stock-common`
retry/circuit-breaker helpers. Feeds are polled politely (per-source interval + backoff).

**EC-N8. Notify good/bad only.** `neutral` items are stored (for ML) but never generate a
notification. The good/bad gate is applied before emitting `news.company`.

**EC-N9. Secrets via env.** Any feed/API key is read from env (`config.py`), never
hardcoded or committed. In-app notifications work with zero external keys; **email requires
SMTP configured in `portfolio-service`** (out of this service's control — see §6, open item).

**EC-N10. User scoping stays in portfolio-service.** The fan-out from a symbol-scoped
`news.company` event to per-user notifications happens in portfolio-service, which owns the
holdings/watchlist. `news-service` never enumerates users.

**EC-N11. Classification cost control.** Only **new** (post-dedup) items are classified, so
LLM calls scale with genuinely-new news, not with poll frequency.

### 2.6 Assumptions and Dependencies

- `stock-data-service` returns company news per symbol (VN companies via vnstock, incl.
  Vietnamese-language text — hence the LLM classifier, which handles VN).
- `ai-insights-service` is reachable and returns a sentiment/category (or the poller marks
  the item `unclassified` and retries next tick — EC-N7).
- `portfolio-service` and `decision-helper-service` expose (or gain — §4.5) a distinct
  watched-symbol read endpoint.
- RabbitMQ is available for `news.company`; if down, the poller logs and the item is left
  `notified_at = NULL` for retry (EC-N7), consistent with the existing best-effort consumers.
- Macro feeds publish stable `guid`/`link` fields usable for `news_id` (EC-N2).

---

## 3. Specific Requirements

Shared requirements (§3.1–3.4) apply to both streams. §3.5 is Stream B (company, built
first). §3.6 is Stream A (macro). §3.7 lists non-functional requirements.

### 3.1 Shared store (FR-NEWS-STORE) — `models/domain.py`, `repositories/news_repository.py`

- **A single table `news_events`** (§4.1) persists every ingested item from both streams,
  keyed by `news_id` (PK). `stream ∈ {company, macro}`; `symbol` is set for company items,
  `NULL` for macro.
- Raw fields (`title`, `body`, `url`, `lang`, `raw_json`) are written once at insert and
  are **immutable** thereafter (EC-N3). Classification and pipeline stamps
  (`sentiment`, `category`, `sentiment_score`, `classified_at`, `notified_at`) are the only
  mutable columns.
- `ts_utc` (published time) is **tz-aware UTC** (EC-N6), indexed with `symbol` and `stream`
  for the read API.
- The repository provides: `upsert(item)`, `exists(news_id)`, `list_new(...)` (rows needing
  classification), `mark_classified(...)`, `mark_notified(...)`, and query helpers for §4.4.

### 3.2 Deduplication (FR-NEWS-DEDUP, EC-N2)

- `news_id = stable_hash(source, primary_key)` where `primary_key` is the first available of
  `guid` / `url` / `(symbol‖title‖ts_utc_date)`. The hash is deterministic (no clock/random).
- `upsert` is a no-op on an existing `news_id` (returns "already seen") so re-polls neither
  re-store nor re-classify nor re-notify. Notification dedup is reinforced downstream by
  `source_event_id = news_id` in portfolio-service's existing dedup path.

### 3.3 Classification (FR-NEWS-CLASSIFY, EC-N5, EC-N11) — `ingest/classifier.py`

- **Input:** a normalized `NewsItem` (title + body + lang).
- **Behaviour:** POST to `ai-insights-service` `NewsAnalysis`; map its response to
  `sentiment ∈ {good, bad, neutral}`, a `category`, and a `sentiment_score ∈ [-1,1]`.
- **Only new items** (post-dedup) are classified (EC-N11). On classifier error/timeout the
  item is stored with `sentiment = NULL` / `category = 'unclassified'` and retried on the
  next tick (EC-N7); it is **not** notified until classified.
- The category vocabulary for company news includes at least `new_product`, `new_tech`,
  `management`, `regulatory`, `earnings`, `other` (Appendix A). Mapping the free-form LLM
  label into this closed set lives here.

### 3.4 Notification emission (FR-NEWS-NOTIFY, EC-N4, EC-N8, EC-N10) — `services/notifier.py`

- After a company item is stored and classified, **if `sentiment ∈ {good, bad}`** (EC-N8),
  emit one RabbitMQ event `news.company` (§4.3) carrying
  `{news_id, symbol, sentiment, category, title, url, ts_utc, sentiment_score}` — **no user
  identity** (EC-N10). Set `notified_at` on success.
- **Consumption (portfolio-service side, added by this project):** a new consumer subscribes
  to `news.company`, resolves the set of users who own or watch `symbol` (holdings ∪
  watchlist), and for each user creates a `notifications` row of a **new**
  `NotificationType.news_company` (`source_event_id = news_id` for per-user dedup) and — per
  the user's channel prefs — an email via the existing `email_consumer`. This reuses the
  existing best-effort, log-and-continue consumer machinery (EC-N4, EC-N7).

### 3.5 Stream B — Company good/bad news (FR-NEWS-COMPANY) — **built first**

`services/company_poller.py`, driven by `services/scheduler.py`:

1. **Resolve** the watched-symbol set (FR-NEWS-WATCH): `ingest/watch_source.py` fetches the
   distinct union of owned/watched tickers from `portfolio-service` and
   `decision-helper-service` over HTTP (§4.5). Empty set ⇒ nothing to do.
2. **Fetch** per symbol: `ingest/company_source.py` calls `stock-data-service`
   `GET /companies/{symbol}/news`, normalizing each entry to a `NewsItem` (§4.2) with
   `stream = company`, `symbol`, tz-aware UTC `ts_utc`, and `raw_json` (EC-N3, EC-N6).
3. **Dedup** by `news_id` (FR-NEWS-DEDUP) — drop already-seen items before any LLM call.
4. **Classify** new items (FR-NEWS-CLASSIFY).
5. **Store** every new item (good/bad/neutral) to `news_events` (FR-NEWS-STORE).
6. **Notify** good/bad items (FR-NEWS-NOTIFY, EC-N8).
- **Resilience (EC-N7):** a failing symbol/source is logged and skipped; the tick continues.

### 3.6 Stream A — Macro/global events (FR-NEWS-MACRO) — built second

`services/macro_poller.py`:

1. **Read** each source in the registry (Appendix B) via `ingest/macro_feeds.py` (RSS/Atom or
   JSON API; no scraping — EC-N1), normalizing to `NewsItem` with `stream = macro`,
   `symbol = NULL`, tz-aware UTC `ts_utc`, `raw_json` (EC-N3, EC-N6).
2. **Tag** each item into a macro `category` (`monetary`, `tariff`, `tax`, `geopolitical`,
   `war`, `trade`, `other`) — rule-based by source + keyword by default; LLM classification
   optional and off by default for macro (coarse tags suffice and it controls cost).
3. **Dedup** and **store** (FR-NEWS-DEDUP, FR-NEWS-STORE).
4. **Bridge** (FR-NEWS-BRIDGE, §3.6.1) qualifying numeric releases.
- **No notification** for Stream A in v1 (store + bridge only).

#### 3.6.1 Event-reaction bridge (FR-NEWS-BRIDGE) — `ingest/event_bridge.py`

- A macro item recognized as a **numeric economic release** with a parseable `actual` and a
  pre-event `consensus` (e.g. a policy-rate decision, a CPI/tariff release from a source that
  publishes consensus) is forwarded to `event-reaction-service` `POST /events` as
  `{event_id: news_id, ts_utc, kind, actual, consensus, asset_scope}`.
- `kind` maps from the macro `category` to an event-reaction kind vocabulary
  (`rate_decision`, `tariff`, …). Only a small, explicitly-listed set of release types is
  bridged in v1 (Appendix A); free-text political/war items are stored but **not** bridged.
- The bridge is **best-effort and idempotent**: `event_id = news_id` means a re-post is an
  upsert on the event-reaction side (its store upserts by `event_id`), so re-runs are safe.

### 3.7 Non-Functional Requirements

- **NFR-N1 Ingest adapters isolated.** All external I/O (HTTP, feeds, RabbitMQ) lives in
  `ingest/` and `services/notifier.py`; the repository is the only DB writer. No business
  logic performs raw network calls inline.
- **NFR-N2 Determinism of dedup.** `news_id` is a pure function of source fields (no clock/
  random) so the same item always maps to the same key (testable offline).
- **NFR-N3 Typing & errors.** Typed schemas for `NewsItem` and API responses; a small
  exception set (`NewsIngestError`, `SourceUnavailableError`, `ClassificationError`) mapped to
  HTTP by the routes and swallowed-and-logged by the pollers (EC-N7).
- **NFR-N4 Observability.** `/health{,/live,/ready}` + `/metrics`; per-stream counters
  (items fetched / new / classified / notified / bridged / errors) and last-successful-tick
  gauges.
- **NFR-N5 Config-driven.** Poll intervals, the feed registry, upstream URLs, API keys, and
  feature toggles (`enable_macro`, `enable_bridge`, `enable_email`) are all in `config.py`
  via env, defaults safe (Stream A/bridge may ship disabled until sources are configured).
- **NFR-N6 Scheduler safety.** The scheduler (FR-NEWS-SCHED) never overlaps a stream's ticks
  (a slow tick defers the next rather than running concurrently) and starts/stops cleanly in
  the FastAPI lifespan.

---

## 4. Data Models and Interfaces

### 4.1 `news_events` table (FR-NEWS-STORE)

```python
# SQLAlchemy sketch — implementation matches repo style (see event-reaction domain.py)
class NewsEvent(Base):
    __tablename__ = "news_events"
    news_id         = Column(String(64), primary_key=True)       # stable dedupe hash (FR-NEWS-DEDUP)
    source          = Column(String(64), nullable=False, index=True)  # "vnstock" | "fed" | "reuters_rss" | ...
    stream          = Column(String(16), nullable=False, index=True)  # "company" | "macro"
    symbol          = Column(String(20), nullable=True, index=True)   # set for company; NULL for macro
    ts_utc          = Column(DateTime(timezone=True), nullable=False, index=True)  # published time (EC-N6)
    title           = Column(Text, nullable=False)               # raw (EC-N3, immutable)
    body            = Column(MEDIUMTEXT, nullable=True)          # raw (immutable)
    url             = Column(String(1024), nullable=True)
    lang            = Column(String(8), nullable=True)           # "vi" | "en" | ...
    category        = Column(String(32), nullable=True, index=True)  # classified/tagged topic
    sentiment       = Column(String(8), nullable=True)           # "good" | "bad" | "neutral" | NULL
    sentiment_score = Column(Float, nullable=True)               # [-1, 1]
    raw_json        = Column(MEDIUMTEXT, nullable=True)          # full source payload (EC-N3)
    ingested_at     = Column(DateTime(timezone=True), nullable=False)
    classified_at   = Column(DateTime(timezone=True), nullable=True)
    notified_at     = Column(DateTime(timezone=True), nullable=True)   # company good/bad only
    bridged_at      = Column(DateTime(timezone=True), nullable=True)   # macro numeric releases only
```

Lives in a new MySQL DB **`stock_news`**. `lifespan` calls `repo.ensure_schema()`
(create-if-not-exists), mirroring event-reaction.

### 4.2 Normalized `NewsItem` (source-agnostic contract)

```python
@dataclass(frozen=True)
class NewsItem:
    source: str
    stream: str            # "company" | "macro"
    symbol: str | None
    ts_utc: datetime       # tz-aware UTC (EC-N6)
    title: str
    body: str | None
    url: str | None
    lang: str | None
    raw_json: str          # verbatim source payload (EC-N3)
    # news_id is derived (FR-NEWS-DEDUP), not carried by the source
    def news_id(self) -> str: ...   # stable_hash(source, guid|url|symbol+title+date)
```

Every adapter (`company_source`, `macro_feeds`) emits `NewsItem`s; the rest of the pipeline
is source-agnostic.

### 4.3 RabbitMQ event `news.company` (FR-NEWS-NOTIFY)

```jsonc
// routing key: "news.company"  (emitted via stock-common EventBus)
{
  "news_id": "…",          // == source_event_id for downstream dedup (EC-N2)
  "symbol": "FPT",
  "sentiment": "good",     // good | bad  (neutral is never emitted — EC-N8)
  "category": "new_product",
  "title": "…",
  "url": "…",
  "ts_utc": "2026-07-02T02:15:00Z",
  "sentiment_score": 0.72
}
```

Portfolio-service's new consumer fans this out per user (§3.4). No user identity is present
in the event (EC-N10).

### 4.4 Service endpoints (news-service, port 8013)

Mounted under `/stock_helper/api/v2/news`:

| Method & path | Purpose |
|---|---|
| `GET /news` | List stored items; filters `stream`, `symbol`, `category`, `sentiment`, `since`, `until`, pagination |
| `GET /news/{news_id}` | One stored item incl. `raw_json` |
| `POST /ingest` | Manual/test ingest of a `NewsItem` (also lets ops backfill); goes through dedup→classify→store→notify |
| `POST /poll/{stream}` | Trigger a poll tick on demand (`company`\|`macro`) — ops/testing |
| `GET /health`, `/health/live`, `/health/ready`, `/metrics` | Standard (unauthenticated live per repo convention) |

Library/pipeline exceptions map to HTTP via a `_handle` (idiom:
`chart-decomp-service/app/api/routes.py:64`): `SourceUnavailableError`→502,
`ClassificationError`→502, validation→422, else 500.

### 4.5 Upstream read endpoints this project adds (watched-symbol set, FR-NEWS-WATCH)

Small **additive** endpoints on existing services (no schema changes), consumed by
`ingest/watch_source.py`:

- `portfolio-service` `GET /portfolio/watched-symbols` → `["ACB","FPT",…]` — `DISTINCT symbol`
  from `portfolio_holdings` (owned **and** `is_watchlist_only`).
- `decision-helper-service` `GET /helper/watched-tickers` → `["…"]` — `DISTINCT ticker` from
  active `helper_watchlists`.

`watch_source.py` unions both (best-effort per EC-N7; if one is down it uses the other).

---

## 5. Validation and Test Requirements

Service tests use FastAPI `TestClient` + mocked upstreams (no real network/DB where
possible; SQLite/in-memory for the repository), matching the repo pattern. All fixtures are
deterministic; `news_id` derivation is a pure function (NFR-N2).

### 5.1 Unit tests

- **Dedup (FR-NEWS-DEDUP, MANDATORY):** the same source entry maps to the same `news_id`
  across runs; a second `upsert` of an already-seen `news_id` is a no-op (no duplicate row,
  no re-classify, no re-notify). Different sources with the same title get different ids.
- **`NewsItem` normalization:** company adapter maps a vnstock payload → `NewsItem` with
  tz-aware UTC `ts_utc` and `raw_json` preserved verbatim (EC-N3, EC-N6); a naive source time
  is converted, not stored naive.
- **Classification mapping (FR-NEWS-CLASSIFY):** an ai-insights response maps to the closed
  `{good,bad,neutral}` × category set; a classifier error yields `sentiment=NULL`,
  `category='unclassified'`, item stored, **not** notified (EC-N7, EC-N8).
- **Macro tagging (FR-NEWS-MACRO):** a Fed/Treasury feed entry tags to the expected macro
  category by rule; free-text geopolitical item → `geopolitical`, not bridged.

### 5.2 Pipeline tests (Stream B, MANDATORY end-to-end)

- **Company poller happy path:** given a mocked watched set `{ACB, FPT}`, mocked company-news
  payloads, and a mocked classifier returning one `good`, one `neutral`: assert both are
  stored, **only the `good` emits exactly one `news.company` event**, `neutral` emits none
  (EC-N8), and re-running the tick emits **zero** new events (EC-N2, the idempotency gate).
- **Notify dedup (EC-N2, MANDATORY):** two consecutive ticks over identical news produce one
  stored row and one emitted event total.
- **Resilience (EC-N7):** with the classifier mocked to raise for one symbol, the other
  symbol's items still store; the tick does not crash; an error counter increments.

### 5.3 Notification-consumer tests (portfolio-service side)

- A `news.company` event for `FPT` fans out to exactly the users who own/watch `FPT`, one
  `notifications` row each with `type = news_company` and `source_event_id = news_id`;
  a second delivery of the same `news_id` creates **no** duplicate per user (existing dedup).
- Email path invoked per user only when email is enabled/configured (EC-N9); in-app always.

### 5.4 Stream A tests

- **Macro store:** a mocked RSS feed yields normalized items stored with `stream=macro`,
  `symbol=NULL`, `raw_json` preserved.
- **Bridge (FR-NEWS-BRIDGE):** a mocked numeric release (`actual`, `consensus`) posts exactly
  one event to a mocked event-reaction `POST /events` with `event_id == news_id`; a re-run
  re-posts the **same** `event_id` (idempotent upsert), and a free-text item posts nothing.

### 5.5 API tests

- `GET /news?stream=company&symbol=FPT&sentiment=good` returns only matching rows;
  `GET /news/{id}` includes `raw_json`; `/health/live` is 200 and unauthenticated.

---

## 6. Reuse & Decisions

| Concern | Decision | Anchor |
|---|---|---|
| Company news source | **Reuse over HTTP** via `stock-data-service /companies/{symbol}/news`; no vnstock import here | `stock_service.py:580` |
| Classification | **Reuse** `ai-insights-service` NewsAnalysis; no model in this service (EC-N5) | `schemas.py:47-52` |
| Notification/email delivery | **Reuse** portfolio-service stack; emit `news.company`, add `NotificationType.news_company` + a consumer (EC-N4) | `domain.py:98-148`, `notification_consumer.py`, `email_consumer.py` |
| Watched-symbol set | Read over HTTP via **new additive endpoints**; no cross-service DB reads (EC-N10) | `portfolio_holdings` `domain.py:40-58`, `helper_watchlists` `domain.py:78-89` |
| Event bridge | **Reuse** event-reaction `POST /events`; `event_id = news_id` for idempotency | `SRS_event_reaction.md` §4.4 |
| Scheduler | **Copy** decision-helper async scheduler idiom (no Celery/APScheduler added) | `scheduler.py` |
| Service shape / wiring | New stateful service; DB `stock_news`; Traefik router `stock-news`, port **8013**, 6 labels | event-reaction 8012, chart-decomp 8011 precedent |
| Module rules | **No nested `CLAUDE.md`** — this is a straightforward ingestion service with no causality discipline; root `CLAUDE.md` governs. Root `CLAUDE.md` untouched | — |

**Open item (email, EC-N9):** email delivery needs SMTP configured in `portfolio-service`.
Plan wires the code behind `enable_email`; **in-app works immediately regardless**. If SMTP
is unset in the deploy env, email is a no-op (logged), not an error.

---

## 7. Dependencies

| Dependency | Used for |
|---|---|
| `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings` | service + config |
| `sqlalchemy` + MySQL driver | `news_events` store (`stock_news` DB) |
| `httpx` | all upstream calls (company news, classifier, watch set, event bridge) |
| `feedparser` (or equivalent) | RSS/Atom reading for Stream A (EC-N1) |
| `stock-common` (`events`, `observability`, `resilience`, `config`) | EventBus for `news.company`, structlog/metrics, retry/circuit-breaker, settings base |
| `prometheus-client` | `/metrics`, per-stream counters (NFR-N4) |

---

## Appendix A — Category & bridge vocabularies (defaults)

**Company categories (FR-NEWS-CLASSIFY):** `new_product`, `new_tech`, `management`,
`regulatory`, `earnings`, `partnership`, `other`.
**Company sentiment:** `good` | `bad` | `neutral` (+ `sentiment_score ∈ [-1,1]`).
**Macro categories (FR-NEWS-MACRO):** `monetary`, `tariff`, `tax`, `trade`, `geopolitical`,
`war`, `other`.
**Bridged release → event-reaction `kind` (FR-NEWS-BRIDGE, v1 whitelist):**
`monetary→rate_decision`, `tariff→tariff`, `tax→tax`. Everything else is stored, not bridged.

## Appendix B — Source registry (Stream A, feeds/APIs only — EC-N1)

Config-driven; each entry is `{name, kind: rss|json, url, category_hint, bridge: bool}`.
Proposed v1 sources (all structured, public, no scraping): U.S. Federal Reserve press-release
RSS, U.S. Treasury press RSS, U.S. Bureau of Labor Statistics releases, Reuters/AP business
RSS, optionally FRED (JSON API, needs a free key) for numeric series. **The exact source list
is finalized in the plan's Stream-A tasks**; the registry makes adding/removing a source a
config edit (NFR-N5). Any keyed source reads its key from env (EC-N9).

## Appendix C — Defaults

| Parameter | Default | Notes |
|---|---|---|
| Company poll interval | 15 min | `enable_company = true` |
| Macro poll interval | 30 min | `enable_macro = false` until sources configured (NFR-N5) |
| Bridge | `enable_bridge = false` | Enable once a numeric-release source is registered |
| Email | `enable_email = false` | Needs portfolio-service SMTP (EC-N9, §6) |
| Notify sentiments | `{good, bad}` | `neutral` stored, not notified (EC-N8) |
| HTTP timeout | 10 s | + `stock-common` retry/circuit-breaker (EC-N7) |
| Classify batch | new items per tick | Only post-dedup items (EC-N11) |

## Appendix D — Known limitations and traps

- **D1. Duplicate notifications** are the #1 trap. Two dedup layers exist for a reason:
  `news_id` at store (EC-N2) and `source_event_id` per user in portfolio-service. Never emit
  before the store confirms the item is new.
- **D2. Naive timestamps from feeds/vnstock.** Convert to tz-aware UTC at the adapter
  boundary (EC-N6) or bridged events (FR-NEWS-BRIDGE) will misalign to the trading day.
- **D3. Classifier is external and may be slow/down.** Classify only new items (EC-N11),
  time-box the call, and defer (not drop) on failure (EC-N7); never block the store on it.
- **D4. Scraping creep.** The registry is feeds/APIs only (EC-N1). If a desired outlet has no
  feed, it stays out of scope rather than becoming a bespoke HTML parser.
- **D5. User fan-out belongs to portfolio-service** (EC-N10). Resist reading holdings here;
  it would duplicate ownership and drift from the system of record.
- **D6. Immutable corpus.** Never overwrite raw `title`/`body`/`raw_json` on re-poll (EC-N3);
  the ML value is in the untouched original.

---

*End of document.*
