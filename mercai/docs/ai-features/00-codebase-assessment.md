# Mercai — Codebase Assessment for Seller AI Features

**Date:** 2026-08-17
**Branch assessed:** `rename/mercai` @ `83d373d0`
**Scope:** read-only investigation. No code was modified.

**Assumptions confirmed with the product owner before writing:**

1. The production database currently holds **pre-launch / test data only** — no real behavioural history.
2. New AI work targets the **microservices** layout (`back_end/services/`), not the monolith.
3. LLM inference will be **self-hosted (local Ollama)**.

These three answers drive the feature ranking in §7 more than anything in the code does.

---

## 1. Repo structure

One git repository, informally organised as a monorepo. There is no workspace tooling (no npm workspaces, no Lerna/Nx, no Python workspace) — each sub-project is independent and built separately.

```
mercai/
├── back_end/               FastAPI. Contains TWO parallel implementations (see below)
│   ├── app/                  Monolith — 12 routers, own SQLAlchemy Base       [NOT DEPLOYED]
│   ├── services/             5 microservices: auth, product, order, chat, seller  [DEPLOYED]
│   ├── shared/               Models, DB, security, config, cache, metrics — mounted into every service
│   ├── migrations/versions/  Alembic, 5 revisions
│   ├── monitoring/           Prometheus / Grafana / Loki / Alertmanager configs
│   ├── nginx/, traefik/      Reverse proxy + gateway config
│   └── docker-compose.yml    The authoritative deployment definition
├── front_end/              React Native (Expo) mobile app — JavaScript, not TypeScript
├── mobile_automation_test/ Detox + Maestro E2E suites
├── docs/, documents/       Feature docs, user guide, architecture notes, roadmap
└── .github/workflows/      CI — frontend only
```

### The dual-backend situation

This is the single most important structural fact about the repo.

`back_end/app/` and `back_end/services/` are **two implementations of the same product**, each with its own SQLAlchemy `Base` and its own copy of every model. `docker-compose.yml` builds and runs **only** `services/`. The monolith has no compose service, no Traefik labels, and no route to it — it is reachable only by running `run.py` manually.

The two model sets have **drifted apart**, and not in one direction:

| Model area | Monolith `app/models/` | Live `shared/models/` |
|---|---|---|
| `Product.slug`, `original_price`, `discount_percentage` | ✅ present | ❌ absent |
| `Product.view_count` | ❌ absent | ✅ present |
| `ProductVariant`, `PriceHistory`, `Brand`, `ProductTag`, `ProductAttribute`, `ProductSpecification` | ✅ defined | ❌ not defined |
| `ProductVideo` | ❌ absent | ✅ present |
| `OrderStatusHistory` | ❌ absent | ✅ present |
| `SellerCategory` (per-seller category tree) | ⚠️ referenced but never imported | ✅ present |

So the richer product schema (variants, price history, brands, attributes) lives **only in the code path that is not deployed**. This matters enormously for §5 — several data structures that look available on a quick read are not actually in the live system.

### Build & deploy

- **Backend:** `docker compose up` — Traefik v2.11 gateway (`:8002`→`:80`), MySQL 8.0, Redis 7, and 5 service containers. Routing is by Traefik `PathPrefix` labels, not by a config file. `deploy-microservices.sh`, `manage.sh`, and a `Makefile` wrap the lifecycle.
- **Monitoring:** a separate `docker-compose.monitoring.yml` with a genuinely complete stack — Prometheus 2.47, Grafana 10.1, Alertmanager, node-exporter, cAdvisor, redis_exporter, mysqld_exporter, blackbox-exporter, Loki 2.9 + Promtail.
- **Frontend:** Expo / EAS (`eas.json`) — built as a mobile app binary, not deployed as a website.
- **No Kubernetes.** No Helm, no manifests, no k8s references anywhere.

---

## 2. Stack & versions

### Backend

| Component | Version |
|---|---|
| Python | 3.11-slim (all service Dockerfiles) |
| FastAPI | 0.116.1 |
| SQLAlchemy | 2.0.43 (declarative, **sync** sessions) |
| Pydantic | 2.11.7 + pydantic-settings 2.10.1 |
| Uvicorn / Gunicorn | 0.35.0 / 23.0.0 |
| Alembic | 1.14.0 |
| MySQL driver | PyMySQL 1.1.2 |
| Redis client | redis 5.0.1 (+ an unused `aioredis` 2.0.1) |
| Auth | python-jose 3.5.0 (JWT), passlib 1.7.4 (bcrypt) |
| Imaging | Pillow 11.3.0 |

