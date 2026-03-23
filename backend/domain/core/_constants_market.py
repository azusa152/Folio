"""Domain — Market data infrastructure constants (cache, forex, ETF, sentiment, retry)."""

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
