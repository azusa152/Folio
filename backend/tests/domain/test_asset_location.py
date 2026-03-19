from domain.enums import StockCategory
from domain.portfolio.asset_location import (
    WrapperAllocation,
    compute_optimal_location,
    compute_tax_efficiency_score,
    estimate_tax_savings,
    suggest_tsumitate_migration,
)
from domain.portfolio.tax_wrapper import QuotaStatus


def _quota(
    wrapper_remaining: float,
    combined_remaining: float,
    lifetime_remaining: float,
    growth_sub_limit_remaining: float | None = None,
) -> QuotaStatus:
    return QuotaStatus(
        wrapper_annual_remaining=wrapper_remaining,
        combined_annual_remaining=combined_remaining,
        lifetime_remaining=lifetime_remaining,
        growth_sub_limit_remaining=growth_sub_limit_remaining,
    )


def _eligibility_all_true() -> dict[str, dict[str, bool]]:
    categories = [
        StockCategory.GROWTH,
        StockCategory.MOAT,
        StockCategory.TREND_SETTER,
        StockCategory.BOND,
        StockCategory.CASH,
    ]
    return {
        "nisa_growth": dict.fromkeys(categories, True),
        "nisa_tsumitate": dict.fromkeys(categories, True),
        "ideco": dict.fromkeys(categories, True),
    }


def test_growth_placed_in_nisa_first():
    plan = compute_optimal_location(
        category_targets={StockCategory.GROWTH: 100_000},
        quotas={"nisa_growth": _quota(200_000, 300_000, 3_000_000, 2_000_000)},
        eligibility=_eligibility_all_true(),
    )
    growth_allocation = next(
        item for item in plan.wrapper_allocations if item.wrapper == "nisa_growth"
    )
    assert growth_allocation.categories[StockCategory.GROWTH] == 100_000


def test_bond_placed_in_tokutei():
    plan = compute_optimal_location(
        category_targets={StockCategory.BOND: 80_000},
        quotas={},
        eligibility={
            "nisa_growth": {StockCategory.BOND: False},
            "nisa_tsumitate": {StockCategory.BOND: False},
            "ideco": {StockCategory.BOND: False},
        },
    )
    tokutei = next(
        item for item in plan.wrapper_allocations if item.wrapper == "tokutei"
    )
    assert tokutei.categories[StockCategory.BOND] == 80_000


def test_quota_exhaustion_overflows_to_tokutei():
    plan = compute_optimal_location(
        category_targets={StockCategory.GROWTH: 150_000},
        quotas={"nisa_growth": _quota(50_000, 50_000, 50_000, 50_000)},
        eligibility=_eligibility_all_true(),
    )
    growth = next(
        item for item in plan.wrapper_allocations if item.wrapper == "nisa_growth"
    )
    tokutei = next(
        item for item in plan.wrapper_allocations if item.wrapper == "tokutei"
    )
    assert growth.categories[StockCategory.GROWTH] == 50_000
    assert tokutei.categories[StockCategory.GROWTH] == 100_000


def test_ineligible_asset_skips_nisa():
    plan = compute_optimal_location(
        category_targets={StockCategory.CRYPTO: 90_000},
        quotas={"nisa_growth": _quota(200_000, 200_000, 200_000, 200_000)},
        eligibility={
            "nisa_growth": {StockCategory.CRYPTO: False},
            "nisa_tsumitate": {StockCategory.CRYPTO: False},
            "ideco": {StockCategory.CRYPTO: False},
        },
    )
    assert all(
        StockCategory.CRYPTO not in item.categories
        for item in plan.wrapper_allocations
        if item.wrapper != "tokutei"
    )
    tokutei = next(
        item for item in plan.wrapper_allocations if item.wrapper == "tokutei"
    )
    assert tokutei.categories[StockCategory.CRYPTO] == 90_000


def test_tax_savings_estimate_calculation():
    plan = compute_optimal_location(
        category_targets={StockCategory.GROWTH: 100_000},
        quotas={"nisa_growth": _quota(100_000, 100_000, 100_000, 100_000)},
        eligibility=_eligibility_all_true(),
    )
    estimate = estimate_tax_savings(plan.wrapper_allocations)
    assert estimate.annual_nisa_benefit > 0
    assert estimate.total_annual == estimate.annual_nisa_benefit
    assert estimate.projected_20yr > estimate.projected_10yr


def test_tax_efficiency_score_optimal():
    plan = compute_optimal_location(
        category_targets={
            StockCategory.GROWTH: 120_000,
            StockCategory.MOAT: 80_000,
            StockCategory.BOND: 60_000,
        },
        quotas={"nisa_growth": _quota(200_000, 200_000, 3_000_000, 2_000_000)},
        eligibility=_eligibility_all_true(),
    )
    score = compute_tax_efficiency_score(
        plan.wrapper_allocations, plan.aggregate_allocation
    )
    assert score == 100.0


def test_tax_efficiency_score_suboptimal():
    score = compute_tax_efficiency_score(
        wrapper_allocations=[
            WrapperAllocation(
                wrapper="tokutei",
                categories={StockCategory.GROWTH: 100_000},
                total=100_000,
            )
        ],
        category_targets={StockCategory.GROWTH: 100_000},
    )
    assert score == 0.0


def test_tsumitate_migration_suggested():
    migration = suggest_tsumitate_migration(
        growth_holdings=[{"ticker": "03311187", "amount": 300_000}],
        tokutei_holdings=[],
        tsumitate_eligible={"03311187"},
        tsumitate_quota=_quota(400_000, 400_000, 2_000_000, None),
    )
    assert migration is not None
    assert migration.monthly_amount == 100_000
    assert "03311187" in migration.eligible_tickers


def test_tsumitate_migration_none_when_no_eligible():
    migration = suggest_tsumitate_migration(
        growth_holdings=[{"ticker": "AAPL", "amount": 300_000}],
        tokutei_holdings=[],
        tsumitate_eligible=set(),
        tsumitate_quota=_quota(400_000, 400_000, 2_000_000, None),
    )
    assert migration is None


def test_tsumitate_migration_prefers_source_with_larger_eligible_amount():
    migration = suggest_tsumitate_migration(
        growth_holdings=[{"ticker": "03311187", "amount": 20_000}],
        tokutei_holdings=[{"ticker": "eMAXIS", "amount": 80_000}],
        tsumitate_eligible={"03311187", "EMAXIS"},
        tsumitate_quota=_quota(400_000, 400_000, 2_000_000, None),
    )
    assert migration is not None
    assert migration.source_wrapper == "tokutei"


def test_placement_suggestion_should_be_limited_to_target_deficit():
    plan = compute_optimal_location(
        category_targets={StockCategory.GROWTH: 100_000},
        quotas={"nisa_growth": _quota(100_000, 100_000, 100_000, 100_000)},
        eligibility=_eligibility_all_true(),
        current_placements={
            "AAA": {"tokutei": 100_000},
            "BBB": {"nisa_growth": 60_000},
        },
        ticker_categories={
            "AAA": StockCategory.GROWTH,
            "BBB": StockCategory.GROWTH,
        },
    )
    assert len(plan.suggestions) == 1
    assert plan.suggestions[0].ticker == "AAA"
    assert plan.suggestions[0].amount == 40_000
