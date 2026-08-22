# Instrumentation Plan — Capturing the Data AI Features Need

**Date:** 2026-08-17
**Prerequisite reading:** [`00-codebase-assessment.md`](./00-codebase-assessment.md) §5
**Target:** microservices (`back_end/services/` + `back_end/shared/`). Do **not** implement any of this in the monolith `back_end/app/` — it is not deployed.

---

## Why this comes before any AI feature

Four signals that seller AI features depend on are currently either **never captured** or **overwritten in place**. Unlike a missing endpoint, this data cannot be backfilled — a search that wasn't logged is gone, and a price that was overwritten leaves no trace. Every week the platform runs without this instrumentation is a week of permanently lost history.

The timing argument is unusually favourable right now:

- **Pre-launch means near-zero migration risk.** No production rows to migrate, no downtime to schedule, no backfill to reconcile.
- **Collection starts with the first real user**, so by the time forecasting and pricing become viable (6–12 months post-launch), the history already exists.
- The work is small — roughly **400–600 lines total across four PRs**, with no changes to existing business logic beyond adding writes.

The cost of deferring is not "we do it later." It is "the models we want in month 9 cannot be built until month 18."

---

## P0 blocker: the Alembic chain was broken — ✅ FIXED 2026-08-17

Every PR below adds a migration, so this had to be fixed first. It has been; the detail is kept here because it explains why the migration files cannot be trusted as a record of the schema.

`migrations/versions/2026_03_02_add_product_videos.py:17` declares:

```python
down_revision = '2026_01_24_seller_category_to_products'
```

But the revision it points at declares its own id as (`2026_01_24_add_seller_category_to_products.py:16`):

```python
revision = '2026_01_24_seller_category_products'    # note: no "to"
```

No revision with the id `2026_01_24_seller_category_to_products` exists, so **`alembic upgrade head` fails** with `Can't locate revision identified by ...`. The full set of declared ids is:

```
2026_01_14_product_enhancements   (down_revision = None)
2026_01_21_order_status_history
2026_01_23_seller_categories
2026_01_24_seller_category_products      ← chain breaks here
2026_03_02_add_product_videos            ← points at a non-existent id
```

**Why nobody noticed:** the schema isn't actually built by Alembic. Every service calls `Base.metadata.create_all()` on startup — `services/product/app/main.py:25`, `services/order/app/main.py:24`, `services/chat/app/main.py:24`, and `services/auth/app/main.py:27` via `shared.database.init_db()`. `create_all` silently creates any missing tables, so the migrations are effectively decorative and their breakage is invisible.

**Two consequences that shape this plan:**

1. **New tables will auto-create on deploy** without a migration ever running. Convenient pre-launch — but it means the migration files must be treated as the source of truth for production *before* real data exists, not after.
2. **`create_all` never ALTERs.** It only creates missing tables. Any change to an *existing* table (a new column, an index) requires a working migration path. All four PRs below are new-table-only precisely to stay clear of this — a deliberate design constraint, not a coincidence.

**Second defect, same area:** `migrations/env.py:11-12` binds `target_metadata` to the **monolith's** models:

```python
from app.core.database import Base
from app.models import *
```

So `alembic revision --autogenerate` would diff against the dead model set and produce wrong migrations. Repoint it to `shared.database.Base` / `shared.models` as part of the P0 fix, or hand-write every migration (which is what has been done so far).

### What was changed

A 4-line diff across two files:

| File | Change |
|---|---|
| `migrations/versions/2026_03_02_add_product_videos.py` | `down_revision` → `'2026_01_24_seller_category_products'` (and the matching docstring line) |
| `migrations/env.py` | `from app.core.database import Base` → `from shared.database import Base`; `from app.models import *` → `import shared.models` |

The `down_revision` pointer was corrected rather than renaming the target revision's id. That direction matters: if any database has already recorded `2026_01_24_seller_category_products` in its `alembic_version` table, renaming the revision would orphan that row, whereas fixing the pointer leaves recorded state valid.

