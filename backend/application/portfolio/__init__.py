"""application.portfolio sub-package — re-exports public API for backward compatibility."""

from application.portfolio.account_service import (  # noqa: F401
    create_account,
    ensure_default_account,
    get_account_summary,
    list_accounts,
    remove_account,
    update_account,
)
from application.portfolio.analytics_service import (  # noqa: F401
    get_contribution_vs_growth,
    get_drawdown_series,
    get_risk_metrics,
)
from application.portfolio.crypto_service import (  # noqa: F401
    get_crypto_details,
    get_crypto_holding_prices,
    get_crypto_price_for_ticker,
    search_crypto_coins,
)
from application.portfolio.dividend_service import (  # noqa: F401
    apply_all_pending_dividends,
    apply_dividend,
    build_dividend_preview,
    check_dividends,
    dismiss_dividend,
    list_dividend_events,
    send_dividend_alerts,
)
from application.portfolio.drift_alert_service import (  # noqa: F401
    acknowledge_drift_alert,
    send_drift_alerts,
)
from application.portfolio.eligibility_service import (  # noqa: F401
    check_asset_eligibility,
    get_eligible_assets,
    refresh_eligible_assets,
)
from application.portfolio.fx_watch_service import (  # noqa: F401
    check_fx_watches,
    create_watch,
    get_all_watches,
    get_forex_history,
    remove_watch,
    send_fx_watch_alerts,
    update_watch,
)
from application.portfolio.holding_service import (  # noqa: F401
    get_holdings_by_account,
    list_holdings,
)
from application.portfolio.insight_service import (  # noqa: F401
    get_portfolio_insights,
    invalidate_insight_cache,
)
from application.portfolio.rebalance_service import (  # noqa: F401
    _compute_holding_market_values,
    acknowledge_xray_alert,
    calculate_currency_exposure,
    calculate_rebalance,
    calculate_withdrawal,
    check_fx_alerts,
    send_fx_alerts,
    send_xray_warnings,
)
from application.portfolio.routing_service import (  # noqa: F401
    get_detax_suggestions,
    suggest_transaction_routing,
)
from application.portfolio.snapshot_service import (  # noqa: F401
    get_snapshot_range,
    get_snapshots,
    take_daily_snapshot,
)
from application.portfolio.stock_split_service import (  # noqa: F401
    apply_all_pending_splits,
    apply_split,
    build_split_preview,
    check_splits,
    dismiss_split,
    list_split_events,
    send_split_alerts,
)
from application.portfolio.stress_test_service import (  # noqa: F401
    calculate_stress_test,
)
from application.portfolio.transaction_service import (  # noqa: F401
    create_transaction,
    get_transaction,
    list_transactions,
    list_transactions_by_account,
    remove_transaction,
)
from application.portfolio.wrapper_service import (  # noqa: F401
    get_all_wrapper_quotas,
    get_contribution_entries,
    get_restoration_forecast,
    record_contribution,
    record_restoration,
)
