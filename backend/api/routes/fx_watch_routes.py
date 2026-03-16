"""
API — FX Watch 外匯監控路由。
提供 CRUD 操作與定期監控觸發端點。
"""

from datetime import UTC, datetime
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from api.rate_limit import limiter
from api.schemas import (
    FXTimingResultResponse,
    FXWatchAlertResponse,
    FXWatchCheckResponse,
    FXWatchCheckResultItem,
    FXWatchCreateRequest,
    FXWatchResponse,
    FXWatchUpdateRequest,
    MessageResponse,
)
from application.portfolio.fx_watch_service import (
    _UNSET,
    check_fx_watches,
    create_watch,
    get_all_watches,
    refresh_fx_data,
    remove_watch,
    send_fx_watch_alerts,
    update_watch,
)
from domain.constants import (
    DEFAULT_USER_ID,
    ERROR_FX_WATCH_NOT_FOUND,
    FX_WATCH_FORCE_REFRESH_COOLDOWN_SECONDS,
)
from domain.entities import FXWatchConfig
from i18n import get_user_language, t
from infrastructure.database import get_session
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()
_force_refresh_tracker_lock = Lock()
_force_refresh_tracker: dict[str, float] = {}


# ---------------------------------------------------------------------------
# Mapping Helpers
# ---------------------------------------------------------------------------


def _enforce_force_refresh_cooldown(request: Request) -> None:
    """Throttle expensive force-refresh calls per client IP."""
    client_ip = request.client.host if request.client else "unknown"
    now = monotonic()
    with _force_refresh_tracker_lock:
        last_seen = _force_refresh_tracker.get(client_ip)
        if last_seen is not None:
            elapsed = now - last_seen
            if elapsed < FX_WATCH_FORCE_REFRESH_COOLDOWN_SECONDS:
                retry_after = max(
                    1,
                    ceil(FX_WATCH_FORCE_REFRESH_COOLDOWN_SECONDS - elapsed),
                )
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error_code": "FX_WATCH_REFRESH_COOLDOWN",
                        "detail": (
                            "Force refresh is cooling down. "
                            "Please retry after the retry_after_seconds window."
                        ),
                        "retry_after_seconds": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )
        _force_refresh_tracker[client_ip] = now

        # Defensive pruning to avoid unbounded growth in long-running processes.
        if len(_force_refresh_tracker) > 1000:
            cutoff = now - FX_WATCH_FORCE_REFRESH_COOLDOWN_SECONDS
            stale_keys = [
                ip for ip, ts in _force_refresh_tracker.items() if ts < cutoff
            ]
            for ip in stale_keys:
                _force_refresh_tracker.pop(ip, None)


def _to_watch_response(w: FXWatchConfig) -> FXWatchResponse:
    """Map FXWatchConfig entity to FXWatchResponse schema."""
    return FXWatchResponse(
        id=w.id,
        user_id=w.user_id,
        base_currency=w.base_currency,
        quote_currency=w.quote_currency,
        recent_high_days=w.recent_high_days,
        consecutive_increase_days=w.consecutive_increase_days,
        alert_on_recent_high=w.alert_on_recent_high,
        alert_on_consecutive_increase=w.alert_on_consecutive_increase,
        target_rate=w.target_rate,
        target_direction=w.target_direction,
        reminder_interval_hours=w.reminder_interval_hours,
        is_active=w.is_active,
        last_alerted_at=w.last_alerted_at.isoformat() if w.last_alerted_at else None,
        created_at=w.created_at.isoformat(),
        updated_at=w.updated_at.isoformat(),
    )


