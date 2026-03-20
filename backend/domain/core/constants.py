"""
Domain — 集中管理所有常數與閾值。
避免散落在各模組中的 magic numbers / magic strings。
"""

__all__ = [
    "ACCOUNT_TYPE_OPTIONS",
    "ANALYTICS_DEFAULT_LOOKBACK_DAYS",
    "ANALYTICS_MIN_DAYS_FOR_RATIOS",
    "ANALYTICS_MIN_DOWNSIDE_SAMPLES",
    "ANALYTICS_RISK_FREE_RATE",
    "ANALYTICS_TRADING_DAYS_PER_YEAR",
    "BACKFILL_DEFAULT_MOAT",
    "BACKFILL_HISTORY_PERIOD",
    "BACKFILL_MARKET_STATUS",
    "BACKFILL_MIN_HISTORY_DAYS",
    "BACKFILL_SAMPLE_INTERVAL",
    "BACKTEST_CACHE_TTL",
    "BACKTEST_FP_WINDOW",
    "BACKTEST_MAX_LOOKBACK_DAYS",
    "BACKTEST_MIN_SAMPLES_HIGH",
    "BACKTEST_MIN_SAMPLES_MEDIUM",
    "BACKTEST_WINDOWS",
    "BENCHMARK_TICKERS",
    "BETA_CACHE_MAXSIZE",
    "BETA_CACHE_TTL",
    "BETA_MIN_HISTORY_PERIODS",
    "BIAS_OVERHEATED_THRESHOLD",
    "BIAS_OVERSOLD_THRESHOLD",
    "BIAS_WEAKENING_THRESHOLD",
    "CATEGORY_DISPLAY_ORDER",
    "CATEGORY_FALLBACK_BETA",
    "CATEGORY_ICON",
    "CATEGORY_LIQUIDITY_ORDER",
    "CATEGORY_RSI_OFFSET",
    "CNN_FG_API_URL",
    "CNN_FG_EXTREME_FEAR",
    "CNN_FG_FEAR",
    "CNN_FG_GREED",
    "CNN_FG_NEUTRAL_HIGH",
    "CNN_FG_REQUEST_TIMEOUT",
    "COINGECKO_API_URL",
    "COINGECKO_RATE_LIMIT_CPS",
    "CRYPTO_CACHE_MAXSIZE",
    "CRYPTO_CACHE_TTL",
    "CRYPTO_QUANTITY_MAX_DECIMALS",
    "CRYPTO_VOLATILITY_EXTREME_PCT",
    "CRYPTO_VOLATILITY_HIGH_PCT",
    "CURL_CFFI_IMPERSONATE",
    "CURRENCY_REGION_MAP",
    "DEFAULT_ACCOUNT_NAME",
    "DEFAULT_DISPLAY_CURRENCY",
    "DEFAULT_GURUS",
    "DEFAULT_IMPORT_CATEGORY",
    "DEFAULT_LANGUAGE",
    "DEFAULT_MARKET",
    "DEFAULT_NOTIFICATION_PREFERENCES",
    "DEFAULT_NOTIFICATION_RATE_LIMITS",
    "DEFAULT_USER_ID",
    "DEFAULT_WEBHOOK_THESIS",
    "DISK_BETA_TTL",
    "DISK_CRYPTO_TTL",
    "DISK_DIVIDEND_TTL",
    "DISK_EARNINGS_TTL",
    "DISK_ETF_HOLDINGS_TTL",
    "DISK_ETF_SECTOR_WEIGHTS_TTL",
    "DISK_EXCHANGE_TTL",
    "DISK_FEAR_GREED_TTL",
    "DISK_FOREX_HISTORY_LONG_TTL",
    "DISK_FOREX_HISTORY_TTL",
    "DISK_FOREX_TTL",
    "DISK_FUNDAMENTALS_TTL",
    "DISK_GURU_FILING_TTL",
    "DISK_KEY_BETA",
    "DISK_KEY_CRYPTO",
    "DISK_KEY_DIVIDEND",
    "DISK_KEY_DIVIDEND_EVENTS",
    "DISK_KEY_EARNINGS",
    "DISK_KEY_ETF_HOLDINGS",
    "DISK_KEY_ETF_SECTOR_WEIGHTS",
    "DISK_KEY_EXCHANGE",
    "DISK_KEY_FEAR_GREED",
    "DISK_KEY_FOREX",
    "DISK_KEY_FOREX_HISTORY",
    "DISK_KEY_FOREX_HISTORY_LONG",
    "DISK_KEY_FUNDAMENTALS",
    "DISK_KEY_GURU_FILING",
    "DISK_KEY_MOAT",
    "DISK_KEY_NAME",
    "DISK_KEY_PRICE_HISTORY",
    "DISK_KEY_PRICE_PAIR",
    "DISK_KEY_ROGUE_WAVE",
    "DISK_KEY_SECTOR",
    "DISK_KEY_SIGNALS",
    "DISK_KEY_STOCK_SPLIT",
    "DISK_KEY_YF_INFO",
    "DISK_MOAT_FAILURE_TTL",
    "DISK_MOAT_PERSISTENT_TTL",
    "DISK_MOAT_TTL",
    "DISK_NAME_TTL",
    "DISK_PRICE_HISTORY_TTL",
    "DISK_PRICE_PAIR_TTL",
    "DISK_ROGUE_WAVE_TTL",
    "DISK_SECTOR_TTL",
    "DISK_SIGNALS_TTL",
    "DISK_YF_INFO_TTL",
    "DIVIDEND_CACHE_MAXSIZE",
    "DIVIDEND_CACHE_TTL",
    "DIVIDEND_LOOKBACK_DAYS",
    "DRAWDOWN_EPSILON",
    "DRAWDOWN_PERIOD_THRESHOLD_DEFAULT",
    "DRIFT_ACK_EXPIRE_DAYS",
    "DRIFT_THRESHOLD_PCT",
    "EARNINGS_CACHE_MAXSIZE",
    "EARNINGS_CACHE_TTL",
    "ENRICHED_CACHE_MAXSIZE",
    "ENRICHED_CACHE_TTL",
    "ENRICHED_PER_TICKER_TIMEOUT",
    "ENRICHED_THREAD_POOL_SIZE",
    "EQUITY_CATEGORIES",
    "ERROR_ACCOUNT_NOT_FOUND",
    "ERROR_BACKTEST_DATA_NOT_FOUND",
    "ERROR_BACKTEST_SIGNAL_UNKNOWN",
    "ERROR_CATEGORY_UNCHANGED",
    "ERROR_DIGEST_IN_PROGRESS",
    "ERROR_FX_WATCH_NOT_FOUND",
    "ERROR_GURU_FILING_NOT_FOUND",
    "ERROR_GURU_NOT_FOUND",
    "ERROR_HOLDING_NOT_FOUND",
    "ERROR_INSUFFICIENT_BALANCE",
    "ERROR_INTERNAL_ERROR",
    "ERROR_INVALID_INPUT",
    "ERROR_INVALID_SCENARIO_DROP",
    "ERROR_PREFERENCES_UPDATE_FAILED",
    "ERROR_PROFILE_NOT_FOUND",
    "ERROR_SCAN_IN_PROGRESS",
    "ERROR_STOCK_ALREADY_ACTIVE",
    "ERROR_STOCK_ALREADY_EXISTS",
    "ERROR_STOCK_ALREADY_INACTIVE",
    "ERROR_STOCK_NOT_FOUND",
    "ERROR_SYNC_IN_PROGRESS",
    "ERROR_TELEGRAM_NOT_CONFIGURED",
    "ERROR_TELEGRAM_SEND_FAILED",
    "ERROR_TRANSACTION_NOT_FOUND",
    "ETF_HOLDINGS_CACHE_MAXSIZE",
    "ETF_HOLDINGS_CACHE_TTL",
    "ETF_TOP_N",
    "FEAR_GREED_CACHE_MAXSIZE",
    "FEAR_GREED_CACHE_TTL",
    "FG_BREADTH_MULT",
    "FG_COMPONENT_FAILURE_COOLDOWN_SECONDS",
    "FG_COMPONENT_WEIGHTS",
    "FG_HYG_TICKER",
    "FG_JUNK_BOND_MULT",
    "FG_LOOKBACK_DAYS",
    "FG_MA_WINDOW",
    "FG_MOMENTUM_MA_MULT",
    "FG_MOMENTUM_RSI_WEIGHT",
    "FG_PRICE_STRENGTH_MULT",
    "FG_QQQ_TICKER",
    "FG_RSP_TICKER",
    "FG_SAFE_HAVEN_MULT",
    "FG_SECTOR_ROTATION_MULT",
    "FG_SPY_TICKER",
    "FG_TLT_TICKER",
    "FG_VIX_BASE",
    "FG_VIX_OFFSET",
    "FG_VIX_SLOPE",
    "FG_XLP_TICKER",
    "FINMIND_API_URL",
    "FINMIND_CIRCUIT_BREAKER_COOLDOWN",
    "FINMIND_CIRCUIT_BREAKER_THRESHOLD",
    "FINMIND_LOOKBACK_DAYS",
    "FINMIND_REQUEST_TIMEOUT",
    "FOREX_CACHE_MAXSIZE",
    "FOREX_CACHE_TTL",
    "FOREX_HISTORY_CACHE_MAXSIZE",
    "FOREX_HISTORY_CACHE_TTL",
    "FOREX_HISTORY_LONG_CACHE_MAXSIZE",
    "FOREX_HISTORY_LONG_CACHE_TTL",
    "FUNDAMENTALS_CACHE_MAXSIZE",
    "FUNDAMENTALS_CACHE_TTL",
    "FX_DAILY_SPIKE_PCT",
    "FX_HISTORY_PERIOD",
    "FX_LONG_TERM_PERIOD",
    "FX_LONG_TERM_TREND_PCT",
    "FX_SHORT_TERM_SWING_PCT",
    "FX_WATCH_DEFAULT_ALERT_ON_CONSECUTIVE",
    "FX_WATCH_DEFAULT_ALERT_ON_RECENT_HIGH",
    "FX_WATCH_DEFAULT_CONSECUTIVE_DAYS",
    "FX_WATCH_DEFAULT_RECENT_HIGH_DAYS",
    "FX_WATCH_DEFAULT_REMINDER_HOURS",
    "FX_WATCH_FORCE_REFRESH_COOLDOWN_SECONDS",
    "FX_WATCH_HIGH_RECENCY_THRESHOLD",
    "FX_WATCH_RECENT_HIGH_TOLERANCE_PCT",
    "FX_WATCH_TREND_LONG_WINDOW",
    "FX_WATCH_TREND_SHORT_WINDOW",
    "FX_WATCH_TREND_SIDEWAYS_THRESHOLD",
    "GENERIC_ERROR_MESSAGE",
    "GENERIC_PREFERENCES_ERROR",
    "GENERIC_TELEGRAM_ERROR",
    "GENERIC_VALIDATION_ERROR",
    "GENERIC_WEBHOOK_ERROR",
    "GURU_BACKFILL_FILING_COUNT",
    "GURU_BACKFILL_YEARS",
    "GURU_BACKTEST_CACHE_TTL",
    "GURU_BACKTEST_MAX_QUARTERS",
    "GURU_FILING_CACHE_MAXSIZE",
    "GURU_FILING_CACHE_TTL",
    "GURU_FILING_DEADLINES",
    "GURU_HEATMAP_CACHE_TTL",
    "GURU_HOLDING_CHANGES_DISPLAY_LIMIT",
    "GURU_HOLDING_CHANGE_THRESHOLD_PCT",
    "GURU_TOP_HOLDINGS_COUNT",
    "HOLDING_QUANTITY_EPSILON",
    "IDECO_LIMITS",
    "INSIGHT_CONCENTRATION_THRESHOLD",
    "INSIGHT_EXCELLENT_HEALTH_SCORE",
    "INSIGHT_MODERATE_DRAWDOWN_THRESHOLD",
    "INSIGHT_OUTPERFORMANCE_THRESHOLD",
    "INSIGHT_POOR_HEALTH_SCORE",
    "INSIGHT_SEVERE_DRAWDOWN_THRESHOLD",
    "INSIGHT_STRONG_SHARPE",
    "INSIGHT_UNDERPERFORMANCE_THRESHOLD",
    "INSTITUTIONAL_HOLDERS_TOP_N",
    "JP_VI_BASE",
    "JP_VI_OFFSET",
    "JP_VI_SLOPE",
    "LANGUAGE_LABELS",
    "LATEST_SCAN_LOGS_DEFAULT_LIMIT",
    "MA60_WINDOW",
    "MA200_DEEP_DEVIATION_THRESHOLD",
    "MA200_WINDOW",
    "MARGIN_TREND_QUARTERS",
    "MARKET_BEARISH_MAX_PCT",
    "MARKET_BULLISH_MAX_PCT",
    "MARKET_NEUTRAL_MAX_PCT",
    "MARKET_STRONG_BULLISH_MAX_PCT",
    "MAX_IMPORT_ROWS",
    "MAX_UPLOAD_BYTES",
    "MIN_CLOSE_PRICES_FOR_CHANGE",
    "MIN_HISTORY_DAYS_FOR_SIGNALS",
    "MOAT_CACHE_MAXSIZE",
    "MOAT_CACHE_TTL",
    "MOAT_MARGIN_DETERIORATION_THRESHOLD",
    "MOAT_PERSISTENT_FAILURE_THRESHOLD",
    "NIKKEI_VI_TICKER",
    "NISA_LIMITS",
    "NISA_RESTORATION_POLICY",
    "NOTIFICATION_TYPES",
    "NOTIFICATION_TYPE_GURU_ALERTS",
    "POSITION_VERIFY_EPSILON",
    "PREWARM_BATCH_TIMEOUT",
    "PREWARM_REFRESH_INTERVAL",
    "PRICE_ALERT_COOLDOWN_HOURS",
    "PRICE_HISTORY_CACHE_MAXSIZE",
    "PRICE_HISTORY_CACHE_TTL",
    "RADAR_CATEGORIES",
    "REBALANCE_CACHE_MAXSIZE",
    "REBALANCE_CACHE_TTL",
    "REMOVAL_REASON_UNKNOWN",
    "RESONANCE_CACHE_TTL",
    "ROGUE_WAVE_BIAS_PERCENTILE",
    "ROGUE_WAVE_CACHE_MAXSIZE",
    "ROGUE_WAVE_CACHE_TTL",
    "ROGUE_WAVE_HISTORY_PERIOD",
    "ROGUE_WAVE_MIN_HISTORY_DAYS",
    "ROGUE_WAVE_VOLUME_RATIO_THRESHOLD",
    "RSI_APPROACHING_BUY_THRESHOLD",
    "RSI_CONTRARIAN_BUY_THRESHOLD",
    "RSI_DEEP_VALUE_THRESHOLD",
    "RSI_OVERBOUGHT",
    "RSI_OVERSOLD",
    "RSI_PERIOD",
    "RSI_WEAKENING_THRESHOLD",
    "SCAN_HISTORY_DEFAULT_LIMIT",
    "SCAN_L1_WARM_THRESHOLD",
    "SCAN_STALE_SECONDS",
    "SCAN_STALE_SECONDS_OFF_HOURS",
    "SCAN_THREAD_POOL_SIZE",
    "SECONDS_PER_DAY",
    "SEC_EDGAR_ARCHIVES_BASE_URL",
    "SEC_EDGAR_BASE_URL",
    "SEC_EDGAR_RATE_LIMIT_CPS",
    "SEC_EDGAR_REQUEST_TIMEOUT",
    "SEC_EDGAR_USER_AGENT",
    "SIGNALS_CACHE_MAXSIZE",
    "SIGNALS_CACHE_TTL",
    "SKIP_MOAT_CATEGORIES",
    "SKIP_PRICE_FETCH_CATEGORIES",
    "SKIP_RSI_CATEGORIES",
    "SP500_TICKER",
    "STOCK_CATEGORIES",
    "STOCK_SPLIT_CACHE_MAXSIZE",
    "STOCK_SPLIT_CACHE_TTL",
    "STOCK_SPLIT_LOOKBACK_DAYS",
    "STRESS_DISCLAIMER",
    "STRESS_EMPTY_PAIN_LABEL",
    "STRESS_PAIN_LEVELS",
    "SUPPORTED_CURRENCIES",
    "SUPPORTED_LANGUAGES",
    "TAX_WRAPPER_OPTIONS",
    "TELEGRAM_API_URL",
    "TELEGRAM_MAX_MESSAGE_LENGTH",
    "TELEGRAM_REQUEST_TIMEOUT",
    "TICKER_MARKET_MAP",
    "TOKUTEI_TAX_RATE",
    "TWII_TICKER",
    "TW_VOL_BASE",
    "TW_VOL_OFFSET",
    "TW_VOL_SLOPE",
    "VIX_EXTREME_FEAR",
    "VIX_FEAR",
    "VIX_GREED",
    "VIX_HISTORY_PERIOD",
    "VIX_NEUTRAL_LOW",
    "VIX_SCORE_BREAKPOINTS",
    "VIX_SCORE_CEILING",
    "VIX_SCORE_CEILING_VIX",
    "VIX_SCORE_FLOOR",
    "VIX_SCORE_FLOOR_VIX",
    "VIX_TICKER",
    "VOLUME_RATIO_LONG_DAYS",
    "VOLUME_RATIO_SHORT_DAYS",
    "VOLUME_SURGE_THRESHOLD",
    "VOLUME_THIN_THRESHOLD",
    "WEBHOOK_ACTION_REGISTRY",
    "WEBHOOK_MISSING_TICKER",
    "WEEKLY_DIGEST_LOOKBACK_DAYS",
    "WITHDRAWAL_MIN_SELL_VALUE",
    "XRAY_ACK_STEP_PCT",
    "XRAY_SINGLE_STOCK_WARN_PCT",
    "XRAY_SKIP_CATEGORIES",
    "YFINANCE_HISTORY_PERIOD",
    "YFINANCE_RATE_LIMIT_CPS",
    "YFINANCE_RETRY_ATTEMPTS",
    "YFINANCE_RETRY_WAIT_MAX",
    "YFINANCE_RETRY_WAIT_MIN",
    "YF_CONNECT_TIMEOUT",
    "YF_INFO_CACHE_MAXSIZE",
    "YF_INFO_CACHE_TTL",
    "YF_READ_TIMEOUT",
]

