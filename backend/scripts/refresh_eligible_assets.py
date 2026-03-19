"""Refresh NISA eligible assets from official sources or local files.

Must run inside the Docker container (uses the container's database volume).
Use the Make target instead of invoking directly:

    make refresh-eligible

To target a specific wrapper or supply a local file, exec into the container:

    docker compose exec backend uv run --frozen --no-dev python -m scripts.refresh_eligible_assets --wrapper nisa_tsumitate
    docker compose exec backend uv run --frozen --no-dev python -m scripts.refresh_eligible_assets --wrapper nisa_tsumitate --file /path/to/file.xlsx

For local-only execution (e.g. debugging against a local DB), set:

    FOLIO_ALLOW_LOCAL_DB=1 uv run python -m scripts.refresh_eligible_assets
"""

from __future__ import annotations

import argparse
import logging

from sqlmodel import Session

from scripts import assert_docker_runtime

logger = logging.getLogger(__name__)


def _refresh_one(
    *,
    wrapper: str,
    file_path: str | None = None,
) -> dict[str, int]:
    from application.portfolio.eligibility_service import refresh_eligible_assets
    from application.portfolio.eligible_sync_service import (
        sync_wrapper_from_official_source,
    )
    from infrastructure.database import engine

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
    assert_docker_runtime()
    global logger
    from infrastructure.database import create_db_and_tables
    from logging_config import get_logger

    logger = get_logger(__name__)

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
