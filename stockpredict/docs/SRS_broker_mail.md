# Software Requirements Specification

## Broker Mail Ingestion — Market Internals, Analyst Calls, and a Scored Second Opinion

**Document version:** 1.0
**Date:** 2026-09-09
**Status:** Draft (Phase 1 — Design)
**Sibling docs:** `SRS_news_ingestion.md` (the subsystem this extends),
`implementation_plan_event_reaction.md` and `event_reaction_gap_map.md` (the surprise
store this bridges into), `docs/implementation_plan_broker_mail.md` (companion plan, to
be written in Phase 2).

---

## 1. Introduction

### 1.1 Purpose

This document specifies a **broker-mail ingestion subsystem**: a daily research email
from a Vietnamese securities house (TCBS, "Cơ hội đầu tư") is captured, extracted to a
strict schema, and turned into three things the platform does not otherwise have —

- **Market internals.** Exchange-level figures no OHLCV series can reconstruct: advance/
  decline breadth, ceiling/floor counts, the matched-versus-put-through turnover split,
  and foreign investor net flow **per ticker**.
- **A ledger of analyst calls.** Each Buy / Sell / Hold recommendation, its verbatim
  label, its rationale and its date — stored, then marked to market so the desk acquires
  a measurable track record.
- **Curated corporate and macro items**, folded into the existing news corpus rather than
  a parallel store.

The founding principle is that **the email is evidence, not an instruction**. It is
published after the close, to every subscriber, and derives from a session the platform
already holds prices for. It therefore carries no timing edge on its own. Its value is
(a) observed data that cannot be computed locally, and (b) a benchmark opinion against
which this platform's own recommendation engine can be measured.

### 1.2 Scope

**In scope.** Mailbox intake and raw retention; schema extraction and validation;
persistence of market internals, foreign flow and broker calls; forward-return scoring
of calls; read APIs; React surfaces for the internals and the head-to-head record;
routing of corporate items into the existing `news_events` corpus and of numeric macro
releases into the existing event-reaction store.

**Out of scope.** Automated order placement. Any use of a broker call to *originate* a
recommendation (see EC-B7). Redistribution of TCBS research text (EC-B8). Parsing of
attached PDF research reports — the mail links to them; only the link is stored in v1.
Sources other than TCBS; the adapter is written so a second broker is a registry entry,
but no second source is specified here.

### 1.3 Definitions, Acronyms, Abbreviations

| Term | Definition |
|---|---|
| Broker mail | One daily research email from a securities house; the unit of ingestion |
| `mail_id` | Deterministic dedupe key = stable hash of the RFC-822 `Message-ID` header |
| Session date | The **trading session the mail describes**, not the date it was sent (they differ) |
| Breadth | Counts of advancing / declining stocks in a session, plus ceiling and floor counts |
| Ceiling / floor (trần / sàn) | Stocks closing at the exchange's daily price limit — a VN board convention |
| Matched turnover (khớp lệnh) | Continuous order-book value; the participation measure |
| Put-through (thỏa thuận) | Negotiated block value; excluded from participation measures |
| Foreign flow | Net foreign buy minus sell, market-wide and per ticker, in VND billion |
| Broker call | One Buy / Sell / Hold recommendation with rationale, attributable to a desk and date |
| `label_verbatim` | The exact phrase used by the desk ("Buy Now", "Hold") before normalisation |
| Forward return | Price change from the call date over 1 / 5 / 20 / 60 sessions |
| Golden set | Hand-labelled emails used to measure field-level extraction accuracy |
| Quarantine | A stored, un-promoted extraction that failed validation and awaits review |
| Thousands-quote | `stock_prices.close` unit: 12.75 means 12,750 VND/share (see EC-B5) |

### 1.4 References

- `docs/SRS_news_ingestion.md` — the corpus, dedupe and classifier this reuses (FR-NEWS-*).
- `services/news-service/app/ingest/` — the source-adapter pattern this follows.
- `services/event-reaction-service/app/models/domain.py` — `EventRecord`, the bridge target.
- `services/decision-helper-service/app/services/regime/classifier.py` — the consumer of
  market-state features in Phase E5.