# ---------------------------------------------------------------------------
# Technical Indicator Parameters
# ---------------------------------------------------------------------------
RSI_PERIOD = 14
MA200_WINDOW = 200
MA60_WINDOW = 60
VOLUME_RATIO_SHORT_DAYS = 5
VOLUME_RATIO_LONG_DAYS = 20
YFINANCE_HISTORY_PERIOD = "1y"
MIN_HISTORY_DAYS_FOR_SIGNALS = 60
MIN_CLOSE_PRICES_FOR_CHANGE = 2  # 計算日漲跌所需的最少收盤價數據點（前日 + 當日）
SECONDS_PER_DAY = 86400  # 判斷訊號是否為「新」（< 24 小時）

# ---------------------------------------------------------------------------
# Decision Engine Thresholds
# ---------------------------------------------------------------------------
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 80
RSI_DEEP_VALUE_THRESHOLD = 35
RSI_CONTRARIAN_BUY_THRESHOLD = 32
RSI_APPROACHING_BUY_THRESHOLD = 37
RSI_WEAKENING_THRESHOLD = 38
BIAS_OVERHEATED_THRESHOLD = 30
BIAS_OVERSOLD_THRESHOLD = -20
BIAS_WEAKENING_THRESHOLD = -15
# Same magnitude as BIAS_WEAKENING but measured against MA200 (not MA60); may diverge independently.
MA200_DEEP_DEVIATION_THRESHOLD = -15  # buy amplifier: price deeply below MA200
MOAT_MARGIN_DETERIORATION_THRESHOLD = -2  # percentage points YoY