**Verified.** `alembic history` previously raised `KeyError: '2026_01_24_seller_category_to_products'`; it now exits 0 with a single linear head:

```
<base> -> 2026_01_14_product_enhancements
       -> 2026_01_21_order_status_history
       -> 2026_01_23_seller_categories
       -> 2026_01_24_seller_category_products
       -> 2026_03_02_add_product_videos (head)
```

`alembic heads` reports one head, no branches. `Base.metadata` now resolves the **17 live tables** from `shared/models`. Not yet verified against a real database — the stack was down during this work, so `alembic upgrade head` should be run once against an empty schema before relying on it.

### ⚠️ Hazard the repoint exposes: do not run `--autogenerate` blind

Pointing `env.py` at `shared` makes autogenerate correct about the deployed models — and simultaneously reveals a discrepancy it will try to "fix" destructively.

The `2026_01_14_add_product_enhancements` revision creates **seven tables that no live model maps**:

```
brands, product_variants, price_history,
product_tags, product_tag_associations,
product_attributes, product_specifications
```

They exist in the database (created by that migration) but are absent from `shared/models` metadata. **`alembic revision --autogenerate` will therefore propose `op.drop_table()` for all seven.** One of them is `price_history` — the table PR 2 is about to start using.

Two consequences:

- **Always read a generated migration before applying it.** Delete any `drop_table` for those seven unless dropping them is genuinely intended.
- **PR 2 partially resolves this.** Adding the `PriceHistory` model to `shared/models` puts `price_history` back into the metadata, so it stops appearing as an orphan. The other six remain orphaned and should be either modelled or deliberately dropped in their own migration — a decision worth making explicitly rather than letting autogenerate make it by accident.

---

## Reliability classes — an important distinction

The four instruments split into two groups that deserve **different failure behaviour**, and conflating them is the main way this work goes wrong:

| Class | Instruments | Failure behaviour | Rationale |
|---|---|---|---|
| **Ledger** (must be exact) | `price_history`, `stock_movements` | Same DB transaction as the mutation. If the log write fails, the mutation fails. | A ledger that silently diverges from the value it tracks is worse than no ledger — it produces confidently wrong analysis. |
| **Telemetry** (best-effort) | `search_logs`, `product_view_events` | Fire-and-forget. Wrapped in `try/except`, never raises, never blocks the response. | A dropped view event costs one row out of millions. Failing a buyer's search because a log write timed out is unacceptable. |

Apply this consistently. It is the single most important design decision in this plan.

---

## PR 1 — `search_logs` (highest priority) — ✅ IMPLEMENTED 2026-08-17

**Files:** `shared/models/analytics.py` (new), `shared/models/__init__.py`, `services/product/app/services/search_logging.py` (new), `services/product/app/routers/products.py`, `migrations/versions/2026_08_17_add_search_logs.py` (new). The router diff is purely additive — no existing logic changed.

**Verified** by an end-to-end test against SQLite (22 assertions, all passing): real HTTP requests through the mounted router, asserting rows land with correct normalisation, totals, filters, and attribution. Two model defects surfaced and were fixed during that run:

- `BigInteger` primary keys do not auto-increment on SQLite (only `INTEGER` does). Fixed with `BigInteger().with_variant(Integer, "sqlite")` so the model stays testable — which matters given the pytest recommendation below.
- `sa.JSON` stores Python `None` as JSON `null`, not SQL `NULL`, so `WHERE filters IS NULL` would silently match nothing. Fixed with `JSON(none_as_null=True)`.

**Still outstanding:** the retention purge is documented (below) but **not scheduled** — there is no job runner. Until one exists it must be run manually or via an external cron:

```sql
-- Retain query_norm + result_count indefinitely; drop the raw text and
-- device id after 90 days.
UPDATE search_logs
   SET query_text = NULL, anon_id = NULL
 WHERE created_at < NOW() - INTERVAL 90 DAY
   AND (query_text IS NOT NULL OR anon_id IS NOT NULL);
```

