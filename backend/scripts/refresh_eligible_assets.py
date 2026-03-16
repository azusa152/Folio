"""Refresh NISA eligible assets from official sources or local files."""

from __future__ import annotations

import argparse

from sqlmodel import Session

from application.portfolio.eligibility_service import refresh_eligible_assets
from application.portfolio.eligible_sync_service import (
    sync_wrapper_from_official_source,
)
from infrastructure.database import create_db_and_tables, engine
from logging_config import get_logger

logger = get_logger(__name__)


def _refresh_one(
    *,
    wrapper: str,
    file_path: str | None = None,
) -> dict[str, int]:
    with Session(engine) as session:
        if file_path:
            return refresh_eligible_assets(
                session=session,
                wrapper=wrapper,
                file_path=file_path,
                source="manual_upload",
                autocommit=True,
            )
        return sync_wrapper_from_official_source(
            session, wrapper, source="official_sync"
        )


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh NISA eligible assets.")
    parser.add_argument(
        "--wrapper",
        choices=["nisa_tsumitate", "nisa_growth", "all"],
        default="all",
        help="Target wrapper to refresh",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Optional local CSV/XLSX file path (single-wrapper mode only)",
    )
    parsed = parser.parse_args(args)

    create_db_and_tables()
    wrappers = (
        ["nisa_tsumitate", "nisa_growth"]
        if parsed.wrapper == "all"
        else [parsed.wrapper]
    )
    if parsed.file and len(wrappers) > 1:
        raise SystemExit("--file can only be used with a single wrapper.")

    for wrapper in wrappers:
        stats = _refresh_one(wrapper=wrapper, file_path=parsed.file)
        logger.info("Eligible assets refreshed for %s: %s", wrapper, stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
