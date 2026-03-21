# 0001 — SQLite as primary datastore

**Date:** 2025-01-01
**Status:** Accepted

---

## Context

Folio is a self-hosted, single-user investment tracking system. It needs a
persistent relational store for stocks, holdings, transactions, scan logs, and
configuration. The deployment target is a single Docker host (home server,
VPS, or Codespaces) — not a horizontally scaled cloud service.

## Decision

Use **SQLite** (via SQLModel / SQLAlchemy) as the sole datastore.

## Options considered

| Option | Pros | Cons |
|--------|------|------|
| **Chosen: SQLite** | Zero-ops (no separate process), file-based backup (`make backup`), zero network latency, sufficient for single-user workload | No concurrent multi-writer support; not suitable if Folio ever becomes multi-tenant |
| PostgreSQL | Multi-writer, rich ecosystem, production-grade | Requires separate container + volume + credentials; over-engineered for single-user use |
| MySQL/MariaDB | Familiar for many developers | Same operational overhead as Postgres; no advantage over Postgres for this use case |

## Consequences

**Positive:**
- `make backup` / `make restore` are a single `cp` of the `.db` file — no dump tooling needed.
- Dev/test setup requires no external service: `DATABASE_URL=sqlite://` creates a disposable in-memory DB.
- Docker Compose is simpler: one `radar-data` named volume, no database service.

**Negative / trade-offs:**
- Write concurrency is limited to one writer at a time. Background threads (scanner, NAV sync) must not write concurrently without locking. The application serialises writes through a single SQLAlchemy engine with `StaticPool` in tests.
- Schema migrations are done manually (scripts under `backend/scripts/`); no Alembic migration history. A future multi-user version would likely require migrating to Postgres and adopting Alembic.

**Neutral / ongoing:**
- The `DATABASE_URL` environment variable is the single override point; switching to Postgres in the future requires only a URL change plus schema migration scripts.
