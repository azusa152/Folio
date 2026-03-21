# 0004 — API key authentication model

**Date:** 2025-01-01
**Status:** Accepted

---

## Context

Folio is a single-user self-hosted application. It exposes a FastAPI backend
that needs to be protected when deployed on the public internet, but it does
not need multi-user session management, OAuth flows, or role-based access
control.

## Decision

Use a **single static API key** passed as the `X-API-Key` HTTP header.
The key is set via the `FOLIO_API_KEY` environment variable. When the variable
is unset, authentication is disabled (dev mode). The same key is embedded in
the frontend at build time as `VITE_API_KEY`.

## Options considered

| Option | Pros | Cons |
|--------|------|------|
| **Chosen: Static API key** | Simple, stateless, no session storage, trivially testable | Key rotation requires redeployment; single factor |
| JWT tokens | Industry standard, expiry, claims | Overkill for single-user; requires token issuance endpoint |
| Basic Auth | Universally supported | Plaintext password in base64; worse developer ergonomics than a key header |
| OAuth 2.0 / OIDC | Industry-grade, supports SSO | Massively over-engineered for a personal tool |

## Consequences

**Positive:**
- Zero session state to manage or expire.
- Easy to test: clear `FOLIO_API_KEY` in the test `conftest.py` and auth is bypassed.
- `/health` is explicitly excluded from auth so Docker healthchecks work without the key.

**Negative / trade-offs:**
- Rotating the key requires updating `.env` and rebuilding the frontend image (since `VITE_API_KEY` is a build-time argument).
- The key is embedded in the browser bundle — acceptable for a single-user deployment behind a reverse proxy / firewall, but not suitable for a shared deployment.

**Neutral / ongoing:**
- Rate limiting (`slowapi`) is applied on top of auth to prevent brute-force key guessing.
- `make generate-key` generates a cryptographically random key (`sk-folio-<urlsafe-32-bytes>`).
