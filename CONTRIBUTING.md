# Contributing to Folio

## Prerequisites

| Tool | Version |
|---|---|
| Python | **3.12** (pinned — see [Python version pinning](docs/DEVELOPMENT.md#python-version-pinning)) |
| Node.js | 20+ |
| [uv](https://docs.astral.sh/uv/) | Latest |
| Docker + Docker Compose | Any recent |

## Setup

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

make setup          # install deps, run codegen, install pre-commit hooks
docker compose up -d
```

## Development Loop

```bash
make dev                 # start backend + frontend dev servers with hot-reload
make ci-quick            # fast: lint + tests (run before pushing)
make backend-test-quick  # even faster: backend tests only, no coverage
make format              # format all code (backend + frontend)
```

## Before Opening a PR

```bash
make ci   # full CI — mirrors all GitHub Actions jobs; must pass before merge
```

## Branch and Commit Conventions

| Convention | Format | Example |
|---|---|---|
| Branch | `<type>/<kebab-case>` | `feat/add-fx-alert` |
| Commit | `<type>: <description>` (imperative) | `feat: add FX exchange timing alert` |

Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

## Architecture Boundaries

- Layer direction: `domain` → `application` → `infrastructure` → `api`
- `api/routes/` must delegate to `application/*` services
- `api/*` must not import `infrastructure/*` directly (except `infrastructure.database`)
- `domain/*` must not import outer layers
- Boundaries are enforced by `backend/tests/test_architecture.py` (runs in `make ci`)

## Where Standards Live

| Topic | Reference |
|---|---|
| Full dev guide (setup, CI, coverage, architecture, logging) | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| Project conventions | `.cursor/rules/project-core.mdc` |
| Architecture rules | `.cursor/rules/architecture-boundaries.mdc` |
| Testing rules | `.cursor/rules/testing.mdc` |
| Frontend standards | `.cursor/rules/frontend-standards.mdc` |
| API reference | [docs/API.md](docs/API.md) |
