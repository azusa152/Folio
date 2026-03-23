from domain.portfolio.routing import suggest_purchase_routing
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


def test_all_to_nisa_growth_when_eligible_and_quota():
    suggestions = suggest_purchase_routing(
        total_amount=100_000,
        quotas={
            "nisa_growth": _quota(200_000, 300_000, 5_000_000, 2_000_000),
            "nisa_tsumitate": _quota(1_200_000, 3_600_000, 10_000_000, None),
        },
        eligibility={"nisa_growth": True, "nisa_tsumitate": False, "ideco": False},
    )
    assert len(suggestions) == 1
    assert suggestions[0].wrapper == "nisa_growth"
    assert suggestions[0].amount == 100_000


def test_split_nisa_and_tokutei_when_quota_partial():
    suggestions = suggest_purchase_routing(
        total_amount=150_000,
        quotas={
            "nisa_growth": _quota(50_000, 50_000, 50_000, 50_000),
            "nisa_tsumitate": _quota(0, 0, 0, None),
        },
        eligibility={"nisa_growth": True, "nisa_tsumitate": False, "ideco": False},
    )
    assert [item.wrapper for item in suggestions] == ["nisa_growth", "tokutei"]
    assert suggestions[0].amount == 50_000
    assert suggestions[1].amount == 100_000


def test_tokutei_only_when_not_eligible():
    suggestions = suggest_purchase_routing(
        total_amount=100_000,
        quotas={"nisa_growth": _quota(200_000, 200_000, 200_000, 200_000)},
        eligibility={"nisa_growth": False, "nisa_tsumitate": False, "ideco": False},
    )
    assert len(suggestions) == 1
    assert suggestions[0].wrapper == "tokutei"
    assert suggestions[0].reason == "routing.tokutei_overflow"


def test_tsumitate_preferred_when_growth_not_eligible():
    suggestions = suggest_purchase_routing(
        total_amount=80_000,
        quotas={
            "nisa_growth": _quota(100_000, 100_000, 100_000, 100_000),
            "nisa_tsumitate": _quota(100_000, 100_000, 100_000, None),
        },
        eligibility={"nisa_growth": False, "nisa_tsumitate": True, "ideco": False},
    )
    assert len(suggestions) == 1
    assert suggestions[0].wrapper == "nisa_tsumitate"


def test_ideco_routing():
    suggestions = suggest_purchase_routing(
        total_amount=90_000,
        quotas={"ideco": _quota(100_000, 100_000, 100_000, None)},
        eligibility={"nisa_growth": False, "nisa_tsumitate": False, "ideco": True},
    )
    assert len(suggestions) == 1
    assert suggestions[0].wrapper == "ideco"
