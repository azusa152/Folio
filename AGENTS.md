# Folio Agent Guide

Folio is a Dockerized investment analysis system (FastAPI + React + SQLite) for watchlists, holdings, FX monitoring, and guru 13F analysis.

## Run And Verify

- Full validation: `make ci`
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
- Account service: `backend/application/portfolio/account_service.py`
- Analytics service: `backend/application/portfolio/analytics_service.py`
- Insight service: `backend/application/portfolio/insight_service.py`
- Domain analytics: `backend/domain/analysis/drawdown.py`, `backend/domain/analysis/risk_metrics.py`

## AI Agent Workflow

- Discover webhook capabilities first: `POST /webhook` with `{"action":"help"}`
- Branch on `error_code`, not localized `detail`
- Prefer `format: "concise"` when token budget matters
- Use `docs/agents/folio/SKILL.md` for compact action usage
- Use `docs/agents/folio/reference.md` only when detailed field-level specs are needed

## Git And Safety

- Commit message format: `<type>: <description>` (imperative)
- Never commit secrets (`.env`, tokens, credentials)
- Do not use destructive git operations unless explicitly requested