Package manager is plain `pip` + `requirements.txt` (one per service plus a root one). **There is no `pyproject.toml`, no linter, no formatter, and no type checker configured** — no ruff, black, flake8, isort, or mypy config exists anywhere in the repo.

### Frontend

| Component | Version |
|---|---|
| React | 19.1.0 |
| React Native | 0.81.4 |
| Expo | ~54.0.0 |
| Redux Toolkit | ^2.0.1 (+ redux-persist 6) |
| React Navigation | ^6 (stack + bottom-tabs + drawer) |
| axios | ^1.6.2 |
| UI | react-native-paper 5, react-native-elements 3.4 |
| Forms | react-hook-form 7.48 |

Written in **JavaScript (`.jsx`), not TypeScript** — `src/types/*.js` are plain constant objects, not type definitions. Package manager is npm (`package-lock.json`).

### Test setup

- **Frontend:** Jest 29 + `jest-expo` + `@testing-library/react-native`. Real but thin — 4 component tests, 2 auth screen tests, 2 seller screen tests, 1 integration test. Detox 20 + Maestro suites live in `mobile_automation_test/`.
- **Backend: no unit test framework at all.** No pytest, no `conftest.py`, no fixtures. The `back_end/test_*.py` files are standalone `requests`-driven smoke scripts that require a running server and a live database (`test_requirements.txt` is just `requests` + `colorama`).
- **CI** (`.github/workflows/test.yml`): frontend Jest unit + integration on every push/PR; Detox iOS/Android E2E gated to `main` or a `run-e2e` label. **No Python job whatsoever** — backend changes are never checked by CI.

---

## 3. Backend

### Service topology

| Service | Port | Traefik PathPrefix | Routers |
|---|---|---|---|
| auth | 8001 | `/api/v1/auth`, `/api/v1/users` | auth (406 L), users (266 L) |
| product | 8002 | `/api/v1/products`, `/api/v1/reviews` | products (950 L), reviews (226 L) |
| order | 8003 | `/api/v1/orders`, `/api/v1/cart` | orders (279 L), cart (241 L) |
| chat | 8004 | `/api/v1/chat` | chat (257 L, incl. WebSocket) |
| seller | 8005 | `/api/v1/seller`, `/static/uploads` | dashboard (907 L), analytics (644 L), categories (951 L), order_fulfillment (965 L), profile (603 L), bulk_operations (98 L) |

**These are not bounded contexts.** All five services connect to the *same* MySQL database (`mercai`) and import the *same* `shared/models` package, which is bind-mounted into every container. The seller service queries `products`, `orders`, `reviews`, and `users` tables directly; the product service queries `reviews` and `seller_profiles`. In practice this is a modular monolith with HTTP boundaries and a shared schema. That is worth knowing before adding a sixth service — the path of least resistance is to keep doing exactly this, and it works, but it means "which service owns this table" is not a question the codebase answers.

`AUTH_SERVICE_URL` / `PRODUCT_SERVICE_URL` / `ORDER_SERVICE_URL` are injected as env vars but there is **no HTTP client code** using them — no `httpx`, no inter-service calls. All cross-domain access is via the shared database.

### Data models (ORM)

SQLAlchemy 2.0 declarative in `shared/models/`, one module per aggregate: `user`, `product`, `order`, `cart`, `chat`, `review`, `address`, `seller_profile`, `seller_category`. Integer surrogate PKs, `Numeric(10,2)` for money, `DateTime(timezone=True)` with `server_default=func.now()`.

Pydantic v2 schemas are duplicated per service under `services/*/app/schemas/`. Some legacy v1 idioms remain (`.dict()`, `from_orm`).

### Database & migrations

MySQL 8.0, `utf8mb4`. **The migration regime is mixed and inconsistent:**

- Alembic exists with 5 revisions (`product_enhancements`, `order_status_history`, `seller_categories`, `seller_category_to_products`, `product_videos`).
- But `shared/database.init_db()` calls `Base.metadata.create_all()`, and the monolith's `main.py` calls `create_tables()` on startup.
- The monolith also runs `initialize_test_data()` on startup, which seeds test users into whatever database it points at.

Consequence: the physical schema is whatever the union of these produced. Notably, the `2026_01_14_add_product_enhancements` migration **creates the `price_history`, `product_variants`, `brands`, `product_tags`, `product_attributes`, and `product_specifications` tables** — so those tables likely exist in the database, while **no deployed service maps or writes to any of them**. They are almost certainly empty.

### Authentication & authorisation

