"""Tax wrapper quota services."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from domain.constants import NISA_LIMITS, NISA_RESTORATION_POLICY
from domain.entities import ContributionLedgerEntry
from domain.portfolio.tax_wrapper import (
    compute_restoration_effective_date,
    get_available_quota,
)
from infrastructure import repositories as repo

if TYPE_CHECKING:
    from sqlmodel import Session


def get_ledger_entries(session: Session, user_id: str) -> list[ContributionLedgerEntry]:
    """Fetch all ledger entries for one user."""
    return repo.find_ledger_entries(session, user_id)


def get_all_wrapper_quotas(
    session: Session,
    user_id: str,
    year: int,
    as_of: date,
) -> dict[str, dict]:
    """Return quota summary for all NISA wrappers."""
    entries = repo.find_ledger_entries(session, user_id)
    limits = NISA_LIMITS
    quotas: dict[str, dict] = {}
    for wrapper in ("nisa_tsumitate", "nisa_growth"):
        status = get_available_quota(entries, wrapper, year, as_of)

        # Derive used-amounts from status fields to avoid re-scanning entries.
        wrapper_annual_limit = float(limits[wrapper].get("annual", 0))
        combined_annual_limit = float(limits["combined_annual"])
        combined_lifetime_limit = float(limits["combined_lifetime"])

        wrapper_annual_used = max(
            0.0, wrapper_annual_limit - status.wrapper_annual_remaining
        )
        combined_annual_used = max(
            0.0, combined_annual_limit - status.combined_annual_remaining
        )
        lifetime_used = max(0.0, combined_lifetime_limit - status.lifetime_remaining)

        growth_sub_limit_used: float | None = None
        if status.growth_sub_limit_remaining is not None:
            growth_sub_limit = float(limits["nisa_growth"]["lifetime_sub_limit"])
            growth_sub_limit_used = max(
                0.0, growth_sub_limit - status.growth_sub_limit_remaining
            )

        quotas[wrapper] = {
            "wrapper": wrapper,
            "wrapper_annual_remaining": round(status.wrapper_annual_remaining, 2),
            "combined_annual_remaining": round(status.combined_annual_remaining, 2),
            "lifetime_remaining": round(status.lifetime_remaining, 2),
            "growth_sub_limit_remaining": (
                round(status.growth_sub_limit_remaining, 2)
                if status.growth_sub_limit_remaining is not None
                else None
            ),
            "wrapper_annual_used": round(wrapper_annual_used, 2),
            "combined_annual_used": round(combined_annual_used, 2),
            "lifetime_used": round(lifetime_used, 2),
            "growth_sub_limit_used": round(growth_sub_limit_used, 2)
            if growth_sub_limit_used is not None
            else None,
        }
    return quotas


def record_contribution(
    session: Session,
    user_id: str,
    wrapper: str,
    amount: float,
    fiscal_year: int,
    transaction_id: int | None,
    effective_date: date,
    *,
    note: str = "",
    autocommit: bool = True,
) -> ContributionLedgerEntry | None:
    """Record one contribution ledger entry (idempotent by transaction id)."""
    if transaction_id is not None:
        existing = repo.find_ledger_entry_by_transaction_and_type(
            session, transaction_id, "CONTRIBUTION"
        )
        if existing is not None:
            return None
    entry = ContributionLedgerEntry(
        user_id=user_id,
        tax_wrapper=wrapper,
        entry_type="CONTRIBUTION",
        fiscal_year=fiscal_year,
        amount=float(amount),
        transaction_id=transaction_id,
        effective_date=effective_date,
        note=note,
        created_at=datetime.now(UTC),
    )
    return repo.create_ledger_entry(session, entry, autocommit=autocommit)


def record_restoration(
    session: Session,
    user_id: str,
    wrapper: str,
    amount: float,
    fiscal_year: int,
    transaction_id: int | None,
    sell_date: date,
    *,
    note: str = "",
    autocommit: bool = True,
) -> ContributionLedgerEntry | None:
    """Record one restoration entry using configured policy (idempotent)."""
    if transaction_id is not None:
        existing = repo.find_ledger_entry_by_transaction_and_type(
            session, transaction_id, "RESTORATION"
        )
        if existing is not None:
            return None
    entry = ContributionLedgerEntry(
        user_id=user_id,
        tax_wrapper=wrapper,
        entry_type="RESTORATION",
        fiscal_year=fiscal_year,
        amount=-abs(float(amount)),
        transaction_id=transaction_id,
        effective_date=compute_restoration_effective_date(sell_date),
        note=note,
        created_at=datetime.now(UTC),
    )
    return repo.create_ledger_entry(session, entry, autocommit=autocommit)


def get_restoration_forecast(session: Session, user_id: str) -> dict:
    """List pending restorations that are not effective yet."""
    today = date.today()
    entries = repo.find_ledger_entries(session, user_id)
    pending = [
        {
            "tax_wrapper": entry.tax_wrapper,
            "amount": abs(float(entry.amount)),
            "effective_date": entry.effective_date,
            "source_transaction_id": entry.transaction_id,
        }
        for entry in entries
        if entry.entry_type == "RESTORATION" and entry.effective_date > today
    ]
    total_pending = sum(item["amount"] for item in pending)
    return {
        "pending": pending,
        "total_pending": round(total_pending, 2),
        "restoration_policy": NISA_RESTORATION_POLICY,
    }