def _to_result_item(r: dict, lang: str) -> FXWatchCheckResultItem:
    """Map service result dict to FXWatchCheckResultItem schema.

    recommendation and reasoning are translated to the user's language using
    the scenario code and interpolation vars produced by the domain layer.
    Emoji prefixes (💡 / 📊) are stripped — they are Telegram-only decoration.
    """
    timing = r["result"]
    scenario = timing.scenario or "no_signal"
    vars_ = timing.scenario_vars or {}
    recommendation = t(f"fx_watch.rec_{scenario}", lang=lang, **vars_).removeprefix(
        "💡 "
    )
    reasoning = t(f"fx_watch.rea_{scenario}", lang=lang, **vars_).removeprefix("📊 ")
    return FXWatchCheckResultItem(
        watch_id=r["watch_id"],
        pair=r["pair"],
        result=FXTimingResultResponse(
            base_currency=timing.base_currency,
            quote_currency=timing.quote_currency,
            current_rate=timing.current_rate,
            is_recent_high=timing.is_recent_high,
            lookback_high=timing.lookback_high,
            lookback_days=timing.lookback_days,
            high_days_ago=timing.high_days_ago,
            distance_from_high_pct=timing.distance_from_high_pct,
            consecutive_increases=timing.consecutive_increases,
            consecutive_threshold=timing.consecutive_threshold,
            trend_direction=timing.trend_direction,
            trend_strength_pct=timing.trend_strength_pct,
            signal_strength=timing.signal_strength,
            alert_on_recent_high=timing.alert_on_recent_high,
            alert_on_consecutive_increase=timing.alert_on_consecutive_increase,
            target_rate=timing.target_rate,
            target_direction=timing.target_direction,
            target_hit=timing.target_hit,
            target_distance_pct=timing.target_distance_pct,
            should_alert=timing.should_alert,
            scenario=scenario,
            scenario_vars=vars_,
            recommendation=recommendation,
            reasoning=reasoning,
        ),
    )


# ---------------------------------------------------------------------------
# CRUD Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/fx-watch",
    response_model=list[FXWatchResponse],
    summary="Get all FX watch configs",
)
def get_fx_watch_configs(
    active_only: bool = False,
    user_id: str = DEFAULT_USER_ID,
    session: Session = Depends(get_session),
) -> list[FXWatchResponse]:
    """
    取得所有外匯監控配置。

    Query Parameters:
    - active_only: 是否僅取啟用中的配置（預設 False）
    - user_id: 使用者 ID（預設 DEFAULT_USER_ID）
    """
    watches = get_all_watches(session, user_id=user_id, active_only=active_only)
    return [_to_watch_response(w) for w in watches]


@router.post(
    "/fx-watch",
    response_model=FXWatchResponse,
    summary="Create FX watch config",
    status_code=201,
)
def create_fx_watch_config(
    req: FXWatchCreateRequest,
    user_id: str = DEFAULT_USER_ID,
    session: Session = Depends(get_session),
) -> FXWatchResponse:
    """
    新增外匯監控配置。

    Request Body:
    - base_currency: 基礎貨幣（例如 USD）
    - quote_currency: 報價貨幣（例如 TWD）
    - recent_high_days: 回溯天數（預設 30）
    - consecutive_increase_days: 連續上漲天數門檻（預設 3）
    - alert_on_recent_high: 是否啟用近期高點警報（預設 True）
    - alert_on_consecutive_increase: 是否啟用連續上漲警報（預設 True）
    - reminder_interval_hours: 提醒間隔（預設 24）
    """
    watch = create_watch(
        session=session,
        base_currency=req.base_currency,
        quote_currency=req.quote_currency,
        recent_high_days=req.recent_high_days,
        consecutive_increase_days=req.consecutive_increase_days,
        alert_on_recent_high=req.alert_on_recent_high,
        alert_on_consecutive_increase=req.alert_on_consecutive_increase,
        target_rate=req.target_rate,
        target_direction=req.target_direction,
        reminder_interval_hours=req.reminder_interval_hours,
        user_id=user_id,
    )
    return _to_watch_response(watch)


