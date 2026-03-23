"""
Application — Stock Service：股票 CRUD、匯入匯出、觀點管理。
"""

from sqlmodel import Session

from domain.constants import (
    DEFAULT_IMPORT_CATEGORY,
    REMOVAL_REASON_UNKNOWN,
)
from domain.entities import RemovalLog, Stock, ThesisLog
from domain.enums import CATEGORY_LABEL, ScanSignal, StockCategory
from i18n import get_user_language, t
from infrastructure import repositories as repo
from infrastructure.market_data import detect_is_etf
from logging_config import get_logger

logger = get_logger(__name__)


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
    tickers = [stock.ticker for stock in stocks]
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
            if thesis:
                _append_thesis_log(session, ticker, thesis, tags_str)
                existing.current_thesis = thesis
            if tags:
                existing.current_tags = tags_str
            existing.category = category
            imported_is_etf = item.get("is_etf")
            if imported_is_etf is not None:
                existing.is_etf = bool(imported_is_etf)
            repo.update_stock(session, existing)
            updated += 1
        else:
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
# Backward-compat re-exports from extracted submodules
# ---------------------------------------------------------------------------
from application.stock.stock_enrichment_service import (  # noqa: E402, F401
    build_nav_signals,
    clear_market_data_caches,
    get_dividend_for_ticker,
    get_earnings_for_ticker,
    get_enriched_signals_for_ticker,
    get_enriched_stocks,
    get_fundamentals_for_ticker,
    get_market_sentiment_multi,
    get_moat_for_ticker,
    get_price_history_for_ticker,
    get_signals_for_ticker,
    invalidate_enriched_cache,
)
from application.stock.stock_thesis_service import (  # noqa: E402, F401
    add_thesis,
    get_thesis_history,
)
