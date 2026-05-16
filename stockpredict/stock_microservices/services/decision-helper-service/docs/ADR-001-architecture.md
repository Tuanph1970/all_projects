# ADR-001 — decision-helper-service Architecture (v2)

Status: **Proposed**
Authors: tuanph + Claude
Date: 2026-05-16
Supersedes: ADR-001 v1 (same path; v1 was over-engineered — see "Changelog" §10).

Related:
- `road_map_version_11.xlsx` — Architecture, Feature_Backlog, **Risks_Open_Questions** (the canonical list of open questions; not duplicated here)
- `knowledge/stock_pipeline_v3.drawio` — pipeline diagram
- Existing service template: any `stock_microservices/services/<svc>/app/` (we match it).

---

## 1. Context

decision-helper-service operationalises Schwager's *Getting Started in Technical Analysis* as a per-bar recommendation engine (action + stop + target + size + reason chain). Two design forces compete:

- **Complexity force**: this service composes ~10 cooperating concerns (regime, signal, confirmation, failed-signal, stop, target, sizing, state machine, discipline, reason chain). A flat `services/orchestrator.py` will rot.
- **Consistency force**: nine existing FastAPI services use the same `api / services / repositories / models` layout. Diverging adds cognitive overhead.

This ADR picks the **smallest deviation from the existing template** that prevents rot. Patterns are introduced when they earn their place — not in advance.

## 2. Decision

### 2.1 Bounded contexts (DDD-lite)

We keep the existing FastAPI template and split the `services/` folder by bounded context. Each subfolder owns its domain language and value objects.

| Context | Language it owns | Key types |
|---|---|---|
| **market** | OHLCV bar, indicator pack, swing pivot, S/R level | `Bar`, `IndicatorPack`, `SwingPivot`, `SRLevel` |
| **regime** | Trend / Range / Undefined | `RegimeAssessment`, `RegimeClassifier` |
| **signal** | Raw signal, confirmed signal | `Signal`, `SignalDetector` (Strategy) |
| **risk** | Stop, target, position size | `Stop`, `Target`, `PositionSize`, `RiskPlanner` |
| **position** | FLAT / LONG / SHORT, transitions | `Position` (aggregate), `Transition` |
| **decision** | Recommendation (in-flight), DecisionRun (persisted) | `Recommendation`, `DecisionRun`, `ReasonChain` (Builder) |
| **discipline** | Plan-before-trade, no-averaging-down, streaks | `RuleViolation`, `DisciplineCheck` (Specification) |

A context's public surface is a small set of types and one or two functions. Cross-context state changes are mediated by **domain events** (§4).

### 2.2 Folder layout

Matches the existing template; the **only** addition is `application/` for non-trivial use cases.

```
decision-helper-service/app/
├── api/
│   ├── routes.py                FastAPI routers; HTTP in/out only.
│   └── dependencies.py
├── application/                 Use cases — multi-step orchestrations.
│   ├── run_decision_for_bar.py  DecisionOrchestrator (the one Facade)
│   ├── recompute_on_demand.py
│   └── replay_for_backtest.py
├── services/                    Domain logic, split by bounded context.
│   ├── market/                  fetch_bar, build_indicator_pack
│   ├── regime/                  classify(bar, ind, pat) -> RegimeAssessment
│   ├── signal/                  detectors (Strategy): trend_ma_cross, range_sr_bounce, …
│   ├── confirmation/            penetration / time-delay / multi-TF rules
│   ├── risk/                    stop, target, sizer (Strategy each)
│   ├── position/                Position aggregate; transition() method
│   ├── decision/                Recommendation, ReasonChain (Builder)
│   └── discipline/              specifications applied at plan-save time
├── repositories/                SQLAlchemy data access (existing template).
├── models/
│   ├── domain.py                SQLAlchemy ORM models
│   ├── schemas.py               pydantic request/response schemas
│   └── events.py                Domain event dataclasses
├── config.py
└── main.py
```

**Why `application/` is justified here and absent in other services**: other services do CRUD + one or two domain methods. This one runs a 7-stage pipeline per bar. The use case object is a *Facade* over `services/*`; that's worth one extra folder.

### 2.3 Layer rules

