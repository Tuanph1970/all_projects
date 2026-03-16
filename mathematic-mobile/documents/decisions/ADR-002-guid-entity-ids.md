# ADR-002: Use Guid Instead of int for Entity IDs

**Date**: March 9, 2026
**Status**: Accepted
**Deciders**: Development Team

---

## Context

The original `User` and `Problem` models used `int Id` (auto-increment primary keys). The design documentation (`back_end_design.md`) defined `BaseEntity` with `Guid Id`. This created a schema mismatch that would cause migration failures if the documented architecture were ever implemented.

When Clean Architecture was adopted (see ADR-001), both approaches were evaluated:

| Aspect | `int` (auto-increment) | `Guid` |
|---|---|---|
| Insert performance | Faster (sequential, DB-generated) | Slightly slower (random, client-generated) |
| Join performance | Faster (4 bytes vs 16 bytes) | Marginally slower |
| ID exposure in URLs | Leaks record count and insertion order | Opaque — no information leakage |
| Distributed/merge safety | Collisions if merging tables from multiple DBs | Globally unique by design |
| Client-side ID generation | Not possible | Possible — ID known before insert |
| Docs alignment | Mismatched | Aligned with `back_end_design.md` |

---

## Decision

**Use `Guid` for all entity IDs**, stored as `char(36)` in MySQL.

```csharp
// Domain/Common/BaseEntity.cs
public abstract class BaseEntity
{
    public Guid Id { get; protected set; } = Guid.NewGuid();
    ...
}
```

Old `int`-based migrations were deleted and the schema was recreated via `EnsureCreated()`.

---

## Consequences

**Positive**
- IDs in API responses and URLs are opaque — users cannot infer the total number of problems or users in the system
- Safe for future data migrations, multi-region setups, or merging datasets from test environments
- Consistent with the documented `BaseEntity` design
- Problem IDs can be generated client-side before the insert completes (useful for optimistic UI updates)

**Negative**
- `char(36)` is larger than `int` — indexes are wider, JOINs are marginally slower
- MySQL does not natively sort GUIDs by insert time — if insertion-order sorting is needed, a `CreatedAt` index must be used (already added as one of the 14 performance indexes)
- Slightly more verbose in logs and debugging output

**Trade-off accepted**: The security and distributed-safety benefits of opaque IDs outweigh the minor performance cost, which is negligible at the expected scale of this application.
