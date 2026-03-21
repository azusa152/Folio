# Runbook: Backup and Restore

## Overview

Folio's data lives in a single SQLite file (`radar.db`) inside the `radar-data`
Docker named volume. Backup is a file copy; restore is a file replacement.

---

## Regular backup

```bash
# Creates backups/radar-YYYYMMDD_HHMMSS.db
make backup
```

The backup file is written to `./backups/` in the repo root on the Docker host.
Keep multiple backups; the Makefile shows the most recent one after each run.

**Recommended schedule:** daily cron on the host machine:

```cron
0 2 * * * cd /path/to/azusa-stock && make backup >> /var/log/folio-backup.log 2>&1
```

---

## Restore from backup

```bash
# Restore the latest backup
make restore

# Restore a specific backup file
make restore FILE=backups/radar-20260101_020000.db
```

> **Warning:** Restoring overwrites all current data. Stop the application
> first if consistency matters:
>
> ```bash
> make down
> make restore FILE=backups/radar-YYYYMMDD_HHMMSS.db
> make up
> ```

---

## Migrate to a new host

1. On the **old host**:
   ```bash
   make backup
   # Copy the backup file to the new host
   scp backups/radar-YYYYMMDD_HHMMSS.db user@newhost:/path/to/azusa-stock/backups/
   ```

2. On the **new host**:
   ```bash
   # Start services so the volume is created
   make up
   # Wait for the backend to initialise, then restore
   make restore FILE=backups/radar-YYYYMMDD_HHMMSS.db
   make restart
   ```

---

## Verify a backup

```bash
# Confirm the backup is a valid SQLite file
sqlite3 backups/radar-YYYYMMDD_HHMMSS.db "PRAGMA integrity_check;"
# Expected output: ok

# Check table counts
sqlite3 backups/radar-YYYYMMDD_HHMMSS.db "SELECT COUNT(*) FROM stock;"
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Error: radar-data volume not found` | Services not running / volume name mismatch | Run `docker volume ls` and verify the volume contains `radar-data`; run `make up` first |
| `Error: No backup found in ./backups/` | No backup files exist | Create a backup with `make backup` first |
| Restore completes but data is wrong | Wrong backup file | Re-run with the correct `FILE=` path |
