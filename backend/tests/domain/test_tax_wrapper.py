"""Domain tests for tax wrapper quota computation."""

from dataclasses import dataclass
from datetime import date

from domain.portfolio.tax_wrapper import (
    compute_annual_used,
    compute_combined_annual_used,
    compute_growth_lifetime_used,
    compute_lifetime_used,
    compute_restoration_effective_date,
    validate_nisa_purchase,
)


@dataclass
class _Entry:
    tax_wrapper: str
    entry_type: str
    fiscal_year: int
    amount: float
    effective_date: date


def test_annual_used_single_wrapper() -> None:
    entries = [
        _Entry("nisa_tsumitate", "CONTRIBUTION", 2026, 500_000, date(2026, 1, 10)),
        _Entry("nisa_tsumitate", "CONTRIBUTION", 2026, 300_000, date(2026, 2, 10)),
        _Entry("nisa_growth", "CONTRIBUTION", 2026, 100_000, date(2026, 2, 10)),
    ]
    assert compute_annual_used(entries, "nisa_tsumitate", 2026) == 800_000


def test_combined_annual_across_wrappers() -> None:
    entries = [
        _Entry("nisa_tsumitate", "CONTRIBUTION", 2026, 1_000_000, date(2026, 1, 10)),
        _Entry("nisa_growth", "CONTRIBUTION", 2026, 2_000_000, date(2026, 2, 10)),
    ]
    assert compute_combined_annual_used(entries, 2026) == 3_000_000


def test_lifetime_with_restorations() -> None:
    entries = [
        _Entry("nisa_tsumitate", "CONTRIBUTION", 2025, 1_000_000, date(2025, 1, 10)),
        _Entry("nisa_growth", "CONTRIBUTION", 2025, 2_000_000, date(2025, 2, 10)),
        _Entry("nisa_growth", "RESTORATION", 2026, -500_000, date(2026, 1, 1)),
    ]
    assert compute_lifetime_used(entries, date(2026, 1, 1)) == 2_500_000


def test_growth_lifetime_used_only_counts_growth_wrapper() -> None:
    entries = [
        _Entry("nisa_tsumitate", "CONTRIBUTION", 2025, 1_000_000.0, date(2025, 1, 10)),
        _Entry("nisa_growth", "CONTRIBUTION", 2025, 3_000_000.0, date(2025, 2, 10)),
        _Entry("nisa_growth", "RESTORATION", 2026, -500_000.0, date(2026, 1, 1)),
        _Entry("nisa_tsumitate", "RESTORATION", 2026, -200_000.0, date(2026, 1, 1)),
    ]
    # Growth lifetime = 3_000_000 + (-500_000) = 2_500_000 (tsumitate excluded)
    assert compute_growth_lifetime_used(entries, date(2026, 1, 1)) == 2_500_000.0


def test_growth_lifetime_used_excludes_future_restorations() -> None:
    entries = [
        _Entry("nisa_growth", "CONTRIBUTION", 2025, 4_000_000.0, date(2025, 3, 1)),
        _Entry("nisa_growth", "RESTORATION", 2026, -1_000_000.0, date(2027, 1, 1)),
    ]
    # Restoration effective 2027-01-01 is not yet effective as of 2026-06-01
    assert compute_growth_lifetime_used(entries, date(2026, 6, 1)) == 4_000_000.0


def test_restoration_effective_date_next_year() -> None:
    assert compute_restoration_effective_date(date(2026, 3, 10), "next_year") == date(
        2027, 1, 1
    )


def test_restoration_effective_date_same_day() -> None:
    assert compute_restoration_effective_date(date(2026, 3, 10), "same_day") == date(
        2026, 3, 10
    )


def test_validate_nisa_purchase_all_pass() -> None:
    entries = [
        _Entry("nisa_tsumitate", "CONTRIBUTION", 2026, 100_000, date(2026, 1, 10)),
    ]
    violations = validate_nisa_purchase(
        entries,
        "nisa_tsumitate",
        amount=200_000,
        year=2026,
        as_of=date(2026, 3, 10),
    )
    assert violations == []


def test_validate_nisa_purchase_annual_exceeded() -> None:
    entries = [
        _Entry("nisa_tsumitate", "CONTRIBUTION", 2026, 1_150_000, date(2026, 1, 10)),
    ]
    violations = validate_nisa_purchase(
        entries,
        "nisa_tsumitate",
        amount=100_000,
        year=2026,
        as_of=date(2026, 3, 10),
    )
    assert "wrapper_annual_exceeded:nisa_tsumitate" in violations


def test_validate_nisa_purchase_combined_exceeded() -> None:
    entries = [
        _Entry("nisa_tsumitate", "CONTRIBUTION", 2026, 1_200_000, date(2026, 1, 10)),
        _Entry("nisa_growth", "CONTRIBUTION", 2026, 2_300_000, date(2026, 2, 10)),
    ]
    violations = validate_nisa_purchase(
        entries,
        "nisa_growth",
        amount=200_000,
        year=2026,
        as_of=date(2026, 3, 10),
    )
    assert "combined_annual_exceeded" in violations


def test_validate_nisa_purchase_lifetime_exceeded() -> None:
    entries = [
        _Entry("nisa_tsumitate", "CONTRIBUTION", 2025, 9_000_000, date(2025, 1, 10)),
        _Entry("nisa_growth", "CONTRIBUTION", 2025, 8_900_000, date(2025, 2, 10)),
    ]
    violations = validate_nisa_purchase(
        entries,
        "nisa_tsumitate",
        amount=200_000,
        year=2026,
        as_of=date(2026, 3, 10),
    )
    assert "lifetime_exceeded" in violations


def test_validate_nisa_purchase_growth_sub_limit() -> None:
    entries = [
        _Entry("nisa_growth", "CONTRIBUTION", 2025, 11_950_000, date(2025, 1, 10)),
    ]
    violations = validate_nisa_purchase(
        entries,
        "nisa_growth",
        amount=100_000,
        year=2026,
        as_of=date(2026, 3, 10),
    )
    assert "growth_sub_limit_exceeded" in violations
