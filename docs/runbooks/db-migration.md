# Runbook: Database Migration

## Overview

Folio uses SQLite with manual migration scripts under `backend/scripts/`.
There is no Alembic migration history; each script is idempotent and safe to
re-run.

---

## Ledger migration (backfill opening balances)

Run when upgrading from a pre-ledger version of Folio that stored positions
directly in the `holding` table without a transaction history.

```bash
# Dry-run first — preview changes without committing
make migrate-ledger-dry

# Apply the migration
make migrate-ledger
```

The script (`backend/scripts/migrate_ledger.py`) scans existing holdings,
creates `OPENING_BALANCE` transactions, and links holdings to accounts.

---

## Purge legacy data

Removes zero-quantity holdings and orphaned data left over from pre-ledger
versions.

```bash
# Preview what would be deleted
make purge-legacy-dry

# Apply the purge
make purge-legacy
```

---

## NISA eligible asset refresh

Updates the NISA-eligible fund list from the official source (Investment Trusts
Association). This runs automatically on the `ELIGIBLE_SYNC_INTERVAL_HOURS`
schedule, but can be triggered manually:

```bash
make refresh-eligible
```

---

## Schema changes (manual DDL)

Folio does not use Alembic. For ad-hoc schema changes:

1. **Back up first:** `make backup`
2. **Apply DDL** using `sqlite3` or a migration script:
   ```bash
   docker compose exec backend sqlite3 /app/data/radar.db "ALTER TABLE stock ADD COLUMN ..."
   ```
3. **Verify:** `make up` — the app runs `create_db_and_tables()` at startup which
   adds new tables but does not drop or alter existing columns.
4. **Document** the change in a new ADR under `docs/adr/` if it represents a
   structural decision.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `docker compose exec` fails | Backend container not running | `make up` first |
| Migration script exits with error | Constraint violation or unexpected data | Run dry-run to inspect, then fix data manually before re-running |
| App won't start after schema change | Incompatible schema | Restore backup and re-apply changes carefully |
