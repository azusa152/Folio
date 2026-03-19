"""Shared helpers for operational scripts."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def assert_docker_runtime() -> None:
    """Refuse DB mutations when invoked outside Docker runtime."""
    db_url = os.getenv("DATABASE_URL", "sqlite:///data/radar.db")
    if os.getenv("FOLIO_ALLOW_LOCAL_DB") == "1":
        logger.warning(
            "FOLIO_ALLOW_LOCAL_DB=1 set; bypassing runtime guard (DB: %s)",
            db_url,
        )
        return

    is_container_runtime = os.path.exists("/.dockerenv")
    if not is_container_runtime:
        logger.error(
            "This script must run inside the Docker container.\n"
            "  DATABASE_URL: %s\n"
            "  Use make targets that run via docker compose exec.\n"
            "  If you intentionally need local execution, set FOLIO_ALLOW_LOCAL_DB=1.",
            db_url,
        )
        raise SystemExit(1)

    if db_url.startswith("sqlite") and not db_url.startswith(
        ("sqlite:///data/", "sqlite:////app/data/")
    ):
        logger.error(
            "Refusing to run against an unexpected SQLite path.\n"
            "  DATABASE_URL: %s\n"
            "  Expected SQLite URL under /app/data.\n"
            "  If intentional, set FOLIO_ALLOW_LOCAL_DB=1.",
            db_url,
        )
        raise SystemExit(1)

    logger.info("Runtime guard passed (DB: %s)", db_url)
