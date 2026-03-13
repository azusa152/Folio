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
from application.portfolio.net_worth_service import (  # noqa: F401
    calculate_net_worth,
    create_item,
    delete_item,
    get_net_worth_history,
    list_items,
    take_net_worth_snapshot,
    update_item,
)
from application.portfolio.rebalance_service import (  # noqa: F401
    _compute_holding_market_values,
    calculate_currency_exposure,
    calculate_rebalance,
    calculate_withdrawal,
    check_fx_alerts,
    send_fx_alerts,
    send_xray_warnings,
)
from application.portfolio.snapshot_service import (  # noqa: F401
    get_snapshot_range,
    get_snapshots,
    take_daily_snapshot,
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

# Backward-compatible aliases for external imports.
create_net_worth_item = create_item
delete_net_worth_item = delete_item
list_net_worth_items = list_items
update_net_worth_item = update_item