1. `services/*` (domain) imports only from other `services/*` and from `models/events`. **No SQLAlchemy, no httpx, no FastAPI.**
2. `application/*` imports `services/*` and depends on `repositories/*` and outbound HTTP clients **through Protocols** declared next to the use case. Concrete implementations are injected by `main.py`.
3. `api/routes.py` imports only `application/*` and `models/schemas`. Translates HTTP ↔ use case ↔ HTTP. No business logic.
4. SQLAlchemy ORM stays in `models/domain.py` and `repositories/*`. Domain value objects in `services/*` are `dataclasses(frozen=True)` or `attrs`.
5. **Domain code never reads wall-clock time.** Every function that needs "now" takes a `bar_date: date` argument. This is the backtest contract — break it and replay diverges from live.
6. **Rule enforcement (planned, not in v1):** import-linter contract will land alongside F-016 (confirmation layer), once the import graph stabilises. Until then the rules above are reviewer-enforced.

### 2.4 Design patterns — actual v1 commitments

Each pattern below is committed because we already know it pays for itself in v1 work. Speculative patterns from v1 of this ADR (State subclasses, Chain of Responsibility, Specification+Composite, Anti-Corruption Layer) are deferred — we'll reach for them only when the simple shape rots.

| Concern | Pattern | Why now |
|---|---|---|
| Signal detectors (MA cross, N-day breakout, S/R bounce, …) | **Strategy** | Each is a class with `detect(ctx) → Optional[Signal]`. Orchestrator iterates per-regime list. We need 3+ from day one (F-013/14/15). |
| Stop choice (chart / swing / ATR / money) | **Strategy** | Same shape: `propose(ctx) → Optional[Stop]`. Composed by `RiskPlanner` that tries them in declared order. No need for an explicit Chain class. |
| Target choice (S/R / measured move / trailing) | **Strategy** | Same shape. |
| Reason chain | **Builder** | Each pipeline stage appends one `(stage, message, evidence)` triple. Final `ReasonChain` is immutable; audit-friendly. |
| Position transitions | **Method on aggregate** (NOT State classes) | `Position.transition(signal, failed) → Transition` is a `match` block. ≤ 6 cases in v1. Promote to State pattern when pyramiding (Phase E) adds polymorphism. |
| Discipline checks | **Specification** (without Composite) | `PlanHasStopAndTarget.is_satisfied_by(plan) → (bool, reason)`. Combination of multiple checks is a simple list iteration. |
| Persistence | **Repository** + **Unit of Work** | Standard for this stack. UoW gives per-bar atomicity. |
| Failed-signal detectors (Ch 11, 12 of them) | *Decide in Phase E* | After 2–3 detectors land, the shape will tell us if we need Specification + Composite or a flat list of functions. Don't pre-commit. |
| Cross-service notifications | **Domain Events** (in-process) + **Observer** to RabbitMQ | Aggregates raise events; `messaging/` subscribes once and forwards. Decouples domain from message bus. |
| Per-bar pipeline | **Facade** (the one orchestrator) | Single entry point; sketch in §2.5. |

What we are **not** doing in v1: Abstract Factory, Mediator, Visitor, CQRS, event sourcing, hexagonal "ports & adapters" formalism.

### 2.5 Orchestrator sketch — corrected

Risk is recomputed **every bar** for non-FLAT positions (trailing stops/targets must update — Ch 9, 10). Only the *initial* stop is locked at entry.

```python
# application/run_decision_for_bar.py
class DecisionOrchestrator:
    """Facade. Composed by main.py via FastAPI Depends — no DI container."""

    def __init__(
        self,
        market: MarketGateway,                  # Protocol; HTTP behind it.
        indicators: IndicatorGateway,           # Protocol.
        patterns: PatternGateway,               # Protocol.
        regime: RegimeClassifier,
        signal_engine: SignalEngine,
        confirmation: ConfirmationLayer,
        failed_signal: FailedSignalChecker,
        risk_planner: RiskPlanner,
        positions: PositionRepository,
        decision_runs: DecisionRunRepository,
        events: EventBus,
    ): ...

    async def run(self, user_id: int, ticker: str, bar_date: date) -> Recommendation:
        bar = await self.market.fetch(ticker, bar_date)
        ind = await self.indicators.fetch(ticker, bar_date)
        pat = await self.patterns.fetch(ticker, bar_date)

        regime = self.regime.classify(bar, ind, pat)
        raw = self.signal_engine.detect(regime, bar, ind, pat)
        signal = self.confirmation.confirm(raw, bar, ind)
        failed = self.failed_signal.check(signal, bar, ind, pat)

        position = await self.positions.get(user_id, ticker)
        transition = position.transition(signal, failed, bar)

        # Risk is computed EVERY bar for held positions — trailing stops/targets
        # must advance. On entry, this also produces the initial stop & target.
        risk = None
        if position.state != PositionState.FLAT or transition.is_entry:
            risk = self.risk_planner.plan(position, bar, ind, pat)

        reasons = (ReasonChain.builder()
                   .stage("regime", regime)
                   .stage("signal", raw)
                   .stage("confirmation", signal)
                   .stage("failed_signal", failed)
                   .stage("transition", transition)
                   .stage("risk", risk)
                   .build())

        recommendation = Recommendation.of(transition, risk, reasons)

        await self.positions.save(position)
        await self.decision_runs.save(
            DecisionRun.from_recommendation(user_id, ticker, bar, recommendation))
        await self.events.publish_all(position.pull_events())

        return recommendation
```

