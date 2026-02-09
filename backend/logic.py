"""
Gooaye Radar — 股癌核心邏輯
- RSI(14) 計算
- 均線趨勢 (200MA / 60MA)
- 毛利率 YoY 比較
所有外部 API 呼叫皆以 try/except 包裹，失敗時回傳 None 或警告訊息，絕不中斷服務。
"""

from typing import Optional

import yfinance as yf
from cachetools import TTLCache
from curl_cffi import requests as cffi_requests

from logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# TTL 快取：避免每次頁面載入都重複呼叫 yfinance（預設 5 分鐘）
# ---------------------------------------------------------------------------
_signals_cache: TTLCache = TTLCache(maxsize=200, ttl=300)
_moat_cache: TTLCache = TTLCache(maxsize=200, ttl=300)


def _get_session() -> cffi_requests.Session:
    """建立模擬 Chrome 瀏覽器的 Session，以繞過 Yahoo Finance 的 bot 防護。"""
    return cffi_requests.Session(impersonate="chrome")


# ---------------------------------------------------------------------------
# 技術面訊號
# ---------------------------------------------------------------------------

def _compute_rsi(closes: list[float], period: int = 14) -> Optional[float]:
    """
    以 Wilder's Smoothed Method 計算 RSI。
    需要至少 period+1 筆收盤價。
    """
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # 初始平均漲跌幅
    gains = [d if d > 0 else 0.0 for d in deltas[:period]]
    losses = [-d if d < 0 else 0.0 for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Wilder smoothing
    for d in deltas[period:]:
        gain = d if d > 0 else 0.0
        loss = -d if d < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def get_technical_signals(ticker: str) -> Optional[dict]:
    """
    取得技術面訊號：RSI(14)、現價、200MA、60MA。
    回傳 dict 包含數值與狀態描述。結果快取 5 分鐘。
    """
    cached = _signals_cache.get(ticker)
    if cached is not None:
        logger.debug("%s 技術訊號命中快取。", ticker)
        return cached

    try:
        logger.debug("取得 %s 技術訊號（快取未命中）...", ticker)
        stock = yf.Ticker(ticker, session=_get_session())
        hist = stock.history(period="1y")

        if hist.empty or len(hist) < 60:
            logger.warning("%s 歷史資料不足（%d 筆），無法計算技術指標。", ticker, len(hist))
            return {"error": f"⚠️ {ticker} 歷史資料不足，無法計算技術指標。"}

        closes = hist["Close"].tolist()
        current_price = round(closes[-1], 2)

        # RSI(14)
        rsi = _compute_rsi(closes)

        # 均線
        ma200 = round(sum(closes[-200:]) / min(len(closes), 200), 2) if len(closes) >= 200 else None
        ma60 = round(sum(closes[-60:]) / 60, 2)

        # 狀態判斷
        status_parts: list[str] = []

        if rsi is not None:
            if rsi < 30:
                status_parts.append(f"🟢 RSI={rsi} 超賣區間（可能是機會）")
            elif rsi > 70:
                status_parts.append(f"🔴 RSI={rsi} 超買區間（留意回檔）")
            else:
                status_parts.append(f"⚪ RSI={rsi} 中性")

        if ma200 is not None:
            if current_price < ma200:
                status_parts.append(f"🔴 股價 {current_price} 跌破 200MA ({ma200})")
            else:
                status_parts.append(f"🟢 股價 {current_price} 站穩 200MA ({ma200})")
        else:
            status_parts.append("⚠️ 資料不足 200 天，無法計算 200MA")

        if current_price < ma60:
            status_parts.append(f"🔴 股價 {current_price} 跌破 60MA ({ma60})")
        else:
            status_parts.append(f"🟢 股價 {current_price} 站穩 60MA ({ma60})")

        logger.info(
            "%s 技術訊號：price=%.2f, RSI=%s, 200MA=%s, 60MA=%s",
            ticker, current_price, rsi, ma200, ma60,
        )

        result = {
            "ticker": ticker,
            "price": current_price,
            "rsi": rsi,
            "ma200": ma200,
            "ma60": ma60,
            "status": status_parts,
        }
        _signals_cache[ticker] = result
        return result

    except Exception as e:
        logger.error("無法取得 %s 技術訊號：%s", ticker, e, exc_info=True)
        return {"error": f"⚠️ 無法取得 {ticker} 技術訊號：{e}"}


# ---------------------------------------------------------------------------
# 基本面：毛利率 YoY 檢查
# ---------------------------------------------------------------------------

def check_moat(ticker: str) -> Optional[dict]:
    """
    比較最近一季 vs 去年同期的毛利率。
    若毛利率衰退則發出警告。結果快取 5 分鐘。
    """
    cached = _moat_cache.get(ticker)
    if cached is not None:
        logger.debug("%s 毛利率檢查命中快取。", ticker)
        return cached

    try:
        logger.debug("檢查 %s 護城河（毛利率 YoY，快取未命中）...", ticker)
        stock = yf.Ticker(ticker, session=_get_session())
        financials = stock.quarterly_financials

        if financials is None or financials.empty:
            logger.warning("%s 無法取得季報資料。", ticker)
            return {"ticker": ticker, "warning": "⚠️ 無法取得季報資料。"}

        # yfinance quarterly_financials: 欄位為日期，列為項目
        # 取得最近兩年的季度資料（至少需要 5 季以取得 YoY 對比）
        columns = financials.columns.tolist()

        if len(columns) < 5:
            return {"ticker": ticker, "warning": "⚠️ 季報資料不足（需至少 5 季），無法進行 YoY 比較。"}

        # 最近一季 (index 0) vs 去年同期 (index 4)
        latest_col = columns[0]
        yoy_col = columns[4]

        def _get_gross_margin(col) -> Optional[float]:
            """從財報中計算毛利率 = Gross Profit / Total Revenue。"""
            try:
                gross_profit = financials.loc["Gross Profit", col]
                revenue = financials.loc["Total Revenue", col]
                if revenue and revenue != 0:
                    return round(float(gross_profit) / float(revenue) * 100, 2)
            except KeyError:
                pass
            return None

        current_margin = _get_gross_margin(latest_col)
        previous_margin = _get_gross_margin(yoy_col)

        if current_margin is None or previous_margin is None:
            return {
                "ticker": ticker,
                "warning": "⚠️ 無法從季報中擷取毛利率資料。",
            }

        change = round(current_margin - previous_margin, 2)

        result = {
            "ticker": ticker,
            "current_quarter": str(latest_col.date()) if hasattr(latest_col, "date") else str(latest_col),
            "yoy_quarter": str(yoy_col.date()) if hasattr(yoy_col, "date") else str(yoy_col),
            "current_margin": current_margin,
            "previous_margin": previous_margin,
            "change": change,
        }

        if change < 0:
            logger.warning(
                "%s 毛利率衰退：%.2f%% → 去年同期 %.2f%%（下降 %.2f 個百分點）",
                ticker, current_margin, previous_margin, abs(change),
            )
            result["warning"] = (
                f"🔴 毛利率衰退！{current_margin}% → 去年同期 {previous_margin}%"
                f"（下降 {abs(change)} 個百分點）— 護城河可能鬆動！"
            )
        else:
            logger.info(
                "%s 毛利率穩健：%.2f%% vs 去年同期 %.2f%%（+%.2f）",
                ticker, current_margin, previous_margin, change,
            )
            result["status"] = (
                f"🟢 毛利率穩健：{current_margin}% vs 去年同期 {previous_margin}%"
                f"（+{change} 個百分點）"
            )

        _moat_cache[ticker] = result
        return result

    except Exception as e:
        logger.error("無法檢查 %s 毛利率：%s", ticker, e, exc_info=True)
        return {"ticker": ticker, "warning": f"⚠️ 無法檢查 {ticker} 毛利率：{e}"}


# ---------------------------------------------------------------------------
# 掃描邏輯（依分類觸發不同檢查）
# ---------------------------------------------------------------------------

def scan_stock(ticker: str, category: str) -> list[str]:
    """
    依據股票分類執行對應的掃描邏輯，回傳警報清單。
    - Trend_Setter: RSI < 30 或跌破 200MA
    - Moat: 毛利 YoY 衰退
    - Growth: 跌破 60MA
    """
    logger.info("掃描 %s（分類：%s）...", ticker, category)
    alerts: list[str] = []

    if category == "Trend_Setter":
        signals = get_technical_signals(ticker)
        if signals and "error" not in signals:
            rsi = signals.get("rsi")
            price = signals.get("price")
            ma200 = signals.get("ma200")
            if rsi is not None and rsi < 30:
                alerts.append(f"📉 {ticker} RSI={rsi}，進入超賣區間（風向球機會訊號）")
            if ma200 is not None and price is not None and price < ma200:
                alerts.append(f"📉 {ticker} 股價 {price} 跌破 200MA ({ma200})（風向球警戒）")
        elif signals and "error" in signals:
            alerts.append(signals["error"])

    elif category == "Moat":
        moat = check_moat(ticker)
        if moat and "warning" in moat:
            alerts.append(moat["warning"])

    elif category == "Growth":
        signals = get_technical_signals(ticker)
        if signals and "error" not in signals:
            price = signals.get("price")
            ma60 = signals.get("ma60")
            if ma60 is not None and price is not None and price < ma60:
                alerts.append(f"📉 {ticker} 股價 {price} 跌破 60MA ({ma60})（成長動能消失）")
        elif signals and "error" in signals:
            alerts.append(signals["error"])

    return alerts
