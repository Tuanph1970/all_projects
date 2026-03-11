# LLM OCR Service — Project Status & Architecture Roadmap

> Last updated: 2026-03-10

---

## Architecture Review

### 1. Microservices Assessment

**Current state: Single monolithic service (not microservices)**

The project is one FastAPI app with internal modules. Internal subdirectories (`api/`, `models/`, `utils/`, `config/`) are **Python packages inside a single process**, not separate services.

| What exists | What microservices would look like |
|---|---|
| `src/api/routers/ocr.py` | Separate `ocr-service` (own repo, own Dockerfile, own port) |
| `src/api/routers/solution.py` | Separate `solution-service` |
| `src/models/` | Separate `model-serving-service` (e.g., Triton Inference Server) |
| Single `main.py` entry point | API Gateway in front of multiple services |

**Verdict**: The current design is appropriate for early-stage development. Splitting into real microservices should happen later when load/team/domain boundaries are proven. For now, focus on **clean internal boundaries** so splitting is easy later.

---

### 2. Domain-Driven Design (DDD) Assessment

#### What is correctly implemented
- `MLTask` entity with lifecycle methods (`mark_processing`, `mark_completed`, `mark_failed`) ✅
- Value objects: `OCRResult`, `SolutionResult`, `SolutionStep`, `ProcessingResult` ✅
- `ModelType` and `TaskStatus` enums as value objects ✅
- Abstract `BaseMLModel` as a port/interface ✅
- `ModelRegistry` as a registry pattern ✅

#### Critical DDD violations

**No layered architecture** — all concerns are mixed:
```
Current (mixed):
src/
├── api/           # HTTP + business logic mixed
├── config/        # OK
├── models/        # ML infra + domain models mixed (naming confusion)
└── utils/         # Infrastructure helpers

Correct DDD layers:
src/
├── domain/        # Entities, Value Objects, Domain Services, Repository interfaces
├── application/   # Use Cases (orchestrate domain)
├── infrastructure/# ML models, image processing, external services
└── api/           # HTTP adapters only (thin controllers)
```

**Business logic bleeding into routers** (`src/api/routers/ocr.py`):
- Lines 88–106: model selection + fallback logic belongs in an application service
- Lines 115–123: metadata assembly belongs in an application service
- Direct `get_model_registry()` calls throughout routers = tight coupling to infrastructure

**No Application Services / Use Cases layer**:
- `ExtractTextFromImage` use case doesn't exist as a class — its logic is inline in the router
- `SolveMathProblem` use case is inline in the solution router
- No single place to add cross-cutting concerns (audit log, metrics) around business operations

**`MLTask` entity is defined but not used** (`base.py:71`):
- Defined but never created or tracked anywhere in the system
- Async task tracking is not implemented despite the entity existing

**Global singleton anti-pattern** (`base.py:220`):
```python
model_registry = ModelRegistry()  # Module-level global — hard to test, not thread-safe on reload
```

**No domain events**:
- No `ImageTextExtracted`, `ProblemSolved`, `ModelLoaded` events
- No way for cross-domain communication without direct coupling

---

### 3. Design Patterns Assessment

| Pattern | Status | Issue |
|---|---|---|
| Factory (`create_app`) | ✅ Correct | — |
| Template Method (`BaseMLModel`) | ✅ Correct | — |
| Strategy (binarization methods) | ✅ Correct | — |
| Registry (`ModelRegistry`) | ⚠️ Partial | Global instance, not injected |
| Repository | ❌ Missing | `ModelRegistry` is not a true repository; no data persistence repo exists |
| Use Case / Application Service | ❌ Missing | Business logic lives in HTTP routers |
| Dependency Injection | ⚠️ Partial | FastAPI `Depends` used for settings, but not for use cases or repositories |
| Observer / Domain Events | ❌ Missing | No event system |
| CQRS | ❌ Missing | Reads and writes are not separated |
| Unit of Work | ❌ Missing | No transaction boundary management |

---

### 4. Recommended Target Architecture