@router.patch(
    "/fx-watch/{watch_id}",
    response_model=FXWatchResponse,
    summary="Update FX watch config",
)
def update_fx_watch_config(
    watch_id: int,
    req: FXWatchUpdateRequest,
    session: Session = Depends(get_session),
) -> FXWatchResponse:
    """
    更新外匯監控配置。

    Path Parameters:
    - watch_id: 配置 ID

    Request Body:
    - recent_high_days: 回溯天數（可選）
    - consecutive_increase_days: 連續上漲天數門檻（可選）
    - alert_on_recent_high: 是否啟用近期高點警報（可選）
    - alert_on_consecutive_increase: 是否啟用連續上漲警報（可選）
    - reminder_interval_hours: 提醒間隔（可選）
    - is_active: 是否啟用（可選）
    """
    update_fields = req.model_dump(exclude_unset=True)
    watch = update_watch(
        session=session,
        watch_id=watch_id,
        recent_high_days=update_fields.get("recent_high_days"),
        consecutive_increase_days=update_fields.get("consecutive_increase_days"),
        alert_on_recent_high=update_fields.get("alert_on_recent_high"),
        alert_on_consecutive_increase=update_fields.get(
            "alert_on_consecutive_increase"
        ),
        target_rate=update_fields.get("target_rate", _UNSET),
        target_direction=update_fields.get("target_direction", _UNSET),
        reminder_interval_hours=update_fields.get("reminder_interval_hours"),
        is_active=update_fields.get("is_active"),
    )
    if not watch:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_FX_WATCH_NOT_FOUND,
                "detail": f"FX watch config with ID {watch_id} not found",
            },
        )

    return _to_watch_response(watch)


@router.delete(
    "/fx-watch/{watch_id}",
    response_model=MessageResponse,
    summary="Delete FX watch config",
)
def delete_fx_watch_config(
    watch_id: int,
    session: Session = Depends(get_session),
) -> MessageResponse:
    """
    刪除外匯監控配置。

    Path Parameters:
    - watch_id: 配置 ID
    """
    success = remove_watch(session, watch_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_FX_WATCH_NOT_FOUND,
                "detail": f"FX watch config with ID {watch_id} not found",
            },
        )

    return MessageResponse(message=f"FX watch config {watch_id} deleted successfully")


# ---------------------------------------------------------------------------
# Analysis & Alert Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/fx-watch/check",
    response_model=FXWatchCheckResponse,
    summary="Check FX watches (no alert)",
)
@limiter.limit("10/minute")
def check_fx_watch_alerts(
    request: Request,
    force_refresh: bool = False,
    user_id: str = DEFAULT_USER_ID,
    session: Session = Depends(get_session),
) -> FXWatchCheckResponse:
    """
    檢查所有啟用中的外匯監控配置，產出分析結果（不發送通知）。

    Query Parameters:
    - force_refresh: 若為 True，先清除 FX 快取再重新抓取最新資料（預設 False）
    - user_id: 使用者 ID（預設 DEFAULT_USER_ID）

    Returns:
    - checked_at: 伺服器端分析完成的 UTC ISO 時間戳
    - total_watches: 啟用中的配置數量
    - results: 分析結果列表（含配置 ID、貨幣對、分析結果）
    """
    if force_refresh:
        _enforce_force_refresh_cooldown(request)
        refresh_fx_data()
    results = check_fx_watches(session, user_id=user_id)
    lang = get_user_language(session)
    return FXWatchCheckResponse(
        checked_at=datetime.now(UTC).isoformat(),
        total_watches=len(results),
        results=[_to_result_item(r, lang) for r in results],
    )


@router.post(
    "/fx-watch/alert",
    response_model=FXWatchAlertResponse,
    summary="Check FX watches & send Telegram alert",
)
def send_fx_watch_alert(
    user_id: str = DEFAULT_USER_ID,
    session: Session = Depends(get_session),
) -> FXWatchAlertResponse:
    """
    檢查所有啟用中的外匯監控配置，發送 Telegram 警報（帶冷卻機制）。

    Query Parameters:
    - user_id: 使用者 ID（預設 DEFAULT_USER_ID）

    Returns:
    - total_watches: 啟用中的配置數量
    - triggered_alerts: 觸發警報的數量
    - sent_alerts: 實際發送的警報數量
    - alerts: 觸發警報的詳細資訊
    """
    result = send_fx_watch_alerts(session, user_id=user_id)
    lang = get_user_language(session)
    return FXWatchAlertResponse(
        total_watches=result["total_watches"],
        triggered_alerts=result["triggered_alerts"],
        sent_alerts=result["sent_alerts"],
        alerts=[_to_result_item(a, lang) for a in result["alerts"]],
    )