# Category RSI offset — derived from CATEGORY_FALLBACK_BETA via round((beta - 1.0) * 4)
# Widens/narrows RSI bands symmetrically on both buy and sell sides per category
CATEGORY_RSI_OFFSET: dict[str, int] = {
    "Trend_Setter": 0,  # beta ~1.0
    "Moat": 1,  # beta ~1.2
    "Growth": 2,  # beta ~1.5
    "Mutual_Fund": 0,  # mutual funds do not run RSI scan; keep compatible default
    "Bond": -3,  # beta ~0.3
    "ETF": 0,  # broad-market ETF baseline
    "Cash": 0,
    "Crypto": 0,  # crypto 不參與 RSI 掃描，保留 0 作為相容值
}
# Market sentiment thresholds — % of Trend Setter stocks below 60MA
MARKET_STRONG_BULLISH_MAX_PCT = 10  # ≤10%  → ☀️ Strong Bullish
MARKET_BULLISH_MAX_PCT = 30  # ≤30%  → 🌤️ Bullish
MARKET_NEUTRAL_MAX_PCT = 50  # ≤50%  → ⛅ Neutral
MARKET_BEARISH_MAX_PCT = 70  # ≤70%  → 🌧️ Bearish
# >70% → ⛈️ Strong Bearish

