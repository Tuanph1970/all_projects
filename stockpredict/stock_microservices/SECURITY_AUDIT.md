# Phase 3.5 Security Audit — 2026-05-06

Owner: Sprint A · Scope: stock_microservices/* (services, infra, deployment).

This document is the audit baseline. Track remediation in `ROADMAP.xlsx → Backlog`. Findings are tagged **HIGH / MEDIUM / LOW / INFO**, with file:line references where possible. The "Quick wins" section at the bottom lists items that can land in under one hour each.

---

## HIGH

1. **Default JWT secret shipped in code.** Multiple services default `JWT_SECRET_KEY` to `"your-secret-key-change-in-production"`. If deployed without overriding the env, all services accept forged tokens.
   - `services/auth-service/app/config.py:33`
   - `services/journal-service/app/config.py:37`
   - `services/analysis-service/app/config.py` (similar)
   - `services/prediction-service/app/config.py` (similar)
   - **Fix**: remove the default, fail-fast at startup if unset or equal to the placeholder.

2. **Default DB password shipped in code.** `DATABASE_PASSWORD: str = "Mysql_2025"` appears as a default across services. Same risk: forgetting to override env produces a known credential.
   - `services/auth-service/app/config.py:27`
   - `services/journal-service/app/config.py:20`
   - **Fix**: remove default; require env var; load via secret manager (Phase 3.5 plan).

3. **CORS wildcard with credentials.** Seven services register `allow_origins=["*"]` together with `allow_credentials=True`. With a valid token leaked or replayed, any origin can exercise authenticated endpoints — the precondition for CSRF on token-bearing flows.
   - `services/journal-service/app/main.py:78`
   - `services/analysis-service/app/main.py`, `ai-insights-service`, `chatbot-service`, `portfolio-service`, `knowledge-qa-service`, `prediction-service` (same pattern)
   - **Fix**: env-driven `CORS_ORIGINS` list (e.g. `https://app.example.com`); never combine `*` with credentials.

4. **Unauthenticated admin-style endpoints.** Two `stock-data-service` POST endpoints have no auth and trigger expensive operations:
   - `services/stock-data-service/app/api/routes.py:176-194` — `POST /companies/sync` re-syncs the full company table.
   - `services/stock-data-service/app/api/routes.py:488-511` — `POST /priceboards/refresh` triggers Vietcap fetch.
   - **Fix**: add `Depends(get_current_user)` and an admin-role check (`require_admin`).

## MEDIUM

5. **HS256 JWTs with shared secret.** All services validate locally using the same symmetric secret. Compromise of any service container leaks the signing key for all of them.
   - `stock-common/stock_common/auth/jwt.py` and per-service config files.
   - **Fix**: switch to RS256 with the auth-service holding the private key; other services validate with the public key (rotation cheaper, blast radius smaller).

6. **Service-to-service traffic over plain HTTP.** Internal URLs are `http://<svc>:<port>` (e.g. `AUTH_SERVICE_URL=http://auth-service:8007`). No mTLS. Any container with network access can read/inject inter-service traffic.
   - `services/*/app/config.py`
   - **Fix**: add Linkerd or Istio sidecar mTLS, or terminate TLS at Traefik with internal certs.

7. **No service-level rate limiting.** Traefik enforces 100 req/min standard / 30 req/min compute (`traefik/dynamic.yml:223-234`), but if traffic ever bypasses Traefik (port-forward, internal call, local override) services have no second line of defense.
   - **Fix**: add `slowapi` middleware on each FastAPI app at minimum for auth endpoints.

8. **Password complexity rules differ between code and policy.** Schema enforces 8 chars; production policy declares 12.
   - `services/auth-service/app/models/schemas.py:14`
   - `production/security/security_config.py:43`
   - **Fix**: pick one (12 is recommended) and apply uniformly.

9. **Traefik dashboard insecure.** `--api.insecure=true` exposes the Traefik admin dashboard without auth.
   - `stock_microservices/docker-compose.yml:19`
   - **Fix**: gate the dashboard behind basic-auth middleware or disable in production.

10. **RabbitMQ / Redis defaults are weak fallbacks.** `RABBITMQ_PASSWORD=${RABBITMQ_PASSWORD:-stockpass}`, `REDIS_PASSWORD=${REDIS_PASSWORD:-stockredis}`.
    - `stock_microservices/docker-compose.yml:51, 271, 275, 436`
    - **Fix**: drop the `:-default` fallback; let compose error out if the env var is missing.

11. **No SAST in CI.** Pre-commit covers `ruff` and `detect-secrets`. No `bandit`, `semgrep`, or comparable.
    - **Fix**: add `bandit -r services/ stock-common/` to a CI job (informational at first, enforced on PRs targeting main).

12. **Production security policy file is unused.** `production/security/security_config.py` defines headers, CSP, password policy — none applied at runtime.
    - **Fix**: wire its `SECURITY_HEADERS` dict into a FastAPI middleware; align password rules with `auth-service`.

## LOW

13. **`/metrics` and `/health*` endpoints unauthenticated.** Acceptable for Prometheus scrapes inside the cluster, but the same routes are reachable from outside via Traefik. Verbose metrics can leak internal counters.
    - `services/auth-service/app/main.py:169` and equivalents.
    - **Fix**: limit `/metrics` to the Prometheus subnet via Traefik IPAllowList middleware; keep health unauthenticated.

14. **No HTTPS-redirect rule in Traefik.** `websecure` entrypoint exists but no global router forces HTTP → HTTPS.
    - `traefik/dynamic.yml`
    - **Fix**: add a redirect-scheme middleware on the `web` entrypoint.

15. **Reset-password JWT shares signing key with access tokens.** Same `JWT_SECRET_KEY`. Stolen access token + algorithm knowledge → forged reset token.
    - `services/auth-service/app/services/auth_service.py` (`create_password_reset_token`)
    - **Fix**: derive a separate signing key (HKDF from `JWT_SECRET_KEY`) and namespace by `kid` claim.

16. **No access-token revocation.** `logout` revokes refresh tokens only; access tokens remain valid until expiry (default 30 min).
    - `services/auth-service/app/services/auth_service.py:215-217`
    - **Fix**: short-lived access tokens (5 min) + Redis-backed revocation list for `/logout-all`.

17. **DEBUG-driven detail leakage.** Exception handlers include `str(exc)` when `DEBUG=True`; if `.env.local` (`DEBUG=1`) ever ships to prod, stack-trace leakage is on.
    - `services/auth-service/app/main.py:119`
    - **Fix**: never pass `str(exc)` to the client even in debug; rely on logs.

18. **Security headers missing.** `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, CSP — all absent from FastAPI response middleware.
    - **Fix**: add `secure-headers` middleware (or wire `production/security/security_config.SECURITY_HEADERS` in).