```
src/
├── domain/                          # Pure Python — no framework imports
│   ├── ocr/
│   │   ├── entities.py             # OCRTask (aggregate root)
│   │   ├── value_objects.py        # ImageData, ExtractedText, ConfidenceScore
│   │   ├── repositories.py         # IOCRModelRepository (interface)
│   │   └── events.py               # TextExtracted domain event
│   ├── solution/
│   │   ├── entities.py             # SolutionTask (aggregate root)
│   │   ├── value_objects.py        # MathProblem, SolutionStep, SolutionResult
│   │   ├── repositories.py         # ISolutionModelRepository (interface)
│   │   └── events.py               # ProblemSolved domain event
│   └── shared/
│       ├── value_objects.py        # ProcessingResult, TaskStatus, ModelType
│       └── exceptions.py           # Domain exceptions
│
├── application/                     # Use cases — orchestrates domain
│   ├── ocr/
│   │   ├── extract_text.py         # ExtractTextUseCase
│   │   ├── batch_extract_text.py   # BatchExtractTextUseCase
│   │   └── dtos.py                 # ExtractTextRequest / Response DTOs
│   └── solution/
│       ├── solve_problem.py        # SolveProblemUseCase
│       ├── ocr_and_solve.py        # OCRAndSolveUseCase
│       └── dtos.py                 # SolveProblemRequest / Response DTOs
│
├── infrastructure/                  # Technical implementations
│   ├── ml/
│   │   ├── trocr_ocr_model.py      # TrOCR adapter (implements IOCRModelRepository)
│   │   ├── flan_t5_solution_model.py
│   │   └── model_registry.py       # Model lifecycle manager
│   ├── image/
│   │   └── image_preprocessor.py
│   ├── math/
│   │   └── math_expression_parser.py
│   └── services/
│       └── model_manager.py        # Startup/shutdown orchestration
│
├── api/                             # HTTP adapters (thin controllers)
│   ├── main.py
│   ├── dependencies.py             # DI container / provider functions
│   ├── middleware.py
│   ├── exceptions.py
│   └── routers/
│       ├── ocr.py                  # Delegates to OCR use cases only
│       ├── solution.py             # Delegates to Solution use cases only
│       ├── health.py
│       └── models.py
│
└── config/
    ├── settings.py
    └── model_config.py
```

---

## Priority Task List

### P0 — Critical Bugs / Blockers ✅ COMPLETED

- [x] **[BUG] `start_time` referenced before assignment in error handler** (`ocr.py`)
  - Fixed: moved `start_time = time.time()` before the `try` block in all three handlers

- [x] **[BUG] Import `from ..services.model_manager import ModelManager` in `main.py:19`**
  - Fixed: created `src/services/__init__.py` and `src/services/model_manager.py` with full `ModelManager` class

- [x] **[BUG] `src/utils/logging.py` missing**
  - Fixed: created `src/utils/logging.py` with `setup_logging(logging_settings)` function (loguru-based)

- [x] **[BUG] `from .routers import debug` — `debug.py` missing**
  - Fixed: created `src/api/routers/debug.py` with overview, registry, and force-reload endpoints

- [x] **[BUG] `SecuritySettings.secret_key` required without default — crashes at import**
  - Fixed: added `default="change-me-in-production"` (override via `SECRET_KEY` env var in production)

---

### P1 — Architecture Foundations ✅ COMPLETED

- [x] **[ARCH] Created proper DDD layer structure**
  - `src/domain/shared/value_objects.py` — canonical Pydantic VOs (ModelType, TaskStatus, ProcessingResult, OCRResult, LLMResult, SolutionResult, SolutionStep, MLTask)
  - `src/infrastructure/ml/base.py` — BaseMLModel + ModelRegistry (infrastructure, not domain)
  - `src/models/base.py` → converted to backward-compat re-export shim

- [x] **[ARCH] Extracted Use Case classes from routers**
  - `src/application/ocr/use_cases.py` → `ExtractTextUseCase`, `BatchExtractTextUseCase`
  - `src/application/solution/use_cases.py` → `SolveProblemUseCase`, `OCRAndSolveUseCase`
  - All 4 routers (ocr, solution, models, health) rewritten as thin HTTP adapters

- [x] **[ARCH] Fixed ModelRegistry injection — removed all global singletons**
  - Created `src/api/dependencies.py` with FastAPI `Depends()`-based providers
  - All routers now receive registry via `request.app.state.model_manager.get_registry()`
  - `ModelManager` creates its own `ModelRegistry()` — no module-level singleton

- [x] **[ARCH] MLTask decision: kept in domain, marked for P2 async implementation**
  - `MLTask` retained in `domain/shared/value_objects.py` with clear NOTE docstring
  - No dead code — entity is documented as the target for async task tracking (P2)

- [x] **[ARCH] Defined Repository interfaces in domain layer**
  - `src/domain/ocr/repositories.py` → `IOCRModelRepository` (ABC)
  - `src/domain/solution/repositories.py` → `ISolutionModelRepository` (ABC)

---

### P2 — Feature Completeness

- [ ] **[FEAT] Complete Authentication/Authorization**
  - `APIKeyMiddleware` is defined but disabled (middleware.py)
  - Implement: enable middleware + add API key management endpoint
  - Optional: JWT token endpoint for mobile clients