**Two collaborator-naming decisions worth noting:**

- `Recommendation` is the **in-flight** value object returned by the orchestrator and the API. `DecisionRun` is the **persisted record** (one row in `decision_runs` per bar). The same data, two lifetimes.
- The orchestrator takes 11 collaborators. That is acceptable for a Facade. DI is FastAPI `Depends` driven from `main.py`'s composition root — **no DI container**.

### 2.6 Where discipline runs

Discipline checks (Ch 16, 17 — plan-has-stop, no-averaging-down, stop-not-wider-than-system) do **not** run inside the per-bar orchestrator. They run when the trader **saves a TradePlanModal** (F-060) or **edits a stop** (F-062). That path lives in `application/save_trade_plan.py` (Phase G), uses `services/discipline/`, and raises `RuleViolation` events that the journal captures.

The per-bar orchestrator emits *recommendations*. Discipline enforces *trader actions on those recommendations*. Keeping the two paths separate matches reality.

### 2.7 SLA & upstream timeouts

Target: < 2 s per `(user, ticker, bar)` recommendation.

Each upstream gateway has a per-call budget and a documented fallback. Implemented via `httpx.AsyncClient(timeout=...)` and a small `@with_fallback` decorator in `application/`.

| Gateway | Timeout | Fallback when timeout |
|---|---|---|
| `MarketGateway.fetch` (OHLCV from stock-data-service) | 800 ms | **Fail bar** — emit no recommendation; log + alert. Bar data is non-negotiable. |
| `IndicatorGateway.fetch` (analysis-service) | 500 ms | Use last-bar's cached indicator pack from Redis (TTL 26 h). |
| `PatternGateway.fetch` (ai-insights-service) | 500 ms | Empty pattern list. Recommendation downgrades to "no pattern confidence." |

If the orchestrator total exceeds 1.5 s wall-clock, it logs a `decision.slow` event for monitoring.

## 3. Database schema (F-011)

MySQL schema `stockpredict`. `user_id` is a plain column with no cross-service FK (matches the rest of the stack — JWT is the auth boundary). All money/price columns are `DECIMAL(18,4)`; sizes are `INT` (shares).

### 3.1 `user_risk_prefs`

| Column | Type | Notes |
|---|---|---|
| `user_id` | BIGINT PK | from JWT; no FK |
| `account_equity` | DECIMAL(18,2) | user-typed (Q-06 decided) |
| `risk_per_trade_pct` | DECIMAL(5,3) | default 1.0 |
| `max_concurrent_positions` | INT | default 5 |
| `max_correlation` | DECIMAL(4,3) | default 0.7 |
| `loss_streak_size_cut` | DECIMAL(4,3) | default 0.5 |
| `loss_streak_threshold` | INT | default 3 |
| `created_at`, `updated_at` | DATETIME | server defaults |

### 3.2 `position_states`

One row per `(user_id, ticker)` — v1 limit of one open leg per pair.

| Column | Type | Notes |
|---|---|---|
| `id` | BIGINT PK auto |  |
| `user_id` | BIGINT | indexed |
| `ticker` | VARCHAR(16) | uppercase |
| `state` | ENUM('FLAT','LONG','SHORT') | default FLAT; SHORT is paper-only in v1 (Q-05 — VN cash market) |
| `entry_bar_date` | DATE NULL | NULL when FLAT |
| `entry_price` | DECIMAL(18,4) NULL |  |
| `position_size` | INT | default 0 |
| `current_stop` | DECIMAL(18,4) NULL | trailing updates rewrite in place |
| `current_target` | DECIMAL(18,4) NULL |  |
| `entry_signal_kind` | VARCHAR(64) NULL | e.g. `trend.ma_cross.long` |
| `last_decision_run_id` | BIGINT NULL |  |
| `created_at`, `updated_at` | DATETIME |  |
| UNIQUE(`user_id`, `ticker`) |  | enforces v1 single-leg limit |

**Known migration cost — Phase E pyramiding (F-043):** the UNIQUE constraint above prevents multiple legs of the same (user, ticker) position. Pyramiding requires migrating to a `position_legs` table with `(user_id, ticker, leg_index)` plus a `position_summary` view. Estimated cost: 1 small migration + repo refactor. Accepted because pyramiding is **P2** and v1 should not pay for it.

