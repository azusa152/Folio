"""domain.portfolio sub-package — portfolio calculations: rebalancing, withdrawal, stress testing, allocation."""

from domain.portfolio.allocation import (  # noqa: F401
    classify_market,
    compute_asset_class_allocation,
    compute_geographic_allocation,
)
from domain.portfolio.insights import (  # noqa: F401
    Insight,
    InsightSeverity,
    generate_allocation_insights,
    generate_performance_insights,
)
from domain.portfolio.rebalance import (  # noqa: F401
    calculate_rebalance,
    compute_portfolio_health_score,
)
from domain.portfolio.stress_test import (  # noqa: F401
    calculate_portfolio_beta,
    calculate_stress_test,
    classify_pain_level,
    generate_advice,
)
from domain.portfolio.tax_wrapper import (  # noqa: F401
    QuotaStatus,
    compute_restoration_effective_date,
    get_available_quota,
    validate_nisa_purchase,
)
from domain.portfolio.withdrawal import (  # noqa: F401
    HoldingData,
    SellRecommendation,
    WithdrawalPlan,
    plan_withdrawal,
)
