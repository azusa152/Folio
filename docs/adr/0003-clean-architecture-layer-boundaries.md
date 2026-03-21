# 0003 — Clean Architecture layer boundaries

**Date:** 2025-01-01
**Status:** Accepted

---

## Context

As Folio grew from a simple script to a multi-feature FastAPI service, the
codebase needed a disciplined structure to prevent spaghetti imports (e.g.
route handlers directly querying the database, domain logic leaking into
infrastructure). Without enforced boundaries, new features would become
increasingly expensive to test and change.

## Decision

Adopt a **Clean Architecture** layering with four layers and a strict
unidirectional dependency rule:

```
domain/ → application/ → infrastructure/ → api/
```

Each layer may only import from the layers to its left. Boundaries are
enforced by an automated AST-based test (`backend/tests/test_architecture.py`)
that fails the CI suite if any violation is introduced.

| Layer | Allowed imports |
|-------|----------------|
| `domain/` | stdlib, `domain.*` only |
| `application/` | `domain.*`, `infrastructure.*`, `i18n`, `logging_config` |
| `infrastructure/` | `domain.*`, `i18n`, `logging_config`, stdlib |
| `api/` | `application.*`, `domain.*`, `api.*`, `i18n`, `logging_config`, `infrastructure.database` |

## Options considered

| Option | Pros | Cons |
|--------|------|------|
| **Chosen: Clean Architecture (enforced)** | Testable domain logic; swappable infrastructure; automated enforcement | More upfront boilerplate for new features; learning curve for contributors |
| Flat package structure | Simple to start, familiar to Flask-style developers | Grows into a tangle; hard to test domain logic in isolation |
| Hexagonal / Ports & Adapters | Similar benefits to Clean Architecture | No meaningful difference for this codebase size |

## Consequences

**Positive:**
- Domain logic is pure Python with no framework dependencies — trivially testable without a DB or HTTP client.
- Infrastructure adapters (yfinance, J-Quants, FinMind) can be swapped or mocked without touching domain or application code.
- The architecture test gives instant feedback on accidental boundary violations.

**Negative / trade-offs:**
- New developers need to read `CONTRIBUTING.md` and `.cursor/rules/architecture-boundaries.mdc` before writing their first feature.
- Some features require touching multiple layers (route → service → domain), which feels verbose for simple CRUD.

**Neutral / ongoing:**
- Backward-compatibility shims (`domain/constants.py`, `infrastructure/repositories.py`) preserve old import paths so existing code doesn't need a mass refactor after each reorganisation.
