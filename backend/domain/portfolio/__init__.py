"""domain.portfolio sub-package — portfolio calculations: rebalancing, withdrawal, stress testing, allocation."""

from domain.portfolio.allocation import (  # noqa: F401
    classify_market,
    compute_asset_class_allocation,
    compute_geographic_allocation,
)
from domain.portfolio.detax import (  # noqa: F401
    DETAX_MIN_BENEFIT_JPY,
    DeTaxOpportunity,
    find_detax_opportunities,
)
from domain.portfolio.eligibility import (  # noqa: F401
    EligibilityResult,
    check_eligibility,
    check_growth_eligibility,
    check_ideco_eligibility,
    check_tsumitate_eligibility,
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
from domain.portfolio.routing import (  # noqa: F401
    RoutingSuggestion,
    suggest_purchase_routing,
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
    REBALANCE_EMERGENCY_THRESHOLD,
    WRAPPER_SELL_PRIORITY,
    HoldingData,
    SellRecommendation,
    WithdrawalPlan,
    plan_withdrawal,
)
