"""Tax wrapper quota services."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass
class WrapperLedgerEntry:
    """Shared parameter bag for contribution and restoration ledger mutations."""

    user_id: str
    wrapper: str
    amount: float
    fiscal_year: int
    transaction_id: int | None
    effective_date: date
    entry_type: str
    note: str = ""
    autocommit: bool = True


def _record_ledger_entry(
    session: Session,
    entry_params: WrapperLedgerEntry,
) -> ContributionLedgerEntry | None:
    """Create a ledger entry after an idempotency check; returns None if already present."""
    if entry_params.transaction_id is not None:
        existing = repo.find_ledger_entry_by_transaction_and_type(
            session, entry_params.transaction_id, entry_params.entry_type
        )
        if existing is not None:
            return None
    entry = ContributionLedgerEntry(
        user_id=entry_params.user_id,
        tax_wrapper=entry_params.wrapper,
        entry_type=entry_params.entry_type,
        fiscal_year=entry_params.fiscal_year,
        amount=float(entry_params.amount),
        transaction_id=entry_params.transaction_id,
        effective_date=entry_params.effective_date,
        note=entry_params.note,
        created_at=datetime.now(UTC),
    )
    return repo.create_ledger_entry(session, entry, autocommit=entry_params.autocommit)


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
    return _record_ledger_entry(
        session,
        WrapperLedgerEntry(
            user_id=user_id,
            wrapper=wrapper,
            amount=float(amount),
            fiscal_year=fiscal_year,
            transaction_id=transaction_id,
            effective_date=effective_date,
            entry_type="CONTRIBUTION",
            note=note,
            autocommit=autocommit,
        ),
    )


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
    return _record_ledger_entry(
        session,
        WrapperLedgerEntry(
            user_id=user_id,
            wrapper=wrapper,
            amount=-abs(float(amount)),
            fiscal_year=fiscal_year,
            transaction_id=transaction_id,
            effective_date=compute_restoration_effective_date(sell_date),
            entry_type="RESTORATION",
            note=note,
            autocommit=autocommit,
        ),
    )


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


def get_contribution_entries(
    session: Session,
    user_id: str,
    *,
    wrapper: str | None = None,
    year: int | None = None,
    limit: int = 500,
) -> list[ContributionLedgerEntry]:
    """List contribution ledger entries with optional wrapper/year filters."""
    entries = repo.find_ledger_entries(session, user_id)
    if wrapper:
        normalized_wrapper = wrapper.strip().lower()
        entries = [
            entry for entry in entries if entry.tax_wrapper == normalized_wrapper
        ]
    if year is not None:
        entries = [entry for entry in entries if entry.fiscal_year == year]
    entries.sort(key=lambda item: (item.effective_date, item.created_at), reverse=True)
    return entries[:limit]
