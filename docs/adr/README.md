# Architecture Decision Records (ADRs)

This folder records significant architectural and technical decisions made during
Folio's development. Each ADR captures the context, options considered, the
decision taken, and its consequences.

## What belongs here

- Technology or library choices with meaningful trade-offs (e.g. database engine, package manager)
- Structural decisions (e.g. layer architecture, test isolation strategy)
- Security or operational policies (e.g. auth model, CVE waivers)
- Deliberate departures from common practice (e.g. why we do X instead of the typical Y)

## What does NOT belong here

- Implementation details that are obvious from the code
- Decisions that can be reversed cheaply without broad impact
- Ongoing tasks or bugs (use GitHub Issues instead)

## ADR lifecycle

| Status | Meaning |
|--------|---------|
| `Proposed` | Under discussion, not yet accepted |
| `Accepted` | Decision is in effect |
| `Superseded` | Replaced by a newer ADR (link to successor) |
| `Deprecated` | No longer relevant but kept for historical context |

## Creating a new ADR

Copy `0000-template.md` to `NNNN-short-title.md`, increment the sequence number,
fill in the sections, and open a PR. ADR numbers are permanent — never renumber.

## Index

| # | Title | Status | Date |
|---|-------|--------|------|
| [0001](0001-sqlite-as-primary-datastore.md) | SQLite as primary datastore | Accepted | 2025-01-01 |
| [0002](0002-uv-for-python-dependency-management.md) | uv for Python dependency management | Accepted | 2025-01-01 |
| [0003](0003-clean-architecture-layer-boundaries.md) | Clean Architecture layer boundaries | Accepted | 2025-01-01 |
| [0004](0004-api-key-auth-model.md) | API key authentication model | Accepted | 2025-01-01 |
| [0005](0005-diskcache-cve-2025-69872-waiver.md) | diskcache CVE-2025-69872 risk waiver | Accepted | 2025-03-20 |
