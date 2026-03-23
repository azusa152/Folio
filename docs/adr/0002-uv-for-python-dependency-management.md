# 0002 — uv for Python dependency management

**Date:** 2025-01-01
**Status:** Accepted

---

## Context

The backend needs a reliable, fast, and reproducible way to install Python
dependencies in both local development environments and Docker builds. The
traditional `pip` + `requirements.txt` approach has known issues with
reproducibility and slow cold installs.

## Decision

Use **[uv](https://docs.astral.sh/uv/)** for all Python dependency management.
`backend/pyproject.toml` defines direct dependencies; `backend/uv.lock` pins
the full transitive closure. Docker builds use `uv sync --frozen` for
bit-for-bit reproducibility.

## Options considered

| Option | Pros | Cons |
|--------|------|------|
| **Chosen: uv** | 10–100× faster than pip, native lockfile, PEP 621 compliant, single binary | Relatively new tool; community adoption still growing |
| pip + pip-tools | Widely understood, stable | Slow cold installs; `requirements.txt` is less expressive than `pyproject.toml` |
| Poetry | Mature, good UX | Heavier; its lockfile format is not PEP 621 native; slower than uv |
| PDM | PEP 621 native, modern | Smaller community than Poetry; no meaningful advantage over uv |

## Consequences

**Positive:**
- `make install` completes in seconds even on a cold cache.
- `uv.lock` is committed to git, making every `uv sync --frozen` fully reproducible.
- Dependabot + the `dependabot-uv-lock.yml` workflow automate lockfile refresh on dependency PRs.
- `make lock` / `make upgrade` are the only entry points for modifying the lockfile.

**Negative / trade-offs:**
- Developers must install `uv` before `make setup` (one curl command; documented in README).
- CI pins `UV_VERSION` in `.github/workflows/ci.yml` and `backend/Dockerfile`; both must be kept in sync when upgrading uv.

**Neutral / ongoing:**
- `uv run` is used in Makefile and CI rather than activating the venv explicitly, which keeps commands portable and avoids shell activation pitfalls.