- `CLAUDE.md` §"Binding constraints" C4 — benchmarks are mandatory; the same rule governs
  EC-B7 here.

### 1.5 Document Overview

§2 sets the service boundary and the constraints that override convenience. §3 gives the
functional requirements. §4 gives the tables, the extraction contract and the endpoints.
§5 gives the mandatory test harnesses. §6 records the reuse decisions and the alternatives
rejected. Appendices carry the vocabularies, defaults and known traps.

---

## 2. Overall Description

### 2.1 Product Perspective, Service Boundary, and Layout

The subsystem is **an extension of `news-service`** (port 8013, DB `stock_news`,
prefix `/stock_helper/api/v2/news`), not a new microservice. That service already owns
the source-adapter pattern, a deduplicated corpus, a classifier client and a scheduler;
a fourteenth service would fork all four. Rationale and rejected alternatives: §6.

```
services/news-service/app/
  ingest/
    broker_mail_source.py     # NEW  IMAP intake -> RawMail
    broker_mail_extract.py    # NEW  LLM pass -> BrokerMailDoc (strict schema)
    broker_mail_validate.py   # NEW  arithmetic + sanity gate, quarantine on failure
    broker_mail_poller.py     # NEW  two-phase tick, mirrors the company poller
  models/
    broker_mail.py            # NEW  RawMail, BrokerMailDoc, BrokerCall contracts
  repositories/
    broker_repository.py      # NEW  raw + extract + stats + flow + calls
  services/
    call_scorer.py            # NEW  forward-return marking job
```

Consumers stay outside the boundary and read over HTTP:

| Consumer | Reads | Phase |
|---|---|---|
| React app | breadth, flow, head-to-head record | E3, E4 |
| `decision-helper-service` | market-state gate (breadth, flow) | E5 |
| `prediction-service` | per-symbol foreign flow feature | E5 |
| `event-reaction-service` | numeric macro releases with consensus | E2 |
| `news-service` corpus (self) | corporate items | E2 |

### 2.2 Product Functions

1. Poll a dedicated mailbox, store raw MIME immutably, dedupe on `Message-ID`.
2. Backfill the existing mailbox history in one pass.
3. Extract one JSON document per email against a strict schema; validate before promoting.
4. Persist market internals, per-ticker foreign flow, and broker calls.
5. Mark every call to market at fixed horizons; publish the desk's running record.
6. Route corporate items to `news_events`; bridge numeric macro releases to event-reaction.
7. Expose read endpoints; surface internals and the head-to-head record in the React app.

### 2.3 User Classes

- **The operator (single user today).** Reads the internals charts and the head-to-head
  record; decides whether a feature graduates to E5.
- **Downstream services.** `decision-helper-service`, `prediction-service` — machine
  consumers of the same read endpoints.

### 2.4 Operating Environment

Python 3.11 / FastAPI / async SQLAlchemy against the shared MySQL (`stock_news`), RabbitMQ
for the existing `news.company` emission, and `ai-insights-service` for the extraction
call. IMAP over TLS to the ingestion mailbox. All timestamps tz-aware UTC (EC-N6 applies
unchanged).

### 2.5 Design and Implementation Constraints

**EC-B1. A dedicated ingestion mailbox — never a personal inbox.** The service
authenticates to one address that exists only to receive forwarded broker mail. A Gmail
filter on `from:tcbs.com.vn` forwards into it. The service must never be given credentials
to a mailbox carrying unrelated personal mail, and must ignore any message failing the
sender allow-list in Appendix B.

**EC-B2. Capture before parse; raw is immutable.** Raw MIME is stored on receipt and never
mutated. Extraction is a separate, re-runnable pass that writes new rows. A parser change
must be replayable over the whole archive without re-fetching mail. *An email not captured
is unrecoverable* — this is why intake ships as its own phase, before any parser exists.