# ---------------------------------------------------------------------------
# Cache Configuration
# ---------------------------------------------------------------------------
SIGNALS_CACHE_MAXSIZE = 200
SIGNALS_CACHE_TTL = 300  # 5 minutes
MOAT_CACHE_MAXSIZE = 200
MOAT_CACHE_TTL = 3600  # 1 hour
EARNINGS_CACHE_MAXSIZE = 200
EARNINGS_CACHE_TTL = 86400  # 24 hours
DIVIDEND_CACHE_MAXSIZE = 200
DIVIDEND_CACHE_TTL = 3600  # 1 hour
STOCK_SPLIT_CACHE_MAXSIZE = 200
STOCK_SPLIT_CACHE_TTL = 86400  # 24 hours
FUNDAMENTALS_CACHE_MAXSIZE = 200
FUNDAMENTALS_CACHE_TTL = 300  # 5 minutes
YF_INFO_CACHE_MAXSIZE = 200
YF_INFO_CACHE_TTL = 120  # 2 minutes (share stock.info across nearby calls)
REBALANCE_CACHE_MAXSIZE = 10
REBALANCE_CACHE_TTL = 300  # 5 minutes
ENRICHED_CACHE_MAXSIZE = 4
ENRICHED_CACHE_TTL = 300  # 5 minutes
RESONANCE_CACHE_TTL = 300  # 5 minutes
PREWARM_REFRESH_INTERVAL = 240  # 4 minutes

# ---------------------------------------------------------------------------
# Disk Cache (L2) TTLs — 比 L1 更長，作為冷啟動 fallback
# ---------------------------------------------------------------------------
DISK_SIGNALS_TTL = (
    3600  # 1 hour — warm restarts skip prewarm for recently-fetched signals
)
DISK_MOAT_TTL = 86400  # 24 hours
DISK_EARNINGS_TTL = 604800  # 7 days
DISK_DIVIDEND_TTL = 86400  # 24 hours
DISK_FUNDAMENTALS_TTL = 86400  # 24 hours
DISK_YF_INFO_TTL = 86400  # 24 hours

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------
YFINANCE_RATE_LIMIT_CPS = (
    0.4  # calls per second — 2 req/5 sec (yfinance official recommendation)
)
COINGECKO_RATE_LIMIT_CPS = 0.5  # calls per second — 30 req/min (free tier)
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# ---------------------------------------------------------------------------
# Scan & Alerts
# ---------------------------------------------------------------------------
BACKTEST_WINDOWS = [5, 10, 30, 60]  # forward return windows in trading days
BACKTEST_MIN_SAMPLES_HIGH = 30
BACKTEST_MIN_SAMPLES_MEDIUM = 10
BACKTEST_CACHE_TTL = 3600  # 1 hour
BACKTEST_MAX_LOOKBACK_DAYS = 365
BACKTEST_FP_WINDOW = 30  # false-positive evaluation window in trading days
BACKFILL_HISTORY_PERIOD = "2y"
BACKFILL_SAMPLE_INTERVAL = 5
BACKFILL_MARKET_STATUS = "BACKFILL"
BACKFILL_DEFAULT_MOAT = "STABLE"
BACKFILL_MIN_HISTORY_DAYS = 200  # MA200 warmup requirement for replay
STOCK_SPLIT_LOOKBACK_DAYS = 30
DIVIDEND_LOOKBACK_DAYS = 45

SCAN_THREAD_POOL_SIZE = 2  # 2 threads match 0.4 req/sec global rate limit
ENRICHED_THREAD_POOL_SIZE = 4  # 與 0.4 req/sec 速率限制相符，避免過度競爭
ENRICHED_PER_TICKER_TIMEOUT = 30  # 每檔股票豐富資料超時（秒）— 配合 0.4 req/sec 放寬
SCAN_STALE_SECONDS = 900  # 15 minutes — scanner skips if last scan is fresher
SCAN_STALE_SECONDS_OFF_HOURS = 3600  # 60 minutes — relaxed scanner cadence off-hours
SCAN_L1_WARM_THRESHOLD = 0.8  # skip batch_download if ≥80% of scan tickers are in L1
MOAT_PERSISTENT_FAILURE_THRESHOLD = (
    3  # consecutive failures before writing sentinel to L2
)
DISK_MOAT_PERSISTENT_TTL = (
    86400  # 1 day — sentinel TTL for persistently-failing moat tickers
)
DISK_MOAT_FAILURE_TTL = (
    3600  # 1 hour — short negative cache for transient moat failures
)
PRICE_ALERT_COOLDOWN_HOURS = 4
WEEKLY_DIGEST_LOOKBACK_DAYS = 7
SCAN_HISTORY_DEFAULT_LIMIT = 20
LATEST_SCAN_LOGS_DEFAULT_LIMIT = 50
INSTITUTIONAL_HOLDERS_TOP_N = 5
MARGIN_TREND_QUARTERS = 5
BETA_MIN_HISTORY_PERIODS = 60  # minimum paired return days for OLS beta computation

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_REQUEST_TIMEOUT = 10
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

# ---------------------------------------------------------------------------
# Shared Messages
# ---------------------------------------------------------------------------
SKIP_RSI_CATEGORIES = [
    "Cash",
    "Crypto",
    "Mutual_Fund",
]  # 非 RSI 類資產不進行技術訊號掃描
SKIP_PRICE_FETCH_CATEGORIES = [
    "Cash",
    "Mutual_Fund",
]  # 不走 yfinance 取價的資產（MF 走 NAV 日次同步，enrichment 分支在 SKIP 判斷前處理）
SKIP_MOAT_CATEGORIES = [
    "Bond",
    "Cash",
    "Crypto",
    "Mutual_Fund",
    "ETF",
]  # 非個股類不適用護城河分析
REMOVAL_REASON_UNKNOWN = "constants.removal_reason_unknown"  # i18n key

# ---------------------------------------------------------------------------
# Default Parameter Values
# ---------------------------------------------------------------------------
DEFAULT_IMPORT_CATEGORY = "Growth"
DEFAULT_WEBHOOK_THESIS = "constants.default_webhook_thesis"  # i18n key

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
# Tax Wrapper — NISA Limits (New NISA, effective 2024-01-01)
# ---------------------------------------------------------------------------
NISA_RESTORATION_POLICY = "next_year"  # Change to "same_day" when 2026 reform activates

NISA_LIMITS = {
    "nisa_tsumitate": {
        "annual": 1_200_000,
    },
    "nisa_growth": {
        "annual": 2_400_000,
        "lifetime_sub_limit": 12_000_000,
    },
    "combined_annual": 3_600_000,
    "combined_lifetime": 18_000_000,
}

# ---------------------------------------------------------------------------
# Tax Wrapper — iDeCo Limits (as of Dec 2024 reform)
# ---------------------------------------------------------------------------
IDECO_LIMITS = {
    "self_employed": {"monthly": 68_000, "annual": 816_000},
    "employee_no_pension": {"monthly": 23_000, "annual": 276_000},
    "employee_dc_only": {"monthly": 20_000, "annual": 240_000},
    "employee_with_db": {"monthly": 20_000, "annual": 240_000},
    "public_servant": {"monthly": 20_000, "annual": 240_000},
    "homemaker": {"monthly": 23_000, "annual": 276_000},
}

# ---------------------------------------------------------------------------
# Tax Wrapper — Tax Rates
# ---------------------------------------------------------------------------
TOKUTEI_TAX_RATE = 0.20315  # 所得税 15.315% + 住民税 5%

