"""Infrastructure — Scan Repository.

ScanLog, PriceAlert, FXWatchConfig, NotificationLog,
StockSplitEvent, DividendEvent, DriftAcknowledgment.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from domain.constants import LATEST_SCAN_LOGS_DEFAULT_LIMIT, SCAN_HISTORY_DEFAULT_LIMIT
from domain.entities import (
    DividendEvent,
    DriftAcknowledgment,
    FXWatchConfig,
    NotificationLog,
    PriceAlert,
    ScanLog,
    StockSplitEvent,
)

# ===========================================================================
# ScanLog Repository
# ===========================================================================


def create_scan_log(session: Session, log: ScanLog) -> None:
    """新增一筆掃描紀錄。"""
    session.add(log)


def find_scan_history(
    session: Session, ticker: str, limit: int = SCAN_HISTORY_DEFAULT_LIMIT
) -> list[ScanLog]:
    """取得指定股票的掃描歷史（時間降序）。"""
    statement = (
        select(ScanLog)
        .where(ScanLog.stock_ticker == ticker)
        .order_by(ScanLog.scanned_at.desc())  # type: ignore[union-attr]
        .limit(limit)
    )
    return list(session.exec(statement).all())


def find_latest_scan_logs(
    session: Session, limit: int = LATEST_SCAN_LOGS_DEFAULT_LIMIT
) -> list[ScanLog]:
    """取得最近的掃描紀錄（跨股票，時間降序）。"""
    statement = (
        select(ScanLog)
        .order_by(ScanLog.scanned_at.desc())  # type: ignore[union-attr]
        .limit(limit)
    )
    return list(session.exec(statement).all())


def find_scan_logs_since(session: Session, since: datetime) -> list[ScanLog]:
    """取得指定時間之後的所有掃描紀錄。"""
    statement = (
        select(ScanLog)
        .where(ScanLog.scanned_at >= since)  # type: ignore[operator]
        .order_by(ScanLog.scanned_at.desc())  # type: ignore[union-attr]
    )
    return list(session.exec(statement).all())


def find_scan_logs_for_backtest(
    session: Session,
    since: datetime,
    exclude_signals: list[str] | None = None,
) -> list[ScanLog]:
    """
    取得回測用掃描紀錄（時間升序，供訊號轉折去重）。

    預設排除 NORMAL，避免把「無動作」訊號視為回測樣本。
    """
    excluded = exclude_signals or ["NORMAL"]
    statement = (
        select(ScanLog)
        .where(ScanLog.scanned_at >= since)  # type: ignore[operator]
        .where(~ScanLog.signal.in_(excluded))  # type: ignore[union-attr]
        .order_by(
            ScanLog.stock_ticker,  # type: ignore[union-attr]
            ScanLog.scanned_at.asc(),  # type: ignore[union-attr]
        )
    )
    return list(session.exec(statement).all())


# ===========================================================================
# PriceAlert Repository
# ===========================================================================


def create_price_alert(session: Session, alert: PriceAlert) -> PriceAlert:
    """新增一筆價格警報。"""
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


def find_active_alerts_for_stock(session: Session, ticker: str) -> list[PriceAlert]:
    """取得指定股票的所有啟用中警報。"""
    statement = select(PriceAlert).where(
        PriceAlert.stock_ticker == ticker,
        PriceAlert.is_active == True,  # noqa: E712
    )
    return list(session.exec(statement).all())


def find_all_alerts_for_stock(session: Session, ticker: str) -> list[PriceAlert]:
    """取得指定股票的所有警報（含已停用）。"""
    statement = select(PriceAlert).where(PriceAlert.stock_ticker == ticker)
    return list(session.exec(statement).all())


def find_all_active_alerts(session: Session) -> list[PriceAlert]:
    """取得所有啟用中的警報。"""
    statement = select(PriceAlert).where(PriceAlert.is_active == True)  # noqa: E712
    return list(session.exec(statement).all())


def find_price_alert_by_id(session: Session, alert_id: int) -> PriceAlert | None:
    """根據 ID 查詢單一警報。"""
    return session.get(PriceAlert, alert_id)


def delete_price_alert(session: Session, alert: PriceAlert) -> None:
    """刪除一筆價格警報。"""
    session.delete(alert)
    session.commit()


# ===========================================================================
# FX Watch Repository
# ===========================================================================


def create_fx_watch(session: Session, watch: FXWatchConfig) -> FXWatchConfig:
    """新增一筆外匯監控配置。"""
    session.add(watch)
    session.commit()
    session.refresh(watch)
    return watch


def find_fx_watch_by_id(session: Session, watch_id: int) -> FXWatchConfig | None:
    """根據 ID 查詢單一外匯監控配置。"""
    return session.get(FXWatchConfig, watch_id)


def find_active_fx_watches(
    session: Session, user_id: str | None = None
) -> list[FXWatchConfig]:
    """取得所有啟用中的外匯監控配置。"""
    statement = select(FXWatchConfig).where(FXWatchConfig.is_active == True)  # noqa: E712
    if user_id is not None:
        statement = statement.where(FXWatchConfig.user_id == user_id)
    return list(session.exec(statement).all())


def find_all_fx_watches(
    session: Session, user_id: str | None = None
) -> list[FXWatchConfig]:
    """取得所有外匯監控配置（含已停用）。"""
    statement = select(FXWatchConfig)
    if user_id is not None:
        statement = statement.where(FXWatchConfig.user_id == user_id)
    return list(session.exec(statement).all())


def update_fx_watch(session: Session, watch: FXWatchConfig) -> FXWatchConfig:
    """更新外匯監控配置（通用）。"""
    watch.updated_at = datetime.now(UTC)
    session.add(watch)
    session.commit()
    session.refresh(watch)
    return watch


def update_fx_watch_last_alerted(
    session: Session, watch_id: int, alerted_at: datetime
) -> None:
    """更新外匯監控配置的最後警報時間。"""
    watch = session.get(FXWatchConfig, watch_id)
    if watch:
        watch.last_alerted_at = alerted_at
        watch.updated_at = datetime.now(UTC)
        session.add(watch)
        session.commit()


def delete_fx_watch(session: Session, watch: FXWatchConfig) -> None:
    """刪除一筆外匯監控配置。"""
    session.delete(watch)
    session.commit()


# ===========================================================================
# Notification Log Repository (rate-limit tracking)
# ===========================================================================


# Keep at most 7 days of notification logs to prevent unbounded growth.
_NOTIFICATION_LOG_RETENTION_DAYS = 7


def log_notification_sent(session: Session, notification_type: str) -> NotificationLog:
    """記錄一筆通知發送記錄並清理過期資料（供頻率限制使用）。"""
    entry = NotificationLog(notification_type=notification_type)
    session.add(entry)

    cutoff = (
        datetime.now(UTC) - timedelta(days=_NOTIFICATION_LOG_RETENTION_DAYS)
    ).replace(tzinfo=None)
    stale = session.exec(
        select(NotificationLog).where(NotificationLog.sent_at < cutoff)
    ).all()
    for row in stale:
        session.delete(row)

    session.commit()
    session.refresh(entry)
    return entry


def count_recent_notifications(
    session: Session, notification_type: str, since: datetime
) -> int:
    """計算指定時間點之後，某通知類型的發送次數。"""
    statement = select(func.count()).where(
        NotificationLog.notification_type == notification_type,
        NotificationLog.sent_at >= since,
    )
    return session.exec(statement).one()


# ===========================================================================
# Stock Split Event Repository
# ===========================================================================


def find_stock_split_event_by_id(
    session: Session, event_id: int
) -> StockSplitEvent | None:
    """根據 ID 查詢單一股票分割事件。"""
    return session.get(StockSplitEvent, event_id)


def find_stock_split_events(
    session: Session,
    *,
    status: str | None = None,
    ticker: str | None = None,
    limit: int | None = 200,
) -> list[StockSplitEvent]:
    """查詢股票分割事件（可依狀態與 ticker 篩選）。"""
    stmt = select(StockSplitEvent).order_by(StockSplitEvent.detected_at.desc())  # pyright: ignore[reportAttributeAccessIssue]
    if status is not None:
        stmt = stmt.where(StockSplitEvent.status == status)
    if ticker is not None:
        stmt = stmt.where(StockSplitEvent.ticker == ticker.upper().strip())
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.exec(stmt).all())


def find_stock_split_event_by_unique_key(
    session: Session, *, ticker: str, split_date: date, ratio: float
) -> StockSplitEvent | None:
    """依 ticker + split_date + ratio 查詢事件（避免重複建立）。"""
    normalized_ticker = ticker.upper().strip()
    stmt = (
        select(StockSplitEvent)
        .where(StockSplitEvent.ticker == normalized_ticker)
        .where(StockSplitEvent.split_date == split_date)
        .where(StockSplitEvent.ratio == ratio)
    )
    return session.exec(stmt).first()


def create_stock_split_event(
    session: Session, event: StockSplitEvent
) -> StockSplitEvent:
    """建立股票分割事件（idempotent — 若 unique key 已存在則回傳現有記錄）。"""
    try:
        session.add(event)
        session.commit()
        session.refresh(event)
        return event
    except IntegrityError:
        session.rollback()
        existing = find_stock_split_event_by_unique_key(
            session,
            ticker=event.ticker,
            split_date=event.split_date,
            ratio=event.ratio,
        )
        if existing is not None:
            return existing
        raise


def save_stock_split_event(session: Session, event: StockSplitEvent) -> StockSplitEvent:
    """更新股票分割事件（含 commit + refresh）。"""
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def try_claim_stock_split_event(
    session: Session, event_id: int, *, from_status: str, to_status: str
) -> bool:
    """Atomic CAS: transition event status from_status -> to_status.

    Returns True when exactly one row was updated (this caller wins the race).
    Returns False when another writer already moved the row away from from_status.
    """
    result = session.exec(  # type: ignore[call-overload]
        update(StockSplitEvent)
        .where(StockSplitEvent.id == event_id)
        .where(StockSplitEvent.status == from_status)
        .values(status=to_status)
        .execution_options(synchronize_session="evaluate")
    )
    session.commit()
    return (result.rowcount or 0) == 1


# ===========================================================================
# Dividend Event Repository
# ===========================================================================


def find_dividend_event_by_id(session: Session, event_id: int) -> DividendEvent | None:
    """根據 ID 查詢單一股息事件。"""
    return session.get(DividendEvent, event_id)


def find_dividend_events(
    session: Session,
    *,
    status: str | None = None,
    ticker: str | None = None,
    limit: int | None = 200,
) -> list[DividendEvent]:
    """查詢股息事件（可依狀態與 ticker 篩選）。"""
    stmt = select(DividendEvent).order_by(DividendEvent.detected_at.desc())  # pyright: ignore[reportAttributeAccessIssue]
    if status is not None:
        stmt = stmt.where(DividendEvent.status == status)
    if ticker is not None:
        stmt = stmt.where(DividendEvent.ticker == ticker.upper().strip())
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.exec(stmt).all())


def find_dividend_event_by_unique_key(
    session: Session, *, ticker: str, ex_dividend_date: date, amount_per_share: float
) -> DividendEvent | None:
    """依 ticker + ex_dividend_date + amount_per_share 查詢事件（避免重複建立）。"""
    normalized_ticker = ticker.upper().strip()
    stmt = (
        select(DividendEvent)
        .where(DividendEvent.ticker == normalized_ticker)
        .where(DividendEvent.ex_dividend_date == ex_dividend_date)
        .where(DividendEvent.amount_per_share == amount_per_share)
    )
    return session.exec(stmt).first()


def create_dividend_event(session: Session, event: DividendEvent) -> DividendEvent:
    """建立股息事件（idempotent — 若 unique key 已存在則回傳現有記錄）。"""
    try:
        session.add(event)
        session.commit()
        session.refresh(event)
        return event
    except IntegrityError:
        session.rollback()
        existing = find_dividend_event_by_unique_key(
            session,
            ticker=event.ticker,
            ex_dividend_date=event.ex_dividend_date,
            amount_per_share=event.amount_per_share,
        )
        if existing is not None:
            return existing
        raise


def save_dividend_event(session: Session, event: DividendEvent) -> DividendEvent:
    """更新股息事件（含 commit + refresh）。"""
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def try_claim_dividend_event(
    session: Session, event_id: int, *, from_status: str, to_status: str
) -> bool:
    """Atomic CAS: transition dividend event status from_status -> to_status."""
    result = session.exec(  # type: ignore[call-overload]
        update(DividendEvent)
        .where(DividendEvent.id == event_id)
        .where(DividendEvent.status == from_status)
        .values(status=to_status)
        .execution_options(synchronize_session="evaluate")
    )
    session.commit()
    return (result.rowcount or 0) == 1


# ===========================================================================
# Alert Acknowledgment Repository (drift/xray anti-fatigue)
# ===========================================================================


def find_drift_acknowledgment(
    session: Session, *, alert_type: str, alert_key: str
) -> DriftAcknowledgment | None:
    """Lookup a non-expired acknowledgment by (type, key)."""
    normalized_type = alert_type.strip().lower()
    normalized_key = alert_key.strip().upper()
    stmt = (
        select(DriftAcknowledgment)
        .where(DriftAcknowledgment.alert_type == normalized_type)
        .where(DriftAcknowledgment.alert_key == normalized_key)
    )
    ack = session.exec(stmt).first()
    if ack is None:
        return None
    now = datetime.now(UTC).replace(tzinfo=None)
    if ack.expires_at < now:
        session.delete(ack)
        session.commit()
        return None
    return ack


def upsert_drift_acknowledgment(
    session: Session,
    *,
    alert_type: str,
    alert_key: str,
    acknowledged_value: float,
    expires_at: datetime,
) -> DriftAcknowledgment:
    """Create or update acknowledgment state for one alert key."""
    normalized_type = alert_type.strip().lower()
    normalized_key = alert_key.strip().upper()
    existing = find_drift_acknowledgment(
        session, alert_type=normalized_type, alert_key=normalized_key
    )
    if existing is None:
        ack = DriftAcknowledgment(
            alert_type=normalized_type,
            alert_key=normalized_key,
            acknowledged_value=float(acknowledged_value),
            acknowledged_at=datetime.now(UTC),
            expires_at=expires_at,
        )
    else:
        ack = existing
        ack.acknowledged_value = float(acknowledged_value)
        ack.acknowledged_at = datetime.now(UTC).replace(tzinfo=None)
        ack.expires_at = expires_at
    session.add(ack)
    session.commit()
    session.refresh(ack)
    return ack


def delete_drift_acknowledgment(
    session: Session, *, alert_type: str, alert_key: str
) -> bool:
    """Delete one acknowledgment; return whether a row existed."""
    ack = find_drift_acknowledgment(session, alert_type=alert_type, alert_key=alert_key)
    if ack is None:
        return False
    session.delete(ack)
    session.commit()
    return True


def find_all_drift_acknowledgments(
    session: Session, *, alert_type: str
) -> list[DriftAcknowledgment]:
    """List all non-expired acknowledgments for the given alert type."""
    normalized_type = alert_type.strip().lower()
    now = datetime.now(UTC).replace(tzinfo=None)
    stmt = (
        select(DriftAcknowledgment)
        .where(DriftAcknowledgment.alert_type == normalized_type)
        .where(DriftAcknowledgment.expires_at > now)
    )
    return list(session.exec(stmt).all())