- JWT via `shared/security.py` — HS256, separate access and refresh tokens with a `type` claim, `OAuth2PasswordBearer`. Password policy enforced (length, upper, lower, digit, special) and bcrypt hashing.
- `get_current_user` / `get_optional_current_user` are the FastAPI dependencies.
- Roles are a 3-value enum: `CUSTOMER`, `SELLER`, `DUAL` (`User.is_seller` covers seller+dual).
- **Authorisation is ad-hoc and repeated inline**, not dependency-based. The pattern `if current_user.role not in [UserRole.SELLER, UserRole.DUAL]: raise HTTPException(403)` is copy-pasted into essentially every seller endpoint, and ownership is re-checked per-endpoint with `filter(Product.seller_id == current_user.id)`. Tenant isolation is correct where I checked it, but it depends entirely on every author remembering the filter — there is no guard rail.

### Async patterns

Effectively **synchronous**. Endpoints are declared `def` (not `async def`) and use blocking SQLAlchemy sessions, so FastAPI runs them in its threadpool. The only genuinely async code is the chat WebSocket endpoint (`ConnectionManager` in `services/chat/app/services/websocket_manager.py`) and two file-upload handlers. There is no async DB driver.

### Background jobs / queues

**None.** This is a material gap for AI features.

There is no Celery, RQ, APScheduler, Dramatiq, or cron anywhere. The only asynchronous work is FastAPI's `BackgroundTasks`, used in `auth.py` for sending verification and password-reset emails — which dies with the request worker and has no retry, no persistence, and no scheduling.

Anything that needs to run nightly, batch-process a corpus, or precompute per-seller aggregates has **nowhere to run today**.

### External integrations

Just one: **SMTP** (`shared/email_service.py`), and it no-ops with a warning if `SMTP_SERVER` is unset.

There is no payment gateway, no object storage (uploads go to a local `uploads/` directory served by `StaticFiles`), no search engine (Elasticsearch/Meilisearch/etc.), no CDN, no analytics SDK, and **no LLM or ML integration of any kind**. There is no `openai`, `anthropic`, `langchain`, `transformers`, `torch`, `scikit-learn`, `pandas`, or `numpy` dependency in any requirements file.

### Caching & observability

- `shared/cache.py` — Redis singleton with a connection pool, `CacheKeys` namespace helpers (product lists, detail, categories, tree, featured, trending, catalog stats, similar/related), and `CacheInvalidation` helpers wired into product mutations. Graceful degradation when Redis is unavailable.
- `shared/metrics.py` — a Prometheus `BaseHTTPMiddleware` with request/latency counters, a `/metrics` endpoint factory, and `track_db_query` / `track_cache_operation` decorators.

### How business logic is organised

Predominantly **inline in the routers**. Routers run 600–965 lines and mix validation, authorisation, query construction, and response shaping. There are only four real service classes in the deployed code:

- `services/product/app/services/product_analytics.py` (386 L) — performance metrics, trending, recommendations
- `services/product/app/services/image_service.py` — validation, thumbnails, primary-image management
- `services/seller/app/services/video_service.py`
- `services/chat/app/services/websocket_manager.py`

For AI work this means there is **no clean domain layer to hook into** — new features will either call the ORM directly or need a service layer built alongside.

---

## 4. Frontend

### Navigation

`App.jsx` → Redux `Provider` + `PersistGate` → `AppNavigator`, which switches on auth state between `AuthNavigator` (login, register, forgot/reset password, email verification) and `MainNavigator`.

`MainNavigator` renders **one of three bottom-tab sets based on `user.role`**:

| Role | Tabs |
|---|---|
| `CUSTOMER` | Home, Search, Cart, Chat, Profile |
| `SELLER` | **Dashboard, Products, Orders, Analytics, Chat, Profile** |
| `DUAL` | Home, Search, Cart, Dashboard, Chat |

Tabs sit inside a stack that also holds detail screens (ProductDetails, WriteReview, Checkout, OrderDetails, CategoryForm, etc.).

### State management

Redux Toolkit with **three slices only** — `auth`, `products`, `cart` — all using `createAsyncThunk`. `redux-persist` over AsyncStorage persists **`auth` only** (whitelist).

Everything else — all chat state and **all seller dashboard/analytics state** — is component-local `useState` fetched on mount. So there is no cached seller data layer; a new AI panel on the seller side would follow the same local-state pattern rather than plugging into Redux.

### API client layer

`src/services/apiClient.js` is a single axios instance with:

