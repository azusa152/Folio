"""Application service for tax-wrapper asset eligibility."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from domain.portfolio.eligibility import EligibilityResult, check_eligibility
from infrastructure import repositories as repo

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
    csv_path: str,
    broker: str | None = None,
    *,
    autocommit: bool = True,
) -> dict[str, int]:
    """Bulk refresh eligible assets from CSV (idempotent upsert + deactivate)."""
    path = Path(csv_path)
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            trust_fee_raw = (row.get("trust_fee_pct") or "").strip()
            trust_fee = float(trust_fee_raw) if trust_fee_raw else None
            rows.append(
                {
                    "ticker": row.get("ticker", ""),
                    "fund_name": row.get("fund_name", ""),
                    "asset_type": row.get("asset_type", "mutual_fund"),
                    "trust_fee_pct": trust_fee,
                }
            )

    return repo.upsert_eligible_assets(
        session=session,
        wrapper=wrapper.strip().lower(),
        rows=rows,
        broker=broker.strip() if broker else None,
        autocommit=autocommit,
    )
