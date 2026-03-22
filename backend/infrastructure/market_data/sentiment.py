"""
Infrastructure — 市場情緒指標適配器（VIX、恐懼貪婪指數、波動率）。

提供：
- VIX 恐慌指數
- CNN Fear & Greed Index（非官方 API）
- 自計算複合恐懼貪婪指數（7 項指標加權）
- 日本 Nikkei VI 波動率
- 台灣大盤 TWII 實現波動率

所有恐懼貪婪指數資料透過 L1 記憶體快取 + L2 磁碟快取雙層保護。
"""

from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from cachetools import TTLCache

from domain.analysis import (
    classify_cnn_fear_greed,
    classify_vix,
    compute_composite_fear_greed,
    compute_weighted_fear_greed,
    score_breadth,
    score_junk_bond_demand,
    score_momentum_composite,
    score_nikkei_vi_linear,
    score_price_strength,
    score_safe_haven,
    score_sector_rotation,
    score_tw_vol_linear,
    score_vix_linear,
)
from domain.constants import (
    CNN_FG_API_URL,
    CNN_FG_REQUEST_TIMEOUT,
    DISK_FEAR_GREED_TTL,
    DISK_KEY_FEAR_GREED,
    FEAR_GREED_CACHE_MAXSIZE,
    FEAR_GREED_CACHE_TTL,
    FG_COMPONENT_FAILURE_COOLDOWN_SECONDS,
    FG_HYG_TICKER,
    FG_LOOKBACK_DAYS,
    FG_MA_WINDOW,
    FG_QQQ_TICKER,
    FG_RSP_TICKER,
    FG_SPY_TICKER,
    FG_TLT_TICKER,
    FG_XLP_TICKER,
    NIKKEI_VI_TICKER,
    TWII_TICKER,
    VIX_HISTORY_PERIOD,
    VIX_TICKER,
)
from domain.enums import FearGreedLevel
from infrastructure.market_data._market_data_shared import (
    _cached_fetch,
    _clear_fg_component_failure,
    _get_session,
    _is_fg_component_in_cooldown,
    _is_transient_yf_error,
    _mark_fg_component_failure,
    _yf_history_short,
    _yf_retry,
)
from logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# L1 cache (in-memory)
# ---------------------------------------------------------------------------

_fear_greed_cache: TTLCache = TTLCache(
    maxsize=FEAR_GREED_CACHE_MAXSIZE, ttl=FEAR_GREED_CACHE_TTL
)


# ---------------------------------------------------------------------------
# VIX
# ---------------------------------------------------------------------------


