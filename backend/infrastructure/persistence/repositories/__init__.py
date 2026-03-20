# pyright: reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
# pyright: reportCallIssue=false
"""Infrastructure — Repository Pattern.

Re-exports all repository functions from the sub-modules below.
Each sub-module owns one aggregate group:

  account_repo   — Account
  eligible_repo  — EligibleAsset, EligibleAssetSyncState, ISIN lookups
  guru_repo      — Guru, GuruFiling, GuruHolding
  holding_repo   — Holding
  nav_repo       — MutualFundNav
  scan_repo      — ScanLog, PriceAlert, FXWatchConfig, NotificationLog,
                   StockSplitEvent, DividendEvent, DriftAcknowledgment
  settings_repo  — UserPreferences, UserTelegramSettings, UserInvestmentProfile
  stock_repo     — Stock, ThesisLog, RemovalLog
  transaction_repo — Transaction, ContributionLedgerEntry
"""

from .account_repo import (  # noqa: F401
    deactivate_account,
    find_account_by_id,
    find_all_accounts,
    save_account,
)
from .eligible_repo import (  # noqa: F401
    _build_eligible_assets_stmt,
    backfill_isin_for_ticker,
    count_eligible_assets,
    find_eligible_asset_by_ticker,
    find_eligible_assets,
    find_eligible_tickers,
    find_fund_code_by_isin,
    find_fund_names_by_tickers,
    find_isin_for_ticker,
    get_eligible_assets_metadata,
    is_active_eligible_mutual_fund,
    upsert_eligible_assets,
)
from .guru_repo import (  # noqa: F401
    _compute_trend,
    _latest_filing_ids_subquery,
    deactivate_guru,
    find_activity_feed,
    find_all_active_gurus,
    find_all_guru_summaries,
    find_consensus_stocks,
    find_filing_by_accession,
    find_filings_by_guru,
    find_grand_portfolio,
    find_guru_by_cik,
    find_guru_by_id,
    find_holding_history_by_guru,
    find_holdings_by_filing,
    find_holdings_by_guru_latest,
    find_holdings_by_ticker_across_gurus,
    find_latest_filing_by_guru,
    find_notable_changes_all_gurus,
    find_sector_breakdown,
    save_filing,
    save_guru,
    save_holdings_batch,
    update_guru,
)
from .holding_repo import (  # noqa: F401
    delete_all_holdings,
    delete_holding,
    delete_holdings_by_account,
    find_all_holdings,
    find_cash_holding_by_account_and_currency,
    find_holding_by_id,
    find_holding_by_ticker,
    find_holdings_by_account,
    find_holdings_for_active_accounts,
    find_stock_holding_by_account_and_ticker,
    save_holding,
)
from .nav_repo import (  # noqa: F401
    bulk_upsert_nav,
    get_latest_nav,
    get_nav_history,
    upsert_nav,
)
from .scan_repo import (  # noqa: F401
    count_recent_notifications,
    create_dividend_event,
    create_fx_watch,
    create_price_alert,
    create_scan_log,
    create_stock_split_event,
    delete_drift_acknowledgment,
    delete_fx_watch,
    delete_price_alert,
    find_active_alerts_for_stock,
    find_active_fx_watches,
    find_all_active_alerts,
    find_all_alerts_for_stock,
    find_all_drift_acknowledgments,
    find_all_fx_watches,
    find_dividend_event_by_id,
    find_dividend_event_by_unique_key,
    find_dividend_events,
    find_drift_acknowledgment,
    find_fx_watch_by_id,
    find_latest_scan_logs,
    find_price_alert_by_id,
    find_scan_history,
    find_scan_logs_for_backtest,
    find_scan_logs_since,
    find_stock_split_event_by_id,
    find_stock_split_event_by_unique_key,
    find_stock_split_events,
    log_notification_sent,
    save_dividend_event,
    save_stock_split_event,
    try_claim_dividend_event,
    try_claim_stock_split_event,
    update_fx_watch,
    update_fx_watch_last_alerted,
    upsert_drift_acknowledgment,
)
from .settings_repo import (  # noqa: F401
    find_active_profile,
    find_profile_by_id,
    find_system_templates,
    find_telegram_settings,
    find_user_preferences,
    save_profile,
    save_telegram_settings,
    save_user_preferences,
)
from .stock_repo import (  # noqa: F401
    bulk_update_display_order,
    bulk_update_scan_signals,
    count_consecutive_scans,
    create_removal_log,
    create_thesis_log,
    find_active_stocks,
    find_active_stocks_by_category,
    find_inactive_stocks,
    find_latest_removal,
    find_latest_removals_batch,
    find_previous_distinct_signal,
    find_recent_scan_logs_for_tickers,
    find_removal_history,
    find_stock_by_ticker,
    find_thesis_history,
    get_max_thesis_version,
    save_stock,
    update_stock,
)
from .transaction_repo import (  # noqa: F401
    create_ledger_entry,
    delete_ledger_entries_by_transaction,
    delete_transaction,
    delete_transactions_by_account,
    find_all_transactions,
    find_ledger_entries,
    find_ledger_entries_by_wrapper,
    find_ledger_entry_by_transaction_and_type,
    find_transaction_by_id,
    find_transactions_by_account,
    save_transaction,
)
