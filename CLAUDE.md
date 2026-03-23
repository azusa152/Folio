# Folio — Investment Analysis System

**Folio** is a self-hosted, thesis-driven stock tracking system for disciplined investors. Track watchlist stocks, monitor market signals, and analyze currency exposure.

## Quick Start

```bash
# First-time: install uv (Python package manager) if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

make setup               # First-time setup: uv sync + npm ci + codegen + pre-commit hooks
docker compose up -d
make ci                  # Full CI check — mirrors ALL GitHub CI pipeline jobs (parallelized)
make ci-quick            # Quick CI — lint + tests (no coverage/security/typecheck)
make test                # Run all tests (backend + frontend)
make backend-test-quick  # Fast backend tests — no coverage, for local iteration
make lint                # Lint all (backend + frontend)
make format              # Format code
make clean               # Remove build caches
```

## Key Documentation

| Document | Contents |
|---|---|
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Python version pinning, uv dependency management, API codegen, CI pipeline, test coverage, architecture, project structure, logging, security |
| [docs/API.md](docs/API.md) | Full API endpoint reference, curl examples, OpenClaw/webhook integration |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Features, scanning logic, import guides, Telegram setup, data management |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Branch/commit conventions, PR workflow |

## Dev Container / Codespaces

Open in VS Code with the Dev Containers extension or launch on GitHub Codespaces.
The container auto-runs `make setup` and forwards ports 3000 (frontend) and 8000 (backend).

## Claude Code Permissions

If using Claude Code, add these portable patterns to `.claude/settings.local.json` (this file is local-only and not tracked by git):

```json
{
  "permissions": {
    "allow": [
      "Bash(make:*)", "Bash(uv:*)", "Bash(python:*)", "Bash(python3:*)",
      "Bash(npm:*)", "Bash(npx:*)", "Bash(git:*)", "Bash(curl:*)",
      "Bash(docker:*)", "Bash(docker compose:*)", "Bash(rg:*)"
    ]
  }
}
```

## Agent API

Folio exposes an agent-friendly webhook entrypoint at `POST /webhook`.

- Start discovery with `{"action":"help"}` to list actions, workflows, and model hints
- Use `docs/agents/folio/SKILL.md` for compact action usage
- Use `docs/agents/folio/reference.md` for detailed fields and thresholds
- Branch on `error_code` (machine-readable), not localized `detail`
- For NISA/iDeCo quota status, use `{"action":"quota"}`
- See [docs/API.md](docs/API.md) for the full webhook action table and curl examples
- When webhook actions change, update agent docs under `docs/agents/`

## Architecture Boundaries (enforced by `backend/tests/test_architecture.py`)

Layer dependency direction: `domain/` → `application/` → `infrastructure/` → `api/`

- `api/routes/` MUST delegate to `application/<domain>/` services. Only `infrastructure.database` (`get_session`, `engine`) is allowed in `api/`.
- `domain/` must not import from any outer layer.
- Run `make ci` after any backend change to verify boundaries.

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#architecture) for the full architecture guide including the layer table, import rules, and complete project structure.