Invariants (enforced in the `Position` aggregate, not in SQL):
- `state = FLAT` ⇒ entry_* and current_* are NULL.
- `state != FLAT` ⇒ entry_price, current_stop, current_target are NOT NULL.
- `current_stop` only moves in the favorable direction (Ch 9: never widen).
- `LONG ↔ SHORT` must pass through FLAT in v1.

### 3.3 `signal_history`

Append-only — every raw signal pre-confirmation. Backtest replay reads it.

| Column | Type | Notes |
|---|---|---|
| `id` | BIGINT PK auto |  |
| `ticker` | VARCHAR(16) | indexed (ticker, bar_date) |
| `bar_date` | DATE |  |
| `signal_kind` | VARCHAR(64) |  |
| `direction` | ENUM('LONG','SHORT') |  |
| `raw_confidence` | DECIMAL(4,3) |  |
| `confirmed` | BOOLEAN |  |
| `confirmation_reason` | VARCHAR(255) NULL |  |
| `regime` | ENUM('TREND_UP','TREND_DOWN','RANGE','UNDEFINED') |  |
| `features_json` | JSON | indicator snapshot |
| `created_at` | DATETIME |  |

### 3.4 `decision_runs`

One row per (user, ticker, bar). The recommendation's persisted form.

| Column | Type | Notes |
|---|---|---|
| `id` | BIGINT PK auto |  |
| `user_id` | BIGINT | indexed |
| `ticker` | VARCHAR(16) | indexed |
| `bar_date` | DATE | indexed |
| `trigger` | ENUM('SCHEDULED','ON_DEMAND','BACKTEST') | Q-15: end-of-day batch + recompute button + backtest replay |
| `regime` | ENUM(…) |  |
| `signal_kind` | VARCHAR(64) NULL |  |
| `signal_confirmed` | BOOLEAN |  |
| `failed_signal_kind` | VARCHAR(64) NULL |  |
| `action` | ENUM('BUY','SELL','SELL_SHORT','COVER','HOLD','WAIT','REVERSE') |  |
| `state_before`, `state_after` | ENUM('FLAT','LONG','SHORT') |  |
| `entry_price`, `stop_price`, `target_price` | DECIMAL(18,4) NULL |  |
| `position_size` | INT NULL |  |
| `reason_chain_json` | JSON |  |
| `confidence` | DECIMAL(4,3) |  |
| `latency_ms` | INT |  |
| `created_at` | DATETIME |  |
| UNIQUE(`user_id`, `ticker`, `bar_date`, `trigger`) |  | one row per (bar, trigger) — on-demand recompute creates a new row, doesn't overwrite the scheduled one |

### 3.5 Migrations

Alembic-managed. Initial migration `0001_decision_helper_baseline.py` creates all four tables. No data seeding — `user_risk_prefs` rows are created lazily on first preference write.

## 4. Event contracts

All events published to RabbitMQ vhost `/stock` are wrapped in the envelope below. Consumers MUST handle `event_id` for idempotency and tolerate unknown fields for forward compatibility.

### 4.1 Envelope

```json
{
  "event_id": "uuid-v4",                       // idempotency key
  "event_type": "decision.recommendation.created",
  "event_version": 1,                          // bump on breaking payload changes
  "occurred_at": "ISO-8601 UTC",
  "aggregate_id": "user_id:ticker:bar_date",   // for partitioning & dedup
  "trace_id": "...",                           // OpenTelemetry correlation
  "payload": { … }
}
```

- **Idempotency**: consumers persist `event_id` and skip duplicates. Required because RabbitMQ delivery is at-least-once.
- **Dead-letter**: each consumer queue has `x-dead-letter-exchange` configured. Messages failing > 3 retries land in `<queue>.dlq` and page on-call (Grafana alert).
- **Versioning**: payload-breaking changes increment `event_version`; consumers should branch on version, not silently accept.

### 4.2 Event types

| Event type | Aggregate | Payload highlights | Consumers |
|---|---|---|---|
| `decision.recommendation.created` | DecisionRun | run_id, user_id, ticker, bar_date, action, stop, target, size, reason_chain, trigger | frontend WebSocket, journal-service (auto-draft) |
| `decision.signal.failed` | Signal | signal_kind, failure_kind, ticker, bar_date | journal-service, analytics |
| `decision.stop.triggered` | Position | position_id, user_id, ticker, stop_price, fill_price | journal-service, portfolio-service |
| `decision.target.hit` | Position | position_id, user_id, ticker, target_price, fill_price | journal-service, portfolio-service |
| `decision.position.transitioned` | Position | from_state, to_state, reason | analytics |

