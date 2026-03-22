"""Domain — Scan engine constants (technical indicators, decision thresholds, scan config)."""

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
# Cache Configuration (L1 — in-memory TTLCache)
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
# Category Filters
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
