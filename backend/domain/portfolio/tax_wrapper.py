"""
Domain — NISA / iDeCo quota computation.

All quota calculations are pure functions operating on ledger entries.
Balances are always derived, never stored.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from domain.core.constants import NISA_LIMITS, NISA_RESTORATION_POLICY


class LedgerEntryLike(Protocol):
    tax_wrapper: str
    entry_type: str
    fiscal_year: int
    amount: float
    effective_date: date


@dataclass(frozen=True)
class QuotaStatus:
    """Quota availability for a specific wrapper at a point in time."""

    wrapper_annual_remaining: float
    combined_annual_remaining: float
    lifetime_remaining: float
    growth_sub_limit_remaining: float | None


def compute_annual_used(
    entries: list[LedgerEntryLike], wrapper: str, year: int
) -> float:
    """Sum of contributions for one wrapper and fiscal year."""
    return sum(
        float(e.amount)
        for e in entries
        if e.tax_wrapper == wrapper
        and e.fiscal_year == year
        and e.entry_type == "CONTRIBUTION"
    )


def compute_combined_annual_used(entries: list[LedgerEntryLike], year: int) -> float:
    """Combined annual usage across NISA wrappers."""
    nisa_wrappers = {"nisa_tsumitate", "nisa_growth"}
    return sum(
        float(e.amount)
        for e in entries
        if e.tax_wrapper in nisa_wrappers
        and e.fiscal_year == year
        and e.entry_type == "CONTRIBUTION"
    )


def compute_lifetime_used(entries: list[LedgerEntryLike], as_of: date) -> float:
    """Lifetime usage = contributions − effective restorations + adjustments.

    Restoration entries carry negative amounts (stored as -abs(cost_basis)),
    so summing them reduces lifetime_used, effectively restoring the allowance.
    """
    total = 0.0
    for entry in entries:
        if entry.tax_wrapper not in {"nisa_tsumitate", "nisa_growth"}:
            continue
        if (
            entry.entry_type == "CONTRIBUTION"
            or (entry.entry_type == "RESTORATION" and entry.effective_date <= as_of)
            or entry.entry_type == "ADJUSTMENT"
        ):
            total += float(entry.amount)
    return total


def compute_growth_lifetime_used(entries: list[LedgerEntryLike], as_of: date) -> float:
    """Growth wrapper lifetime usage against the 12M sub-limit."""
    total = 0.0
    for entry in entries:
        if entry.tax_wrapper != "nisa_growth":
            continue
        if (
            entry.entry_type == "CONTRIBUTION"
            or (entry.entry_type == "RESTORATION" and entry.effective_date <= as_of)
            or entry.entry_type == "ADJUSTMENT"
        ):
            total += float(entry.amount)
    return total


def get_available_quota(
    entries: list[LedgerEntryLike],
    wrapper: str,
    year: int,
    as_of: date,
) -> QuotaStatus:
    """Compute remaining quota across all NISA dimensions."""
    limits = NISA_LIMITS
    wrapper_limits = limits.get(wrapper, {})

    annual_used = compute_annual_used(entries, wrapper, year)
    combined_annual_used = compute_combined_annual_used(entries, year)
    lifetime_used = compute_lifetime_used(entries, as_of)

    growth_sub_limit_remaining: float | None = None
    if wrapper == "nisa_growth":
        growth_used = compute_growth_lifetime_used(entries, as_of)
        growth_sub_limit_remaining = (
            float(limits["nisa_growth"]["lifetime_sub_limit"]) - growth_used
        )

    return QuotaStatus(
        wrapper_annual_remaining=float(wrapper_limits.get("annual", 0)) - annual_used,
        combined_annual_remaining=float(limits["combined_annual"])
        - combined_annual_used,
        lifetime_remaining=float(limits["combined_lifetime"]) - lifetime_used,
        growth_sub_limit_remaining=growth_sub_limit_remaining,
    )


def compute_restoration_effective_date(
    sell_date: date,
    policy: str | None = None,
) -> date:
    """Determine when a NISA sell restores lifetime quota."""
    selected_policy = policy or NISA_RESTORATION_POLICY
    if selected_policy == "same_day":
        return sell_date
    return date(sell_date.year + 1, 1, 1)


def validate_nisa_purchase(
    entries: list[LedgerEntryLike],
    wrapper: str,
    amount: float,
    year: int,
    as_of: date,
) -> list[str]:
    """Return violated quota constraints; empty list means valid."""
    quota = get_available_quota(entries, wrapper, year, as_of)
    violations: list[str] = []
    if amount > quota.wrapper_annual_remaining:
        violations.append(f"wrapper_annual_exceeded:{wrapper}")
    if amount > quota.combined_annual_remaining:
        violations.append("combined_annual_exceeded")
    if amount > quota.lifetime_remaining:
        violations.append("lifetime_exceeded")
    if (
        quota.growth_sub_limit_remaining is not None
        and amount > quota.growth_sub_limit_remaining
    ):
        violations.append("growth_sub_limit_exceeded")
    return violations