# ---------------------------------------------------------------------------
# Tax Wrapper — Wrapper Type Options (for frontend selector)
# ---------------------------------------------------------------------------
TAX_WRAPPER_OPTIONS = [
    "tokutei",
    "nisa_tsumitate",
    "nisa_growth",
    "ideco",
    "ippan",
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
# Forex Cache
# ---------------------------------------------------------------------------
FOREX_CACHE_MAXSIZE = 50
FOREX_CACHE_TTL = 3600  # 1 hour
DISK_FOREX_TTL = 86400  # 24 hours

# ---------------------------------------------------------------------------
# Supported Currencies
# ---------------------------------------------------------------------------
SUPPORTED_CURRENCIES = ["USD", "TWD", "JPY", "EUR", "GBP", "CNY", "HKD", "SGD", "THB"]

# ---------------------------------------------------------------------------
# Price History Cache
# ---------------------------------------------------------------------------
PRICE_HISTORY_CACHE_MAXSIZE = 200
PRICE_HISTORY_CACHE_TTL = 300  # L1: 5 minutes (same as signals)
DISK_PRICE_HISTORY_TTL = 1800  # L2: 30 minutes

# ---------------------------------------------------------------------------
# ETF Holdings Cache (for X-Ray analysis)
# ---------------------------------------------------------------------------
ETF_HOLDINGS_CACHE_MAXSIZE = 100
ETF_HOLDINGS_CACHE_TTL = 86400  # 24 hours (ETF holdings change slowly)
DISK_ETF_HOLDINGS_TTL = 604800  # 7 days
ETF_TOP_N = 25  # only resolve top N constituents per ETF
DISK_ETF_SECTOR_WEIGHTS_TTL = 604800  # 7 days (same cadence as ETF holdings)

# ---------------------------------------------------------------------------
# Currency Exposure Monitor
# ---------------------------------------------------------------------------
FX_DAILY_SPIKE_PCT = 1.5  # 單日波動門檻
FX_SHORT_TERM_SWING_PCT = 2.0  # 5 日波段門檻
FX_LONG_TERM_TREND_PCT = 8.0  # 3 個月趨勢門檻
FX_HISTORY_PERIOD = "5d"  # yfinance period for short-term detection
FX_LONG_TERM_PERIOD = "3mo"  # yfinance period for long-term trend detection
DISK_KEY_FOREX_HISTORY = "forex_history"
DISK_FOREX_HISTORY_TTL = 3600  # 1 hour
FOREX_HISTORY_CACHE_MAXSIZE = 50
FOREX_HISTORY_CACHE_TTL = 3600  # 1 hour
DISK_KEY_FOREX_HISTORY_LONG = "forex_history_long"
DISK_FOREX_HISTORY_LONG_TTL = 14400  # 4 hours (long-term data changes slowly)
FOREX_HISTORY_LONG_CACHE_MAXSIZE = 50
FOREX_HISTORY_LONG_CACHE_TTL = 7200  # 2 hours L1

# ---------------------------------------------------------------------------
# FX Watch (Exchange Timing Alerts)
# ---------------------------------------------------------------------------
FX_WATCH_DEFAULT_RECENT_HIGH_DAYS = 30  # 30-day recent high window
FX_WATCH_DEFAULT_CONSECUTIVE_DAYS = 3  # 3-day consecutive increase threshold
FX_WATCH_DEFAULT_REMINDER_HOURS = 24  # 24-hour cooldown between alerts
FX_WATCH_DEFAULT_ALERT_ON_RECENT_HIGH = True  # Enable recent high alerts by default
FX_WATCH_DEFAULT_ALERT_ON_CONSECUTIVE = (
    True  # Enable consecutive increase alerts by default
)
FX_WATCH_TREND_SHORT_WINDOW = 5  # 5-day SMA window for trend direction
FX_WATCH_TREND_LONG_WINDOW = 10  # 10-day SMA window for trend direction
FX_WATCH_HIGH_RECENCY_THRESHOLD = 3  # alert if high was within N days
FX_WATCH_TREND_SIDEWAYS_THRESHOLD = 0.001  # abs(short_sma-long_sma)/long_sma
FX_WATCH_RECENT_HIGH_TOLERANCE_PCT = 2.0  # near-high tolerance percentage
FX_WATCH_FORCE_REFRESH_COOLDOWN_SECONDS = 30  # cooldown between force_refresh calls

# ---------------------------------------------------------------------------
# X-Ray (Portfolio Overlap Analysis)
# ---------------------------------------------------------------------------
XRAY_SINGLE_STOCK_WARN_PCT = 15.0  # Telegram warning threshold (%)
XRAY_SKIP_CATEGORIES = ["Cash", "Bond"]  # skip non-equity for X-Ray

# ---------------------------------------------------------------------------
# Fear & Greed Index
# ---------------------------------------------------------------------------
VIX_TICKER = "^VIX"
VIX_HISTORY_PERIOD = "5d"

# VIX 閾值（對應恐懼與貪婪等級）
VIX_EXTREME_FEAR = 30  # VIX > 30 → 極度恐懼
VIX_FEAR = 20  # VIX 20–30 → 恐懼
VIX_NEUTRAL_LOW = 15
VIX_GREED = 10  # VIX 10–15 → 貪婪
# VIX < 10 → 極度貪婪

# VIX → 0–100 分數的分段線性映射斷點（對齊 CNN 分級閾值）
VIX_SCORE_BREAKPOINTS: list[tuple[int, int]] = [
    (30, 25),  # VIX 30 → score 25（極度恐懼/恐懼 邊界）
    (20, 45),  # VIX 20 → score 45（恐懼/中性 邊界）
    (15, 55),  # VIX 15 → score 55（中性/貪婪 邊界）
    (10, 75),  # VIX 10 → score 75（貪婪/極度貪婪 邊界）
]
VIX_SCORE_FLOOR = 0  # VIX ≥ VIX_SCORE_FLOOR_VIX → score 0
VIX_SCORE_CEILING = 100  # VIX ≤ VIX_SCORE_CEILING_VIX → score 100
VIX_SCORE_FLOOR_VIX = 40  # 恐懼分數地板對應的 VIX 值
VIX_SCORE_CEILING_VIX = 8  # 貪婪分數天花板對應的 VIX 值

# CNN Fear & Greed Index 閾值（0–100 分）
CNN_FG_EXTREME_FEAR = 25  # 0–25 → 極度恐懼
CNN_FG_FEAR = 45  # 25–45 → 恐懼
CNN_FG_NEUTRAL_HIGH = 55  # 45–55 → 中性
CNN_FG_GREED = 75  # 55–75 → 貪婪
# 75–100 → 極度貪婪

CNN_FG_API_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
CNN_FG_REQUEST_TIMEOUT = 10  # seconds

# Fear & Greed Cache
FEAR_GREED_CACHE_MAXSIZE = 10
FEAR_GREED_CACHE_TTL = 1800  # L1: 30 minutes
DISK_FEAR_GREED_TTL = 7200  # L2: 2 hours

# ---------------------------------------------------------------------------
# Self-Calculated Fear & Greed Index — 7-Component Weighted Composite
# Modeled after OnOff.Markets' transparent methodology (https://onoff.markets)
# ---------------------------------------------------------------------------

# ETF tickers for component data (all available via yfinance)
FG_SPY_TICKER = "SPY"  # S&P 500 (price strength, momentum, breadth base)
FG_TLT_TICKER = "TLT"  # 20+ Year Treasury (safe haven, junk bond baseline)
FG_HYG_TICKER = "HYG"  # High Yield Corporate Bond (junk bond demand)
FG_RSP_TICKER = "RSP"  # Equal-Weight S&P 500 (market breadth)
FG_QQQ_TICKER = "QQQ"  # Nasdaq-100 (sector rotation — growth/tech)
FG_XLP_TICKER = "XLP"  # Consumer Staples (sector rotation — defensive)

# Lookback period for return-based components (days)
FG_LOOKBACK_DAYS = 14

# MA window for momentum component
FG_MA_WINDOW = 50

# Component weights (must sum to 1.0)
FG_COMPONENT_WEIGHTS: dict[str, float] = {
    "price_strength": 0.20,
    "vix": 0.20,
    "momentum": 0.15,
    "breadth": 0.15,
    "junk_bond": 0.10,
    "safe_haven": 0.10,
    "sector_rotation": 0.10,
}

# VIX continuous linear formula: score = FG_VIX_BASE - (vix - FG_VIX_OFFSET) * FG_VIX_SLOPE
# VIX 10 → 90, VIX 20 → 58, VIX 30 → 26, VIX 38+ → 0
FG_VIX_BASE: float = 90.0
FG_VIX_OFFSET: float = 10.0
FG_VIX_SLOPE: float = 3.2

# Price strength multiplier: score = 50 + return_pct * FG_PRICE_STRENGTH_MULT
# Saturates at ±6.25% (score 0 or 100)
FG_PRICE_STRENGTH_MULT: float = 8.0

# Momentum MA50 component multiplier: score = 50 + deviation_pct * FG_MOMENTUM_MA_MULT
# Saturates at ±10% deviation from MA50
FG_MOMENTUM_MA_MULT: float = 5.0

# Market breadth multiplier: score = 50 + (rsp_ret - spy_ret) * FG_BREADTH_MULT
# Saturates at ±2.78% divergence
FG_BREADTH_MULT: float = 18.0

# Junk bond demand multiplier: score = 50 + (hyg_ret - tlt_ret) * FG_JUNK_BOND_MULT
# Saturates at ±10% divergence
FG_JUNK_BOND_MULT: float = 5.0

# Safe haven demand multiplier (TLT inverted): score = 50 - tlt_ret * FG_SAFE_HAVEN_MULT
# Saturates at ±10% TLT move
FG_SAFE_HAVEN_MULT: float = 5.0

# Sector rotation multiplier: score = 50 + (qqq_ret - xlp_ret) * FG_SECTOR_ROTATION_MULT
# Saturates at ±10% divergence
FG_SECTOR_ROTATION_MULT: float = 5.0

# RSI weight within momentum composite (remainder goes to MA50 position)
FG_MOMENTUM_RSI_WEIGHT: float = 0.70

# ---------------------------------------------------------------------------
# Disk Cache Key Prefixes
# ---------------------------------------------------------------------------
DISK_KEY_SIGNALS = "signals"
DISK_KEY_MOAT = "moat"
DISK_KEY_EARNINGS = "earnings"
DISK_KEY_DIVIDEND = "dividend"
DISK_KEY_DIVIDEND_EVENTS = "dividend_events"
DISK_KEY_STOCK_SPLIT = "stock_split"
DISK_KEY_FUNDAMENTALS = "fundamentals"
DISK_KEY_YF_INFO = "yf_info"
DISK_KEY_PRICE_HISTORY = "price_history"
DISK_KEY_FOREX = "forex"
DISK_KEY_ETF_HOLDINGS = "etf_holdings"
DISK_KEY_ETF_SECTOR_WEIGHTS = "etf_sector_weights"
DISK_KEY_FEAR_GREED = "fear_greed"
DISK_KEY_ROGUE_WAVE = "rogue_wave"
DISK_KEY_CRYPTO = "crypto"

# ---------------------------------------------------------------------------
# Webhook Messages (use t("webhook.missing_ticker") at call sites)
# ---------------------------------------------------------------------------
WEBHOOK_MISSING_TICKER = "webhook.missing_ticker"  # i18n key

# ---------------------------------------------------------------------------
# Webhook Action Registry — single source of truth for AI agent actions
# ---------------------------------------------------------------------------
WEBHOOK_ACTION_REGISTRY: dict[str, dict] = {
    "help": {
        "description": "List all supported webhook actions and their parameters",
        "requires_ticker": False,
    },
    "summary": {
        "description": "Portfolio health overview (plain text)",
        "requires_ticker": False,
    },
    "dashboard": {
        "description": "Portfolio + market overview in one call",
        "requires_ticker": False,
    },
    "signals": {
        "description": "Technical indicators for a ticker (RSI, MA, Bias)",
        "requires_ticker": True,
    },
    "analyze": {
        "description": "Full stock analysis (signals + moat + fundamentals)",
        "requires_ticker": True,
    },
    "scan": {
        "description": "Trigger background full scan (results via Telegram)",
        "requires_ticker": False,
    },
    "moat": {
        "description": "Gross margin YoY analysis for a ticker",
        "requires_ticker": True,
    },
    "alerts": {
        "description": "List price alerts for a ticker",
        "requires_ticker": True,
    },
    "add_stock": {
        "description": "Add a stock to the watchlist",
        "requires_ticker": True,
        "params": {
            "ticker": "str (required)",
            "category": "StockCategory (Trend_Setter|Moat|Growth|Mutual_Fund|Bond|Crypto|Cash|ETF)",
            "thesis": "str (investment thesis)",
            "tags": "list[str] (e.g. ['AI', 'Semiconductor'])",
        },
    },
    "fear_greed": {
        "description": "Current Fear & Greed Index (VIX + CNN composite)",
        "requires_ticker": False,
    },
    "withdraw": {
        "description": "Smart withdrawal plan (Liquidity Waterfall)",
        "requires_ticker": False,
        "params": {
            "amount": "float (required, target withdrawal amount)",
            "currency": "str (display currency, default USD)",
        },
    },
    "fx_watch": {
        "description": "Check FX watch configs & send Telegram alerts (with cooldown)",
        "requires_ticker": False,
    },
    "stock_splits": {
        "description": "Check stock splits for held tickers and notify/apply updates",
        "requires_ticker": False,
    },
    "dividends": {
        "description": "Check dividends for held tickers and notify/apply updates",
        "requires_ticker": False,
    },
    "drift_alerts": {
        "description": "Run portfolio drift checks and send alert summaries",
        "requires_ticker": False,
    },
    "acknowledge_drift": {
        "description": "Acknowledge one drift category to suppress repeated alerts",
        "requires_ticker": False,
        "params": {
            "category": "str (required — allocation category name)",
            "drift_pct": "float (optional — current drift percentage points)",
            "display_currency": "str (optional — default USD)",
        },
    },
    "acknowledge_xray": {
        "description": "Acknowledge one X-Ray symbol to suppress repeated alerts",
        "requires_ticker": False,
        "params": {
            "symbol": "str (required — concentrated underlying symbol)",
            "total_weight_pct": "float (optional — current portfolio weight percentage)",
            "display_currency": "str (optional — default USD)",
        },
    },
    "guru_sync": {
        "description": "Trigger 13F filing sync for all tracked gurus (EDGAR fetch)",
        "requires_ticker": False,
    },
    "guru_summary": {
        "description": "Send latest guru holding changes digest via Telegram",
        "requires_ticker": False,
    },
    "transactions": {
        "description": "List recent transactions (buy/sell/dividend/deposit/withdrawal)",
        "requires_ticker": False,
        "params": {
            "ticker": "str (optional — filter by ticker)",
            "account_id": "int (optional — filter by account)",
            "start": "str (optional — YYYY-MM-DD start date)",
            "end": "str (optional — YYYY-MM-DD end date)",
            "limit": "int (optional — default 10, max 50)",
        },
    },
    "add_transaction": {
        "description": "Record a new transaction",
        "requires_ticker": True,
        "params": {
            "type": "str (required — BUY/SELL/DIVIDEND/DEPOSIT/WITHDRAWAL/OPENING_BALANCE/ADJUSTMENT/STOCK_SPLIT/TRANSFER_IN/TRANSFER_OUT)",
            "account_id": "int (required — account identifier)",
            "quantity": "float (required)",
            "price": "float (optional — per-unit price)",
            "total_amount": "float (required — total transaction value)",
            "date": "str (required — YYYY-MM-DD)",
        },
    },
    "accounts": {
        "description": "List accounts with holdings count per account",
        "requires_ticker": False,
    },
    "analytics": {
        "description": "Portfolio risk metrics: Sharpe, Sortino, max drawdown, volatility",
        "requires_ticker": False,
        "params": {
            "start": "str (optional — YYYY-MM-DD start date)",
            "end": "str (optional — YYYY-MM-DD end date)",
        },
    },
    "insights": {
        "description": "Natural language portfolio insights and suggestions",
        "requires_ticker": False,
        "params": {
            "display_currency": "str (optional — default USD)",
        },
    },
    "quota": {
        "description": "NISA/iDeCo 額度狀態查詢",
        "requires_ticker": False,
        "description_en": "NISA/iDeCo quota status (annual/lifetime remaining, restoration forecast)",
        "params": {
            "year": "int (optional — fiscal year, default current year)",
        },
    },
}

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
# curl_cffi
# ---------------------------------------------------------------------------
CURL_CFFI_IMPERSONATE = "chrome"

# ---------------------------------------------------------------------------
# Rogue Wave (瘋狗浪) — Historical Bias Percentile Alert
# ---------------------------------------------------------------------------
ROGUE_WAVE_HISTORY_PERIOD = "3y"
ROGUE_WAVE_MIN_HISTORY_DAYS = 200
ROGUE_WAVE_BIAS_PERCENTILE = 95  # 95th percentile = extreme overheating
ROGUE_WAVE_VOLUME_RATIO_THRESHOLD = 1.5  # 50% above normal volume
VOLUME_SURGE_THRESHOLD = 1.5  # volume confidence qualifier: surge
VOLUME_THIN_THRESHOLD = 0.5  # volume confidence qualifier: thin volume

ROGUE_WAVE_CACHE_MAXSIZE = 200
ROGUE_WAVE_CACHE_TTL = 86400  # L1: 24 hours
DISK_ROGUE_WAVE_TTL = 172800  # L2: 48 hours

# ---------------------------------------------------------------------------
# Retry Configuration (yfinance transient network failures)
# ---------------------------------------------------------------------------
YFINANCE_RETRY_ATTEMPTS = 3
YFINANCE_RETRY_WAIT_MIN = 2  # seconds (exponential backoff minimum)
YFINANCE_RETRY_WAIT_MAX = 10  # seconds (exponential backoff maximum)
YF_CONNECT_TIMEOUT = 10  # seconds (curl_cffi connect timeout)
YF_READ_TIMEOUT = 30  # seconds (curl_cffi total/read timeout)
PREWARM_BATCH_TIMEOUT = 120  # seconds (upper bound for prewarm batches)
FG_COMPONENT_FAILURE_COOLDOWN_SECONDS = (
    120  # short cooldown after transient FG failures
)

# ---------------------------------------------------------------------------
# Beta Cache Configuration (Stress Test)
# ---------------------------------------------------------------------------
BETA_CACHE_MAXSIZE = 200
BETA_CACHE_TTL = 86400  # 24 hours (L1)
DISK_BETA_TTL = 604800  # 7 days (L2)
DISK_KEY_BETA = "beta"

# Category Fallback Beta (when yfinance returns None)
CATEGORY_FALLBACK_BETA: dict[str, float] = {
    "Trend_Setter": 1.0,
    "Moat": 1.2,
    "Growth": 1.5,
    "Mutual_Fund": 0.0,
    "ETF": 1.0,
    "Bond": 0.3,
    "Cash": 0.0,
    "Crypto": 0.0,
}

# ---------------------------------------------------------------------------
# Stress Test Pain Levels
# ---------------------------------------------------------------------------
# threshold 表示該等級的最低損失門檻（含）
# loss_pct < 10% → low, 10% <= loss < 20% → moderate, 20% <= loss < 30% → high, loss >= 30% → panic
STRESS_PAIN_LEVELS = [
    {
        "threshold": 0,
        "level": "low",
        "label": "constants.stress_pain_low",
        "emoji": "green",
    },
    {
        "threshold": 10,
        "level": "moderate",
        "label": "constants.stress_pain_moderate",
        "emoji": "yellow",
    },
    {
        "threshold": 20,
        "level": "high",
        "label": "constants.stress_pain_high",
        "emoji": "orange",
    },
    {
        "threshold": 30,
        "level": "panic",
        "label": "constants.stress_pain_panic",
        "emoji": "red",
    },
]

STRESS_DISCLAIMER = "constants.stress_disclaimer"  # i18n key
STRESS_EMPTY_PAIN_LABEL = "stress_test.no_holdings"  # i18n key (when no holdings)

# ---------------------------------------------------------------------------
# Smart Money Tracker (大師足跡追蹤)
# ---------------------------------------------------------------------------
GURU_HOLDING_CHANGE_THRESHOLD_PCT = 20.0  # +/-20% = significant change
GURU_TOP_HOLDINGS_COUNT = 10
GURU_HOLDING_CHANGES_DISPLAY_LIMIT = 20  # default limit for per-guru holding changes
GURU_FILING_DEADLINES = ["02-14", "05-15", "08-14", "11-14"]
SEC_EDGAR_BASE_URL = "https://data.sec.gov"
SEC_EDGAR_ARCHIVES_BASE_URL = "https://www.sec.gov"
# TODO(Phase 2): override with env var SEC_EDGAR_USER_AGENT in sec_edgar.py;
# SEC policy requires a real contact email in the User-Agent header.
SEC_EDGAR_USER_AGENT = "Folio/1.0 (folio@example.com)"
SEC_EDGAR_RATE_LIMIT_CPS = 10.0  # SEC allows 10 req/sec
SEC_EDGAR_REQUEST_TIMEOUT = 15

# Default Gurus (CIK codes)
DEFAULT_GURUS = [
    {
        "name": "Berkshire Hathaway Inc",
        "cik": "0001067983",
        "display_name": "Warren Buffett",
        "style": "VALUE",
        "tier": "TIER_1",
    },
    {
        "name": "Bridgewater Associates, LP",
        "cik": "0001350694",
        "display_name": "Ray Dalio",
        "style": "MACRO",
        "tier": "TIER_1",
    },
    {
        "name": "Citadel Advisors LLC",
        "cik": "0001423053",
        "display_name": "Ken Griffin",
        "style": "QUANT",
        "tier": "TIER_1",
    },
    {
        "name": "Renaissance Technologies LLC",
        "cik": "0001037389",
        "display_name": "Renaissance Technologies",
        "style": "QUANT",
        "tier": "TIER_1",
    },
    {
        "name": "Baupost Group LLC",
        "cik": "0001061768",
        "display_name": "Seth Klarman",
        "style": "VALUE",
        "tier": "TIER_1",
    },
    {
        "name": "Oaktree Capital Management, L.P.",
        "cik": "0001535581",
        "display_name": "Howard Marks",
        "style": "VALUE",
        "tier": "TIER_1",
    },
    {
        "name": "ARK Investment Management LLC",
        "cik": "0001603466",
        "display_name": "Cathie Wood",
        "style": "GROWTH",
        "tier": "TIER_2",
    },
    {
        "name": "Pershing Square Capital Management",
        "cik": "0001336528",
        "display_name": "Bill Ackman",
        "style": "ACTIVIST",
        "tier": "TIER_2",
    },
    {
        "name": "Scion Asset Management, LLC",
        "cik": "0001649339",
        "display_name": "Michael Burry",
        "style": "VALUE",
        "tier": "TIER_2",
    },
    {
        "name": "Appaloosa Management LP",
        "cik": "0001656456",
        "display_name": "David Tepper",
        "style": "MULTI_STRATEGY",
        "tier": "TIER_2",
    },
    {
        "name": "Himalaya Capital Management LLC",
        "cik": "0001598220",
        "display_name": "Li Lu",
        "style": "VALUE",
        "tier": "TIER_2",
    },
    {
        "name": "Gotham Asset Management, LLC",
        "cik": "0001452934",
        "display_name": "Joel Greenblatt",
        "style": "QUANT",
        "tier": "TIER_2",
    },
    {
        "name": "Soros Fund Management LLC",
        "cik": "0001029160",
        "display_name": "George Soros",
        "style": "MACRO",
        "tier": "TIER_1",
    },
    {
        "name": "Social Capital Holdings Inc.",
        "cik": "0001705696",
        "display_name": "Chamath Palihapitiya",
        "style": "GROWTH",
        "tier": "TIER_3",
    },
]

# Notification
NOTIFICATION_TYPE_GURU_ALERTS = "guru_alerts"

GURU_BACKFILL_YEARS = 5  # 回填歷史 13F 資料的年數
GURU_BACKFILL_FILING_COUNT = 20  # 每位大師最多取回 20 筆申報（約 5 年）
GURU_BACKTEST_CACHE_TTL = 3600  # 1 hour
GURU_HEATMAP_CACHE_TTL = 300  # 5 minutes
GURU_BACKTEST_MAX_QUARTERS = 12

# Cache
GURU_FILING_CACHE_MAXSIZE = 50
GURU_FILING_CACHE_TTL = 86400  # 24h (13F data is quarterly)
DISK_GURU_FILING_TTL = 604800  # 7 days
DISK_KEY_GURU_FILING = "guru_filing"
DISK_SECTOR_TTL = 2592000  # 30 days (sectors change very rarely)
DISK_KEY_SECTOR = "sector"
DISK_NAME_TTL = 2592000  # 30 days (company names change very rarely)
DISK_KEY_NAME = "name"
DISK_EXCHANGE_TTL = 2592000  # 30 days (exchange metadata is mostly static)
DISK_KEY_EXCHANGE = "exchange"
DISK_KEY_PRICE_PAIR = "price_pair"
DISK_PRICE_PAIR_TTL = 0  # permanent — historical close prices are immutable

# ---------------------------------------------------------------------------
# Equity Categories (used by sector exposure, X-Ray, etc.)
# ---------------------------------------------------------------------------
EQUITY_CATEGORIES: frozenset[str] = frozenset(
    {"Trend_Setter", "Moat", "Growth", "Mutual_Fund", "ETF"}
)

# ---------------------------------------------------------------------------
# Crypto Market Data Cache
# ---------------------------------------------------------------------------
CRYPTO_CACHE_MAXSIZE = 200
CRYPTO_CACHE_TTL = 120  # L1: 2 minutes
DISK_CRYPTO_TTL = 600  # L2: 10 minutes

# Crypto UI thresholds
CRYPTO_VOLATILITY_HIGH_PCT = 5.0
CRYPTO_VOLATILITY_EXTREME_PCT = 10.0
CRYPTO_QUANTITY_MAX_DECIMALS = 8

# ---------------------------------------------------------------------------
# J-Quants API (optional JP data supplement)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# FinMind API (optional TW data supplement)
# ---------------------------------------------------------------------------
FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"
FINMIND_REQUEST_TIMEOUT = 10
FINMIND_CIRCUIT_BREAKER_THRESHOLD = 3
FINMIND_CIRCUIT_BREAKER_COOLDOWN = 1800  # 30 minutes
FINMIND_LOOKBACK_DAYS = 365

# ---------------------------------------------------------------------------
# JP Market Sentiment (Nikkei VI)
# ---------------------------------------------------------------------------
NIKKEI_VI_TICKER = "^JNV"  # Nikkei Volatility Index on yfinance

# Continuous linear formula: score = JP_VI_BASE - (nikkei_vi - JP_VI_OFFSET) * JP_VI_SLOPE
# NKV 12 → ~90, NKV 20 → ~58, NKV 35 → ~10
JP_VI_BASE: float = 90.0
JP_VI_OFFSET: float = 12.0
JP_VI_SLOPE: float = 3.5

# ---------------------------------------------------------------------------
# TW Market Sentiment (^TWII Realized Volatility)
# ---------------------------------------------------------------------------
TWII_TICKER = "^TWII"  # TAIEX Weighted Index on yfinance

# Continuous linear formula: score = TW_VOL_BASE - (vol_pct - TW_VOL_OFFSET) * TW_VOL_SLOPE
# vol 8% → ~90, vol 18% → ~55, vol 30% → ~13
TW_VOL_BASE: float = 90.0
TW_VOL_OFFSET: float = 8.0
TW_VOL_SLOPE: float = 3.5

# ---------------------------------------------------------------------------
# Geographic Market Detection (ticker suffix → market code)
# ---------------------------------------------------------------------------
TICKER_MARKET_MAP: dict[str, str] = {
    ".TW": "TW",
    ".TWO": "TW",
    ".T": "JP",
    ".HK": "HK",
}
DEFAULT_MARKET = "US"

# Cash currency geographic mapping (currency → market code)
CURRENCY_REGION_MAP: dict[str, str] = {
    "USD": "US",
    "TWD": "TW",
    "JPY": "JP",
    "HKD": "HK",
    "EUR": "EU",
    "GBP": "UK",
    "CNY": "CN",
    "SGD": "SG",
    "THB": "TH",
}

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
