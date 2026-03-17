"""
Purge legacy data left over from pre-ledger direct-holding management.

Removes:
  1. Orphan holdings — rows with no account_id (never migrated to an account)
  2. Orphan transactions — rows with no account_id
  3. Stale holdings with zero or negative quantity (float residue / ghost positions)
  4. Orphaned Net Worth tables — networthitem / networthsnapshot (feature removed)

After purging, runs verify_positions() to report any remaining ledger drift.

Must run inside the Docker container (uses the container's database volume).
Use the Make targets instead of invoking directly:

    make purge-legacy-dry   # preview without commit
    make purge-legacy       # apply purge

To exec into the container manually:

    docker compose exec backend uv run --frozen --no-dev python -m scripts.purge_legacy_holdings [--dry-run]

For local-only execution (e.g. debugging against a local DB), set:

    FOLIO_ALLOW_LOCAL_DB=1 uv run python -m scripts.purge_legacy_holdings
"""

from __future__ import annotations

import argparse
import logging
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from scripts import assert_docker_runtime

LEGACY_TABLES = ["networthitem", "networthsnapshot"]

logger = logging.getLogger(__name__)


def purge(dry_run: bool = False) -> dict[str, Any]:
    from domain.constants import HOLDING_QUANTITY_EPSILON
    from domain.entities import Holding, Transaction
    from infrastructure.database import create_db_and_tables, engine

    create_db_and_tables()
    stats: dict[str, Any] = {
        "orphan_holdings_deleted": 0,
        "orphan_transactions_deleted": 0,
        "zero_qty_holdings_deleted": 0,
        "legacy_tables_dropped": [],
        "discrepancies": [],
    }

    with Session(engine) as session:
        orphan_holdings = session.exec(
            select(Holding).where(Holding.account_id == None)  # noqa: E711
        ).all()
        for holding in orphan_holdings:
            logger.info(
                "Purging orphan holding: id=%s ticker=%s qty=%s",
                holding.id,
                holding.ticker,
                holding.quantity,
            )
            session.delete(holding)
        stats["orphan_holdings_deleted"] = len(orphan_holdings)

        orphan_transactions = session.exec(
            select(Transaction).where(Transaction.account_id == None)  # noqa: E711
        ).all()
        for txn in orphan_transactions:
            logger.info(
                "Purging orphan transaction: id=%s ticker=%s type=%s",
                txn.id,
                txn.ticker,
                txn.transaction_type,
            )
            session.delete(txn)
        stats["orphan_transactions_deleted"] = len(orphan_transactions)

        zero_holdings = session.exec(
            select(Holding).where(
                Holding.account_id != None,  # noqa: E711
                Holding.quantity <= HOLDING_QUANTITY_EPSILON,
                Holding.is_cash == False,  # noqa: E712
            )
        ).all()
        for holding in zero_holdings:
            logger.info(
                "Purging zero-qty holding: id=%s ticker=%s qty=%s account=%s",
                holding.id,
                holding.ticker,
                holding.quantity,
                holding.account_id,
            )
            session.delete(holding)
        stats["zero_qty_holdings_deleted"] = len(zero_holdings)

        if dry_run:
            session.rollback()
            logger.info("[DRY RUN] Purge preview: %s", stats)
        else:
            session.commit()
            logger.info("Purge committed: %s", stats)

    existing_tables = set(inspect(engine).get_table_names())
    for table_name in LEGACY_TABLES:
        if table_name in existing_tables:
            if dry_run:
                logger.info("[DRY RUN] Would drop legacy table: %s", table_name)
            else:
                with engine.begin() as conn:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                logger.info("Dropped legacy table: %s", table_name)
            stats["legacy_tables_dropped"].append(table_name)
        else:
            logger.info("Legacy table already absent: %s", table_name)

    try:
        from application.portfolio.settlement_service import verify_positions

        with Session(engine) as session:
            discrepancies = verify_positions(session)
        stats["discrepancies"] = discrepancies
        if discrepancies:
            logger.warning(
                "Ledger drift detected after purge (%d positions): %s",
                len(discrepancies),
                discrepancies,
            )
        else:
            logger.info("Ledger verification passed — no drift detected.")
    except Exception:
        logger.info("Skipped ledger verification (run inside Docker for full check).")

    return stats


def main(args: list[str] | None = None) -> int:
    assert_docker_runtime()
    global logger
    from logging_config import get_logger

    logger = get_logger(__name__)

    parser = argparse.ArgumentParser(
        description="Purge orphaned / zero-quantity legacy holding data.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without commit")
    parsed = parser.parse_args(args)
    try:
        result: dict[str, Any] = purge(dry_run=parsed.dry_run)
    except OperationalError as exc:
        logger.error("Purge failed — database not initialized: %s", exc)
        return 1
    logger.info("Purge result: %s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
