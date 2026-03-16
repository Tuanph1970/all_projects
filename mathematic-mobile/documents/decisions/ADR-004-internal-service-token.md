# ADR-004: Shared Static Token for Inter-Service Authentication

**Date**: March 9, 2026
**Status**: Accepted
**Deciders**: Development Team

---

## Context

The Problem Service calls the ML/OCR Solution Service over HTTP to submit problems for solving. These calls happen on the internal Docker network, but the Solution Service endpoint still needs to distinguish legitimate calls from the Problem Service versus external or unauthorized requests.

Three patterns were considered:

| Pattern | Description | Complexity |
|---|---|---|
| **No auth** | Trust the Docker network; accept all requests on the internal network | Low — but any container on the network can call the endpoint |
| **Shared static token** | Both services share a pre-configured secret token sent as `X-Service-Token` header | Low — simple to implement and rotate via env var |
| **mTLS / service mesh** | Mutual TLS certificates between services | High — requires PKI infrastructure, not justified at this scale |
| **JWT signed by Auth Service** | Problem Service requests a short-lived token from Auth Service before each ML call | Medium — adds a round-trip and a dependency on Auth Service availability |

---

## Decision

**Use a shared static token** (`INTERNAL_SERVICE_TOKEN`) passed as the `X-Service-Token` HTTP header.

```csharp
// SolutionServiceClient.cs — Problem Service sends the token on every call
_httpClient.DefaultRequestHeaders.Add("X-Service-Token", _serviceToken);
```

The token value is:
1. Read from `appsettings.json` key `InternalServiceToken`, **or**
2. Read from environment variable `INTERNAL_SERVICE_TOKEN`, **or**
3. Falls back to `"internal-service-token"` (development only — must be overridden in production)

The ML service validates the `X-Service-Token` header on protected endpoints.

---

## Consequences

**Positive**
- Simple to implement — no extra infrastructure, no round-trips
- Token can be rotated by updating the env var and redeploying both services (no code change)
- Works within Docker Compose's internal network without external dependencies

**Negative**
- The token is a long-lived shared secret — if it leaks, any caller can impersonate the Problem Service
- Rotation requires coordinated restart of both services (brief downtime or rolling deploy)
- No per-request audit trail of which specific service instance made the call

**Mitigations**
- Token must be set via `INTERNAL_SERVICE_TOKEN` environment variable in production — the hardcoded fallback `"internal-service-token"` is intentionally weak and will fail any security audit, serving as a forcing function to set the real value
- Docker network isolation limits exposure to containers on the same network
- All inter-service calls are logged with the Problem ID — sufficient for audit at current scale

**When to reconsider**: If the architecture expands to a service mesh (Istio, Linkerd) or multiple deployment environments with strict compliance requirements, replace this with mTLS.
