"""Application service for tax-wrapper asset eligibility."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from domain.portfolio.eligibility import EligibilityResult, check_eligibility
from infrastructure import repositories as repo
from infrastructure.external.eligible_fund_parser import detect_and_parse

if TYPE_CHECKING:
    from sqlmodel import Session

    from domain.entities import EligibleAsset


def check_asset_eligibility(
    session: Session,
    ticker: str,
    wrapper: str,
    broker: str | None = None,
) -> EligibilityResult:
    """Check whether an asset is eligible for the requested tax wrapper."""
    normalized_ticker = ticker.strip().upper()
    normalized_wrapper = wrapper.strip().lower()
    normalized_broker = broker.strip() if broker else None

    approved_tickers: set[str] | None = None
    broker_lineup: set[str] | None = None
    asset_type = "stock"

    if normalized_wrapper == "nisa_tsumitate":
        approved_tickers = repo.find_eligible_tickers(
            session=session,
            wrapper=normalized_wrapper,
        )
        asset_type = "mutual_fund"
    elif normalized_wrapper == "nisa_growth":
        approved_tickers = repo.find_eligible_tickers(
            session=session,
            wrapper=normalized_wrapper,
            broker=normalized_broker,
        )
        if approved_tickers and normalized_ticker not in approved_tickers:
            return EligibilityResult(
                eligible=False,
                reasons=["eligibility.not_in_growth_approved_list"],
                suggested_wrapper="tokutei",
            )
    elif normalized_wrapper == "ideco":
        broker_lineup = repo.find_eligible_tickers(
            session=session,
            wrapper=normalized_wrapper,
            broker=normalized_broker,
        )

    return check_eligibility(
        ticker=normalized_ticker,
        wrapper=normalized_wrapper,
        asset_type=asset_type,
        approved_tickers=approved_tickers,
        broker_lineup=broker_lineup,
    )


def get_eligible_assets(
    session: Session,
    wrapper: str,
    broker: str | None = None,
    search: str | None = None,
    limit: int = 50,
) -> list[EligibleAsset]:
    """List eligible assets for a wrapper with optional filters."""
    return repo.find_eligible_assets(
        session=session,
        wrapper=wrapper.strip().lower(),
        broker=broker.strip() if broker else None,
        search=search,
        limit=limit,
    )


def refresh_eligible_assets(
    session: Session,
    wrapper: str,
    file_path: str,
    broker: str | None = None,
    *,
    source: str = "manual_upload",
    autocommit: bool = True,
) -> dict[str, int]:
    """Bulk refresh eligible assets from CSV/XLSX (idempotent upsert + deactivate)."""
    normalized_wrapper = wrapper.strip().lower()
    path = Path(file_path)
    rows = detect_and_parse(path, wrapper=normalized_wrapper)
    return refresh_eligible_assets_from_rows(
        session=session,
        wrapper=normalized_wrapper,
        rows=rows,
        broker=broker.strip() if broker else None,
        source=source,
        autocommit=autocommit,
    )


def refresh_eligible_assets_from_rows(
    session: Session,
    wrapper: str,
    rows: list[dict],
    broker: str | None = None,
    *,
    source: str = "manual_upload",
    autocommit: bool = True,
) -> dict[str, int]:
    """Bulk refresh eligible assets from normalized rows."""
    if not rows:
        raise ValueError("No eligible assets parsed from source file.")
    return repo.upsert_eligible_assets(
        session=session,
        wrapper=wrapper.strip().lower(),
        rows=rows,
        broker=broker.strip() if broker else None,
        source=source,
        autocommit=autocommit,
    )


def get_eligible_assets_metadata(session: Session, wrapper: str) -> dict[str, object]:
    """Get eligible-asset freshness metadata for one wrapper."""
    return repo.get_eligible_assets_metadata(session=session, wrapper=wrapper)


def seed_default_eligible_assets_if_empty(
    session: Session,
) -> dict[str, dict[str, int]]:
    """Seed bundled snapshot CSVs for NISA wrappers if tables are empty."""
    seeded: dict[str, dict[str, int]] = {}
    base_dir = Path(__file__).resolve().parents[2] / "data"
    wrapper_to_file = {
        "nisa_tsumitate": base_dir / "nisa_tsumitate_snapshot.csv",
        "nisa_growth": base_dir / "nisa_growth_snapshot.csv",
    }
    for wrapper, path in wrapper_to_file.items():
        current = repo.get_eligible_assets_metadata(session=session, wrapper=wrapper)
        if int(current["count"]) > 0 or not path.exists():
            continue
        seeded[wrapper] = refresh_eligible_assets(
            session=session,
            wrapper=wrapper,
            file_path=str(path),
            source="csv_seed",
            autocommit=True,
        )
    return seeded
