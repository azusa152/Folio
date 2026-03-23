"""Domain — Portfolio management constants (categories, accounts, analytics, notifications)."""

# ---------------------------------------------------------------------------
# Category Lists & Icons
# ---------------------------------------------------------------------------
CATEGORY_DISPLAY_ORDER = [
    "Trend_Setter",
    "Moat",
    "Growth",
    "Mutual_Fund",
    "Bond",
    "Crypto",
    "Cash",
    "ETF",
]

# All stock categories supported by API / forms (must be a literal list for check_constant_sync.py).
STOCK_CATEGORIES = [
    "Trend_Setter",
    "Moat",
    "Growth",
    "Mutual_Fund",
    "Bond",
    "Crypto",
    "Cash",
    "ETF",
]

# Categories shown on Radar tab filters.
RADAR_CATEGORIES = ["Trend_Setter", "Moat", "Growth", "Mutual_Fund", "Bond", "Crypto"]

CATEGORY_ICON: dict[str, str] = {
    "Trend_Setter": "🌊",
    "Moat": "🏰",
    "Growth": "🚀",
    "Mutual_Fund": "🧺",
    "Bond": "🛡️",
    "Crypto": "₿",
    "Cash": "💵",
    "ETF": "📈",
}

# ---------------------------------------------------------------------------
# Equity Categories (used by sector exposure, X-Ray, etc.)
# ---------------------------------------------------------------------------
EQUITY_CATEGORIES: frozenset[str] = frozenset(
    {"Trend_Setter", "Moat", "Growth", "Mutual_Fund", "ETF"}
)

# ---------------------------------------------------------------------------
# Account Types
# ---------------------------------------------------------------------------
DEFAULT_ACCOUNT_NAME = "Default"
ACCOUNT_TYPE_OPTIONS = [
    "brokerage",
    "retirement",
    "savings",
    "crypto",
    "bank",
    "wallet",
    "cash_wallet",
    "insurance",
    "loan",
    "other",
]

# ---------------------------------------------------------------------------
# User & Profile
# ---------------------------------------------------------------------------
DEFAULT_USER_ID = "default"
DRIFT_THRESHOLD_PCT = 5.0  # rebalancing drift threshold (percentage points)

# ---------------------------------------------------------------------------
# Benchmark Tickers
# ---------------------------------------------------------------------------
BENCHMARK_TICKERS = ("^GSPC", "VT", "^N225", "^TWII")
SP500_TICKER = "^GSPC"
DRIFT_ACK_EXPIRE_DAYS = 90  # acknowledged drift/xray suppression safety expiry
XRAY_ACK_STEP_PCT = 5.0  # re-alert when concentration worsens by another 5pp

# ---------------------------------------------------------------------------
# i18n Language Support
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = ["zh-TW", "en", "ja", "zh-CN"]
DEFAULT_LANGUAGE = "zh-TW"
LANGUAGE_LABELS = {
    "zh-TW": "繁體中文",
    "en": "English",
    "ja": "日本語",
    "zh-CN": "简体中文",
}

# ---------------------------------------------------------------------------
# Display Currency Defaults
# ---------------------------------------------------------------------------
DEFAULT_DISPLAY_CURRENCY = "USD"

# ---------------------------------------------------------------------------
# Smart Withdrawal (聰明提款機)
# ---------------------------------------------------------------------------
# 流動性優先順序：最容易變現的排最前面，複利核心資產排最後
CATEGORY_LIQUIDITY_ORDER = [
    "Cash",
    "Crypto",
    "Mutual_Fund",
    "Bond",
    "ETF",
    "Growth",
    "Moat",
    "Trend_Setter",
]
WITHDRAWAL_MIN_SELL_VALUE = 10.0  # 最小賣出金額（避免灰塵交易）

# ---------------------------------------------------------------------------
# Analytics — Drawdown & Risk Metrics
# ---------------------------------------------------------------------------
ANALYTICS_DEFAULT_LOOKBACK_DAYS = 365 * 10  # ~10 years — effectively "all data"

# ---------------------------------------------------------------------------
# Insight Thresholds
# ---------------------------------------------------------------------------
INSIGHT_CONCENTRATION_THRESHOLD = 0.40
INSIGHT_OUTPERFORMANCE_THRESHOLD = 0.01
INSIGHT_UNDERPERFORMANCE_THRESHOLD = -0.05
INSIGHT_SEVERE_DRAWDOWN_THRESHOLD = -0.20
INSIGHT_MODERATE_DRAWDOWN_THRESHOLD = -0.10
INSIGHT_EXCELLENT_HEALTH_SCORE = 80
INSIGHT_POOR_HEALTH_SCORE = 50
INSIGHT_STRONG_SHARPE = 1.0