- [ ] **[FEAT] Async task processing**
  - Currently all requests are synchronous; large images block the server
  - Implement: POST `/ocr/extract` returns `task_id` → GET `/tasks/{id}` polls status
  - Requires: Redis for task state, background task runner (Celery or asyncio)

- [ ] **[FEAT] Persistent task history**
  - `MLTask` needs a persistence layer (Redis or PostgreSQL)
  - Enables: audit trail, retry logic, analytics

- [ ] **[FEAT] Solution router tests**
  - `tests/api/` only has `test_health_router.py` and `test_ocr_router.py`
  - Missing: `test_solution_router.py`, `test_models_router.py`

- [ ] **[FEAT] Batch endpoint for solution solving**
  - OCR has `/extract-batch` but Solution has no equivalent
  - Implement `/solution/solve-batch` for multiple problems at once

---

### P3 — Code Quality & Testing

- [ ] **[TEST] Fix missing test coverage for routers**
  - Add `tests/api/test_solution_router.py`
  - Add `tests/api/test_models_router.py`
  - Current coverage: health + ocr only

- [ ] **[TEST] Integration tests for full pipeline (OCR → Solution)**
  - `tests/integration/test_ml_service_integration.py` exists but verify it covers the combined flow
  - Add end-to-end test: upload image → extract text → solve problem

- [ ] **[QUALITY] Move business logic out of error responses in routers**
  - `ocr.py` returns `OCRResponse(success=False, ...)` from `except` block instead of raising
  - This swallows errors silently; batch and single endpoints behave differently
  - Standardize: always raise, let exception handlers return the response

- [ ] **[QUALITY] Enable disabled middleware**
  - `RequestSizeLimitMiddleware` is defined but not added to the middleware stack
  - `APIKeyMiddleware` is defined but not added
  - Evaluate and enable or delete them

- [ ] **[QUALITY] Type annotation consistency**
  - Some router functions use `Any` return types instead of explicit response models
  - Enable stricter mypy checks in `pyproject.toml`

---

### P4 — Observability & Operations

- [ ] **[OPS] Enable OpenTelemetry distributed tracing**
  - `settings.monitoring` has tracing config but it's not wired up in `main.py`
  - Implement: add `opentelemetry-instrumentation-fastapi` to startup

- [ ] **[OPS] Structured error logging with context**
  - Errors logged as plain strings; add request_id, model_name, user_id to every error log
  - Use loguru's `contextvars` integration

- [ ] **[OPS] Docker Compose for local development**
  - No `docker-compose.yml` in the repo
  - Create: `llmOCR` + `redis` + optional `prometheus` + `grafana`

- [ ] **[OPS] Environment-specific configuration validation**
  - Production override functions exist in `settings.py` but are not called at startup
  - Wire `apply_environment_overrides()` into the `lifespan()` function

- [ ] **[OPS] Model warm-up endpoint**
  - Cold-start inference can be slow; add `/models/{name}/warmup` endpoint
  - Run dummy inference on startup so first real request is fast

---

### P5 — Future / Nice-to-Have

- [ ] **[FUTURE] Split into true microservices** (when traffic/team justifies)
  - `ocr-service`: handles image → text (port 8003)
  - `solution-service`: handles text → math solution (port 8004)
  - `model-service`: handles model lifecycle/serving (port 8005)
  - API Gateway in front (nginx or Kong)

- [ ] **[FUTURE] Add domain events**
  - `TextExtracted` event → can trigger solution automatically
  - `ProblemSolved` event → can trigger notification to mobile client
  - Use Redis Pub/Sub or an in-process event bus

- [ ] **[FUTURE] WebSocket support for streaming solutions**
  - Stream solution steps as they are generated instead of waiting for full result
  - Good UX for mobile: user sees steps appearing in real-time

- [ ] **[FUTURE] Multi-language OCR support**
  - Current TrOCR is English-only
  - Evaluate `PaddleOCR` or `EasyOCR` for Vietnamese/multilingual math problems

- [ ] **[FUTURE] Fine-tuning pipeline**
  - `ModelType.FINE_TUNE` is defined as an enum value but no fine-tuning code exists
  - Implement training endpoint or separate training script

---

## Summary Counts

| Priority | Count | Description |
|---|---|---|
| P0 — Critical Bugs | 4 | App startup failures and runtime bugs |
| P1 — Architecture | 5 | DDD layers, use cases, DI, repository interfaces |
| P2 — Features | 5 | Auth, async tasks, missing tests, batch solution |
| P3 — Code Quality | 5 | Test coverage, error handling, middleware |
| P4 — Operations | 5 | Tracing, Docker Compose, config, warm-up |
| P5 — Future | 5 | Microservices split, events, WebSocket, multi-lang |

**Recommended focus order**: P0 → P1 → P3 → P2 → P4 → P5
