"""
Application — Stock Service：股票 CRUD、匯入匯出、護城河查詢。
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlmodel import Session

from domain.analysis import determine_scan_signal
from domain.constants import (
    DEFAULT_IMPORT_CATEGORY,
    ENRICHED_CACHE_MAXSIZE,
    ENRICHED_CACHE_TTL,
    ENRICHED_PER_TICKER_TIMEOUT,
    ENRICHED_THREAD_POOL_SIZE,
    REMOVAL_REASON_UNKNOWN,
    SKIP_MOAT_CATEGORIES,
    SKIP_PRICE_FETCH_CATEGORIES,
)
from domain.entities import RemovalLog, Stock, ThesisLog
from domain.enums import CATEGORY_LABEL, ScanSignal, StockCategory
from i18n import get_user_language, t
from infrastructure import repositories as repo
from infrastructure.cache import SWRCache
from infrastructure.database import engine
from infrastructure.market_data import (
    analyze_moat_trend,
    detect_is_etf,
    get_bias_distribution,
    get_crypto_price,
    get_dividend_info,
    get_earnings_date,
    get_fear_greed_index,
    get_fundamentals,
    get_jp_volatility_index,
    get_technical_signals,
    get_ticker_sector_cached,
    get_tw_volatility_index,
)
from infrastructure.market_data import (
    get_price_history as _get_price_history,
)
from logging_config import get_logger

logger = get_logger(__name__)

_SKIP_DIVIDEND_CATEGORIES = {"Trend_Setter", "Growth", "Cash", "Mutual_Fund"}


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class StockNotFoundError(Exception):
    """股票不存在。"""


class StockAlreadyExistsError(Exception):
    """股票已存在。"""


class StockAlreadyInactiveError(Exception):
    """股票已是停用狀態。"""


class StockAlreadyActiveError(Exception):
    """股票已是啟用狀態。"""


class CategoryUnchangedError(Exception):
    """分類相同，無需變更。"""


# ---------------------------------------------------------------------------
# Tag 轉換工具
# ---------------------------------------------------------------------------


def _tags_to_str(tags: list[str]) -> str:
    """將標籤列表轉為逗號分隔字串存入 DB。"""
    return ",".join(tag.strip() for tag in tags if tag.strip())


def _str_to_tags(s: str) -> list[str]:
    """將 DB 中的逗號分隔字串轉為標籤列表。"""
    return [tag.strip() for tag in s.split(",") if tag.strip()] if s else []


# ---------------------------------------------------------------------------
# 共用內部工具
# ---------------------------------------------------------------------------


def _get_stock_or_raise(session: Session, ticker: str) -> Stock:
    """查詢股票，不存在時拋出 StockNotFoundError。"""
    upper = ticker.upper()
    stock = repo.find_stock_by_ticker(session, upper)
    if not stock:
        lang = get_user_language(session)
        raise StockNotFoundError(t("stock.not_found", lang=lang, ticker=upper))
    return stock


def _append_thesis_log(
    session: Session,
    ticker: str,
    content: str,
    tags: str = "",
) -> ThesisLog:
    """建立新版觀點紀錄（自動遞增版本號）。"""
    max_version = repo.get_max_thesis_version(session, ticker)
    log = ThesisLog(
        stock_ticker=ticker,
        content=content,
        tags=tags,
        version=max_version + 1,
    )
    repo.create_thesis_log(session, log)
    return log


def _is_eligible_mutual_fund(session: Session, ticker: str) -> bool:
    """Return True if ticker is an active eligible mutual fund."""
    return repo.is_active_eligible_mutual_fund(session, ticker)


def reclassify_mutual_fund_stocks(
    session: Session,
    *,
    autocommit: bool = True,
) -> int:
    """Reclassify active stocks to Mutual_Fund when eligible master indicates so."""
    stocks = repo.find_active_stocks(session)
    updated = 0
    for stock in stocks:
        if stock.category == StockCategory.MUTUAL_FUND:
            continue
        if not _is_eligible_mutual_fund(session, stock.ticker):
            continue
        stock.category = StockCategory.MUTUAL_FUND
        stock.is_etf = False
        repo.update_stock(session, stock)
        updated += 1
    if updated:
        if autocommit:
            session.commit()
        else:
            session.flush()
    return updated


# ---------------------------------------------------------------------------
# Stock CRUD
# ---------------------------------------------------------------------------


def create_stock(
    session: Session,
    ticker: str,
    category: StockCategory,
    thesis: str,
    tags: list[str] | None = None,
    is_etf: bool | None = None,
    coingecko_id: str | None = None,
) -> Stock:
    """
    新增股票到追蹤清單，同時建立第一筆觀點紀錄。
    is_etf=None 時自動透過 yfinance 偵測。
    """
    ticker_upper = ticker.upper()
    tags = tags or []
    tags_str = _tags_to_str(tags)
    lang = get_user_language(session)
    logger.info(
        "新增股票：%s（分類：%s，標籤：%s）", ticker_upper, category.value, tags
    )

    existing = repo.find_stock_by_ticker(session, ticker_upper)
    if existing:
        raise StockAlreadyExistsError(
            t("stock.already_exists", lang=lang, ticker=ticker_upper)
        )

    if is_etf is None:
        if category == StockCategory.MUTUAL_FUND:
            is_etf = False
        else:
            is_etf = detect_is_etf(ticker_upper)

    stock = Stock(
        ticker=ticker_upper,
        category=category,
        coingecko_id=coingecko_id.strip().lower() if coingecko_id else None,
        current_thesis=thesis,
        current_tags=tags_str,
        is_active=True,
        is_etf=is_etf,
    )
    session.add(stock)

    thesis_log = ThesisLog(
        stock_ticker=ticker_upper,
        content=thesis,
        tags=tags_str,
        version=1,
    )
    repo.create_thesis_log(session, thesis_log)

    session.commit()
    session.refresh(stock)

    logger.info("股票 %s 已成功新增至追蹤清單。", ticker_upper)
    return stock


def ensure_stock_on_radar(
    session: Session,
    ticker: str,
    thesis: str | None = None,
    category: StockCategory | str | None = None,
) -> tuple[Stock, bool]:
    """
    Ensure ticker exists in radar stock list without committing.

    Returns (stock, created):
    - created=False when stock already exists
    - created=True when a new stock + initial thesis log are added to session
    """
    ticker_upper = ticker.upper()
    resolved_category: StockCategory | None = None
    if category is not None:
        if isinstance(category, StockCategory):
            resolved_category = category
        else:
            normalized_category = category.strip()
            if not normalized_category:
                raise ValueError("category must not be empty")
            resolved_category = StockCategory(normalized_category)

    eligible_mutual_fund = _is_eligible_mutual_fund(session, ticker_upper)
    existing = repo.find_stock_by_ticker(session, ticker_upper)
    if existing:
        if existing.is_active:
            if (
                resolved_category is None
                and eligible_mutual_fund
                and existing.category != StockCategory.MUTUAL_FUND
            ):
                existing.category = StockCategory.MUTUAL_FUND
                existing.is_etf = False
                repo.update_stock(session, existing)
                return existing, False
            if (
                existing.category != StockCategory.MUTUAL_FUND
                and not bool(existing.is_etf)
                and detect_is_etf(ticker_upper)
            ):
                existing.is_etf = True
                repo.update_stock(session, existing)
            return existing, False

        has_custom_thesis = bool(thesis and thesis.strip())
        final_thesis = thesis.strip() if has_custom_thesis and thesis else ""
        existing.is_active = True
        if resolved_category is None and eligible_mutual_fund:
            resolved_category = StockCategory.MUTUAL_FUND
        if resolved_category is not None:
            existing.category = resolved_category
        if has_custom_thesis:
            existing.current_thesis = final_thesis
            existing.current_tags = ""
        existing.last_scan_signal = ScanSignal.NORMAL.value
        existing.signal_since = None
        if existing.category == StockCategory.MUTUAL_FUND:
            existing.is_etf = False
        elif not bool(existing.is_etf) and detect_is_etf(ticker_upper):
            existing.is_etf = True
        repo.update_stock(session, existing)
        if has_custom_thesis:
            _append_thesis_log(session, ticker_upper, final_thesis, tags="")
        else:
            _append_thesis_log(
                session,
                ticker_upper,
                t("stock.reactivated_log", lang="zh-TW"),
                tags=existing.current_tags,
            )
        return existing, True

    if resolved_category == StockCategory.MUTUAL_FUND:
        is_etf = False
    elif resolved_category is None and eligible_mutual_fund:
        resolved_category = StockCategory.MUTUAL_FUND
        is_etf = False
    else:
        is_etf = detect_is_etf(ticker_upper)
    if resolved_category is None:
        if is_etf:
            resolved_category = StockCategory.TREND_SETTER
        else:
            resolved_category = StockCategory.GROWTH
    lang = get_user_language(session)
    final_thesis = (
        thesis.strip()
        if thesis and thesis.strip()
        else t("stock.auto_thesis", lang=lang)
    )

    stock = Stock(
        ticker=ticker_upper,
        category=resolved_category,
        current_thesis=final_thesis,
        current_tags="",
        is_active=True,
        is_etf=is_etf,
    )
    session.add(stock)

    thesis_log = ThesisLog(
        stock_ticker=ticker_upper,
        content=final_thesis,
        tags="",
        version=1,
    )
    repo.create_thesis_log(session, thesis_log)
    return stock, True


def list_active_stocks(session: Session) -> list[dict]:
    """取得所有啟用中的追蹤股票（僅 DB 資料，不含技術訊號）。"""
    logger.info("取得所有追蹤股票清單...")
    stocks = repo.find_active_stocks(session)
    logger.info("共 %d 檔追蹤中股票。", len(stocks))

    return [
        {
            "ticker": stock.ticker,
            "category": stock.category,
            "current_thesis": stock.current_thesis,
            "current_tags": _str_to_tags(stock.current_tags),
            "display_order": stock.display_order,
            "last_scan_signal": stock.last_scan_signal,
            "signal_since": stock.signal_since.isoformat()
            if stock.signal_since
            else None,
            "is_active": stock.is_active,
            "is_etf": stock.is_etf,
        }
        for stock in stocks
    ]


def update_stock_category(
    session: Session, ticker: str, new_category: StockCategory
) -> dict:
    """
    切換股票分類，並在觀點歷史中記錄變更。
    """
    stock = _get_stock_or_raise(session, ticker)
    ticker_upper = stock.ticker
    lang = get_user_language(session)
    logger.info("分類變更請求：%s → %s", ticker_upper, new_category.value)

    old_category = stock.category
    if old_category == new_category:
        old_label = CATEGORY_LABEL.get(old_category.value, old_category.value)
        raise CategoryUnchangedError(
            t(
                "stock.category_unchanged",
                lang=lang,
                ticker=ticker_upper,
                category=old_label,
            )
        )

    stock.category = new_category
    repo.update_stock(session, stock)

    old_label = CATEGORY_LABEL.get(old_category.value, old_category.value)
    new_label = CATEGORY_LABEL.get(new_category.value, new_category.value)
    change_log = t(
        "stock.category_change_log", lang="zh-TW", old=old_label, new=new_label
    )
    _append_thesis_log(session, ticker_upper, change_log)

    session.commit()
    logger.info("股票 %s 分類已從 %s 變更為 %s。", ticker_upper, old_label, new_label)

    return {
        "message": t(
            "stock.category_changed",
            lang=lang,
            ticker=ticker_upper,
            old=old_label,
            new=new_label,
        ),
        "old_category": old_category.value,
        "new_category": new_category.value,
    }


def deactivate_stock(session: Session, ticker: str, reason: str) -> dict:
    """
    移除追蹤股票，記錄移除原因與觀點版控。
    """
    stock = _get_stock_or_raise(session, ticker)
    ticker_upper = stock.ticker
    lang = get_user_language(session)
    logger.info("移除追蹤：%s", ticker_upper)

    if not stock.is_active:
        raise StockAlreadyInactiveError(
            t("stock.already_inactive", lang=lang, ticker=ticker_upper)
        )

    stock.is_active = False
    repo.update_stock(session, stock)

    removal_log = RemovalLog(stock_ticker=ticker_upper, reason=reason)
    repo.create_removal_log(session, removal_log)

    removal_thesis_log = t("stock.removed_log", lang="zh-TW", reason=reason)
    _append_thesis_log(session, ticker_upper, removal_thesis_log)

    session.commit()
    logger.info("股票 %s 已移除追蹤（原因：%s）。", ticker_upper, reason)

    return {
        "message": t("stock.removed", lang=lang, ticker=ticker_upper),
        "reason": reason,
    }


def reactivate_stock(
    session: Session,
    ticker: str,
    category: StockCategory | None = None,
    thesis: str | None = None,
) -> dict:
    """
    重新啟用已移除的股票。可選擇性更新分類與觀點。
    """
    stock = _get_stock_or_raise(session, ticker)
    ticker_upper = stock.ticker
    lang = get_user_language(session)
    logger.info("重新啟用追蹤：%s", ticker_upper)

    if stock.is_active:
        raise StockAlreadyActiveError(
            t("stock.already_active", lang=lang, ticker=ticker_upper)
        )

    stock.is_active = True
    stock.last_scan_signal = ScanSignal.NORMAL.value
    if category:
        stock.category = category
    repo.update_stock(session, stock)

    reactivate_log = thesis or t("stock.reactivated_log", lang="zh-TW")
    _append_thesis_log(session, ticker_upper, reactivate_log)

    if thesis:
        stock.current_thesis = thesis
        repo.update_stock(session, stock)

    session.commit()
    logger.info("股票 %s 已重新啟用追蹤。", ticker_upper)

    return {"message": t("stock.reactivated", lang=lang, ticker=ticker_upper)}


def export_stocks(session: Session) -> list[dict]:
    """匯出所有啟用中股票（精簡格式，適用於 JSON 下載與匯入）。"""
    logger.info("匯出所有追蹤股票...")
    stocks = repo.find_active_stocks(session)
    return [
        {
            "ticker": stock.ticker,
            "category": stock.category.value,
            "thesis": stock.current_thesis,
            "tags": _str_to_tags(stock.current_tags),
            "is_etf": stock.is_etf,
        }
        for stock in stocks
    ]


def update_display_order(session: Session, ordered_tickers: list[str]) -> dict:
    """批次更新股票顯示順位（委託 Repository 執行）。"""
    lang = get_user_language(session)
    logger.info("更新顯示順位，共 %d 檔股票。", len(ordered_tickers))
    upper_tickers = [tk.upper() for tk in ordered_tickers]
    repo.bulk_update_display_order(session, upper_tickers)
    return {
        "message": t(
            "stock.display_order_updated", lang=lang, count=len(ordered_tickers)
        )
    }


def list_removed_stocks(session: Session) -> list[dict]:
    """取得所有已移除的股票，含最新移除原因（批次查詢，避免 N+1）。"""
    logger.info("取得已移除股票清單...")
    stocks = repo.find_inactive_stocks(session)

    # 一次性取得所有已移除股票的最新移除紀錄
    tickers = [s.ticker for s in stocks]
    removal_map = repo.find_latest_removals_batch(session, tickers)

    results: list[dict] = []
    for stock in stocks:
        latest_removal = removal_map.get(stock.ticker)
        results.append(
            {
                "ticker": stock.ticker,
                "category": stock.category,
                "current_thesis": stock.current_thesis,
                "removal_reason": latest_removal.reason
                if latest_removal
                else t(REMOVAL_REASON_UNKNOWN, lang=get_user_language(session)),
                "removed_at": (
                    latest_removal.created_at.isoformat()
                    if latest_removal and latest_removal.created_at
                    else None
                ),
            }
        )

    logger.info("共 %d 檔已移除股票。", len(results))
    return results


def get_removal_history(session: Session, ticker: str) -> list[dict]:
    """取得指定股票的完整移除紀錄歷史。"""
    stock = _get_stock_or_raise(session, ticker)
    logs = repo.find_removal_history(session, stock.ticker)
    return [
        {
            "reason": log.reason,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ---------------------------------------------------------------------------
# Thesis Service
# ---------------------------------------------------------------------------


def add_thesis(
    session: Session,
    ticker: str,
    content: str,
    tags: list[str] | None = None,
) -> dict:
    """為指定股票新增觀點，自動遞增版本號。"""
    stock = _get_stock_or_raise(session, ticker)
    ticker_upper = stock.ticker
    tags = tags or []
    tags_str = _tags_to_str(tags)
    lang = get_user_language(session)
    logger.info("更新觀點：%s（標籤：%s）", ticker_upper, tags)

    thesis_log = _append_thesis_log(session, ticker_upper, content, tags_str)
    new_version = thesis_log.version

    stock.current_thesis = content
    stock.current_tags = tags_str
    repo.update_stock(session, stock)
    session.commit()

    logger.info("股票 %s 觀點已更新至第 %d 版。", ticker_upper, new_version)

    return {
        "message": t(
            "stock.thesis_updated", lang=lang, ticker=ticker_upper, version=new_version
        ),
        "version": new_version,
        "content": content,
        "tags": tags,
    }


def get_thesis_history(session: Session, ticker: str) -> list[dict]:
    """取得指定股票的完整觀點版控歷史。"""
    stock = _get_stock_or_raise(session, ticker)
    logs = repo.find_thesis_history(session, stock.ticker)
    return [
        {
            "version": log.version,
            "content": log.content,
            "tags": _str_to_tags(log.tags),
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ---------------------------------------------------------------------------
# Import Service
# ---------------------------------------------------------------------------


def import_stocks(session: Session, stock_list: list[dict]) -> dict:
    """
    批次匯入股票（upsert 邏輯）。
    新股票建立，已存在的更新觀點與標籤。
    """
    lang = get_user_language(session)
    logger.info("批次匯入 %d 筆股票...", len(stock_list))
    created = 0
    updated = 0
    errors: list[str] = []

    for item in stock_list:
        ticker = item.get("ticker", "").strip().upper()
        category_str = item.get("category", DEFAULT_IMPORT_CATEGORY)
        thesis = item.get("thesis", "") or item.get("initial_thesis", "")
        tags = item.get("tags", [])

        if not ticker:
            errors.append(t("stock.import_missing_ticker", lang=lang))
            continue

        try:
            category = StockCategory(category_str)
        except ValueError:
            errors.append(
                t(
                    "stock.import_invalid_category",
                    lang=lang,
                    ticker=ticker,
                    category=category_str,
                )
            )
            continue

        existing = repo.find_stock_by_ticker(session, ticker)
        tags_str = _tags_to_str(tags)

        if existing:
            # Upsert: 更新觀點與標籤
            if thesis:
                _append_thesis_log(session, ticker, thesis, tags_str)
                existing.current_thesis = thesis
            if tags:
                existing.current_tags = tags_str
            existing.category = category
            # 更新 is_etf（如有提供）
            imported_is_etf = item.get("is_etf")
            if imported_is_etf is not None:
                existing.is_etf = bool(imported_is_etf)
            repo.update_stock(session, existing)
            updated += 1
        else:
            # 新增：auto-detect ETF if not specified
            imported_is_etf = item.get("is_etf")
            if imported_is_etf is None:
                if category == StockCategory.MUTUAL_FUND:
                    imported_is_etf = False
                else:
                    imported_is_etf = detect_is_etf(ticker)
            stock = Stock(
                ticker=ticker,
                category=category,
                current_thesis=thesis,
                current_tags=tags_str,
                is_active=True,
                is_etf=bool(imported_is_etf),
            )
            session.add(stock)
            thesis_log = ThesisLog(
                stock_ticker=ticker,
                content=thesis,
                tags=tags_str,
                version=1,
            )
            repo.create_thesis_log(session, thesis_log)
            created += 1

    session.commit()
    logger.info("匯入完成：新增 %d，更新 %d，錯誤 %d。", created, updated, len(errors))

    return {
        "message": t(
            "stock.import_complete",
            lang=lang,
            created=created,
            updated=updated,
            errors=len(errors),
        ),
        "created": created,
        "updated": updated,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Moat Service（Bond / Cash 不適用）
# ---------------------------------------------------------------------------


def get_moat_for_ticker(session: Session, ticker: str) -> dict:
    """取得指定股票的護城河趨勢。Bond / Cash 類別直接回傳 N/A。"""
    upper_ticker = ticker.upper()
    stock = repo.find_stock_by_ticker(session, upper_ticker)
    if stock and stock.category.value in SKIP_MOAT_CATEGORIES:
        lang = get_user_language(session)
        return {
            "ticker": upper_ticker,
            "moat": "N/A",
            "details": t(
                "stock.moat_not_applicable", lang=lang, category=stock.category.value
            ),
        }
    return analyze_moat_trend(upper_ticker)


# ---------------------------------------------------------------------------
# Batch Enriched Stocks（一次回傳所有股票 + 訊號 / 財報 / 股息）
# ---------------------------------------------------------------------------

# SWR 快取：fresh 視窗後仍可短暫回傳 stale 資料，避免使用者遇到冷啟動等待。
_ENRICHED_STALE_TTL = ENRICHED_CACHE_TTL * 3
_enriched_cache: SWRCache[str, list[dict]] = SWRCache(
    maxsize=ENRICHED_CACHE_MAXSIZE,
    fresh_ttl=ENRICHED_CACHE_TTL,
    stale_ttl=_ENRICHED_STALE_TTL,
)
_enriched_cache_lock = threading.Lock()
# 防止 thundering herd：快取未命中時，後續並行請求等待第一個請求完成後共享結果。
_enriched_in_progress: threading.Event | None = None


def invalidate_enriched_cache() -> None:
    """主動清除豐富資料快取（股票新增 / 移除 / 停用後呼叫）。"""
    global _enriched_in_progress
    with _enriched_cache_lock:
        _enriched_cache.clear()
        if _enriched_in_progress is not None:
            _enriched_in_progress.set()
        _enriched_in_progress = None


def get_enriched_stocks(session: Session, force_refresh: bool = False) -> list[dict]:
    """
    取得所有啟用中股票，並行附加技術訊號、最近財報日與股息資訊。
    前端可一次取得所有資料，避免逐卡 N+1 API 呼叫。
    結果透過 SWR 快取，在 fresh/stale 視窗內重複請求可快速回應；
    stale 狀態會背景 revalidate。force_refresh=True 可強制同步重算。
    並行 cache miss/force refresh 時，後續請求等待第一個計算完成，避免 thundering herd。
    """
    global _enriched_in_progress
    _cache_key = "enriched"

    while True:
        with _enriched_cache_lock:
            refresh_fn = None if force_refresh else _refresh_enriched_cache_background
            cached, cache_state = _enriched_cache.get(_cache_key, refresh_fn=refresh_fn)
            if cached is not None and not force_refresh:
                logger.debug("豐富資料快取命中（%s）", cache_state)
                return cached

            # First request after a miss: set an in-progress event; others will wait
            if _enriched_in_progress is None:
                _enriched_in_progress = threading.Event()
                event_owner = True
            else:
                event_to_wait = _enriched_in_progress
                event_owner = False

        if not event_owner:
            # Another thread is computing — wait for it, then re-check cache
            logger.debug("等待豐富資料計算完成...")
            event_to_wait.wait(timeout=120)
            continue  # re-enter loop to read from cache

        # This thread owns the computation
        break

    try:
        stocks = repo.find_active_stocks(session)
    except Exception:
        # Ensure waiters are unblocked even on DB error
        with _enriched_cache_lock:
            _enriched_in_progress = None
        raise

    if not stocks:
        with _enriched_cache_lock:
            _enriched_in_progress = None
        return []

    # try/finally ensures waiters are always unblocked, even on unexpected errors.
    try:
        result = _compute_enriched_stocks(stocks)
    except Exception:
        with _enriched_cache_lock:
            if _enriched_in_progress is not None:
                _enriched_in_progress.set()
            _enriched_in_progress = None
        raise

    with _enriched_cache_lock:
        _enriched_cache.set(_cache_key, result)
        if _enriched_in_progress is not None:
            _enriched_in_progress.set()
        _enriched_in_progress = None
    return result


def _refresh_enriched_cache_background() -> list[dict]:
    """Background revalidate path for stale enriched cache entries."""
    with Session(engine) as bg_session:
        stocks = repo.find_active_stocks(bg_session)
        if not stocks:
            return []
        return _compute_enriched_stocks(stocks)


def build_nav_signals(nav_row: object, *, include_nav_date: bool = False) -> dict:
    """Convert a MutualFundNav row into an enrichment-compatible signals dict.

    Shared by stock_service (enrichment pipeline) and scan_service (scan loop).
    """
    prev = nav_row.nav_previous  # type: ignore[attr-defined]
    change_pct = ((nav_row.nav - prev) / prev * 100) if prev else None  # type: ignore[attr-defined]
    result: dict = {
        "price": nav_row.nav,  # type: ignore[attr-defined]
        "previous_close": prev,
        "change_pct": change_pct,
        "rsi": None,
        "bias": None,
        "bias_200": None,
        "volume_ratio": None,
    }
    if include_nav_date:
        result["nav_date"] = str(nav_row.nav_date)  # type: ignore[attr-defined]
    return result


def _compute_enriched_stocks(stocks: list[Stock]) -> list[dict]:
    """Inner computation: fetch signals/earnings/dividends for all stocks in parallel."""
    logger.info("批次取得 %d 檔股票的豐富資料...", len(stocks))

    # Pre-fetch NAV data for Mutual_Fund stocks (single DB read, not per-thread)
    nav_cache: dict[str, dict] = {}
    mf_tickers = [
        s.ticker
        for s in stocks
        if (s.category.value if hasattr(s.category, "value") else str(s.category))
        == StockCategory.MUTUAL_FUND.value
    ]
    if mf_tickers:
        with Session(engine) as nav_session:
            for ticker in mf_tickers:
                nav_row = repo.get_latest_nav(nav_session, ticker)
                if nav_row:
                    nav_cache[ticker] = build_nav_signals(
                        nav_row, include_nav_date=True
                    )

    # 建立基礎資料；sector 從磁碟快取讀取（非阻塞，30 天 TTL）
    enriched: dict[str, dict] = {}
    for stock in stocks:
        enriched[stock.ticker] = {
            "ticker": stock.ticker,
            "category": stock.category.value
            if hasattr(stock.category, "value")
            else str(stock.category),
            "current_thesis": stock.current_thesis,
            "current_tags": _str_to_tags(stock.current_tags),
            "display_order": stock.display_order,
            "last_scan_signal": stock.last_scan_signal,
            "is_active": stock.is_active,
            "is_etf": stock.is_etf,
            "sector": get_ticker_sector_cached(stock.ticker),
            "signals": None,
            "earnings": None,
            "dividend": None,
            "fundamentals": None,
            "computed_signal": None,
            "price": None,
            "change_pct": None,
            "rsi": None,
            "market_cap": None,
            "trailing_pe": None,
            "nav_date": None,
        }

    def _fetch_enrichment(
        ticker: str, cat_value: str, coingecko_id: str | None
    ) -> tuple[str, dict | None, dict | None, dict | None, dict | None]:
        """並行取得單一股票的附加資料。"""
        signals = None
        earnings = None
        dividend = None
        fundamentals = None

        if cat_value == StockCategory.CRYPTO.value:
            crypto_data = get_crypto_price(coingecko_id, ticker)
            price = (
                crypto_data.get("price_usd")
                if crypto_data
                and isinstance(crypto_data.get("price_usd"), (int, float))
                else None
            )
            change_pct = (
                crypto_data.get("change_24h_pct")
                if crypto_data
                and isinstance(crypto_data.get("change_24h_pct"), (int, float))
                else None
            )
            signals = {
                "price": price,
                "change_pct": change_pct,
                "rsi": None,
                "bias": None,
                "bias_200": None,
                "volume_ratio": None,
            }
        elif cat_value == StockCategory.MUTUAL_FUND.value:
            signals = nav_cache.get(ticker)
        elif cat_value not in SKIP_PRICE_FETCH_CATEGORIES:
            signals = get_technical_signals(ticker)

        if cat_value not in SKIP_PRICE_FETCH_CATEGORIES:
            try:
                earnings = get_earnings_date(ticker)
            except Exception:
                earnings = None

        if cat_value not in _SKIP_DIVIDEND_CATEGORIES:
            try:
                dividend = get_dividend_info(ticker)
            except Exception:
                dividend = None

        if cat_value not in SKIP_PRICE_FETCH_CATEGORIES:
            try:
                fundamentals = get_fundamentals(ticker)
            except Exception:
                fundamentals = None

        return ticker, signals, earnings, dividend, fundamentals

    # 並行取得所有附加資料（使用較大執行緒池 + 單檔超時保護）
    with ThreadPoolExecutor(max_workers=ENRICHED_THREAD_POOL_SIZE) as executor:
        futures = {
            executor.submit(
                _fetch_enrichment,
                stock.ticker,
                stock.category.value
                if hasattr(stock.category, "value")
                else str(stock.category),
                stock.coingecko_id,
            ): stock.ticker
            for stock in stocks
        }
        for future in as_completed(futures):
            tk = futures[future]
            try:
                ticker, signals, earnings, dividend, fundamentals = future.result(
                    timeout=ENRICHED_PER_TICKER_TIMEOUT
                )
                if ticker in enriched:
                    enriched[ticker]["signals"] = signals
                    enriched[ticker]["earnings"] = earnings
                    enriched[ticker]["dividend"] = dividend
                    enriched[ticker]["fundamentals"] = fundamentals
                    # Surface key metrics at top level for heat map / dashboard use
                    enriched[ticker]["price"] = (signals or {}).get("price")
                    enriched[ticker]["change_pct"] = (signals or {}).get("change_pct")
                    enriched[ticker]["rsi"] = (signals or {}).get("rsi")
                    enriched[ticker]["nav_date"] = (signals or {}).get("nav_date")
                    # Hybrid loading: quick-scan metrics also exposed at top-level.
                    enriched[ticker]["market_cap"] = (fundamentals or {}).get(
                        "market_cap"
                    )
                    enriched[ticker]["trailing_pe"] = (fundamentals or {}).get(
                        "trailing_pe"
                    )
                    # Compute real-time signal from live RSI/bias (skip moat — too expensive here)
                    persisted_signal = enriched[ticker].get(
                        "last_scan_signal", "NORMAL"
                    )
                    if persisted_signal != "THESIS_BROKEN":
                        rsi = (signals or {}).get("rsi")
                        bias = (signals or {}).get("bias")
                        volume_ratio = (signals or {}).get("volume_ratio")
                        computed = determine_scan_signal(
                            moat="NOT_AVAILABLE",
                            rsi=rsi,
                            bias=bias,
                            volume_ratio=volume_ratio,
                        )
                        enriched[ticker]["computed_signal"] = computed.value
                    else:
                        enriched[ticker]["computed_signal"] = "THESIS_BROKEN"
            except TimeoutError:
                logger.warning(
                    "批次取得 %s 豐富資料超時（%ds），跳過。",
                    tk,
                    ENRICHED_PER_TICKER_TIMEOUT,
                )
            except Exception as exc:
                logger.error("批次取得 %s 豐富資料失敗：%s", tk, exc, exc_info=True)

    logger.info("批次豐富資料取得完成。")
    return list(enriched.values())


# ---------------------------------------------------------------------------
# Market Data Wrappers
# ---------------------------------------------------------------------------


def get_signals_for_ticker(session: Session, ticker: str) -> dict | None:
    """Category-aware signals routing — single entry point for all callers.

    Mutual_Fund -> NAV from DB; SKIP categories -> empty; others -> yfinance.
    """
    upper = ticker.upper()
    cat = _resolve_stock_category(session, upper)
    if cat == StockCategory.MUTUAL_FUND.value:
        nav_row = repo.get_latest_nav(session, upper)
        return build_nav_signals(nav_row) if nav_row else {}
    if cat and cat in SKIP_PRICE_FETCH_CATEGORIES:
        return {}
    signals = get_technical_signals(upper)
    if signals:
        signals["bias_distribution"] = get_bias_distribution(upper)
    return signals


def get_price_history_for_ticker(session: Session, ticker: str) -> list[dict]:
    """Resolve category once and return the appropriate price history."""
    upper = ticker.upper()
    cat = _resolve_stock_category(session, upper)
    if cat == StockCategory.MUTUAL_FUND.value:
        rows = repo.get_nav_history(session, upper)
        return [{"date": str(r.nav_date), "close": r.nav} for r in reversed(rows)]
    if cat and cat in SKIP_PRICE_FETCH_CATEGORIES:
        return []
    return _get_price_history(upper) or []


def _resolve_stock_category(session: Session, ticker: str) -> str | None:
    """Look up a stock's category from Stock table, falling back to Holding table."""
    upper = ticker.upper()
    stock = repo.find_stock_by_ticker(session, upper)
    if stock:
        return (
            stock.category.value
            if hasattr(stock.category, "value")
            else str(stock.category)
        )
    holding = repo.find_holding_by_ticker(session, upper)
    if holding:
        return (
            holding.category.value
            if hasattr(holding.category, "value")
            else str(holding.category)
        )
    return None