---


**Unblocks:** opportunity/assortment finder (its *only* signal), plus better ranking and query understanding for the listing optimizer and pricing advisor.

**Why first:** it is the only instrument whose target feature has *no* alternative data source whatsoever. Views have a crude counter, prices are partially recoverable from `order_items.unit_price`, stock is partly derivable from orders. Buyer search intent is recorded nowhere, in any form.

### Table

```sql
CREATE TABLE search_logs (
  id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  query_text     VARCHAR(500)  NULL,          -- raw, as typed
  query_norm     VARCHAR(500)  NULL,          -- lowercased/trimmed, for grouping
  filters        JSON          NULL,          -- category, price range, material, colour, ...
  result_count   INT           NOT NULL,      -- 0 = the money signal
  source         VARCHAR(20)   NOT NULL,      -- 'basic' | 'advanced'
  user_id        INT           NULL,          -- NULL for anonymous
  anon_id        VARCHAR(64)   NULL,          -- client-generated, for anonymous sessions
  created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_search_logs_created (created_at),
  INDEX ix_search_logs_norm    (query_norm),
  INDEX ix_search_logs_zero    (result_count, created_at)   -- zero-result queries
);
```

`query_norm` exists so `GROUP BY` gives useful aggregates without normalising 100k rows at query time. The `(result_count, created_at)` index makes "what did buyers search for last month and find nothing?" — the assortment-gap query — a fast index scan.

### Call sites

Both in `services/product/app/routers/products.py`:

| Line | Function | Note |
|---|---|---|
| ~139 | `read_products(... search=...)` | log only when `search` is non-empty |
| ~527 | `advanced_search(q=...)` | log always — filter-only searches are signal too |

Log **after** the query executes (`result_count` is needed) but **outside** the response path — use FastAPI `BackgroundTasks`, consistent with how `services/auth/app/routers/auth.py` already handles email.

Both endpoints already accept an optional user via the existing `get_optional_current_user` dependency pattern, so attributing logged-in searches needs no auth changes.

### Two traps

1. **Cache ordering.** Neither search endpoint is cached today, but `shared/cache.py` already defines `CacheKeys.products_list(skip, limit, **filters)` — so caching is clearly anticipated. If it is ever added, **the log write must sit before the cache lookup**, or every cache hit becomes an invisible search and the data quietly skews toward rare queries.
2. **Debounced typing.** If the client fires a request per keystroke, you will log `"v"`, `"va"`, `"vas"`, `"vase"`. Either debounce client-side in `SearchScreen.jsx` before calling, or drop queries shorter than 3 characters server-side. Without this, `query_norm` aggregates are dominated by prefixes.

### Privacy

