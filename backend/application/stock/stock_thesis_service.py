"""Application — Thesis management for watchlist stocks.

Provides versioned, append-only investment thesis tracking:
add a thesis entry, read history.
"""

from sqlmodel import Session

from i18n import get_user_language, t
from infrastructure import repositories as repo
from logging_config import get_logger

logger = get_logger(__name__)


def add_thesis(
    session: Session,
    ticker: str,
    content: str,
    tags: list[str] | None = None,
) -> dict:
    """為指定股票新增觀點，自動遞增版本號。"""
    from application.stock.stock_service import (
        _append_thesis_log,
        _get_stock_or_raise,
        _tags_to_str,
    )

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
    from application.stock.stock_service import _get_stock_or_raise, _str_to_tags

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