def get_earnings_for_ticker(session: Session, ticker: str) -> dict | None:
    """Category-aware earnings fetch. Returns None for non-yfinance categories."""
    cat = _resolve_stock_category(session, ticker)
    if cat and cat in SKIP_PRICE_FETCH_CATEGORIES:
        return None
    return get_earnings_date(ticker.upper())


def get_dividend_for_ticker(session: Session, ticker: str) -> dict | None:
    """Category-aware dividend fetch. Returns None for non-yfinance categories."""
    cat = _resolve_stock_category(session, ticker)
    if cat and cat in _SKIP_DIVIDEND_CATEGORIES:
        return None
    return get_dividend_info(ticker.upper())


def get_fundamentals_for_ticker(session: Session, ticker: str) -> dict:
    """Category-aware fundamentals fetch. Returns ticker-only dict for non-yfinance categories."""
    cat = _resolve_stock_category(session, ticker)
    if cat and cat in SKIP_PRICE_FETCH_CATEGORIES:
        return {"ticker": ticker.upper()}
    return get_fundamentals(ticker.upper())


def get_market_sentiment_multi(session: Session) -> dict:
    """Return sentiment for each market the user has stocks in."""
    result: dict = {"US": get_fear_greed_index()}

    stocks = repo.find_active_stocks(session)

    # Check if user has JP stocks
    has_jp = any(s.ticker.endswith(".T") for s in stocks)
    if has_jp:
        result["JP"] = get_jp_volatility_index()

    # Check if user has TW stocks
    has_tw = any(s.ticker.endswith(".TW") for s in stocks)
    if has_tw:
        result["TW"] = get_tw_volatility_index()

    return result