Search text is user-authored content and can contain anything. Decide retention **now**, before the table exists: recommend keeping `query_norm` + `result_count` indefinitely (that's the analytical value) and purging `query_text` and `anon_id` after 90 days. Add it to the privacy policy alongside launch.

**Effort:** ~120 lines (model, migration, 2 call sites, a purge query). Half a day.

---

## PR 2 — `price_history` writes — ✅ IMPLEMENTED 2026-08-17

**No migration needed** — the table was already created by `2026_01_14_add_product_enhancements`; this PR only added the model and the writes. Alembic head is unchanged.

`variant_id` is modelled as a plain `Integer` with **no** `ForeignKey`, even though the table has one to `product_variants`. Declaring the FK would make `create_all()` fail resolving a table that isn't in the live metadata (there is no `ProductVariant` model). The column stays permanently NULL until variants are modelled.

**As predicted, this reduced the autogenerate orphan set from seven tables to six** — `price_history` is now mapped. The remaining six (`brands`, `product_variants`, `product_tags`, `product_tag_associations`, `product_attributes`, `product_specifications`) still need a deliberate model-or-drop decision.

**Known limitation:** `create_product` commits the product before adding the origin row (the pre-existing code commits early to obtain the ID). If the origin insert fails, the product exists without one and the request errors — visible, not silent, but not strictly atomic. The two *change* paths (`update_product`, `bulk_update_product_prices`) are fully atomic, which is what the ledger contract actually requires.

---


**Unblocks:** dynamic pricing (elasticity), plus discount-effectiveness analysis.

The `price_history` **table already exists** — created by `2026_01_14_add_product_enhancements` — and a `PriceHistory` model exists in the monolith (`app/models/product.py:146`). Neither is reachable from deployed code: `shared/models/product.py` doesn't define it, and **no INSERT exists anywhere in the repo**, in either tree. So this PR is mostly *wiring*, not new schema.

### Work

1. Port `PriceHistory` into `shared/models/product.py` (columns already defined by the existing migration: `product_id`, `variant_id`, `old_price`, `new_price`, `change_reason`, `changed_by`, `created_at`). Drop `variant_id` or leave it nullable — the live schema has no `ProductVariant`.
2. Register it in `shared/models/__init__.py`.
3. Write on **every** price mutation, in the same transaction as the change.

### Call sites

| File | Line | Function | Difficulty |
|---|---|---|---|
| `services/product/app/routers/products.py` | ~315 | `update_product` | Easy — object is loaded; capture `product.price` before `setattr` |
| `services/seller/app/routers/dashboard.py` | ~611 | `bulk_update_product_prices` | **Needs restructuring — see below** |
| `services/product/app/routers/products.py` | ~108 | `create_product` | Write an origin row (`old_price = new_price`, reason `initial`) |

**The bulk path needs care.** It currently does:

```python
result = db.query(Product).filter(...).update({"price": update["price"]})
```

`Query.update()` issues raw SQL and **does not load the objects**, so the old price is never in memory and cannot be captured after the fact. The products *are* already loaded a few lines above for the ownership check — reuse that list to read old prices before issuing the update, rather than adding a second SELECT.

**Seed the origin row.** Without a `create_product` entry, the first price change produces a history that begins mid-story, and any "price at time T" reconstruction before that change returns nothing. One row at creation avoids a whole class of off-by-one analysis bugs.

**Effort:** ~100 lines. Half a day.

---

## PR 3 — `product_view_events`

**Unblocks:** conversion rate (currently hardcoded to `0` and shipped to sellers), view-based trending, per-SKU funnel, and the demand side of pricing.

Today `POST /products/{id}/view` (`services/product/app/routers/products.py:253`) does exactly:

```python
product.view_count = (product.view_count or 0) + 1
```

One monotonic integer, no time dimension. It *is* correctly wired from the client (`ProductDetailsScreen.jsx:78`) — the plumbing works, only the storage is wrong.

### Table

```sql
CREATE TABLE product_view_events (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  product_id  INT          NOT NULL,
  user_id     INT          NULL,
  anon_id     VARCHAR(64)  NULL,
  source      VARCHAR(30)  NULL,      -- 'search' | 'category' | 'related' | 'featured' | 'direct'
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_pve_product_created (product_id, created_at),
  INDEX ix_pve_created (created_at)
);
```

`source` is worth capturing from day one — "which surface actually drives views" is a question sellers ask immediately, and it is free to record now and impossible to recover later.

### Then fix the two lies

Once events exist, replace the hardcoded zeros flagged in the assessment:

- `services/product/app/services/product_analytics.py:49` — `view_count = 0`
- `services/seller/app/routers/analytics.py` (`performance-metrics`) — `product_views_total = 0`

Both currently cause `conversion_rate` to render as `0` for every seller regardless of reality. **This is the one user-visible bug this plan fixes**, and it is worth calling out in release notes.

### Design decisions

- **Keep `products.view_count`** as a denormalised counter (cheap, and `products.py:277` returns it). Increment both. Treat the event table as the source of truth for anything analytical.
- **Deduplicate.** The endpoint fires on every `ProductDetailsScreen` mount, so back-navigation and pull-to-refresh inflate counts. Suppress repeat events for the same `(product_id, user_id|anon_id)` within ~30 minutes — a Redis `SETNX` with TTL is the natural fit, and Redis is already a dependency.
- **Plan for volume.** This will be the largest table in the system by an order of magnitude. It does not matter pre-launch, but add a **daily rollup** (`product_view_daily`: product_id, date, views, uniques) before it reaches tens of millions of rows, and keep raw events on a retention window.

**Effort:** ~150 lines including the two analytics fixes. One day.

---

## PR 4 — `stock_movements` ledger

**Unblocks:** demand forecasting (correctly), restock recommendations, and stockout analysis.

**Why this is not optional for forecasting.** Today `quantity_available` is mutated in place with no record. That makes "sold zero units last week" indistinguishable from "was out of stock all week." A forecasting model trained on censored demand read as zero demand learns to **under-order exactly the items that sell best** — a failure that is self-reinforcing and hard to detect once deployed. The ledger is what makes the difference observable.

### Table

```sql
CREATE TABLE stock_movements (
  id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  product_id     INT          NOT NULL,
  delta          INT          NOT NULL,      -- signed: -3 sold, +50 restocked
  balance_after  INT          NOT NULL,      -- for audit / drift detection
  reason         VARCHAR(30)  NOT NULL,      -- 'order_placed'|'order_cancelled'|'restock'|'manual_adjustment'
  order_id       INT          NULL,
  actor_id       INT          NULL,          -- NULL for system-driven
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_sm_product_created (product_id, created_at)
);
```

`balance_after` is redundant by construction — which is the point. It lets you detect divergence between the ledger and `products.quantity_available` with a single query, catching any mutation path someone forgets to instrument.

### Call sites (all five must be covered)

| File | Line | Context | Reason code |
|---|---|---|---|
| `services/order/app/routers/orders.py` | ~83 | `create_order` decrement | `order_placed` |
| `services/order/app/routers/orders.py` | ~165 | `cancel_order` restore | `order_cancelled` |
| `services/order/app/routers/orders.py` | ~256 | `checkout_from_cart` decrement | `order_placed` |
| `services/product/app/routers/products.py` | ~315 | `update_product` when `quantity_available` changes | `manual_adjustment` |
| `services/product/app/routers/products.py` | ~766 | `bulk_update_stock` | `restock` |

**`bulk_update_stock` has the same `Query.update()` problem as PR 2** — it never loads the objects, so the prior balance isn't available. It also already loads the products for the ownership check; reuse that list.

**Miss any one of these five and the ledger is wrong** — which is precisely why `balance_after` earns its place.

**Note the semantic gap:** `bulk_update_stock` sets an *absolute* quantity, not a delta. Whether a seller setting stock from 3 to 50 means "received a 47-unit shipment" or "corrected a counting error" is genuinely ambiguous, and the API cannot tell. Record it as `restock` with the computed delta, and consider adding an optional reason field to the endpoint later.

**Effort:** ~180 lines across two services. One to one and a half days.

---

## Sequencing and effort

| PR | Instrument | Unblocks | Effort | Priority |
|---|---|---|---|---|
| ~~**P0**~~ | ~~Fix Alembic chain + `env.py`~~ | everything below | — | ✅ **Done** |
| ~~**1**~~ | ~~`search_logs`~~ | Opportunity finder (sole signal) | — | ✅ **Done** |
| ~~**2**~~ | ~~`price_history` writes~~ | Dynamic pricing | — | ✅ **Done** |
| **3** | `product_view_events` | Conversion, trending, funnel | 1 d | High |
| **4** | `stock_movements` | Forecasting, restock | 1–1.5 d | Medium-High |

**Total: roughly 3.5–4 days of engineering** to permanently unblock four of the six candidate AI features.

PRs 1–4 are mutually independent after P0 and can be parallelised or landed in any order. The ordering above reflects *irrecoverability* — PR 1 first because search intent has no alternative source, PR 2 next because it is nearly free (the table and model already exist).

---

## Cross-cutting concerns

**Do not add these to the monolith.** `back_end/app/` is not deployed. Adding models there widens the existing drift (assessment §1) for zero benefit. If the monolith is ever revived, port then.

**Model placement.** Suggest `shared/models/analytics.py` for `search_logs` + `product_view_events` (telemetry), `price_history` into the existing `shared/models/product.py`, and `stock_movements` into `shared/models/inventory.py`. All must be imported in `shared/models/__init__.py` or `create_all()` won't see them.

**Autogenerate is now usable but not safe unattended.** `env.py` points at `shared` (P0), so generated migrations diff against the deployed models — but every generated file must be read before applying, because of the seven orphan tables described above. Hand-writing remains the safer default for these four PRs, all of which are single-table and trivial to write by hand.

**Testing — ✅ done.** `pytest` is now set up (`back_end/pytest.ini`, `back_end/tests/`), running against in-memory SQLite so it needs no MySQL or Redis, plus a `backend-tests` job in `.github/workflows/test.yml`. **24 tests passing**, covering PR 1 and PR 2.

Collection is scoped to `tests/` so the legacy `back_end/test_*.py` smoke scripts (which need a live server) are not picked up.

One structural gotcha is handled by a `load_service()` fixture: every service — and the legacy monolith — exposes a top-level `app` package, so only one can be importable at a time, and the loser resolves to the wrong module **silently, with no import error**. Tests are grouped per service and each client fixture re-points `app` before importing. Verified to pass in both collection orders.

Ledger correctness is exactly what needs regression tests: `test_ledger_write_failure_rolls_back_the_price_change` and `test_ledger_matches_products_after_bulk_update` already encode the invariant, and the equivalent for PR 4 ("does cancelling an order write a compensating stock movement") is now a few lines.

**No backfill is possible** for any of the four. Every row starts accumulating from deploy day. This is the entire argument for doing it now.

---

## Verification

After deploying all four, these should return rows within a day of real traffic:

```sql
-- PR1: the assortment-gap query the opportunity finder is built on
SELECT query_norm, COUNT(*) AS searches
FROM search_logs
WHERE result_count = 0 AND created_at >= NOW() - INTERVAL 30 DAY
GROUP BY query_norm ORDER BY searches DESC LIMIT 50;

-- PR2: every price change leaves a trace
SELECT p.id, p.name, COUNT(ph.id) AS changes, MAX(ph.created_at) AS last_change
FROM products p LEFT JOIN price_history ph ON ph.product_id = p.id
GROUP BY p.id, p.name HAVING changes > 0;

-- PR3: conversion is finally computable
SELECT v.product_id, COUNT(DISTINCT v.id) AS views, COALESCE(SUM(oi.quantity),0) AS units
FROM product_view_events v
LEFT JOIN order_items oi
  ON oi.product_id = v.product_id AND oi.created_at >= NOW() - INTERVAL 30 DAY
WHERE v.created_at >= NOW() - INTERVAL 30 DAY
GROUP BY v.product_id;

-- PR4: ledger drift detector — MUST return zero rows
SELECT p.id, p.quantity_available, SUM(sm.delta) AS ledger_sum
FROM products p JOIN stock_movements sm ON sm.product_id = p.id
GROUP BY p.id, p.quantity_available
HAVING p.quantity_available <> ledger_sum;
```

The last query is worth running on a schedule once a scheduler exists — it is a standing correctness check on the instrument that forecasting will depend on most.

---

## What this plan does *not* do

- It does not add a **scheduler or job queue** — still absent (assessment §3), still required before any batch or nightly AI work.
- It does not add an **LLM client or Ollama integration** — that belongs with the first AI feature, not with instrumentation.
- It does not fix the **dual-backend drift**, the **shared-database coupling**, or the **broken frontend endpoint calls** — all real, none blocking here.
- It does not add **`ai-service`** itself. That comes next, and by then it will have data worth reading.
