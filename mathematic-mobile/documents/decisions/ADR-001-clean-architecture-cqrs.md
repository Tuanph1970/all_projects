# ADR-001: Adopt Clean Architecture + CQRS over Transaction Script

**Date**: March 9, 2026
**Status**: Accepted
**Deciders**: Development Team

---

## Context

The original backend code used a **Transaction Script** pattern:
- Controllers called service classes directly (`AuthenticationService`, `ProblemManagementService`)
- Services called `DbContext` directly — no repository abstraction
- Services returned `(bool Success, string Message, T? Response)` tuples instead of using exceptions
- No separation between business logic and infrastructure concerns

The design documentation (`back_end_design.md`) described Clean Architecture + CQRS + MediatR + Repository pattern — but none of this existed in the actual code. This created a misleading mismatch between docs and reality, and made unit testing require EF Core in-memory databases.

Two options were evaluated:

| Option | Description | Effort |
|---|---|---|
| **A** | Update the docs to describe Transaction Script (keep the code as-is) | ~1 day |
| **B** | Implement the documented Clean Architecture (refactor the code) | ~3 days |

---

## Decision

**Chose Option B** — implement Clean Architecture + CQRS in both services.

### What was built

**Domain layer**
- `BaseEntity` with `Guid Id`, `CreatedAt`, `UpdatedAt`, domain event support
- Rich entities with private setters and factory methods: `User.Create()`, `Problem.Create()`
- Domain-significant state transitions encapsulated as methods (`RecordLogin()`, `SetProcessing()`, etc.)

**Application layer**
- MediatR 12.2.0 CQRS: all business logic split into `Command`/`Query` + `Handler` pairs
- FluentValidation 11.9.0 with `ValidationBehavior<TRequest, TResponse>` pipeline
- Repository interfaces (`IUserRepository`, `IProblemRepository`, `IUnitOfWork`)
- Typed exceptions (`NotFoundException`, `UnauthorizedException`, `AppValidationException`)

**Infrastructure layer**
- Concrete EF Core repositories, `UnitOfWork`, external service clients

**Presentation layer**
- Thin controllers — only call `ISender.Send()` from MediatR; zero business logic

---

## Consequences

**Positive**
- Unit tests can now mock `IUserRepository` / `IUnitOfWork` — no EF Core in-memory setup required
- Adding a new feature = add a `Command` + `Handler` + `Validator` without touching existing code
- Code matches documentation — no more misleading mismatch
- Typed exceptions + global middleware eliminate the `(bool, string, T?)` tuple anti-pattern

**Negative**
- More files per feature (command, handler, validator, DTO) — more boilerplate than Transaction Script
- Higher upfront learning curve for developers unfamiliar with MediatR / CQRS
- 3 days of refactor effort instead of 1

**Trade-off accepted**: The testability and extensibility gains outweigh the boilerplate cost for a project expected to grow with new problem types and auth providers.
