"""
Application — Webhook Service：OpenClaw / AI agent webhook 處理。
"""

from collections.abc import Callable, Mapping
from datetime import date as date_type

from fastapi import HTTPException
from sqlmodel import Session

from application.formatters import format_fear_greed_label
from application.messaging.notification_service import (
    get_portfolio_summary,
    send_filing_season_digest,
)
from application.portfolio.account_service import get_account_summary
from application.portfolio.analytics_service import (
    get_risk_metrics as get_risk_metrics_svc,
)
from application.portfolio.dividend_service import check_dividends
from application.portfolio.drift_alert_service import (
    acknowledge_drift_alert,
    send_drift_alerts,
)
from application.portfolio.fx_watch_service import send_fx_watch_alerts
from application.portfolio.insight_service import get_portfolio_insights
from application.portfolio.nav_sync_service import sync_single_fund_nav
from application.portfolio.rebalance_service import (
    acknowledge_xray_alert,
    calculate_withdrawal,
)
from application.portfolio.stock_split_service import check_splits
from application.portfolio.transaction_service import (
    create_transaction,
    list_transactions,
)
from application.portfolio.wrapper_service import (
    get_all_wrapper_quotas,
    get_restoration_forecast,
)
from application.scan.scan_service import list_price_alerts, run_scan
from application.stock.filing_service import sync_all_gurus
from application.stock.stock_service import (
    StockAlreadyExistsError,
    StockNotFoundError,
    create_stock,
    get_fundamentals_for_ticker,
    get_moat_for_ticker,
    get_signals_for_ticker,
)
from domain.constants import (
    DEFAULT_IMPORT_CATEGORY,
    DEFAULT_USER_ID,
    DEFAULT_WEBHOOK_THESIS,
    ERROR_INTERNAL_ERROR,
    ERROR_INVALID_INPUT,
    ERROR_STOCK_ALREADY_EXISTS,
    ERROR_STOCK_NOT_FOUND,
    GENERIC_VALIDATION_ERROR,
    WEBHOOK_ACTION_REGISTRY,
)
from domain.core.entities import _normalize_stock_category
from domain.enums import StockCategory
from i18n import get_user_language, t
from infrastructure.market_data import (
    get_fear_greed_index,
)
from logging_config import get_logger

logger = get_logger(__name__)


def _is_concise(params: Mapping[str, object]) -> bool:
    return str(params.get("format", "detailed")).lower() == "concise"


def _build_interpretation_from_signals(result: Mapping[str, object], lang: str) -> str:
    status = result.get("status")
    if isinstance(status, list) and status:
        return str(status[0])
    return t("webhook.interpretation.signal_ready", lang=lang)


def _wrap_response(
    *,
    success: bool,
    message: str,
    interpretation: str,
    params: Mapping[str, object],
    data: dict | None = None,
    error_code: str | None = None,
    always_include_data: bool = False,
) -> dict:
    response: dict = {
        "success": success,
        "message": message,
        "interpretation": interpretation,
    }
    if error_code:
        response["error_code"] = error_code
    if always_include_data or not _is_concise(params):
        response["data"] = data or {}
    return response


def _build_help_actions() -> dict[str, dict]:
    actions: dict[str, dict] = {}
    for action, meta in WEBHOOK_ACTION_REGISTRY.items():
        entry: dict = {
            "description": str(meta.get("description", "")),
            "requires_ticker": bool(meta.get("requires_ticker")),
        }
        params = meta.get("params")
        if isinstance(params, dict) and params:
            entry["params"] = params
        actions[action] = entry
    return actions


def _missing_ticker_response(params: dict, lang: str) -> dict:
    return _wrap_response(
        success=False,
        message=t("webhook.missing_ticker", lang=lang),
        interpretation=t("webhook.interpretation.action_failed", lang=lang),
        params=params,
        error_code=ERROR_INVALID_INPUT,
    )