**EC-B3. No heading-based parsing.** The observed samples prove headings are unreliable:
section "3" appears twice under different names ("Recommendation" for PHP, "Stock
recommendations" for CTD); *Ngành* (sector) is machine-translated to "Plants" and its
items are flattened into the macroeconomics bullet list. Extraction is therefore one LLM
pass emitting the schema in §4.3, followed by deterministic validation — never a regex
over section titles.

**EC-B4. Preserve the verbatim label.** The desk's vocabulary is richer than three verbs:
"Buy Now" carries a timing qualifier that "BUY" discards. Every call stores both
`action` (normalised enum) and `label_verbatim` (exact source phrase). Normalisation is
never lossy.

**EC-B5. Three units in one pipeline — convert once, test it.** The mail speaks **VND
billions** and index points; `stock_prices.close` is a **thousands-quote** (12.75 =
12,750 VND/share); `portfolio_holdings.average_price` is **actual VND**. Every boundary
crossing is an explicit, unit-tested conversion. This class of bug has already cost this
project once (portfolio summary, Backlog #43).

**EC-B6. Approximate figures stay flagged.** The mail prints "~" on most values and rounds
to one decimal. Stored figures carry `approximate = true` and must never be treated as
exact when reconciled against tick data (see FR-BM-RECONCILE tolerance).

**EC-B7. Benchmark or drop — no feature reaches a decision unproven.** No broker-mail
field may influence a recommendation until it beats the existing baseline out-of-sample
in the `decision-helper-service` walk-forward harness. Broker calls are *displayed beside*
this platform's own output, never merged into it. This mirrors CLAUDE.md C4.

**EC-B8. Subscriber material — parse privately, do not republish.** TCBS research text may
be stored and shown to the operator. It must not be exposed through any public or shared
surface of the application, nor forwarded onward by the app.

**EC-B9. Reuse the corpus, classifier and notification stack.** Corporate items become
`news_events` rows via the existing repository and are notified through the existing
`news.company` path. Sentiment/category come from `ai-insights-service`. This subsystem
holds no model, no prompt logic beyond request/response shaping, and no second corpus.

**EC-B10. Fail loudly; never write a partial row.** A validation failure quarantines the
whole document. Partial promotion is forbidden — a half-parsed session silently mixing
real and missing internals is worse than an absent day.

**EC-B11. Bilingual duplication is collapsed at extraction.** The body repeats in
Vietnamese-flavoured English and English. Exactly one canonical document per email is
promoted; the language variants observed are recorded on it.

### 2.6 Assumptions and Dependencies

- One email per trading day, ≈250/year. The archive is small; **history is the asset**,
  which makes backfill (FR-BM-BACKFILL) disproportionately valuable.
- TCBS format will drift. Detection is the validator's job, not a human's.
- Consensus/forecast figures are **usually absent** from the macro section, so most macro
  items cannot form a surprise and will not bridge (see FR-BM-MACRO).
- `ai-insights-service` availability gates extraction but not intake — intake must keep
  working while extraction is down.

---

## 3. Specific Requirements

### 3.1 Mailbox intake (FR-BM-INTAKE, EC-B1, EC-B2) — `ingest/broker_mail_source.py`

Poll the ingestion mailbox over IMAP on a schedule. For each message: verify the sender
against the allow-list (Appendix B), compute `mail_id`, and insert raw MIME plus headers
if absent. Non-allow-listed mail is ignored without error. Network/auth failure logs and
retries on the next tick; it never raises into the scheduler.

### 3.2 Deduplication (FR-BM-DEDUP, EC-B2)

`mail_id = sha256(Message-ID)`. Insert-if-absent; re-seeing a message is a no-op, not an
update. A forwarded copy carries a different `Message-ID` than the original, so the
`session_date` + `source` pair carries a **secondary** uniqueness check at promotion time
(FR-BM-EXTRACT) to catch the same session arriving twice by different routes.

### 3.3 History backfill (FR-BM-BACKFILL)

A one-shot command walks the mailbox from a given date and applies FR-BM-INTAKE to every
matching message. Idempotent by FR-BM-DEDUP; safe to re-run.

### 3.4 Extraction (FR-BM-EXTRACT, EC-B3, EC-B11) — `ingest/broker_mail_extract.py`

For each raw mail without a promoted document: strip HTML to text, collapse the bilingual
duplication, and issue **one** call to `ai-insights-service` requesting the §4.3 schema.
The response is parsed strictly — unknown fields rejected, missing required fields fatal.
`session_date` is the session described, resolved from the body, and must not be assumed
equal to the send date.

### 3.5 Validation and quarantine (FR-BM-VALIDATE, EC-B10) — `ingest/broker_mail_validate.py`

Before promotion, a deterministic gate:

1. `foreign_flow.buy − foreign_flow.sell == foreign_flow.net` within tolerance.
2. `advancers + decliners ≤ listed-count` and both > 0; `ceiling ≤ advancers`;
   `floor ≤ decliners`.
3. `matched_turnover ≤ total_turnover`; put-through non-negative.
4. `session_date` is a plausible trading day, not in the future, within N days of receipt.
5. Every `broker_calls[].symbol` and `foreign_flow.by_symbol[].symbol` resolves in
   `companies`; unknown tickers are recorded but do not fail the document.
6. `action ∈ {BUY, SELL, HOLD}` and `label_verbatim` non-empty.

Any failure in 1–4 quarantines the whole document with the failing rule recorded. Nothing
is promoted. Quarantined rows are listable and re-runnable after a parser fix.

### 3.6 Market internals (FR-BM-MARKET, FR-BM-FLOW, EC-B5, EC-B6)

Promote one `market_session_stats` row per session and N `market_foreign_flow` child rows
(one per named ticker). Values stored in the mail's own units (VND billion) with the unit
named on the column, plus `approximate`.

### 3.7 Broker calls (FR-BM-CALLS, EC-B4)

Promote one `broker_calls` row per recommendation: symbol, `action`, `label_verbatim`,
`horizon_hint`, rationale, `target_price` when printed, source date, and the reference
close on the session date. Initiating-coverage notes (e.g. GAS) are recorded with
`action = NULL` and `kind = 'initiation'` — they are research, not a call.

### 3.8 Forward-return scoring (FR-BM-SCORE, EC-B7) — `services/call_scorer.py`

A scheduled job marks every unscored call to market at **1, 5, 20 and 60 sessions** after
the call date, writing absolute and index-relative returns. Horizons fill in as sessions
elapse; a call is never scored on a horizon that has not yet completed. The desk's
aggregate hit rate is exposed only once **≥30 scored calls** exist (below that it is not
reportable — FR-BM-RECORD).

### 3.9 Corporate items (FR-BM-CORP, EC-B9)

Each corporate item becomes a `news_events` row via the existing repository, with
`source = 'tcbs.daily'`, `stream = 'company'`, the ticker as `symbol`, and classification
through the existing `ai-insights` path. Notification follows the unchanged
`news.company` route. No new notification channel.

### 3.10 Macro items (FR-BM-MACRO)

Numeric macro releases are stored in the corpus as `stream = 'macro'`. A release bridges
to `event-reaction` `POST /events` **only when a consensus or forecast figure is present**,
reusing the existing `KIND_MAP`. Absent consensus, the item is recorded and not bridged —
a surprise cannot be computed and must not be fabricated.

### 3.11 Reconciliation (FR-BM-RECONCILE, EC-B6)

A daily check recomputes advance/decline counts from `stock_prices` for the same session
and compares against the mail's breadth within tolerance. A persistent mismatch raises an
operational warning: it means either the parser drifted or the price data is incomplete.
This is the cheapest available detector of silent extraction failure.

### 3.12 Read API and UI (FR-BM-API, FR-BM-RECORD, EC-B8)

Endpoints in §4.4. React surfaces: a breadth/flow panel on the market page (E3), and a
head-to-head panel on the stock page showing the broker's call beside this platform's own
`/recommend` output, each with its running record (E4). Both are read-only. Neither is
exposed on a shared or public surface.

### 3.13 Market-state gate (FR-BM-GATE, EC-B7) — Phase E5 only

Breadth and foreign flow become inputs to the `decision-helper-service` regime/risk layer
**only after** demonstrating out-of-sample improvement in the walk-forward harness. The
gate operates at portfolio level (position sizing, confirmation strictness), not as a
per-signal override.

### 3.14 Non-Functional Requirements

- **Idempotency.** Every phase re-runnable without duplicate rows or duplicate notifications.
- **Isolation.** Extraction failure never blocks intake; scoring failure never blocks either.
- **Latency.** Not time-critical; the mail is post-close. A tick every 30 minutes suffices.
- **Retention.** Raw mail retained indefinitely (EC-B2). Extractions are versioned by
  parser revision so a re-parse is auditable.
- **Observability.** Counters for received / promoted / quarantined per tick, exported to
  the existing Prometheus surface.

---

## 4. Data Models and Interfaces

### 4.1 `broker_mail_raw` (FR-BM-INTAKE)

```python
# SQLAlchemy sketch — matches news-service domain.py style
class BrokerMailRaw(Base):
    __tablename__ = "broker_mail_raw"
    mail_id:      Mapped[str]      = mapped_column(String(64), primary_key=True)
    message_id:   Mapped[str]      = mapped_column(String(512))
    sender:       Mapped[str]      = mapped_column(String(320), index=True)
    subject:      Mapped[str]      = mapped_column(String(998))
    received_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_mime:     Mapped[str]      = mapped_column(MEDIUMTEXT)   # immutable, EC-B2
    extracted_at: Mapped[datetime | None]
```

### 4.2 Promoted tables

```python
class MarketSessionStats(Base):            # FR-BM-MARKET
    __tablename__ = "market_session_stats"
    session_date:            Mapped[date]  = mapped_column(Date, primary_key=True)
    source:                  Mapped[str]   = mapped_column(String(64), primary_key=True)
    index_name:              Mapped[str]                       # "VN-Index"
    close:                   Mapped[float]
    change_pct:              Mapped[float]
    change_pts:              Mapped[float]
    advancers:               Mapped[int]
    decliners:               Mapped[int]
    ceiling_count:           Mapped[int]
    floor_count:             Mapped[int]
    matched_turnover_vnd_bn: Mapped[float]                      # khớp lệnh, EC-B5
    putthrough_vnd_bn:       Mapped[float]                      # thỏa thuận
    volume_m_shares:         Mapped[float]
    foreign_net_vnd_bn:      Mapped[float]
    foreign_buy_vnd_bn:      Mapped[float]
    foreign_sell_vnd_bn:     Mapped[float]
    approximate:             Mapped[bool]                       # EC-B6
    mail_id:                 Mapped[str]                        # provenance

class MarketForeignFlow(Base):             # FR-BM-FLOW
    __tablename__ = "market_foreign_flow"
    session_date: Mapped[date]  = mapped_column(Date, primary_key=True)
    symbol:       Mapped[str]   = mapped_column(String(20), primary_key=True)
    net_vnd_bn:   Mapped[float]
    mail_id:      Mapped[str]

class BrokerCall(Base):                    # FR-BM-CALLS, FR-BM-SCORE
    __tablename__ = "broker_calls"
    call_id:         Mapped[str]  = mapped_column(String(64), primary_key=True)
    source:          Mapped[str]  = mapped_column(String(64), index=True)
    symbol:          Mapped[str]  = mapped_column(String(20), index=True)
    session_date:    Mapped[date] = mapped_column(Date, index=True)
    action:          Mapped[str | None]      # BUY | SELL | HOLD | NULL for initiation
    label_verbatim:  Mapped[str]             # "Buy Now" — EC-B4, never normalised away
    horizon_hint:    Mapped[str | None]
    rationale:       Mapped[str]  = mapped_column(MEDIUMTEXT)
    target_price:    Mapped[float | None]
    ref_close:       Mapped[float | None]    # actual VND at call date, EC-B5
    ret_1d:          Mapped[float | None]
    ret_5d:          Mapped[float | None]
    ret_20d:         Mapped[float | None]
    ret_60d:         Mapped[float | None]
    ret_20d_vs_index: Mapped[float | None]
    mail_id:         Mapped[str]
```

`quarantine` is a column on the extraction row, not a separate table: `promoted_at IS NULL
AND failed_rule IS NOT NULL`.

### 4.3 Extraction contract — `BrokerMailDoc` (FR-BM-EXTRACT)

One document per email. Values below are the real 7 September 2026 session, used as the
canonical fixture in the golden set.

```jsonc
{
  "source": "tcbs.daily",
  "session_date": "2026-09-07",          // session described, NOT the send date
  "lang_variants": ["vi", "en"],         // EC-B11, collapsed to one canonical doc

  "market": {
    "index": "VN-Index",
    "close": 1821.64, "change_pct": -1.70, "change_pts": -31.44,
    "advancers": 81, "decliners": 234,
    "ceiling": 3, "floor": 1,
    "matched_turnover_vnd_bn": 13627.6,
    "putthrough_vnd_bn": 3525.4,
    "volume_m_shares": 498.0,
    "approximate": true                  // EC-B6
  },

  "foreign_flow": {
    "net_vnd_bn": -470.4, "buy_vnd_bn": 1741.8, "sell_vnd_bn": 2212.2,
    "by_symbol": [
      {"symbol": "VCB", "net_vnd_bn": -91.8},
      {"symbol": "CTG", "net_vnd_bn": -73.7},
      {"symbol": "HDB", "net_vnd_bn":  54.0},
      {"symbol": "VRE", "net_vnd_bn":  42.8}
    ]
  },

  "broker_calls": [
    {
      "symbol": "CTD", "action": "BUY",
      "label_verbatim": "Buy Now",       // EC-B4
      "horizon_hint": "immediate",
      "rationale": "Q4 FY26 revenue VND 10,471bn (+25.4% YoY); NPAT VND 146bn (-25.5%)…",
      "target_price": null
    },
    {
      "symbol": "PHP", "action": "HOLD",
      "label_verbatim": "Hold", "horizon_hint": null,
      "rationale": "8M2026 throughput 134.4m tons (+11.7% YoY); Lach Huyen deep-water…",
      "target_price": null
    },
    {
      "symbol": "GAS", "action": null, "kind": "initiation",
      "label_verbatim": "Initiating Coverage", "rationale": null, "target_price": null
    }
  ],

  "corporate": [                          // -> news_events, FR-BM-CORP
    {"symbol": "RAL", "kind": "dividend",   "value_pct": 25,   "text": "…"},
    {"symbol": "MWG", "kind": "operations", "value_pct": null, "text": "…"},
    {"symbol": "NKG", "kind": "governance", "value_pct": null, "text": "…"}
  ],

  "macro": [                              // -> corpus; bridges only with consensus
    {"category": "domestic", "metric": "retail_sales_yoy", "actual": 13.3,
     "consensus": null, "unit": "pct"},
    {"category": "monetary", "metric": "fed_hike_probability", "actual": 57.0,
     "consensus": null, "unit": "pct"}
  ],

  "sector": [
    {"sector": "securities",  "text": "HOSE surveillance of FTSE-basket stocks…"},
    {"sector": "real_estate", "text": "57.8 km expressway ~VND 30,000bn, >99% complete…"}
  ]
}
```

### 4.4 Service endpoints (news-service, port 8013)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/news/broker/sessions` | Market internals by date range (FR-BM-MARKET) |
| `GET` | `/news/broker/sessions/{date}` | One session incl. per-ticker flow |
| `GET` | `/news/broker/flow/{symbol}` | Foreign flow history for one ticker (FR-BM-FLOW) |
| `GET` | `/news/broker/calls` | Call ledger, filterable by symbol/action/date |
| `GET` | `/news/broker/calls/record` | Aggregate hit rate; 409 below 30 calls (FR-BM-RECORD) |
| `GET` | `/news/broker/quarantine` | Failed extractions awaiting review (FR-BM-VALIDATE) |
| `POST` | `/news/broker/poll` | Force an intake tick (operator) |
| `POST` | `/news/broker/reparse` | Re-run extraction over stored raw mail (EC-B2) |

---

## 5. Validation and Test Requirements

### 5.1 Unit tests

- Sender allow-list accepts TCBS, rejects everything else (EC-B1).
- `mail_id` stable across re-parse; re-seeing a message inserts nothing (FR-BM-DEDUP).
- Bilingual collapse yields exactly one document from a two-language body (EC-B11).
- `label_verbatim` survives normalisation: `"Buy Now" -> action BUY` **and** label intact
  (EC-B4).
- Unit conversions: VND billion ↔ VND, thousands-quote ↔ actual VND, both directions,
  with a case asserting a 1000× error is caught (EC-B5).
- `session_date` resolution when it differs from the send date.

### 5.2 Extraction accuracy — golden set (MANDATORY, FR-BM-EXTRACT)

Ten hand-labelled emails spanning at least two months. Field-level accuracy measured per
field, not per document. **Gate: ≥95% on required fields, 100% on `session_date` and on
every `broker_calls[].symbol`** — a call attributed to the wrong ticker is worse than no
call. The 7 Sep fixture in §4.3 is the first member.

### 5.3 Validator tests (FR-BM-VALIDATE, EC-B10)

Each rule in §3.5 gets a passing and a failing fixture. A document failing any of rules
1–4 must leave **zero** rows in the promoted tables — asserted directly, not inferred.

### 5.4 Scoring tests (FR-BM-SCORE)

- Forward returns match a hand-computed fixture at each horizon.
- A horizon that has not yet elapsed stays `NULL`; no forward-looking fill.
- Index-relative return uses the same session window as the absolute return.
- `/calls/record` refuses to report below 30 scored calls.

### 5.5 Reconciliation test (FR-BM-RECONCILE)

Breadth recomputed from `stock_prices` agrees with the mail's counts within tolerance on
the fixture session; an injected parser drift is detected.

### 5.6 Benchmark gate (EC-B7, mirrors C4)

Before E5 ships, the walk-forward harness reports the baseline and the
breadth/flow-augmented model side by side. **A feature that does not beat baseline
out-of-sample is dropped, not shipped behind a flag.** Broker calls are additionally
compared against a buy-and-hold-the-index null.

---

## 6. Reuse & Decisions

| Decision | Choice | Why |
|---|---|---|
| New service vs. extend | **Extend `news-service`** | It already owns source adapters, dedupe, corpus, classifier client and scheduler. A 14th service forks all four for one source. |
| Where internals live | `stock_news` DB | Ingestion owns its tables; consumers read over HTTP. Rejected: writing into stock-data-service's schema from outside, which would couple two services at the table level. |
| Parsing strategy | LLM + strict schema + deterministic validator | Headings are provably unreliable (EC-B3). Regex would fail silently; the validator makes drift loud. |
| Capture vs. parse first | **Capture first, always** | Un-captured mail is unrecoverable; parsers are rewritable. This is the single most important ordering decision in the plan. |
| Calls in the engine | Displayed beside, never merged | One desk, unmeasured hit rate. Measure first (EC-B7). |
| PDF reports | Link only in v1 | Attachment parsing is a separate problem with its own failure modes; the mail's body already carries the extractable value. |

---

## 7. Dependencies

- **Blocking:** an ingestion mailbox and its IMAP credentials (EC-B1); a forwarding rule
  from the receiving account.
- **Runtime:** `ai-insights-service` for extraction; MySQL `stock_news`; RabbitMQ for the
  existing corporate-news notification path.
- **Phase E5 only:** `decision-helper-service` walk-forward harness; `prediction-service`
  feature pipeline.
- **Not required:** any Claude-side Gmail connector. That is a development convenience for
  inspecting samples, not a production dependency.

---

## Appendix A — Vocabularies (defaults)

**Action:** `BUY` | `SELL` | `HOLD` | `null` (initiation / research note).
**Corporate kind:** `dividend`, `earnings`, `operations`, `governance`, `m_and_a`,
`capital_raise`, `regulatory`, `other`.
**Sector:** `securities`, `banking`, `real_estate`, `construction`, `steel`, `energy`,
`retail`, `autos`, `logistics`, `other`.
**Macro category:** reuses the existing news-service vocabulary (`monetary`, `tariff`,
`tax`, `trade`, `geopolitical`, `war`, `domestic`, `other`) so the bridge `KIND_MAP`
applies unchanged.

## Appendix B — Source registry

| Key | Sender allow-list | Subject pattern | Status |
|---|---|---|---|
| `tcbs.daily` | `*@tcbs.com.vn`, plus the forwarding address's own `From` | `Cơ hội đầu tư` / `Investment Opportunity` | v1 |

A second broker is a new row here plus a golden set of its own — no new code path.

## Appendix C — Defaults

| Setting | Default |
|---|---|
| `BROKER_MAIL_ENABLED` | `0` until E1 verified |
| Poll interval | 1800 s |
| Scoring horizons | 1, 5, 20, 60 sessions |
| Minimum calls before a hit rate is reportable | 30 |
| Breadth reconciliation tolerance | ±3 stocks |
| Foreign-flow arithmetic tolerance | ±0.5 VND bn (rounding, EC-B6) |
| Golden-set accuracy gate | ≥95% required fields; 100% `session_date`, call symbols |

## Appendix D — Known limitations and traps

1. **No timing edge.** Post-close, universally distributed, derived from prices already
   held. Treat as features and benchmark; never as alpha in itself.
2. **≈250 emails a year.** Far too little to train on alone. Sufficient for features and
   a track record — which is exactly why backfill matters.
3. **Consensus is usually missing**, so most macro items cannot bridge to event-reaction.
   Expect a low bridge rate and do not treat it as a defect.
4. **Duplicate section numbers and "Plants" for *Ngành*** are present in today's samples.
   Assume worse drift later.
5. **Rounded, "~"-prefixed figures.** Never reconcile against tick data without tolerance.
6. **Forwarded mail changes `Message-ID`**, so the same session can arrive twice by
   different routes — hence the secondary `(source, session_date)` check.
7. **Three units in one pipeline.** The most likely source of a silent, large-magnitude
   bug in this subsystem (EC-B5).

## Appendix E — Phase gates

Phases are referenced throughout as E1–E5. Detail belongs in the companion
`docs/implementation_plan_broker_mail.md`; the gates are binding here.

| Phase | Delivers | Gate before the next phase starts |
|---|---|---|
| **E1** | Intake only (FR-BM-INTAKE, FR-BM-DEDUP, FR-BM-BACKFILL). No parsing. | A week of mail lands automatically, zero duplicates, mailbox history backfilled. |
| **E2** | Extractor, validator, golden set (FR-BM-EXTRACT, FR-BM-VALIDATE); corporate + macro routing (FR-BM-CORP, FR-BM-MACRO). | ≥95% field accuracy on the golden set; 100% on `session_date` and call symbols; every failure quarantined, none silently dropped. |
| **E3** | Market internals persisted and charted (FR-BM-MARKET, FR-BM-FLOW, FR-BM-RECONCILE, FR-BM-API). Read-only, decision-free. | 30 sessions stored; breadth reconciles against `stock_prices` within tolerance. |
| **E4** | Call ledger and scoring (FR-BM-CALLS, FR-BM-SCORE, FR-BM-RECORD); head-to-head UI. | ≥30 scored calls before any hit rate is quoted. |
| **E5** | Features into the decision path (FR-BM-GATE) — *only* if earned. | Walk-forward improvement over the current baseline, or the feature is dropped (EC-B7). |

E1 ships alone and first. Every day spent designing the parser is a day of emails that may
become unrecoverable, and the parser is far easier to write against sixty stored samples
than against two pasted ones.