In-process domain events are flushed only on successful UoW commit — no half-emitted events on rollback.

## 5. Testing strategy

- **Unit (pure)**: every `services/*` module; no DB, no HTTP. Indicator math, transitions, specifications. Aspiration: high domain coverage; numbers tracked in CI but not gated.
- **Use case**: orchestrator + fakes for the gateway protocols. One test per branch (trend long, trend short, range bounce long, range breakout long, failed-signal reversal).
- **Integration**: real MySQL via `docker-compose.test.yml`; covers repositories + a thin orchestrator slice.
- **Contract**: gateway clients tested against recorded analysis-service / ai-insights-service responses (pytest-recording).
- **Backtest harness** (Phase F) doubles as a system regression: replay one year of bars → identical trade ledger across runs.

## 6. Non-goals (v1)

- No order execution. Helper only recommends.
- Daily bars only.
- ≤ 30 tickers per user per bar.
- VN cash market: SHORT state is **paper-only** — recommendations exist, fills don't.
- ML predictions are advisory-only — never used in stop/target/size/state transitions.
- No CQRS, no event sourcing, no DI container, no hexagonal formalism.

## 7. Open questions

**Not duplicated here.** See `road_map_version_11.xlsx → Risks_Open_Questions`. Items still **Open** that block F-010: Q-02 (bar frequency), Q-04 (universe cap), Q-07 (pattern detector source), Q-08 (multi-timeframe), Q-14 (auth). The assumed answers in that sheet are what F-010 will encode — flag any you want changed before F-010 PR opens.

## 8. Implementation order (top 5)

This ADR locks the structure. The first five backlog items map onto it:

1. **F-001** ATR — `analysis-service` extension. **Done** (2026-05-16).
2. **F-002** Swing pivots — `analysis-service` extension. **Done** (2026-05-16).
3. **F-003** S/R typed object refactor — `analysis-service` extension.
4. **F-010** decision-helper-service bootstrap — `main.py`, `api/routes.py` (health only), `config.py`, Dockerfile, Traefik label, deploy.sh wiring; empty `application/` and `services/<context>/` folders from §2.2.
5. **F-011** DB schema — Alembic migration from §3 + SQLAlchemy models in `models/domain.py` + Repository interfaces in `repositories/`. No business logic yet.

## 9. What changed from v1 (changelog)

| # | Change | Reason |
|---|---|---|
| 1 | Dropped hexagonal `domain/ + application/ + infrastructure/` layout for a smaller deviation from the existing template: keep `services/repositories/models`, add only `application/`, split `services/` by bounded context. | v1 was inconsistent with the other nine services. (Review finding #2) |
| 2 | Removed State subclasses, Chain of Responsibility, Specification+Composite, ACL from v1 commitments. Kept Strategy, Builder, Repository+UoW, Domain Events, Specification (uncomposed). | Premature abstractions. (#1) |
| 3 | Failed-signal detector pattern choice **deferred to Phase E.** | Decide when we have 2–3 implementations to compare. (#1) |
| 4 | Orchestrator sketch fixed: risk is recomputed **every bar** when position ≠ FLAT, not only on entry. | Trailing stops/targets need it. (#4) |
| 5 | Added §2.6 — discipline runs at plan-save, not in the per-bar orchestrator. | v1 implied discipline was in the orchestrator. (#9) |
| 6 | Added §2.7 — per-upstream timeout budgets + fallbacks. | SLA was unenforceable without it. (#8) |
| 7 | Added §4.1 — event envelope with `event_id` (idempotency), `event_version`, dead-letter policy. | Consumers couldn't be written safely. (#6) |
| 8 | Schema: dropped FK from `user_risk_prefs.user_id` to auth-service. Added `trigger` column + UNIQUE on `decision_runs(user, ticker, bar, trigger)`. Documented pyramiding migration cost on `position_states`. | Match stack convention; Q-15; #3. |
| 9 | Added §6 line on SHORT being paper-only in VN cash. | (#11) |
| 10 | Moved open questions to a pointer at §7 instead of duplicating. | ADRs record decisions, not questions. (#5) |
| 11 | Added layer rule 5: domain code never reads wall-clock time. | Backtest contract. (#14) |
| 12 | Stated DI mechanism: FastAPI `Depends` + composition root in `main.py`; no DI container. | (#13) |
| 13 | import-linter downgraded from "enforced" to "planned, lands with F-016." | Was aspirational. (#12) |
| 14 | Distinguished `Recommendation` (in-flight) vs `DecisionRun` (persisted) in §2.5. | (#10) |