def _validation_error_response(params: dict, lang: str) -> dict:
    return _wrap_response(
        success=False,
        message=t(GENERIC_VALIDATION_ERROR, lang=lang),
        interpretation=t("webhook.interpretation.action_failed", lang=lang),
        params=params,
        error_code=ERROR_INVALID_INPUT,
    )


def _internal_error_response(params: dict, lang: str, message: str) -> dict:
    return _wrap_response(
        success=False,
        message=message,
        interpretation=t("webhook.interpretation.action_failed", lang=lang),
        params=params,
        error_code=ERROR_INTERNAL_ERROR,
    )


def _get_signals_or_error(
    session: Session, ticker: str, params: dict, lang: str
) -> tuple[dict, None] | tuple[None, dict]:
    """Fetch signals for ticker; return (signals, None) on success or (None, error_response)."""
    result = get_signals_for_ticker(session, ticker)
    if not result or "error" in result:
        message = (
            result.get("error", t("webhook.signals_unavailable", lang=lang))
            if result
            else t("webhook.signals_unavailable", lang=lang)
        )
        return None, _internal_error_response(params, lang, message)
    return result, None


def _handle_help(session: Session, ticker: str | None, params: dict, lang: str) -> dict:
    return _wrap_response(
        success=True,
        message=t("webhook.help_message", lang=lang),
        interpretation=t("webhook.interpretation.help_ready", lang=lang),
        params=params,
        data={
            "actions": _build_help_actions(),
            "workflows": {
                "quick_check": "dashboard -> analyze {ticker}",
                "buy_decision": "analyze {ticker} -> fear_greed",
                "sell_decision": "withdraw {amount, currency}",
                "asset_review": "dashboard -> analytics -> insights -> transactions {ticker}",
                "record_trade": "add_transaction {ticker} -> transactions {ticker}",
                "nisa_check": "quota -> dashboard",
                "tax_optimization": "quota -> insights",
            },
            "model_hint": t("webhook.help_model_hint", lang=lang),
        },
        always_include_data=True,
    )


