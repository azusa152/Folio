"""
Seed or refresh wrapper eligible assets from CSV.

Usage:
    cd backend && python -m scripts.seed_eligible_assets \
      --wrapper nisa_tsumitate \
      --csv data/fsa_tsumitate_funds_sample.csv \
      --dry-run
"""

from __future__ import annotations

import argparse

from sqlmodel import Session

from application.portfolio.eligibility_service import refresh_eligible_assets
from infrastructure.database import create_db_and_tables, engine
from logging_config import get_logger

logger = get_logger(__name__)


def run(
    *,
    wrapper: str,
    csv_path: str,
    broker: str | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    create_db_and_tables()
    with Session(engine) as session:
        stats = refresh_eligible_assets(
            session=session,
            wrapper=wrapper,
            csv_path=csv_path,
            broker=broker,
            autocommit=not dry_run,
        )
        if dry_run:
            session.rollback()
            logger.info("[DRY RUN] Eligible asset refresh preview: %s", stats)
        else:
            logger.info("Eligible asset refresh completed: %s", stats)
        return stats


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh wrapper eligible assets from CSV.",
    )
    parser.add_argument(
        "--wrapper",
        required=True,
        help="Wrapper type (e.g. nisa_tsumitate, nisa_growth, ideco)",
    )
    parser.add_argument("--csv", required=True, help="Path to source CSV")
    parser.add_argument(
        "--broker",
        default=None,
        help="Optional broker scope (mainly for iDeCo lineups)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without commit")
    parsed = parser.parse_args(args)

    run(
        wrapper=parsed.wrapper,
        csv_path=parsed.csv,
        broker=parsed.broker,
        dry_run=parsed.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
