"""
API — 持倉 (Holding) 管理與再平衡 (Rebalance) 路由。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session

from api.schemas import (
    CurrencyExposureResponse,
    FXAlertResponse,
    HoldingResponse,
    MessageResponse,
    RebalanceResponse,
    StressTestResponse,
    WithdrawRequest,
    WithdrawResponse,
    XRayAlertResponse,
)
from application.portfolio import holding_service
from application.portfolio.drift_alert_service import (
    acknowledge_drift_alert,
    send_drift_alerts,
)
from application.portfolio.fx_exposure_service import (
    calculate_currency_exposure,
    send_fx_alerts,
)
from application.portfolio.rebalance_service import (
    acknowledge_xray_alert,
    calculate_rebalance,
    send_xray_warnings,
)
from application.portfolio.stress_test_service import calculate_stress_test
from application.portfolio.withdrawal_service import calculate_withdrawal
from application.stock.stock_service import StockNotFoundError
from domain.constants import (
    ERROR_HOLDING_NOT_FOUND,
    ERROR_INVALID_INPUT,
    ERROR_INVALID_SCENARIO_DROP,
    GENERIC_VALIDATION_ERROR,
    SUPPORTED_CURRENCIES,
)
from i18n import get_user_language, t
from infrastructure.database import get_session
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/holdings", response_model=list[HoldingResponse], summary="List all holdings"
)
def list_holdings(session: Session = Depends(get_session)) -> list[HoldingResponse]:
    """取得所有持倉。"""
    return [HoldingResponse(**h) for h in holding_service.list_holdings(session)]


# ---------------------------------------------------------------------------
# Rebalance Analysis
# ---------------------------------------------------------------------------


@router.get(
    "/rebalance",
    response_model=RebalanceResponse,
    summary="Calculate rebalance analysis",
)
def get_rebalance(
    response: Response,
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> dict:
    """計算再平衡分析（目標 vs 實際配置）。可透過 display_currency 指定顯示幣別。"""
    response.headers["Cache-Control"] = (
        "private, max-age=60, stale-while-revalidate=300"
    )
    try:
        return calculate_rebalance(
            session, display_currency=display_currency.strip().upper()
        )
    except StockNotFoundError as e:
        from domain.constants import ERROR_PROFILE_NOT_FOUND

        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_PROFILE_NOT_FOUND, "detail": str(e)},
        ) from e


@router.post(
    "/rebalance/drift-alert",
    response_model=FXAlertResponse,
    summary="Trigger portfolio drift alert via Telegram",
)
def trigger_drift_alert(
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> dict:
    """檢查組合漂移並發送 Telegram 警報摘要。"""
    result = send_drift_alerts(
        session, display_currency=display_currency.strip().upper()
    )
    alerts = [
        f"{row['category']}: actual {row['actual_pct']}% vs target {row['target_pct']}% "
        f"(drift {abs(row['drift_pct'])}%)"
        for row in result.get("alerts", [])
    ]
    return {
        "message": t(
            "api.drift_alert_done",
            lang=get_user_language(session),
            count=result.get("count", len(alerts)),
        ),
        "alerts": alerts,
    }


@router.post(
    "/rebalance/drift-alert/ack",
    response_model=MessageResponse,
    summary="Acknowledge one drift category and suppress repeats",
)
def acknowledge_drift(
    category: str,
    drift_pct: float | None = None,
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> MessageResponse:
    """確認漂移提醒（同一類別後續僅在惡化或反轉時重送）。"""
    lang = get_user_language(session)
    try:
        result = acknowledge_drift_alert(
            session,
            category=category,
            drift_pct=drift_pct,
            display_currency=display_currency.strip().upper(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": str(e) or ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
            },
        ) from e
    return MessageResponse(
        message=t(
            "webhook.acknowledge_drift_summary",
            lang=lang,
            category=result["key"],
            drift=round(float(result["acknowledged_value"]), 2),
        )
    )


@router.post(
    "/rebalance/xray-alert",
    response_model=XRayAlertResponse,
    summary="Trigger X-Ray alert via Telegram",
)
def trigger_xray_alert(
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> dict:
    """觸發 X-Ray 穿透式持倉分析並發送 Telegram 警告。"""
    try:
        rebalance = calculate_rebalance(
            session, display_currency=display_currency.strip().upper()
        )
        xray = rebalance.get("xray", [])
        warnings = send_xray_warnings(xray, display_currency, session)
        return {
            "message": t(
                "api.xray_done", lang=get_user_language(session), count=len(warnings)
            ),
            "warnings": warnings,
        }
    except StockNotFoundError as e:
        from domain.constants import ERROR_PROFILE_NOT_FOUND

        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_PROFILE_NOT_FOUND, "detail": str(e)},
        ) from e


@router.post(
    "/rebalance/xray-alert/ack",
    response_model=MessageResponse,
    summary="Acknowledge one X-Ray symbol and suppress repeats",
)
def acknowledge_xray(
    symbol: str,
    total_weight_pct: float | None = None,
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> MessageResponse:
    """確認 X-Ray 集中度提醒（同標的後續僅在明顯惡化時重送）。"""
    lang = get_user_language(session)
    try:
        result = acknowledge_xray_alert(
            session,
            symbol=symbol,
            total_weight_pct=total_weight_pct,
            display_currency=display_currency.strip().upper(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": str(e) or ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
            },
        ) from e
    return MessageResponse(
        message=t(
            "webhook.acknowledge_xray_summary",
            lang=lang,
            symbol=result["key"],
            weight=round(float(result["acknowledged_value"]), 2),
        )
    )


# ---------------------------------------------------------------------------
# Smart Withdrawal (聰明提款機)
# ---------------------------------------------------------------------------


@router.post(
    "/withdraw",
    response_model=WithdrawResponse,
    summary="Smart withdrawal plan (Liquidity Waterfall)",
)
def calculate_withdraw_route(
    payload: WithdrawRequest,
    session: Session = Depends(get_session),
) -> WithdrawResponse:
    """
    聰明提款：根據 Liquidity Waterfall 演算法產生賣出建議。
    優先順序：再平衡超配 → 節稅（虧損持倉）→ 流動性（Cash/Bond 優先）。
    """
    try:
        result = calculate_withdrawal(
            session,
            target_amount=payload.target_amount,
            display_currency=payload.display_currency.strip().upper(),
            notify=payload.notify,
        )
        return WithdrawResponse(**result)
    except StockNotFoundError as e:
        from domain.constants import ERROR_PROFILE_NOT_FOUND

        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_PROFILE_NOT_FOUND, "detail": str(e)},
        ) from e


# ---------------------------------------------------------------------------
# Currency Exposure Monitor
# ---------------------------------------------------------------------------


@router.get(
    "/currency-exposure",
    response_model=CurrencyExposureResponse,
    summary="Calculate currency exposure",
)
def get_currency_exposure(
    home_currency: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    """計算匯率曝險分析：幣別分佈、匯率變動、風險等級與建議。"""
    normalized_home_currency = (
        home_currency.strip().upper() if home_currency is not None else None
    )
    if (
        normalized_home_currency is not None
        and normalized_home_currency not in SUPPORTED_CURRENCIES
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t(
                    GENERIC_VALIDATION_ERROR,
                    lang=get_user_language(session),
                ),
            },
        )
    return calculate_currency_exposure(session, home_currency=normalized_home_currency)


@router.post(
    "/currency-exposure/alert",
    response_model=FXAlertResponse,
    summary="Trigger FX alert via Telegram",
)
def trigger_fx_alert(
    session: Session = Depends(get_session),
) -> dict:
    """檢查匯率曝險並發送 Telegram 警報。"""
    alerts = send_fx_alerts(session)
    return {
        "message": t(
            "api.fx_alert_done", lang=get_user_language(session), count=len(alerts)
        ),
        "alerts": alerts,
    }


# ---------------------------------------------------------------------------
# Stress Test
# ---------------------------------------------------------------------------


@router.get(
    "/stress-test",
    response_model=StressTestResponse,
    summary="Calculate portfolio stress test",
)
def get_stress_test(
    scenario_drop_pct: float = -20.0,
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> StressTestResponse:
    """
    計算組合壓力測試：評估市場崩盤情境下的預期損失。

    Args:
        scenario_drop_pct: 市場崩盤情境 % (範圍: -50 到 0，預設 -20)
        display_currency: 顯示幣別（預設 USD）
        session: DB session (injected)

    Returns:
        StressTestResponse: 壓力測試結果（portfolio_beta, total_loss, pain_level, advice, breakdown）

    Raises:
        HTTPException 404: 當無任何持倉時
        HTTPException 422: 當 scenario_drop_pct 超出範圍時
    """
    # 驗證 scenario_drop_pct 範圍
    if not -50 <= scenario_drop_pct <= 0:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": ERROR_INVALID_SCENARIO_DROP,
                "detail": t(
                    "api.scenario_range_error", lang=get_user_language(session)
                ),
            },
        )

    try:
        result = calculate_stress_test(
            session,
            scenario_drop_pct=scenario_drop_pct,
            display_currency=display_currency.strip().upper(),
        )
        lang = get_user_language(session)
        # Translate i18n keys in pain_level, disclaimer, and advice
        result["pain_level"] = {
            **result["pain_level"],
            "label": t(result["pain_level"]["label"], lang=lang),
        }
        result["disclaimer"] = t(result["disclaimer"], lang=lang)
        result["advice"] = [t(advice_key, lang=lang) for advice_key in result["advice"]]
        return StressTestResponse(**result)
    except StockNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_HOLDING_NOT_FOUND, "detail": str(e)},
        ) from e
