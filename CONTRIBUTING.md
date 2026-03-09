# Contributing To Folio

## Prerequisites

- Python 3.12
- Node.js 20
- `uv`
- Docker + Docker Compose

## Setup

```bash
make setup
docker compose up -d
```

## Development

```bash
make dev
```

## Verification

Run before opening a PR:

```bash
make ci
```

## Branch And Commit Conventions

- Branch: `<type>/<kebab-case>` (example: `feat/add-fx-alert`)
- Commit: `<type>: <description>` (imperative, concise)
- Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

## Architecture Boundaries

- Layer direction: `domain` -> `application` -> `infrastructure` -> `api`
- `api/routes` must delegate to `application/*` services
- `api/*` must not import `infrastructure/*` directly (except `infrastructure.database`)
- `domain/*` must not import outer layers
- Boundaries are enforced by `backend/tests/test_architecture.py`

## Where Standards Live

- Project conventions: `.cursor/rules/project-core.mdc`
- Architecture rules: `.cursor/rules/architecture-boundaries.mdc`
- Testing rules: `.cursor/rules/testing.mdc`
- Frontend standards: `.cursor/rules/frontend-standards.mdc`