# ---------------------------------------------------------------------------
# Analytics / Risk Metrics
# ---------------------------------------------------------------------------
ANALYTICS_TRADING_DAYS_PER_YEAR = 252
ANALYTICS_RISK_FREE_RATE = 0.04  # approximate US T-bill rate
ANALYTICS_MIN_DAYS_FOR_RATIOS = 30
ANALYTICS_MIN_DOWNSIDE_SAMPLES = 10
DRAWDOWN_PERIOD_THRESHOLD_DEFAULT = -0.05
DRAWDOWN_EPSILON = 1e-9
HOLDING_QUANTITY_EPSILON = 1e-8

# ---------------------------------------------------------------------------
# Notification Preferences — toggleable notification types
# ---------------------------------------------------------------------------
NOTIFICATION_TYPES = {
    "scan_alerts": "constants.notification_scan_alerts",
    "price_alerts": "constants.notification_price_alerts",
    "weekly_digest": "constants.notification_weekly_digest",
    "xray_alerts": "constants.notification_xray_alerts",
    "fx_alerts": "constants.notification_fx_alerts",
    "fx_watch_alerts": "constants.notification_fx_watch_alerts",
    "guru_alerts": "constants.notification_guru_alerts",
    "stock_split_alerts": "constants.notification_stock_split_alerts",
    "dividend_alerts": "constants.notification_dividend_alerts",
    "drift_alerts": "constants.notification_drift_alerts",
}
DEFAULT_NOTIFICATION_PREFERENCES: dict[str, bool] = dict.fromkeys(
    NOTIFICATION_TYPES, True
)

# Empty dict means no rate limit is applied by default for any notification type.
# When a user configures a limit, an entry like {"fx_alerts": {"max_count": 2, "window_hours": 24}}
# is added. Only notification types present in this dict are throttled.
DEFAULT_NOTIFICATION_RATE_LIMITS: dict[str, dict[str, int]] = {}

# ---------------------------------------------------------------------------
# Error Codes — machine-readable slugs for AI agent error handling
# ---------------------------------------------------------------------------
ERROR_STOCK_NOT_FOUND = "STOCK_NOT_FOUND"
ERROR_STOCK_ALREADY_EXISTS = "STOCK_ALREADY_EXISTS"
ERROR_STOCK_ALREADY_INACTIVE = "STOCK_ALREADY_INACTIVE"
ERROR_STOCK_ALREADY_ACTIVE = "STOCK_ALREADY_ACTIVE"
ERROR_CATEGORY_UNCHANGED = "CATEGORY_UNCHANGED"
ERROR_HOLDING_NOT_FOUND = "HOLDING_NOT_FOUND"
ERROR_TRANSACTION_NOT_FOUND = "TRANSACTION_NOT_FOUND"
ERROR_PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
ERROR_GURU_NOT_FOUND = "GURU_NOT_FOUND"
ERROR_BACKTEST_SIGNAL_UNKNOWN = "BACKTEST_SIGNAL_UNKNOWN"
ERROR_BACKTEST_DATA_NOT_FOUND = "BACKTEST_DATA_NOT_FOUND"
ERROR_INVALID_SCENARIO_DROP = "INVALID_SCENARIO_DROP"
ERROR_SYNC_IN_PROGRESS = "SYNC_IN_PROGRESS"
ERROR_GURU_FILING_NOT_FOUND = "GURU_FILING_NOT_FOUND"
ERROR_ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"
ERROR_INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
ERROR_FX_WATCH_NOT_FOUND = "FX_WATCH_NOT_FOUND"
ERROR_SCAN_IN_PROGRESS = "SCAN_IN_PROGRESS"
ERROR_DIGEST_IN_PROGRESS = "DIGEST_IN_PROGRESS"
ERROR_TELEGRAM_NOT_CONFIGURED = "TELEGRAM_NOT_CONFIGURED"
ERROR_TELEGRAM_SEND_FAILED = "TELEGRAM_SEND_FAILED"
ERROR_PREFERENCES_UPDATE_FAILED = "PREFERENCES_UPDATE_FAILED"
ERROR_INVALID_INPUT = "INVALID_INPUT"
ERROR_INTERNAL_ERROR = "INTERNAL_ERROR"

# ---------------------------------------------------------------------------
# Generic Error Messages — i18n keys, resolve with t() at call sites
# ---------------------------------------------------------------------------
GENERIC_ERROR_MESSAGE = "constants.generic_error"
GENERIC_VALIDATION_ERROR = "constants.generic_validation_error"
GENERIC_TELEGRAM_ERROR = "constants.generic_telegram_error"
GENERIC_PREFERENCES_ERROR = "constants.generic_preferences_error"
GENERIC_WEBHOOK_ERROR = "constants.generic_webhook_error"

# ---------------------------------------------------------------------------
# Import / upload limits
# ---------------------------------------------------------------------------
MAX_IMPORT_ROWS = 1000  # max rows per bulk import (stocks, transactions)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB max for eligible-asset CSV uploads

# ---------------------------------------------------------------------------
# Float comparison tolerances for quantity / balance checks
# ---------------------------------------------------------------------------
HOLDING_QUANTITY_EPSILON: float = 1e-9  # below this a quantity is effectively zero
POSITION_VERIFY_EPSILON: float = 1e-6  # tolerance for settlement position verification