- request interceptor injecting `Authorization: Bearer` from `expo-secure-store` (`utils/secureStorage.js`),
- response interceptor doing 401 → refresh-token retry with a subscriber queue to avoid refresh stampedes,
- an **auto base-URL detection** routine that probes a list of candidate hosts (`API_CONFIG.BASE_URLS`) and picks the first that responds — a pragmatic answer to the office/home/emulator addressing problem.

Thirteen domain modules wrap it: `authService`, `productService`, `cartService`, `chatService`, `customerOrderService`, `orderFulfillmentService`, `reviewService`, `sellerService`, `sellerAnalyticsService`, `sellerCategoryService`, `sellerProfileService`, `notificationService`. Endpoints are centralised in `src/constants/config.js`.

### Seller-facing screens (the insertion points for AI)

13 screens under `src/screens/seller/`:

`SellerDashboardScreen`, `AnalyticsScreen`, `OrderAnalyticsScreen`, `ProductManagementScreen`, `AddProductScreen`, `ProductFormScreen`, `OrderManagementScreen`, `OrderDetailsScreen`, `CategoryManagementScreen`, `CategoryFormScreen`, `SellerProfileScreen`, `StoreSettingsScreen`, `ThemeManagementScreen`.

Supported by 15 components under `src/components/seller/`, including `AnalyticsDashboard`, `RevenueTrendChart`, `SalesChart`, `CategoryPerformanceChart`, `CustomerDemographicsChart`, `TopProductsList`, `InventoryOverview`, `PerformanceWidget`, and — notably — **`InsightsPanel`**, which is the obvious host for AI-generated recommendations.

Charts are drawn with `react-native-svg`. i18n covers English and Vietnamese (`src/i18n/translations/`).

**Push notifications are a mock.** `notificationService.js` stubs out `PushNotification` and `PushNotificationIOS` with console logs "to prevent compilation errors". There is currently **no working channel for proactive AI alerts** (restock warnings, price suggestions) to reach a seller who isn't in the app.

---

## 5. DATA AVAILABILITY — the critical section

Assessed against `shared/models/` (the deployed schema). Two separate questions are answered per entity: *does the structure exist*, and *is history retained*.

### What exists and is queryable

| Entity | Table(s) | History retained? | Notes for AI |
|---|---|---|---|
| **Users / sellers** | `users` | Partial | `created_at`, `last_login` (single value). No login or session log. Roles: customer/seller/dual. |
| **Seller profiles** | `seller_profiles`, `store_themes` | Current state only | Rich: store name/description, business hours (JSON), **`shipping_policy`, `return_policy`, `processing_time`**, specialties, certifications, SEO keywords. Directly usable as RAG context. |
| **Products / SKUs** | `products` | **Current state only** | One `price` column, `quantity_available`, `view_count` counter, `tags` as a **comma-separated string**, auto-generated 8-char `sku`. `material`, `color`, `technique`, `dimensions`, `weight`. **No variants in the live model.** |
| **Product media** | `product_images`, `product_videos` | Yes (rows accumulate) | Images have `is_primary`/`order_index`; Pillow already available for analysis. |
| **Categories** | `categories` (global), `seller_categories` (per-seller, ≤4 levels, path-indexed) | Current state only | `seller_categories` is a well-built tree with cached `product_count`. |
| **Cart** | `carts`, `cart_items` | ❌ **No** | Live state only. Items are consumed at checkout — **no abandoned-cart history**. |
| **Orders** | `orders`, `order_items` | ✅ **Yes — the strongest asset** | `created_at`, `shipped_at`, `delivered_at`, status + payment status, `subtotal`/`tax`/`shipping`/`total`. Line items carry `quantity`, **`unit_price` as sold**, and a product-name snapshot. This is a genuine transactional time series. |
| **Order status changes** | `order_status_history` | ✅ **Yes** | Real audit trail written on fulfilment transitions (`order_fulfillment.py:293/441/956`): old→new status, who changed it, `changed_at`. Enables lead-time/SLA analysis. |
| **Reviews** | `reviews` | ✅ **Yes** | `rating` 1–5, `title`, `comment`, `image_urls`, `created_at`, **`seller_response` + `seller_response_at`**, `is_verified_purchase`, `is_helpful_count`. FK to `order_id` and creation enforces the reviewer owns that order — so review provenance is trustworthy. **A clean text corpus.** |
| **Chat messages** | `chat_rooms`, `messages` | ✅ **Yes** | Full history: `content`, `sender_id`/`receiver_id`, `created_at` (indexed), `is_read`/`read_at`, `message_type`, optional `image_url`. Rooms carry **`product_id`**, so a conversation is linked to the product it's about. Soft delete only (`is_deleted`). **Ideal shape for a chat copilot.** |
| **Addresses** | `shipping_addresses` + denormalised shipping fields on `orders` | Yes on orders | City/state/postal on every order — enables geographic demand analysis. |

