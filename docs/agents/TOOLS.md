# Folio Environment

- API base URL: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- API key env var: `FOLIO_API_KEY` (`X-API-Key` header when set)
- Dev mode auth: disabled when `FOLIO_API_KEY` is unset

## Common Commands

- Start/update stack: `make up`
- Health check: `curl -sf http://localhost:8000/health`
- Status: `docker compose ps`
- Backend logs: `docker compose logs backend --tail 50`
- Backup DB: `make backup`
- Restore DB: `make restore`

## Safety

- `docker compose down -v` deletes data volumes.
- Run `make backup` before destructive operations.
