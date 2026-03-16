# ADR-005: Store Refresh Tokens in Redis (Not Database)

**Date**: March 9, 2026
**Status**: Accepted
**Deciders**: Development Team

---

## Context

The original `RefreshTokenAsync()` in `AuthenticationService` was a stub that always returned `(false, "Refresh token validation not implemented", null)`. This meant users silently lost their sessions whenever their access token expired, requiring a full re-login.

Refresh tokens need a storage backend that supports:
1. Fast lookup by token value
2. Automatic expiry (TTL)
3. Atomic delete-on-use (token rotation — each refresh issues a new pair and invalidates the old one)

Two options were evaluated:

| Aspect | MySQL (new `RefreshTokens` table) | Redis |
|---|---|---|
| TTL / auto-expiry | Requires a scheduled cleanup job | Native — `EXPIRE` command, no cleanup needed |
| Lookup speed | Index scan on token column | O(1) key lookup |
| Token rotation (atomic invalidate + write) | DB transaction required | Single `DEL` + `SET` — effectively atomic at this scale |
| Already in the stack | No (extra migration) | Yes — Redis is already used for API response caching |
| Persistence on restart | Yes | Configurable (RDB/AOF) — acceptable to lose on restart (user re-logs in) |

---

## Decision

**Store refresh tokens in Redis** using the key pattern `refresh:{token_value}` with TTL equal to `Jwt:RefreshTokenExpirationDays` from configuration.

```csharp
// On login / register — store token
await _redisCacheService.SetAsync(
    $"refresh:{refreshToken}",
    userId.ToString(),
    TimeSpan.FromDays(_refreshTokenExpirationDays));

// On refresh — validate, rotate, clean up old token
var userId = await _redisCacheService.GetAsync($"refresh:{incomingToken}");
await _redisCacheService.DeleteAsync($"refresh:{incomingToken}");
// ... issue new pair, store new refresh token
```

Token rotation is implemented: every successful refresh call deletes the old token and writes a new one. A stolen token can only be used once before it is invalidated.

---

## Consequences

**Positive**
- Zero extra DB tables or migrations
- Tokens expire automatically — no scheduled cleanup job required
- Fast: O(1) Redis lookup vs index scan on a potentially large tokens table
- Token rotation limits replay-attack window to a single use
- Redis was already a project dependency (used for API caching and rate limiting)

**Negative**
- Redis data is not durable by default — a Redis restart without persistence configured will invalidate all active sessions (users must re-login)
- No built-in query capability: cannot list "all active sessions for user X" without maintaining a secondary index (not currently needed)
- Redis is a single point of failure for authentication if not clustered

**Mitigations**
- Redis restart = forced re-login is acceptable for an MVP mobile app (not a banking system)
- If session management becomes a requirement, add a `user:{userId}:sessions` Redis set as a secondary index
- Redis is already behind Docker Compose health checks — auth service waits for Redis to be ready on startup

**When to reconsider**: If regulatory requirements demand an auditable session log, move to a dedicated `RefreshTokens` table in MySQL and use Redis only as a fast lookup cache.
