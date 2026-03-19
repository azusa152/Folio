"""Domain logic for tax-aware asset location across account wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import TYPE_CHECKING

from domain.core.constants import TOKUTEI_TAX_RATE
from domain.core.enums import StockCategory

if TYPE_CHECKING:
    from domain.portfolio.tax_wrapper import QuotaStatus


NISA_PRIORITY_RANK: dict[str, int] = {
    StockCategory.GROWTH: 1,
    StockCategory.MOAT: 2,
    StockCategory.TREND_SETTER: 3,
    StockCategory.CRYPTO: 4,
    StockCategory.BOND: 5,
    StockCategory.CASH: 6,
}

EXPECTED_ANNUAL_RETURN: dict[str, float] = {
    StockCategory.GROWTH: 0.10,
    StockCategory.MOAT: 0.08,
    StockCategory.TREND_SETTER: 0.07,
    StockCategory.CRYPTO: 0.12,
    StockCategory.BOND: 0.03,
    StockCategory.CASH: 0.01,
}


@dataclass(frozen=True)
class WrapperAllocation:
    wrapper: str
    categories: dict[str, float]
    total: float


@dataclass(frozen=True)
class PlacementSuggestion:
    ticker: str
    category: str
    from_wrapper: str
    to_wrapper: str
    amount: float
    reason: str  # i18n key


@dataclass(frozen=True)
class TsumitateMigrationPlan:
    monthly_amount: float
    source_wrapper: str
    eligible_tickers: list[str]
    reason: str  # i18n key


@dataclass(frozen=True)
class TaxSavingsEstimate:
    annual_nisa_benefit: float
    annual_detax_benefit: float
    annual_ideco_deduction: float
    total_annual: float
    projected_10yr: float
    projected_20yr: float


@dataclass
class AssetLocationPlan:
    aggregate_allocation: dict[str, float]
    wrapper_allocations: list[WrapperAllocation]
    suggestions: list[PlacementSuggestion]
    tsumitate_migration: TsumitateMigrationPlan | None
    tax_savings_estimate: TaxSavingsEstimate
    tax_efficiency_score: float


def _available_wrapper_capacity(wrapper: str, quota: QuotaStatus | None) -> float:
    if wrapper == "tokutei":
        return inf
    if quota is None:
        return 0.0
    available = min(
        float(quota.wrapper_annual_remaining),
        float(quota.combined_annual_remaining),
        float(quota.lifetime_remaining),
    )
    if wrapper == "nisa_growth" and quota.growth_sub_limit_remaining is not None:
        available = min(available, float(quota.growth_sub_limit_remaining))
    return max(0.0, available)


def estimate_tax_savings(
    wrapper_allocations: list[WrapperAllocation],
    detax_benefit: float = 0.0,
    ideco_deduction: float = 0.0,
) -> TaxSavingsEstimate:
    """Estimate annual and long-term tax value from wrapper placement."""
    annual_nisa_benefit = 0.0
    for allocation in wrapper_allocations:
        if allocation.wrapper not in {"nisa_growth", "nisa_tsumitate"}:
            continue
        for category, amount in allocation.categories.items():
            expected_return = EXPECTED_ANNUAL_RETURN.get(category, 0.0)
            annual_nisa_benefit += float(amount) * expected_return * TOKUTEI_TAX_RATE

    total_annual = annual_nisa_benefit + float(detax_benefit) + float(ideco_deduction)
    projected_10yr = total_annual * (((1 + 0.05) ** 10) - 1) / 0.05
    projected_20yr = total_annual * (((1 + 0.05) ** 20) - 1) / 0.05

    return TaxSavingsEstimate(
        annual_nisa_benefit=round(annual_nisa_benefit, 2),
        annual_detax_benefit=round(float(detax_benefit), 2),
        annual_ideco_deduction=round(float(ideco_deduction), 2),
        total_annual=round(total_annual, 2),
        projected_10yr=round(projected_10yr, 2),
        projected_20yr=round(projected_20yr, 2),
    )


def compute_tax_efficiency_score(
    wrapper_allocations: list[WrapperAllocation],
    category_targets: dict[str, float],
) -> float:
    """Return 0-100 score based on category placement quality by wrapper."""
    wrapper_category_values: dict[str, dict[str, float]] = {
        item.wrapper: item.categories for item in wrapper_allocations
    }
    high = [StockCategory.GROWTH, StockCategory.MOAT, StockCategory.TREND_SETTER]
    defensive = [StockCategory.BOND, StockCategory.CASH]

    total_weight = 0.0
    score_points = 0.0

    for category in high:
        target = float(category_targets.get(category, 0.0))
        if target <= 0:
            continue
        in_nisa = float(
            wrapper_category_values.get("nisa_growth", {}).get(category, 0.0)
        ) + float(wrapper_category_values.get("nisa_tsumitate", {}).get(category, 0.0))
        ratio = min(1.0, in_nisa / target) if target > 0 else 0.0
        total_weight += target
        score_points += target * ratio

    for category in defensive:
        target = float(category_targets.get(category, 0.0))
        if target <= 0:
            continue
        in_tokutei = float(
            wrapper_category_values.get("tokutei", {}).get(category, 0.0)
        )
        ratio = min(1.0, in_tokutei / target) if target > 0 else 0.0
        total_weight += target
        score_points += target * ratio

    if total_weight <= 0:
        return 100.0
    return round(max(0.0, min(100.0, (score_points / total_weight) * 100)), 2)


def suggest_tsumitate_migration(
    growth_holdings: list[dict[str, float | str]],
    tokutei_holdings: list[dict[str, float | str]],
    tsumitate_eligible: set[str],
    tsumitate_quota: QuotaStatus,
    monthly_max: float = 100_000,
) -> TsumitateMigrationPlan | None:
    """Suggest monthly DCA migration into tsumitate for eligible tickers."""
    if monthly_max <= 0:
        return None
    quota_cap = max(
        0.0,
        min(
            float(tsumitate_quota.wrapper_annual_remaining),
            float(tsumitate_quota.combined_annual_remaining),
            float(tsumitate_quota.lifetime_remaining),
        ),
    )
    if quota_cap <= 0:
        return None

    candidates: list[str] = []
    source_totals: dict[str, float] = {"nisa_growth": 0.0, "tokutei": 0.0}
    for item in growth_holdings:
        ticker = str(item.get("ticker", "")).upper()
        if ticker and ticker in tsumitate_eligible and ticker not in candidates:
            candidates.append(ticker)
        amount = float(item.get("amount", 0.0))
        if ticker and ticker in tsumitate_eligible and amount > 0:
            source_totals["nisa_growth"] = (
                source_totals.get("nisa_growth", 0.0) + amount
            )
    for item in tokutei_holdings:
        ticker = str(item.get("ticker", "")).upper()
        if ticker and ticker in tsumitate_eligible and ticker not in candidates:
            candidates.append(ticker)
        amount = float(item.get("amount", 0.0))
        if ticker and ticker in tsumitate_eligible and amount > 0:
            source_totals["tokutei"] = source_totals.get("tokutei", 0.0) + amount

    if not candidates:
        return None

    monthly_amount = min(float(monthly_max), quota_cap)
    source = (
        "nisa_growth"
        if source_totals.get("nisa_growth", 0.0) >= source_totals.get("tokutei", 0.0)
        else "tokutei"
    )
    return TsumitateMigrationPlan(
        monthly_amount=round(monthly_amount, 2),
        source_wrapper=source,
        eligible_tickers=sorted(candidates),
        reason="location.tsumitate_reason",
    )


def compute_optimal_location(
    category_targets: dict[str, float],
    quotas: dict[str, QuotaStatus],
    eligibility: dict[str, dict[str, bool]],
    current_placements: dict[str, dict[str, float]] | None = None,
    ticker_categories: dict[str, str] | None = None,
) -> AssetLocationPlan:
    """
    Greedy placement algorithm:

    1. Sort categories by NISA priority (higher expected return first)
    2. Fill tax-advantaged wrappers where eligible and quota is available
    3. Put remaining target amount into Tokutei
    """
    wrappers = ["nisa_growth", "nisa_tsumitate", "ideco", "tokutei"]
    wrapper_category_alloc: dict[str, dict[str, float]] = {w: {} for w in wrappers}
    capacities = {w: _available_wrapper_capacity(w, quotas.get(w)) for w in wrappers}

    sorted_categories = sorted(
        category_targets.items(),
        key=lambda kv: (NISA_PRIORITY_RANK.get(kv[0], 99), kv[0]),
    )
    for category, target_amount in sorted_categories:
        remaining = max(0.0, float(target_amount))
        if remaining <= 0:
            continue
        for wrapper in wrappers:
            if remaining <= 0:
                break
            if wrapper != "tokutei" and not eligibility.get(wrapper, {}).get(
                category, False
            ):
                continue
            cap = capacities.get(wrapper, 0.0)
            if cap <= 0:
                continue
            allocation = min(remaining, cap)
            wrapper_category_alloc[wrapper][category] = round(
                wrapper_category_alloc[wrapper].get(category, 0.0) + allocation, 2
            )
            if wrapper != "tokutei":
                capacities[wrapper] = max(0.0, cap - allocation)
            remaining -= allocation

    wrapper_allocations = [
        WrapperAllocation(
            wrapper=wrapper,
            categories=categories,
            total=round(sum(categories.values()), 2),
        )
        for wrapper, categories in wrapper_category_alloc.items()
        if categories
    ]

    suggestions: list[PlacementSuggestion] = []
    if current_placements and ticker_categories:
        preferred_wrapper_by_category: dict[str, str] = {}
        for category in category_targets:
            ranked = sorted(
                (
                    (
                        wrapper,
                        wrapper_category_alloc.get(wrapper, {}).get(category, 0.0),
                    )
                    for wrapper in wrappers
                ),
                key=lambda item: item[1],
                reverse=True,
            )
            if ranked and ranked[0][1] > 0:
                preferred_wrapper_by_category[category] = ranked[0][0]

        current_by_category_wrapper: dict[str, dict[str, float]] = {}
        for ticker, by_wrapper in current_placements.items():
            category = ticker_categories.get(ticker)
            if not category:
                continue
            current_by_category_wrapper.setdefault(category, {})
            for wrapper, amount in by_wrapper.items():
                current_by_category_wrapper[category][wrapper] = float(
                    current_by_category_wrapper[category].get(wrapper, 0.0)
                ) + float(amount)

        for ticker, by_wrapper in current_placements.items():
            category = ticker_categories.get(ticker)
            if not category:
                continue
            target_wrapper = preferred_wrapper_by_category.get(category)
            if not target_wrapper:
                continue
            if target_wrapper == "tokutei":
                continue
            for current_wrapper, current_amount in by_wrapper.items():
                if current_wrapper == target_wrapper or float(current_amount) <= 0:
                    continue
                category_totals = current_by_category_wrapper.get(category, {})
                target_current = float(category_totals.get(target_wrapper, 0.0))
                target_goal = float(
                    wrapper_category_alloc.get(target_wrapper, {}).get(category, 0.0)
                )
                surplus_in_source = max(
                    0.0,
                    float(category_totals.get(current_wrapper, 0.0))
                    - float(
                        wrapper_category_alloc.get(current_wrapper, {}).get(
                            category, 0.0
                        )
                    ),
                )
                deficit = max(0.0, target_goal - target_current)
                suggested = min(float(current_amount), surplus_in_source, deficit)
                if suggested <= 0:
                    continue
                suggestions.append(
                    PlacementSuggestion(
                        ticker=ticker,
                        category=category,
                        from_wrapper=current_wrapper,
                        to_wrapper=target_wrapper,
                        amount=round(suggested, 2),
                        reason="location.move_suggestion",
                    )
                )
                category_totals[current_wrapper] = max(
                    0.0, float(category_totals.get(current_wrapper, 0.0)) - suggested
                )
                category_totals[target_wrapper] = (
                    float(category_totals.get(target_wrapper, 0.0)) + suggested
                )

    tax_savings = estimate_tax_savings(wrapper_allocations)
    tax_efficiency = compute_tax_efficiency_score(wrapper_allocations, category_targets)

    return AssetLocationPlan(
        aggregate_allocation={
            k: round(float(v), 2) for k, v in category_targets.items()
        },
        wrapper_allocations=wrapper_allocations,
        suggestions=suggestions,
        tsumitate_migration=None,
        tax_savings_estimate=tax_savings,
        tax_efficiency_score=tax_efficiency,
    )