def get_vix_data() -> dict:
    """從 yfinance 取得 VIX 指數資料。
    回傳 {"value": float, "change_1d": float, "level": str, "fetched_at": str}。
    失敗時回傳 {"value": None, "level": "N/A", ...}。
    """
    try:
        hist = _yf_history_short(VIX_TICKER, VIX_HISTORY_PERIOD)

        if hist is None or hist.empty:
            logger.warning("VIX 資料為空。")
            return {
                "value": None,
                "change_1d": None,
                "level": FearGreedLevel.NOT_AVAILABLE.value,
                "fetched_at": datetime.now(UTC).isoformat(),
            }

        closes = hist["Close"].dropna().tolist()
        if not closes:
            return {
                "value": None,
                "change_1d": None,
                "level": FearGreedLevel.NOT_AVAILABLE.value,
                "fetched_at": datetime.now(UTC).isoformat(),
            }

        current_vix = round(float(closes[-1]), 2)
        change_1d = (
            round(float(closes[-1] - closes[-2]), 2) if len(closes) >= 2 else None
        )
        vix_level = classify_vix(current_vix)

        logger.info(
            "VIX = %.2f（等級：%s，日變動：%s）",
            current_vix,
            vix_level.value,
            change_1d,
        )

        return {
            "value": current_vix,
            "change_1d": change_1d,
            "level": vix_level.value,
            "fetched_at": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        if _is_transient_yf_error(e):
            logger.info("取得 VIX 資料暫時失敗（非致命）：%s", e)
        else:
            logger.warning("取得 VIX 資料失敗（非致命）：%s", e, exc_info=True)
        return {
            "value": None,
            "change_1d": None,
            "level": FearGreedLevel.NOT_AVAILABLE.value,
            "fetched_at": datetime.now(UTC).isoformat(),
        }


# ---------------------------------------------------------------------------
# CNN Fear & Greed
# ---------------------------------------------------------------------------


def get_cnn_fear_greed() -> dict | None:
    """從 CNN Fear & Greed Index API 取得市場恐懼貪婪分數。
    回傳 {"score": int, "label": str, "level": str, "fetched_at": str} 或 None。
    此為非官方 API，失敗時靜默回傳 None（graceful degradation）。
    """
    try:
        session = _get_session()
        resp = session.get(CNN_FG_API_URL, timeout=CNN_FG_REQUEST_TIMEOUT)
        resp.raise_for_status()

        data = resp.json()
        fg_data = data.get("fear_and_greed", {})
        score_raw = fg_data.get("score")
        label = fg_data.get("rating", "")

        if score_raw is None:
            logger.warning("CNN Fear & Greed API 回傳無 score 欄位。")
            return None

        score = round(float(score_raw))
        level = classify_cnn_fear_greed(score)

        logger.info("CNN Fear & Greed = %d（%s，等級：%s）", score, label, level.value)

        return {
            "score": score,
            "label": label,
            "level": level.value,
            "fetched_at": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.warning("CNN Fear & Greed API 取得失敗（非致命）：%s", e)
        return None


# ---------------------------------------------------------------------------
# Fear & Greed composite (self-calculated from 7 components)
# ---------------------------------------------------------------------------


@_yf_retry
def _fetch_fg_component_history(ticker: str) -> list[float] | None:
    """Fetch recent close prices for a Fear & Greed component ticker."""
    hist = _yf_history_short(ticker, "3mo")
    if hist is None or hist.empty:
        raise OSError(f"FG component {ticker}: yfinance returned empty history")
    closes = hist["Close"].dropna().tolist()
    if not closes:
        raise OSError(f"FG component {ticker}: no usable close prices")
    return [float(c) for c in closes]


def _fetch_fg_component_history_safe(ticker: str) -> list[float] | None:
    """Wrapper that catches all errors from _fetch_fg_component_history."""
    if _is_fg_component_in_cooldown(ticker):
        logger.debug(
            "FG 組件 %s 於失敗冷卻期內，略過本次抓取（%ds）。",
            ticker,
            FG_COMPONENT_FAILURE_COOLDOWN_SECONDS,
        )
        return None
    try:
        prices = _fetch_fg_component_history(ticker)
        _clear_fg_component_failure(ticker)
        return prices
    except Exception as e:
        _mark_fg_component_failure(ticker)
        if _is_transient_yf_error(e):
            logger.info("FG 組件 %s 暫時性網路錯誤，將短暫降級：%s", ticker, e)
        else:
            logger.warning("FG 組件 %s 取得失敗（非致命）：%s", ticker, e)
        return None


def _fetch_fear_greed(_key: str) -> dict:
    """綜合 VIX、CNN Fear & Greed 及 7 項自計算指標（供 _cached_fetch 使用）。
    _key 固定為 "composite"。
    """
    _fg_tickers = [
        FG_SPY_TICKER,
        FG_TLT_TICKER,
        FG_HYG_TICKER,
        FG_RSP_TICKER,
        FG_QQQ_TICKER,
        FG_XLP_TICKER,
    ]

    with ThreadPoolExecutor(max_workers=8) as pool:
        vix_future = pool.submit(get_vix_data)
        cnn_future = pool.submit(get_cnn_fear_greed)
        etf_futures = {
            ticker: pool.submit(_fetch_fg_component_history_safe, ticker)
            for ticker in _fg_tickers
        }
        vix_data = vix_future.result()
        cnn_data = cnn_future.result()
        results = {ticker: f.result() for ticker, f in etf_futures.items()}

    vix_value = vix_data.get("value")
    cnn_score = cnn_data.get("score") if cnn_data else None

    spy_prices = results[FG_SPY_TICKER]
    tlt_prices = results[FG_TLT_TICKER]
    hyg_prices = results[FG_HYG_TICKER]
    rsp_prices = results[FG_RSP_TICKER]
    qqq_prices = results[FG_QQQ_TICKER]
    xlp_prices = results[FG_XLP_TICKER]

    comp_vix = score_vix_linear(vix_value) if vix_value is not None else None
    comp_price_strength = (
        score_price_strength(spy_prices, FG_LOOKBACK_DAYS) if spy_prices else None
    )
    comp_momentum = (
        score_momentum_composite(spy_prices, ma_window=FG_MA_WINDOW)
        if spy_prices
        else None
    )
    comp_breadth = (
        score_breadth(rsp_prices, spy_prices, FG_LOOKBACK_DAYS)
        if rsp_prices and spy_prices
        else None
    )
    comp_junk_bond = (
        score_junk_bond_demand(hyg_prices, tlt_prices, FG_LOOKBACK_DAYS)
        if hyg_prices and tlt_prices
        else None
    )
    comp_safe_haven = (
        score_safe_haven(tlt_prices, FG_LOOKBACK_DAYS) if tlt_prices else None
    )
    comp_sector = (
        score_sector_rotation(qqq_prices, xlp_prices, FG_LOOKBACK_DAYS)
        if qqq_prices and xlp_prices
        else None
    )

    components = {
        "price_strength": comp_price_strength,
        "vix": comp_vix,
        "momentum": comp_momentum,
        "breadth": comp_breadth,
        "junk_bond": comp_junk_bond,
        "safe_haven": comp_safe_haven,
        "sector_rotation": comp_sector,
    }

    _level, self_calculated_score_val = compute_weighted_fear_greed(components)
    self_calc = (
        self_calculated_score_val if _level != FearGreedLevel.NOT_AVAILABLE else None
    )

    level, composite_score = compute_composite_fear_greed(
        vix_value, cnn_score, self_calc
    )

    logger.info(
        "Fear & Greed — composite=%d（%s）cnn=%s self=%s vix=%s",
        composite_score,
        level.value,
        cnn_score,
        self_calc,
        vix_value,
    )

    return {
        "composite_score": composite_score,
        "composite_level": level.value,
        "self_calculated_score": self_calc,
        "components": components,
        "vix": vix_data,
        "cnn": cnn_data,
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def _is_fear_greed_error(result: dict) -> bool:
    """判斷 Fear & Greed 結果是否為失敗回應。"""
    return (
        isinstance(result, dict)
        and result.get("composite_level") == FearGreedLevel.NOT_AVAILABLE.value
    )


def get_fear_greed_index() -> dict:
    """取得恐懼與貪婪指數（VIX + CNN 綜合）。
    結果透過 L1 + L2 快取（L1: 30 分鐘，L2: 2 小時）。
    錯誤結果僅寫入 L1，不寫入 L2。
    """
    return _cached_fetch(
        _fear_greed_cache,
        "composite",
        DISK_KEY_FEAR_GREED,
        DISK_FEAR_GREED_TTL,
        _fetch_fear_greed,
        is_error=_is_fear_greed_error,
    )


# ---------------------------------------------------------------------------
# JP and TW volatility indices
# ---------------------------------------------------------------------------


def get_jp_volatility_index() -> dict | None:
    """Fetch Nikkei VI as JP market fear indicator.
    Returns {"value": float, "score": int, "level": str, "source": "Nikkei VI"} or None.
    """
    try:
        hist = _yf_history_short(NIKKEI_VI_TICKER, VIX_HISTORY_PERIOD)

        if hist is None or hist.empty:
            logger.warning("Nikkei VI 資料為空。")
            return None

        closes = hist["Close"].dropna().tolist()
        if not closes:
            return None

        current = float(closes[-1])
        score = score_nikkei_vi_linear(current)
        level = classify_cnn_fear_greed(score).value

        logger.info("Nikkei VI = %.2f（score=%d，等級：%s）", current, score, level)
        return {
            "value": round(current, 2),
            "score": score,
            "level": level,
            "source": "Nikkei VI",
        }

    except Exception as e:
        logger.warning("Nikkei VI 取得失敗：%s", e)
        return None


def get_tw_volatility_index() -> dict | None:
    """Calculate TW market fear indicator from ^TWII realized volatility.
    Returns {"value": float, "score": int, "level": str, "source": "TAIEX Realized Vol"} or None.
    """
    try:
        hist = _yf_history_short(TWII_TICKER, "1mo")

        if hist is None or hist.empty:
            logger.warning("TAIEX ^TWII 資料為空。")
            return None

        closes = hist["Close"].dropna()
        if len(closes) < 15:
            logger.warning("TAIEX ^TWII 資料不足（%d 筆），需至少 15 筆。", len(closes))
            return None

        returns = (closes / closes.shift(1)).apply(math.log).dropna()
        annualized_vol = float(returns.std() * math.sqrt(252) * 100)

        score = score_tw_vol_linear(annualized_vol)
        level = classify_cnn_fear_greed(score).value

        logger.info(
            "TAIEX realized vol = %.2f%%（score=%d，等級：%s，source=twii, market=TW）",
            annualized_vol,
            score,
            level,
        )
        return {
            "value": round(annualized_vol, 2),
            "score": score,
            "level": level,
            "source": "TAIEX Realized Vol",
        }

    except Exception as e:
        logger.warning("TAIEX realized vol 取得失敗：%s", e)
        return None