### What does NOT exist — the blockers

These are the findings that decide the feature ranking.

**1. Search queries: zero logging. Nothing is recorded, anywhere.**
`GET /api/v1/products/` (with `search=`) and `GET /api/v1/products/search/advanced` both execute the query and discard the input. A repo-wide grep for `search_log`, `SearchQuery`, `search_history`, `log_search`, `SearchEvent` returns **no matches**. There is no table, no model, no middleware capturing it.
→ *The core signal for an opportunity/assortment finder does not exist and is not being accumulated.*

**2. Price history: the table exists, nothing writes to it.**
`PriceHistory` is defined **only in the non-deployed monolith** (`app/models/product.py:146`) and is **read but never written** even there (`app/routers/products.py:1596` serves a GET; there is no corresponding INSERT anywhere in the repo). The live `shared/models/product.py` doesn't define it at all. Meanwhile both live price-mutation paths overwrite in place:
- `services/product/app/routers/products.py:315` `update_product` — `setattr(product, field, value)`
- `services/seller/app/routers/dashboard.py:611` `bulk_update_product_prices` — `.update({"price": ...})`

→ *No price change is ever recorded. Elasticity cannot be computed.* Partial mitigation: `order_items.unit_price` preserves the price at which each sale actually occurred, so *realised* prices are recoverable — but only for SKUs that sold, and only at sale timestamps.

**3. Product views: a bare counter, not events.**
`POST /products/{id}/view` (`products.py:253`) does exactly `product.view_count = (product.view_count or 0) + 1`. No timestamp, no user, no session, no source. It *is* wired up — `ProductDetailsScreen.jsx:78` calls it — but the resulting number is a single monotonic integer per product.
→ *You cannot compute views/day, trend, funnel, or per-SKU conversion over any window.*

Worse, two analytics paths have this **stubbed to zero and shipped**:
- `services/product/app/services/product_analytics.py:49` — `view_count = 0`, so the returned `conversion_rate` is **always 0**
- `services/seller/app/routers/analytics.py` (`performance-metrics`) — `product_views_total = 0`, so `efficiency_metrics.conversion_rate` is **always 0**

Any seller reading the current Analytics screen is being shown a conversion rate of zero regardless of reality.

**4. Inventory events: no ledger.**
`quantity_available` is mutated in place — decremented at `orders.py:83` and `:256`, incremented on cancel at `:165`. Restocks happen via a plain product update. There is **no stock movement table, no restock record, no supplier data, and no lead times**. Stock history can only be crudely back-derived from `order_items`, which misses every manual adjustment.

**5. No behavioural event stream of any kind.**
No impressions, no clicks, no add-to-cart events, no category browse events, no sessions, no referrers. There is no generic events/telemetry table. Prometheus captures *HTTP* metrics for ops, not user behaviour, and retains nothing per-entity.