19. **`detect-secrets` excludes `rabbitmq/definitions.json`.** Definitions can include passwords; excluding it from scans is a future foot-gun.
    - `.pre-commit-config.yaml:32`
    - **Fix**: keep file but don't ship credentials in it (use `definitions.template.json` + envsubst at startup).

## INFO (in good shape)

- Bcrypt is used correctly for password hashing (`services/auth-service/app/services/auth_service.py:29`).
- Pydantic password validators enforce lower / upper / digit (`schemas.py:24-33`).
- Traefik rate-limit middleware is present (`traefik/dynamic.yml:223-234`).
- Pre-commit runs `detect-secrets` against a baseline (`.pre-commit-config.yaml`).
- Pre-commit runs `ruff` on Python sources.
- Pure SQLAlchemy `text(...)` with named params used throughout (e.g. `services/prediction-service/app/api/routes.py:379-395`); no string-concat SQL spotted in this pass.

---

## Quick wins (≤ 1 hour each)

1. **Fail-fast on default secrets.** In each `config.py`, raise on startup if `JWT_SECRET_KEY` equals the placeholder or `DATABASE_PASSWORD` equals `Mysql_2025`. (~ 30 min total across services.)

2. **Replace CORS wildcard with env list.** Add `CORS_ORIGINS: list[str]` to each service's `Settings`, default to `["http://localhost:3004"]` for dev. (~ 45 min for 7 services.)

3. **Auth on stock-data-service admin endpoints.** Add `Depends(get_current_user)` (and an admin check once we have role plumbing) to `POST /companies/sync` and `POST /priceboards/refresh`. (~ 20 min.)

4. **Add `bandit` to backend CI.** New job in `.github/workflows/backend-ci.yml`, informational-only at first. (~ 15 min.)

5. **HTTPS redirect middleware in Traefik.** Append a `redirect-scheme` middleware in `traefik/dynamic.yml`. (~ 15 min.)

---

## Performance baseline

A reproducible perf baseline against a running stack lives at `stock_microservices/scripts/perf_baseline.sh`. It runs a short load against the public, unauthenticated endpoints and prints a markdown row of `(endpoint, p50, p95, p99, rps)`. See script header for usage.

Initial p99 target (Phase 3.5 plan): **< 300 ms** per service for cached-response endpoints. Capture an actual baseline once the stack is up — track results in `ROADMAP.xlsx → Sessions Log`.
