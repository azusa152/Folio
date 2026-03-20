"""Infrastructure — Stock Repository.

Stock, ThesisLog, RemovalLog aggregates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Session, func, select

from domain.entities import RemovalLog, ScanLog, Stock, ThesisLog

if TYPE_CHECKING:
    from datetime import datetime

    from domain.enums import StockCategory

# ===========================================================================
# Stock Repository
# ===========================================================================


def find_stock_by_ticker(session: Session, ticker: str) -> Stock | None:
    """根據 ticker 查詢單一股票。"""
    return session.get(Stock, ticker)


def find_active_stocks(session: Session) -> list[Stock]:
    """查詢所有啟用中的股票（依 display_order 排序）。"""
    statement = (
        select(Stock)
        .where(Stock.is_active == True)  # noqa: E712
        .order_by(Stock.display_order, Stock.ticker)
    )
    return list(session.exec(statement).all())


def find_active_stocks_by_category(
    session: Session,
    category: StockCategory,
) -> list[Stock]:
    """查詢指定分類中所有啟用的股票（依 display_order 排序）。"""
    statement = (
        select(Stock)
        .where(
            Stock.is_active == True,  # noqa: E712
            Stock.category == category,
        )
        .order_by(Stock.display_order, Stock.ticker)
    )
    return list(session.exec(statement).all())


def find_inactive_stocks(session: Session) -> list[Stock]:
    """查詢所有已移除的股票。"""
    statement = select(Stock).where(Stock.is_active == False)  # noqa: E712
    return list(session.exec(statement).all())


def save_stock(session: Session, stock: Stock) -> Stock:
    """新增或更新股票。"""
    session.add(stock)
    session.commit()
    session.refresh(stock)
    return stock


def update_stock(session: Session, stock: Stock) -> None:
    """更新股票（不做 refresh）。"""
    session.add(stock)


def bulk_update_display_order(session: Session, ordered_tickers: list[str]) -> None:
    """批次更新多檔股票的 display_order（單一 SELECT + 批次寫入）。"""
    if not ordered_tickers:
        return
    stocks = session.exec(select(Stock).where(Stock.ticker.in_(ordered_tickers))).all()
    stock_map = {s.ticker: s for s in stocks}
    for index, ticker in enumerate(ordered_tickers):
        s = stock_map.get(ticker)
        if s:
            s.display_order = index
    session.commit()


def bulk_update_scan_signals(
    session: Session,
    updates: dict[str, str],
    signal_since_updates: dict[str, datetime | None] | None = None,
) -> None:
    """批次更新多檔股票的 last_scan_signal 與 signal_since。"""
    if not updates:
        return
    stocks = session.exec(select(Stock).where(Stock.ticker.in_(updates.keys()))).all()
    for stock in stocks:
        stock.last_scan_signal = updates[stock.ticker]
        if signal_since_updates and stock.ticker in signal_since_updates:
            stock.signal_since = signal_since_updates[stock.ticker]
    session.commit()


def find_previous_distinct_signal(
    session: Session, ticker: str, current_signal: str
) -> tuple[str | None, datetime | None]:
    """
    在 ScanLog 中找到緊接在目前連續訊號之前的最後一個不同訊號及其時間。
    回傳 (previous_signal, changed_at)，若無則回傳 (None, None)。
    """
    logs = list(
        session.exec(
            select(ScanLog)
            .where(ScanLog.stock_ticker == ticker)
            .order_by(ScanLog.scanned_at.desc())  # type: ignore[union-attr]
            .limit(100)
        ).all()
    )
    idx = 0
    while idx < len(logs) and logs[idx].signal == current_signal:
        idx += 1
    if idx < len(logs):
        return logs[idx].signal, logs[idx].scanned_at
    return None, None


def count_consecutive_scans(session: Session, ticker: str, signal: str) -> int:
    """計算目前訊號連續出現的掃描次數（從最新往回算）。"""
    logs = list(
        session.exec(
            select(ScanLog)
            .where(ScanLog.stock_ticker == ticker)
            .order_by(ScanLog.scanned_at.desc())  # type: ignore[union-attr]
            .limit(50)
        ).all()
    )
    count = 0
    for log in logs:
        if log.signal == signal:
            count += 1
        else:
            break
    return max(count, 1)


def find_recent_scan_logs_for_tickers(
    session: Session, tickers: list[str], limit_per_ticker: int = 100
) -> dict[str, list[ScanLog]]:
    """
    一次批次取得多檔股票的最新 ScanLog（單一 SQL 查詢）。
    回傳 ticker → logs（時間降序）的對應表，供呼叫端自行計算統計值。
    使用 ROW_NUMBER 窗函數或 Python 端分組取 top-N。
    """
    if not tickers:
        return {}
    all_logs = list(
        session.exec(
            select(ScanLog)
            .where(ScanLog.stock_ticker.in_(tickers))  # type: ignore[union-attr]
            .order_by(
                ScanLog.stock_ticker,  # type: ignore[union-attr]
                ScanLog.scanned_at.desc(),  # type: ignore[union-attr]
            )
        ).all()
    )
    grouped: dict[str, list[ScanLog]] = {}
    for log in all_logs:
        bucket = grouped.setdefault(log.stock_ticker, [])
        if len(bucket) < limit_per_ticker:
            bucket.append(log)
    return grouped


# ===========================================================================
# ThesisLog Repository
# ===========================================================================


def get_max_thesis_version(session: Session, ticker: str) -> int:
    """取得指定股票目前最大的觀點版本號。"""
    statement = select(func.max(ThesisLog.version)).where(
        ThesisLog.stock_ticker == ticker
    )
    max_version = session.exec(statement).one()
    return max_version or 0


def create_thesis_log(session: Session, thesis: ThesisLog) -> None:
    """新增一筆觀點紀錄。"""
    session.add(thesis)


def find_thesis_history(session: Session, ticker: str) -> list[ThesisLog]:
    """取得指定股票的觀點歷史（版本降序）。"""
    statement = (
        select(ThesisLog)
        .where(ThesisLog.stock_ticker == ticker)
        .order_by(ThesisLog.version.desc())  # type: ignore[union-attr]
    )
    return list(session.exec(statement).all())


# ===========================================================================
# RemovalLog Repository
# ===========================================================================


def create_removal_log(session: Session, log: RemovalLog) -> None:
    """新增一筆移除紀錄。"""
    session.add(log)


def find_latest_removal(session: Session, ticker: str) -> RemovalLog | None:
    """取得指定股票的最新移除紀錄。"""
    statement = (
        select(RemovalLog)
        .where(RemovalLog.stock_ticker == ticker)
        .order_by(RemovalLog.created_at.desc())  # type: ignore[union-attr]
    )
    return session.exec(statement).first()


def find_latest_removals_batch(
    session: Session, tickers: list[str]
) -> dict[str, RemovalLog]:
    """
    批次取得多檔股票的最新移除紀錄（避免 N+1）。
    利用子查詢找出每檔股票最新的 removal log。
    """
    if not tickers:
        return {}

    # 子查詢：每檔股票的最大 created_at
    subq = (
        select(
            RemovalLog.stock_ticker,
            func.max(RemovalLog.created_at).label("max_created"),
        )
        .where(RemovalLog.stock_ticker.in_(tickers))  # type: ignore[union-attr]
        .group_by(RemovalLog.stock_ticker)
    ).subquery()

    # 主查詢：用 join 取回完整的 RemovalLog
    statement = select(RemovalLog).join(
        subq,
        (RemovalLog.stock_ticker == subq.c.stock_ticker)
        & (RemovalLog.created_at == subq.c.max_created),
    )
    results = session.exec(statement).all()
    return {r.stock_ticker: r for r in results}


def find_removal_history(session: Session, ticker: str) -> list[RemovalLog]:
    """取得指定股票的完整移除歷史（時間降序）。"""
    statement = (
        select(RemovalLog)
        .where(RemovalLog.stock_ticker == ticker)
        .order_by(RemovalLog.created_at.desc())  # type: ignore[union-attr]
    )
    return list(session.exec(statement).all())