def _handle_summary(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    return _wrap_response(
        success=True,
        message=get_portfolio_summary(session),
        interpretation=t("webhook.interpretation.summary_ready", lang=lang),
        params=params,
    )


def _handle_dashboard(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    summary = get_portfolio_summary(session)
    fg = get_fear_greed_index()
    fg_label = format_fear_greed_label(
        fg.get("composite_level", "N/A"), fg.get("composite_score", 50), lang=lang
    )
    message = f"{summary}\n\n{t('webhook.fear_greed_prefix', lang=lang)}: {fg_label}"
    return _wrap_response(
        success=True,
        message=message,
        interpretation=t("webhook.interpretation.dashboard_ready", lang=lang),
        params=params,
        data={"fear_greed": fg},
    )


def _handle_signals(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    if not ticker:
        return _missing_ticker_response(params, lang)
    result, err = _get_signals_or_error(session, ticker, params, lang)
    if err:
        return err
    status_text = "\n".join(result.get("status", []))
    msg = (
        t(
            "webhook.signals_line",
            lang=lang,
            ticker=ticker,
            price=result.get("price"),
            rsi=result.get("rsi"),
            bias=result.get("bias"),
        )
        + f"\n{status_text}"
    )
    return _wrap_response(
        success=True,
        message=msg,
        interpretation=_build_interpretation_from_signals(result, lang=lang),
        params=params,
        data=result,
    )


def _handle_analyze(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    if not ticker:
        return _missing_ticker_response(params, lang)
    signals, err = _get_signals_or_error(session, ticker, params, lang)
    if err:
        return err
    moat = get_moat_for_ticker(session, ticker)
    fundamentals = get_fundamentals_for_ticker(session, ticker)
    message = t(
        "webhook.analyze_line",
        lang=lang,
        ticker=ticker,
        price=signals.get("price"),
        rsi=signals.get("rsi"),
        bias=signals.get("bias"),
        moat=moat.get("moat", "N/A"),
        pe=fundamentals.get("trailing_pe"),
    )
    return _wrap_response(
        success=True,
        message=message,
        interpretation=_build_interpretation_from_signals(signals, lang=lang),
        params=params,
        data={"signals": signals, "moat": moat, "fundamentals": fundamentals},
    )


def _handle_scan(session: Session, ticker: str | None, params: dict, lang: str) -> dict:
    import threading as _threading

    from infrastructure.database import engine as _engine

    def _bg_scan() -> None:
        with Session(_engine) as s:
            run_scan(s)

    _threading.Thread(target=_bg_scan, daemon=True).start()
    return _wrap_response(
        success=True,
        message=t("webhook.scan_started", lang=lang),
        interpretation=t("webhook.interpretation.scan_started", lang=lang),
        params=params,
    )


def _handle_moat(session: Session, ticker: str | None, params: dict, lang: str) -> dict:
    if not ticker:
        return _missing_ticker_response(params, lang)
    result = get_moat_for_ticker(session, ticker)
    return _wrap_response(
        success=True,
        message=t(
            "webhook.moat_result",
            lang=lang,
            ticker=ticker,
            moat=result.get("moat", "N/A"),
            details=result.get("details", "N/A"),
        ),
        interpretation=t("webhook.interpretation.moat_ready", lang=lang),
        params=params,
        data=result,
    )


def _handle_alerts(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    if not ticker:
        return _missing_ticker_response(params, lang)
    alerts = list_price_alerts(session, ticker)
    if not alerts:
        return _wrap_response(
            success=True,
            message=t("webhook.no_alerts", lang=lang, ticker=ticker),
            interpretation=t("webhook.interpretation.no_alerts", lang=lang),
            params=params,
            data={"alerts": []},
        )
    lines = [t("webhook.price_alerts_header", lang=lang, ticker=ticker)]
    for a in alerts:
        op_str = "<" if a["operator"] == "lt" else ">"
        status_label = (
            t("webhook.alert_status.active", lang=lang)
            if a["is_active"]
            else t("webhook.alert_status.inactive", lang=lang)
        )
        lines.append(f"  {a['metric']} {op_str} {a['threshold']} ({status_label})")
    return _wrap_response(
        success=True,
        message="\n".join(lines),
        interpretation=t("webhook.interpretation.alerts_ready", lang=lang),
        params=params,
        data={"alerts": alerts},
    )


def _handle_fear_greed(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    fg = get_fear_greed_index()
    fg_label = format_fear_greed_label(
        fg.get("composite_level", "N/A"), fg.get("composite_score", 50), lang=lang
    )
    vix_data = fg.get("vix", {})
    vix_val = vix_data.get("value")
    vix_text = f"VIX={vix_val}" if vix_val is not None else "VIX=N/A"
    cnn_data = fg.get("cnn")
    cnn_text = (
        f"CNN={cnn_data['score']}"
        if cnn_data and cnn_data.get("score") is not None
        else "CNN=N/A"
    )
    msg = f"{t('webhook.fear_greed_prefix', lang=lang)}：{fg_label}\n{vix_text}, {cnn_text}"
    return _wrap_response(
        success=True,
        message=msg,
        interpretation=t("webhook.interpretation.fear_greed_ready", lang=lang),
        params=params,
        data=fg,
    )


def _handle_add_stock(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    t_ticker = params.get("ticker", ticker)
    if not t_ticker:
        return _missing_ticker_response(params, lang)
    cat_str = str(params.get("category", DEFAULT_IMPORT_CATEGORY))
    thesis = str(params.get("thesis") or t(DEFAULT_WEBHOOK_THESIS, lang=lang))
    tags = params.get("tags", [])
    try:
        stock = create_stock(
            session, str(t_ticker), _normalize_stock_category(cat_str), thesis, tags
        )
        if stock.category == StockCategory.MUTUAL_FUND:
            sync_single_fund_nav(session, stock.ticker)
        return _wrap_response(
            success=True,
            message=t("stock.added", lang=lang, ticker=stock.ticker, category=cat_str),
            interpretation=t("webhook.interpretation.add_stock_ready", lang=lang),
            params=params,
        )
    except StockAlreadyExistsError:
        return _wrap_response(
            success=False,
            message=t("stock.already_exists", lang=lang, ticker=str(t_ticker)),
            interpretation=t("webhook.interpretation.action_failed", lang=lang),
            params=params,
            error_code=ERROR_STOCK_ALREADY_EXISTS,
        )
    except ValueError:
        return _wrap_response(
            success=False,
            message=t("webhook.invalid_category", lang=lang, category=cat_str),
            interpretation=t("webhook.interpretation.action_failed", lang=lang),
            params=params,
            error_code=ERROR_INVALID_INPUT,
        )


def _handle_withdraw(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    amount = params.get("amount")
    if not amount:
        return _wrap_response(
            success=False,
            message=t("webhook.missing_amount", lang=lang),
            interpretation=t("webhook.interpretation.action_failed", lang=lang),
            params=params,
            error_code=ERROR_INVALID_INPUT,
        )
    try:
        amount_float = float(amount)
    except (ValueError, TypeError):
        return _wrap_response(
            success=False,
            message=t("webhook.invalid_amount", lang=lang, amount=amount),
            interpretation=t("webhook.interpretation.action_failed", lang=lang),
            params=params,
            error_code=ERROR_INVALID_INPUT,
        )
    currency = str(params.get("currency", "USD"))
    try:
        result = calculate_withdrawal(session, amount_float, currency, notify=True)
        return _wrap_response(
            success=True,
            message=result.get("message", ""),
            interpretation=t("webhook.interpretation.withdraw_ready", lang=lang),
            params=params,
            data=result,
        )
    except StockNotFoundError as e:
        return _wrap_response(
            success=False,
            message=str(e),
            interpretation=t("webhook.interpretation.action_failed", lang=lang),
            params=params,
            error_code=ERROR_STOCK_NOT_FOUND,
        )


def _handle_fx_watch(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    try:
        result = send_fx_watch_alerts(session)
        msg = t(
            "webhook.fx_watch_complete",
            lang=lang,
            total=result["total_watches"],
            triggered=result["triggered_alerts"],
            sent=result["sent_alerts"],
        )
        return _wrap_response(
            success=True,
            message=msg,
            interpretation=t("webhook.interpretation.fx_watch_ready", lang=lang),
            params=params,
            data=result,
        )
    except Exception as e:
        logger.error("外匯監控執行失敗：%s", e)
        return _internal_error_response(
            params, lang, t("webhook.fx_watch_failed", lang=lang, error=str(e))
        )


def _handle_stock_splits(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    try:
        result = check_splits(session)
        return _wrap_response(
            success=True,
            message=t(
                "webhook.stock_splits_summary",
                lang=lang,
                checked=result["checked_tickers"],
                detected=result["detected"],
                auto_applied=result["auto_applied"],
            ),
            interpretation=t("webhook.interpretation.stock_splits_ready", lang=lang),
            params=params,
            data=result,
        )
    except Exception as e:
        logger.error("stock_splits 執行失敗：%s", e)
        return _internal_error_response(
            params, lang, t("webhook.stock_splits_failed", lang=lang, error=str(e))
        )


def _handle_dividends(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    try:
        result = check_dividends(session)
        return _wrap_response(
            success=True,
            message=t(
                "webhook.dividends_summary",
                lang=lang,
                checked=result["checked_tickers"],
                detected=result["detected"],
                auto_applied=result["auto_applied"],
            ),
            interpretation=t("webhook.interpretation.dividends_ready", lang=lang),
            params=params,
            data=result,
        )
    except Exception as e:
        logger.error("dividends 執行失敗：%s", e)
        return _internal_error_response(
            params, lang, t("webhook.dividends_failed", lang=lang, error=str(e))
        )


def _handle_drift_alerts(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    try:
        result = send_drift_alerts(session)
        return _wrap_response(
            success=True,
            message=t(
                "webhook.drift_alerts_summary",
                lang=lang,
                count=result.get("count", 0),
                sent=result.get("sent", False),
            ),
            interpretation=t("webhook.interpretation.drift_alerts_ready", lang=lang),
            params=params,
            data=result,
        )
    except Exception as e:
        logger.error("drift_alerts 執行失敗：%s", e)
        return _internal_error_response(
            params, lang, t("webhook.drift_alerts_failed", lang=lang, error=str(e))
        )


def _handle_acknowledge_drift(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    category = str(params.get("category", "")).strip()
    display_currency = str(params.get("display_currency", "USD")).strip().upper()
    drift_pct_raw = params.get("drift_pct")
    try:
        drift_pct = float(drift_pct_raw) if drift_pct_raw is not None else None
        result = acknowledge_drift_alert(
            session,
            category=category,
            drift_pct=drift_pct,
            display_currency=display_currency,
        )
        return _wrap_response(
            success=True,
            message=t(
                "webhook.acknowledge_drift_summary",
                lang=lang,
                category=result["key"],
                drift=round(float(result["acknowledged_value"]), 2),
            ),
            interpretation=t(
                "webhook.interpretation.acknowledge_drift_ready", lang=lang
            ),
            params=params,
            data=result,
        )
    except ValueError:
        return _validation_error_response(params, lang)
    except Exception as e:
        logger.error("acknowledge_drift 執行失敗：%s", e)
        return _internal_error_response(
            params,
            lang,
            t("webhook.acknowledge_drift_failed", lang=lang, error=str(e)),
        )


def _handle_acknowledge_xray(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    symbol = str(params.get("symbol", "")).strip().upper()
    display_currency = str(params.get("display_currency", "USD")).strip().upper()
    total_weight_raw = params.get("total_weight_pct")
    try:
        total_weight_pct = (
            float(total_weight_raw) if total_weight_raw is not None else None
        )
        result = acknowledge_xray_alert(
            session,
            symbol=symbol,
            total_weight_pct=total_weight_pct,
            display_currency=display_currency,
        )
        return _wrap_response(
            success=True,
            message=t(
                "webhook.acknowledge_xray_summary",
                lang=lang,
                symbol=result["key"],
                weight=round(float(result["acknowledged_value"]), 2),
            ),
            interpretation=t(
                "webhook.interpretation.acknowledge_xray_ready", lang=lang
            ),
            params=params,
            data=result,
        )
    except ValueError:
        return _validation_error_response(params, lang)
    except Exception as e:
        logger.error("acknowledge_xray 執行失敗：%s", e)
        return _internal_error_response(
            params,
            lang,
            t("webhook.acknowledge_xray_failed", lang=lang, error=str(e)),
        )


def _handle_guru_sync(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    try:
        results = sync_all_gurus(session)
        synced = sum(1 for r in results if r.get("status") == "synced")
        skipped = sum(1 for r in results if r.get("status") == "skipped")
        errors = sum(1 for r in results if r.get("status") == "error")
        return _wrap_response(
            success=True,
            message=t(
                "webhook.guru_sync_complete",
                lang=lang,
                total=len(results),
                synced=synced,
                skipped=skipped,
                errors=errors,
            ),
            interpretation=t("webhook.interpretation.guru_sync_ready", lang=lang),
            params=params,
            data={
                "total": len(results),
                "synced": synced,
                "skipped": skipped,
                "errors": errors,
            },
        )
    except Exception as e:
        logger.error("guru_sync 執行失敗：%s", e)
        return _internal_error_response(
            params, lang, t("webhook.guru_sync_failed", lang=lang, error=str(e))
        )


def _handle_guru_summary(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    try:
        result = send_filing_season_digest(session)
        return _wrap_response(
            success=True,
            message=t(
                "webhook.guru_summary_complete",
                lang=lang,
                status=result.get("status", ""),
                count=result.get("guru_count", 0),
            ),
            interpretation=t("webhook.interpretation.guru_summary_ready", lang=lang),
            params=params,
            data=result,
        )
    except Exception as e:
        logger.error("guru_summary 執行失敗：%s", e)
        return _internal_error_response(
            params, lang, t("webhook.guru_summary_failed", lang=lang, error=str(e))
        )


def _handle_transactions(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    ticker_filter = params.get("ticker")
    account_id_raw = params.get("account_id")
    start = params.get("start")
    end = params.get("end")
    try:
        account_id = int(account_id_raw) if account_id_raw is not None else None
        start_date = date_type.fromisoformat(str(start)) if start else None
        end_date = date_type.fromisoformat(str(end)) if end else None
        limit = max(1, min(int(params.get("limit", 10)), 50))
    except (TypeError, ValueError):
        return _validation_error_response(params, lang)
    txns = list_transactions(
        session,
        ticker=ticker_filter,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    count = len(txns)
    return _wrap_response(
        success=True,
        message=t("webhook.transactions_summary", lang=lang, count=count),
        interpretation=t(
            "webhook.interpretation.transactions_ready", lang=lang, count=count
        ),
        params=params,
        data={"transactions": txns, "count": count},
    )


def _handle_add_transaction(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    if not ticker:
        return _missing_ticker_response(params, lang)
    txn_type = str(params.get("type", "BUY")).upper()
    quantity = params.get("quantity")
    total_amount = params.get("total_amount")
    txn_date = params.get("date")
    account_id = params.get("account_id")
    if not quantity or not total_amount or not txn_date or account_id in (None, ""):
        return _wrap_response(
            success=False,
            message=t("webhook.missing_required_params", lang=lang),
            interpretation=t("webhook.interpretation.action_failed", lang=lang),
            params=params,
            error_code=ERROR_INVALID_INPUT,
        )
    price = params.get("price")
    try:
        parsed_data = {
            "ticker": ticker,
            "transaction_type": txn_type,
            "account_id": int(account_id),
            "quantity": float(quantity),
            "price": float(price) if price else None,
            "total_amount": float(total_amount),
            "transaction_date": date_type.fromisoformat(str(txn_date)).isoformat(),
        }
    except (TypeError, ValueError):
        return _validation_error_response(params, lang)
    try:
        result = create_transaction(session, parsed_data, lang)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        return _wrap_response(
            success=False,
            message=detail.get("detail", str(exc.detail)),
            interpretation=t("webhook.interpretation.action_failed", lang=lang),
            params=params,
            error_code=detail.get("error_code"),
        )
    return _wrap_response(
        success=True,
        message=t("transaction.created", lang=lang),
        interpretation=t("webhook.interpretation.transaction_recorded", lang=lang),
        params=params,
        data=result,
    )


def _handle_accounts(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    summary = get_account_summary(session)
    return _wrap_response(
        success=True,
        message=t("webhook.accounts_summary", lang=lang, count=len(summary)),
        interpretation=t("webhook.interpretation.accounts_ready", lang=lang),
        params=params,
        data={"accounts": summary, "count": len(summary)},
    )


def _handle_analytics(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    start = params.get("start")
    end = params.get("end")
    try:
        start_d = date_type.fromisoformat(str(start)) if start else None
        end_d = date_type.fromisoformat(str(end)) if end else None
    except (TypeError, ValueError):
        return _validation_error_response(params, lang)
    metrics = get_risk_metrics_svc(session, start=start_d, end=end_d)
    sharpe = metrics.get("sharpe_ratio", "N/A")
    max_dd_raw = metrics.get("max_drawdown_pct", 0)
    max_dd = f"{abs(max_dd_raw) * 100:.1f}%" if max_dd_raw else "N/A"
    return _wrap_response(
        success=True,
        message=t("webhook.analytics_summary", lang=lang),
        interpretation=t(
            "webhook.interpretation.analytics_ready",
            lang=lang,
            sharpe=sharpe,
            max_dd=max_dd,
        ),
        params=params,
        data=metrics,
    )


def _handle_quota(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    as_of = date_type.today()
    year_raw = params.get("year")
    try:
        year = int(year_raw) if year_raw is not None else as_of.year
    except (TypeError, ValueError):
        return _validation_error_response(params, lang)
    quotas = get_all_wrapper_quotas(session, DEFAULT_USER_ID, year, as_of)
    forecast = get_restoration_forecast(session, DEFAULT_USER_ID)
    return _wrap_response(
        success=True,
        message=t("webhook.quota_summary", lang=lang, count=len(quotas)),
        interpretation=t("webhook.interpretation.quota_ready", lang=lang),
        params=params,
        data={
            "year": year,
            "as_of": as_of.isoformat(),
            "restoration_policy": forecast.get("restoration_policy"),
            "quotas": quotas,
            "restoration_forecast": forecast,
        },
    )


def _handle_insights(
    session: Session, ticker: str | None, params: dict, lang: str
) -> dict:
    display_currency = str(params.get("display_currency", "USD"))
    insights = get_portfolio_insights(session, display_currency)
    return _wrap_response(
        success=True,
        message=t("webhook.insights_summary", lang=lang, count=len(insights)),
        interpretation=t("webhook.interpretation.insights_ready", lang=lang),
        params=params,
        data={"insights": insights, "count": len(insights)},
    )


_WEBHOOK_HANDLERS: dict[str, "Callable[[Session, str | None, dict, str], dict]"] = {
    "help": _handle_help,
    "summary": _handle_summary,
    "dashboard": _handle_dashboard,
    "signals": _handle_signals,
    "analyze": _handle_analyze,
    "scan": _handle_scan,
    "moat": _handle_moat,
    "alerts": _handle_alerts,
    "fear_greed": _handle_fear_greed,
    "add_stock": _handle_add_stock,
    "withdraw": _handle_withdraw,
    "fx_watch": _handle_fx_watch,
    "stock_splits": _handle_stock_splits,
    "dividends": _handle_dividends,
    "drift_alerts": _handle_drift_alerts,
    "acknowledge_drift": _handle_acknowledge_drift,
    "acknowledge_xray": _handle_acknowledge_xray,
    "guru_sync": _handle_guru_sync,
    "guru_summary": _handle_guru_summary,
    "transactions": _handle_transactions,
    "add_transaction": _handle_add_transaction,
    "accounts": _handle_accounts,
    "analytics": _handle_analytics,
    "quota": _handle_quota,
    "insights": _handle_insights,
}


def _unsupported_action_response(action: str, params: dict, lang: str) -> dict:
    supported = ", ".join(sorted(WEBHOOK_ACTION_REGISTRY.keys()))
    return _wrap_response(
        success=False,
        message=t(
            "webhook.unsupported_action", lang=lang, action=action, supported=supported
        ),
        interpretation=t("webhook.interpretation.action_failed", lang=lang),
        params=params,
        error_code=ERROR_INVALID_INPUT,
    )


def handle_webhook(
    session: Session, action: str, ticker: str | None, params: dict
) -> dict:
    """
    處理 AI agent webhook 請求。回傳 dict(success, message, interpretation, data)。
    業務邏輯分散於各 _handle_<action> 函式，此處僅負責正規化與派發。
    """
    lang = get_user_language(session)
    action = action.lower().strip()
    ticker = ticker.upper().strip() if ticker else None
    params = params or {}

    handler = _WEBHOOK_HANDLERS.get(action)
    if handler is None:
        return _unsupported_action_response(action, params, lang)

    return handler(session, ticker, params, lang)
