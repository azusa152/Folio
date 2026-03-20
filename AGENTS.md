# Folio Agent Guide

> **Audience:** AI coding assistants and human contributors working on the codebase.
> For the Folio webhook AI agent behavioral rules (action routing, auth, runtime
> discovery), see [`docs/agents/AGENTS.md`](docs/agents/AGENTS.md).

Folio is a Dockerized investment analysis system (FastAPI + React + SQLite) for watchlists, ledger-driven positions, FX monitoring, and guru 13F analysis.

## Run And Verify

- Full validation: `make ci` (parallelized in 3 phases: fast checks, tests+build, security)
- Quick validation: `make ci-quick` (lint + tests, no coverage/security/typecheck)
- Fast backend test loop: `make backend-test-quick`
- Lint everything: `make lint`
- Regenerate API contract after schema changes: `make generate-api`

## Architecture Boundaries

- Layers: `domain` -> `application` -> `infrastructure` -> `api`
- In `api/routes`, delegate to `application/*` services
- Do not import `infrastructure/*` directly from `api/*` (except `infrastructure.database`)
- Keep domain rules inside `domain/*` (no outer-layer imports)
- Verify with `backend/tests/test_architecture.py` (included in `make ci`)

## Key Paths

- Backend constants and action metadata: `backend/domain/core/constants.py`
- API schemas: `backend/api/schemas/`
- API routes: `backend/api/routes/`
- Application services: `backend/application/`
- Frontend API contract: `frontend-react/src/api/openapi.json`
- AI/webhook docs: `docs/agents/`
- Transaction service: `backend/application/portfolio/transaction_service.py`
- Settlement service (stock + cash): `backend/application/portfolio/settlement_service.py`
- Account service: `backend/application/portfolio/account_service.py`
- Analytics service: `backend/application/portfolio/analytics_service.py`
- Insight service: `backend/application/portfolio/insight_service.py`
- Tax wrapper domain: `backend/domain/portfolio/tax_wrapper.py`, `backend/domain/portfolio/eligibility.py`, `backend/domain/portfolio/asset_location.py`
- Tax wrapper services: `backend/application/portfolio/wrapper_service.py`, `backend/application/portfolio/eligibility_service.py`, `backend/application/portfolio/routing_service.py`
- Tax wrapper routes: `backend/api/routes/wrapper_routes.py`
- Tax wrapper schemas: `backend/api/schemas/wrapper.py`
- Eligible asset seed: `backend/scripts/seed_eligible_assets.py`
- NAV sync service (periodic + on-demand): `backend/application/portfolio/nav_sync_service.py`
- Toushin adapter: `backend/infrastructure/market_data/toushin_adapter.py`
- Ledger migration: `backend/scripts/migrate_ledger.py`
- Domain analytics: `backend/domain/analysis/drawdown.py`, `backend/domain/analysis/risk_metrics.py`

## AI Agent Workflow

- Discover webhook capabilities first: `POST /webhook` with `{"action":"help"}`
- Branch on `error_code`, not localized `detail`
- Prefer `format: "concise"` when token budget matters
- For NISA/iDeCo quota status, use webhook `quota`
- NISA quota is tracked at cost basis (簿價), not market value
- Use `docs/agents/folio/SKILL.md` for compact action usage
- Use `docs/agents/folio/reference.md` only when detailed field-level specs are needed

## Git And Safety

- Commit message format: `<type>: <description>` (imperative)
- Never commit secrets (`.env`, tokens, credentials)
- Do not use destructive git operations unless explicitly requested
