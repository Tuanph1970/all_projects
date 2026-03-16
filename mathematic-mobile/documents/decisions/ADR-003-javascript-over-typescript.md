# ADR-003: Keep JavaScript for Frontend (Defer TypeScript Migration)

**Date**: March 16, 2026
**Status**: Accepted
**Deciders**: Development Team

---

## Context

The design documentation (`front_end_design.md`) specified TypeScript with `.tsx`/`.ts` files and typed interfaces throughout. The actual frontend implementation is entirely JavaScript (`.js` files) using React Native / Expo.

This was flagged as a P2 architecture gap. Two paths were evaluated:

| Option | Description | Effort | Risk |
|---|---|---|---|
| **A** | Migrate all `frontend/src/**/*.js` to TypeScript | 3–4 days | Medium — must not break running app during migration |
| **B** | Defer migration; update docs to reflect actual JS codebase | 2 hours | None |

Context at time of decision:
- Project is at ~95% MVP completion
- Primary developer is proficient in React JavaScript, not TypeScript
- All 64 frontend unit tests are already written and passing in JS
- TypeScript migration adds no new user-visible functionality
- The app runs correctly as-is

---

## Decision

**Defer TypeScript migration to post-MVP** (Option B).

`front_end_design.md` has been updated to reflect the actual JavaScript implementation. TypeScript is listed as a future expansion point.

---

## Consequences

**Positive**
- Zero risk to the working MVP — no broken imports or type errors introduced mid-project
- Developer can stay productive in a familiar language
- All existing Jest tests continue to work unchanged
- Saved 3–4 days of effort for higher-priority work (CI/CD, docs, error handling)

**Negative**
- No compile-time type checking — prop shape errors and API contract mismatches are caught at runtime or in tests, not at build time
- Onboarding a TypeScript-native developer would require they adapt to a JS codebase
- The documented Redux slice state shapes and service interfaces are informational only (not enforced by the compiler)

**When to revisit**:
- When adding a significant new feature module (migrate that module to TS first)
- When onboarding a second developer
- When the codebase stabilises post-v1.0 and a clean migration window opens

**Migration approach when ready**: Use `allowJs: true` in `tsconfig.json` to migrate files incrementally — one slice / one service at a time — rather than a big-bang rewrite.