**6. Assorted smaller gaps.**
- **No wishlist/favourites table** — despite `productSlice.js` defining `fetchFavorites` / `toggleFavorite` thunks (they call endpoints that don't exist).
- **No returns/refund reasons** — only an order `status` of `REFUNDED`/`CANCELLED`; the *why* is never captured.
- **No COGS, margin, or supplier cost** anywhere → profit-aware pricing is impossible.
- **No competitor/external market data** — though cross-seller comparison *within* Mercai is possible since all sellers share one `products` table.

### And the overriding constraint

**The database currently holds pre-launch test data only.** Even for the entities that *do* retain history correctly — orders, reviews, chat, status changes — there is no real history in them yet. The seed file (`seed_test_data.sql`) is a small synthetic fixture.

So the practical availability picture is:

- **Structure good + history accruing correctly:** orders, order items, order status history, reviews, chat messages.
- **Structure exists but history is destroyed:** prices, stock levels, carts.
- **Structure does not exist at all:** search queries, view events, any behavioural telemetry.
- **All of the above currently contain no production data.**

To verify volumes once the stack is up:

```sql
SELECT 'orders', COUNT(*), MIN(created_at), MAX(created_at) FROM orders
UNION ALL SELECT 'order_items', COUNT(*), MIN(created_at), MAX(created_at) FROM order_items
UNION ALL SELECT 'reviews', COUNT(*), MIN(created_at), MAX(created_at) FROM reviews
UNION ALL SELECT 'messages', COUNT(*), MIN(created_at), MAX(created_at) FROM messages
UNION ALL SELECT 'products', COUNT(*), MIN(created_at), MAX(created_at) FROM products;

-- Per-SKU depth — the number that gates forecasting:
SELECT product_id, COUNT(*) AS order_lines, SUM(quantity) AS units,
       MIN(created_at) AS first_sale, MAX(created_at) AS last_sale
FROM order_items GROUP BY product_id ORDER BY order_lines DESC LIMIT 20;
```

---

## 6. Gaps & risks

**Architecture**

1. **Dual drifted backends.** Two implementations, two `Base` registries, two copies of every model, drifting in *both* directions (§1). A change made in the wrong tree is silently ineffective. This is the top tech-debt item.
2. **Latent mapper break in the monolith.** `app/models/product.py:63` declares `relationship("SellerCategory", ...)` and `app/models/product.py` has a `seller_category_id` FK to `seller_categories`, but `app/models/__init__.py` **never imports a `SellerCategory` class** (none exists under `app/models/`). SQLAlchemy resolves relationship strings lazily at mapper-configuration time, so the monolith will raise on first ORM use. Consistent with it being unused — and a trap for anyone who tries to run it.
3. **Shared database across "microservices."** All 5 services read and write each other's tables directly (§3). Adding a 6th service inherits this coupling.
4. **No service layer.** Business logic sits inline in 600–965-line routers; there is little to extend or reuse.

**Testing & quality**

5. **Zero backend automated tests.** No pytest, no fixtures, no in-process test client. The `test_*.py` scripts require a live server and a live DB, so they cannot gate a PR.
6. **No Python job in CI.** `.github/workflows/test.yml` runs frontend Jest + Detox only. Backend changes are entirely unverified by automation.
7. **No Python linting, formatting, or type checking configured.**
8. **Thin frontend coverage** — ~9 test files for ~40 screens/components.

**Correctness / dead code**

9. **Shipped-broken analytics.** `conversion_rate` is hardcoded to 0 in two places (§5.3) and displayed to sellers.
10. **Frontend calls endpoints that don't exist:** `sellerAnalyticsService.scheduleReport` → `POST /api/v1/seller/analytics/schedule-report` (marked with a `TODO` acknowledging this), `productService.getPopularProducts` → `GET /api/v1/products/analytics/popular` (only `/analytics/trending` exists), plus the favourites thunks.
11. **Schema/response mismatch in chat.** `MessageResponse` declares `reply_to_id` and `client_message_id`; the `Message` model has neither column.
12. **Narrow search recall.** `advanced_search` combines multi-term queries with `and_(...)` — *every* term must match, so "blue ceramic vase" fails unless all three appear.
13. **`trending` is review-count based**, not views or sales — it will be near-random at low volume.

**Operational / security**

14. **Insecure defaults committed.** `docker-compose.yml` defaults `SECRET_KEY=your-secret-key-change-in-production` and `MYSQL_ROOT_PASSWORD=Mysql_2025`; `.env.microservices`, `.env.production`, and `.env.save` are in the repo.
15. **`allow_origins=["*"]` with `allow_credentials=True`** in the service `main.py` files.
16. **Startup seeding.** The monolith seeds test users on startup — hazardous if ever pointed at production.
17. **Mixed migration regime** (Alembic + `create_all`) means the real schema isn't reliably described by the migration history.
18. **Local-disk uploads** with no object store or CDN; media is bound to a single host.
19. **N+1 queries** in `product_to_dict(include_seller=True)` — a seller-stats aggregate per product row.

**Direct blockers for AI features**

20. **No scheduler or job queue** (§3) — nothing can run nightly or batch-process.
21. **No ML/LLM dependency or client** in any requirements file — the entire inference layer is greenfield.
22. **Push notifications are mocked** — no delivery channel for proactive insights.
23. **Every behavioural signal is either uncollected or non-historised** (§5) — and every day this stays true is data permanently lost.

---

## 7. Candidate seller AI features — feasibility ranking

Ranked against what the code and data actually support, given: **pre-launch data, microservices target, local Ollama**.

The decisive split is not model difficulty. It is **whether a feature needs historical behavioural data or only the content of records that already exist**. Everything in Tier 1 works on day one because it reads a single record and reasons about its content. Everything in Tier 2 is blocked by *data*, not by code — and no amount of engineering shortens the wait.

---

### Tier 1 — Buildable now

#### 1. Listing optimizer (title / description / image) — **Difficulty: Low**

**Already in place.** Everything this needs exists. Products carry `name`, `description`, `tags`, `material`, `color`, `technique`, `dimensions`, `weight`; `product_images` with `is_primary` and Pillow already installed for image inspection; `seller_categories` gives a per-seller taxonomy for context; and `AddProductScreen` is the natural insertion point — a "Improve this listing" action fits into an existing form with no navigation changes. (This originally also named `ProductFormScreen`; implementation found that screen unreachable and it was deleted. `AddProductScreen` is dual-purpose and covers editing too — see `02-listing-optimizer.md` §6.) Local Ollama handles this comfortably (single-record, latency-tolerant, seller-initiated).

**Missing.** Nothing blocking. But note two honest limits: with no traffic you **cannot measure lift** — there is no A/B capability and `view_count` is useless (§5.3) — so quality must be judged against a rubric, not conversion. And there is no baseline of "good" listings on the platform to learn house style from; the first version will encode generic e-commerce best practice plus whatever the ceramics domain suggests.

**Why it ranks first.** It is the only candidate that delivers full value *pre-launch*, when sellers are onboarding and creating their first listings — which is exactly the moment listing quality is set, and exactly when the platform has no other data to work with.

---

#### 2. Chat copilot / auto-reply for buyer questions — **Difficulty: Medium**

**Already in place.** A surprisingly good foundation. `messages` retains full conversation history with timestamps and read receipts; `chat_rooms` carries **`product_id`**, so the copilot knows which product a question concerns without inference; the WebSocket `ConnectionManager` and a seller Chat tab already exist. Critically, `seller_profiles` already stores **`shipping_policy`, `return_policy`, `processing_time`, and business hours** — a ready-made, seller-specific knowledge base for RAG, alongside the seller's own product rows.

**Missing.** No FAQ/canned-response table; no draft or approval state on `Message` (a suggested reply has nowhere to live before a seller sends it); no consent or disclosure model for automated replies; no per-seller tone configuration. Retrieval over products would benefit from embeddings, and there is no vector store — though at pre-launch catalogue sizes, plain SQL retrieval over a seller's own products is entirely sufficient and much simpler.

**Recommendation.** Build **suggest-a-draft, seller approves** rather than auto-send. It sidesteps the disclosure and liability questions, needs no new delivery infrastructure, degrades gracefully when the model is wrong, and is far cheaper to evaluate. Auto-send can come later once you have a corpus of accepted drafts to validate against.

---

#### 3. Review intelligence (sentiment + themes) — **Difficulty: Low–Medium**

**Already in place.** `reviews` is the cleanest table in the schema for this: `rating`, `title`, `comment`, `created_at`, `seller_id` FK, `seller_response`, and `is_verified_purchase` enforced by real order ownership at creation. `AnalyticsScreen` and `InsightsPanel` are ready-made hosts. Aspect extraction and sentiment over short review text is well within a local 14B model's competence.

**Missing.** No table to persist extracted themes/aspects, so results must be recomputed or cached (Redis is already available — cache per seller with a TTL and recompute on demand; this neatly sidesteps the absent scheduler). No aspect taxonomy. No moderation queue. And **no review volume**: theme extraction is meaningless below roughly 20–30 reviews per seller.

**Recommendation.** Build it now — it is cheap — but understand it **activates post-launch**, when reviews accumulate. Compute on demand and cache; don't wait for a scheduler.

---

### Tier 2 — Blocked on data, not on code

#### 4. Dynamic pricing assistant — **Difficulty: High** *(a useful rule-based version is Low)*

**Already in place.** More than you'd expect. `order_items.unit_price` preserves the price at which every sale actually occurred — realised price history *is* recoverable for anything that sells. Because all sellers share one `products` table, **cross-seller comparison within Mercai is a plain SQL query**: price percentile within a category, versus similar `material`/`technique`/`color`. `bulk_update_product_prices` already exists as the write path for accepting a suggestion.

**Missing.** Price *change* history is never written (§5.2) — the single most consequential omission for this feature. No view→purchase funnel, so demand response to a price move is unobservable. **No COGS or margin**, so no suggestion can be profit-aware — it can only optimise revenue, which is often the wrong objective. No external competitor data.

**Recommendation.** Ship a **rule-based price advisor now** — "your price sits in the 85th percentile for stoneware vases in this size band; median is X" — which is honest, immediately useful, needs no history, and is a straightforward query. Genuine *dynamic* pricing requires writing `PriceHistory` on every mutation and logging view events, then waiting for the data.

---

#### 5. Demand forecasting & smart restock (per-SKU) — **Difficulty: High, and gated on time**

**Already in place.** The data *shape* is right: `order_items` with `product_id`, `quantity`, and `created_at` is exactly a per-SKU demand series. `order_status_history` and `orders.shipped_at` give real fulfilment lead times. `GET /seller/dashboard/inventory-alerts` already exists (low-stock/out-of-stock thresholds) as the UI hook a forecast would upgrade.

**Missing.** The history itself — pre-launch means the series are empty. No stock ledger (§5.4), so you cannot distinguish "sold out" from "seller never restocked", which is a *fatal* ambiguity for forecasting: censored demand read as zero demand teaches the model to under-order exactly the items that sell best. No supplier lead times, no reorder costs, no seasonality baseline.

**Realistic threshold.** Per-SKU statistical forecasting needs roughly **6–12 months and a few dozen orders per SKU** before it beats a moving average. For a marketplace of artisan ceramics with long-tail SKUs, many products will *never* reach that bar and should be handled by category-level or rule-based logic instead.

**Recommendation.** Build the **stock ledger now** (it is small, and it is the thing that makes forecasting possible later), ship a naive moving-average reorder point against it, and revisit modelling once real history exists.

---

#### 6. Opportunity / assortment finder (demand gaps) — **Difficulty: High / currently blocked**

**Already in place.** Only the supply side: the catalogue of what *is* listed, `seller_categories`, and cross-seller visibility within the shared database. You can already answer "what does this seller not stock that other sellers in their categories do" — which is a genuine, if weaker, assortment signal.

**Missing.** The entire demand side. **No search logs, no zero-result queries, no category browse events, no impressions** (§5.1). "Demand gap" means *buyers looked for something and didn't find it* — and Mercai currently has no record that any buyer ever looked for anything. This is the one candidate whose core signal does not exist anywhere in the codebase, in any form, retained or otherwise.

**Recommendation.** This is simultaneously the **highest long-term value** and the **most urgent instrumentation decision**, because search logs can only accumulate forward. Every week without search logging is a week of demand data permanently lost. Add the logging now even though the feature ships much later.

---

### Ranking summary

| # | Feature | Data ready? | Difficulty | When |
|---|---|---|---|---|
| 1 | **Listing optimizer** | ✅ Yes | Low | Now — full value pre-launch |
| 2 | **Chat copilot (suggest-draft)** | ✅ Yes | Medium | Now |
| 3 | **Review intelligence** | ⚠️ Structure yes, volume no | Low–Med | Build now, activates at launch |
| 4 | **Dynamic pricing** | ⚠️ Partial | High (rule-based: Low) | Rule-based now; ML after history |
| 5 | **Demand forecasting / restock** | ❌ No history | High | 6–12 months post-launch |
| 6 | **Opportunity finder** | ❌ Signal doesn't exist | High | Blocked — instrument now |

### The one recommendation that shouldn't wait

Three small writes are worth adding **before** any AI feature, because each is well under ~100 lines and each concerns data that is otherwise **irrecoverable**:

1. **`search_logs`** — query string, filters, result count, user (nullable), timestamp. Unblocks feature 6 and improves 1 and 4. *Nothing else in the system captures buyer intent.*
2. **Write `PriceHistory`** on both price-mutation paths. Unblocks feature 4.
3. **`product_view_events`** — product, user (nullable), timestamp — replacing the bare counter. Unblocks conversion metrics (and fixes the two hardcoded zeros already shipped to sellers).

Optionally a fourth: a **stock movement ledger**, which is what makes feature 5 possible at all.

Pre-launch is the ideal moment for these — no migration risk against real data, and the instrumentation starts collecting from the first real user.

### Architecture note for whatever gets built

Add a **sixth service** (`ai-service`, port 8006) behind Traefik with `PathPrefix('/api/v1/ai')`, following the existing pattern: reuse `shared/` (models, security, cache, metrics), mount `./services/ai/app` and `./shared`, add the Traefik labels. This matches the deployed topology and avoids touching the five existing services.

Two things it will need that don't exist yet:

- **A scheduler.** APScheduler in-process is the cheapest step up; Celery + Redis is the durable option and **Redis is already running**, so the marginal infrastructure cost is near zero.
- **An Ollama client.** No HTTP client library is currently used by any service (`httpx` is not a dependency anywhere) — it will need adding.

Also worth deciding early: whether new AI tables live in the shared `mercai` database (consistent with current practice, simplest) or in their own schema (cleaner boundary, but breaks the pattern every other service follows).
