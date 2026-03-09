"""
Application — Webhook Service：OpenClaw / AI agent webhook 處理。
"""

from collections.abc import Mapping

from sqlmodel import Session

from application.formatters import format_fear_greed_label
from application.messaging.notification_service import (
    get_portfolio_summary,
    send_filing_season_digest,
)
from application.portfolio.fx_watch_service import send_fx_watch_alerts
from application.portfolio.rebalance_service import calculate_withdrawal
from application.scan.scan_service import list_price_alerts, run_scan
from application.stock.filing_service import sync_all_gurus
from application.stock.stock_service import (
    StockAlreadyExistsError,
    StockNotFoundError,
    create_stock,
    get_fundamentals_for_ticker,
)
from domain.constants import (
    DEFAULT_IMPORT_CATEGORY,
    DEFAULT_WEBHOOK_THESIS,
    WEBHOOK_ACTION_REGISTRY,
)
from domain.enums import StockCategory
from i18n import get_user_language, t
from infrastructure.market_data import (
    analyze_moat_trend,
    get_fear_greed_index,
    get_technical_signals,
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
    always_include_data: bool = False,
) -> dict:
    response: dict = {
        "success": success,
        "message": message,
        "interpretation": interpretation,
    }
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


def handle_webhook(
    session: Session, action: str, ticker: str | None, params: dict
) -> dict:
    """
    處理 AI agent webhook 請求。回傳 dict(success, message, interpretation, data)。
    業務邏輯集中於此，API handler 只負責 parse + 回傳。
    """
    import threading as _threading

    lang = get_user_language(session)
    action = action.lower().strip()
    ticker = ticker.upper().strip() if ticker else None
    params = params or {}

    # Validate action against registry
    if action not in WEBHOOK_ACTION_REGISTRY:
        supported = ", ".join(sorted(WEBHOOK_ACTION_REGISTRY.keys()))
        message = t(
            "webhook.unsupported_action",
            lang=lang,
            action=action,
            supported=supported,
        )
        return _wrap_response(
            success=False,
            message=message,
            interpretation=t("webhook.interpretation.action_failed", lang=lang),
            params=params,
        )

    if action == "help":
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
                },
                "model_hint": t("webhook.help_model_hint", lang=lang),
            },
            always_include_data=True,
        )

    if action == "summary":
        text = get_portfolio_summary(session)
        return _wrap_response(
            success=True,
            message=text,
            interpretation=t("webhook.interpretation.summary_ready", lang=lang),
            params=params,
        )

    if action == "dashboard":
        summary = get_portfolio_summary(session)
        fg = get_fear_greed_index()
        fg_label = format_fear_greed_label(
            fg.get("composite_level", "N/A"),
            fg.get("composite_score", 50),
            lang=lang,
        )
        message = (
            f"{summary}\n\n{t('webhook.fear_greed_prefix', lang=lang)}: {fg_label}"
        )
        return _wrap_response(
            success=True,
            message=message,
            interpretation=t("webhook.interpretation.dashboard_ready", lang=lang),
            params=params,
            data={"fear_greed": fg},
        )

    if action == "signals":
        if not ticker:
            return _wrap_response(
                success=False,
                message=t("webhook.missing_ticker", lang=lang),
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )
        result = get_technical_signals(ticker)
        if not result or "error" in result:
            message = (
                result.get("error", t("webhook.signals_unavailable", lang=lang))
                if result
                else t("webhook.signals_unavailable", lang=lang)
            )
            return _wrap_response(
                success=False,
                message=message,
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )
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

    if action == "analyze":
        if not ticker:
            return _wrap_response(
                success=False,
                message=t("webhook.missing_ticker", lang=lang),
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )
        signals = get_technical_signals(ticker)
        if not signals or "error" in signals:
            message = (
                signals.get("error", t("webhook.signals_unavailable", lang=lang))
                if signals
                else t("webhook.signals_unavailable", lang=lang)
            )
            return _wrap_response(
                success=False,
                message=message,
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )
        moat = analyze_moat_trend(ticker)
        fundamentals = get_fundamentals_for_ticker(ticker)
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
            data={
                "signals": signals,
                "moat": moat,
                "fundamentals": fundamentals,
            },
        )

    if action == "scan":
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

    if action == "moat":
        if not ticker:
            return _wrap_response(
                success=False,
                message=t("webhook.missing_ticker", lang=lang),
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )
        result = analyze_moat_trend(ticker)
        details = result.get("details", "N/A")
        return _wrap_response(
            success=True,
            message=t(
                "webhook.moat_result",
                lang=lang,
                ticker=ticker,
                moat=result.get("moat", "N/A"),
                details=details,
            ),
            interpretation=t("webhook.interpretation.moat_ready", lang=lang),
            params=params,
            data=result,
        )

    if action == "alerts":
        if not ticker:
            return _wrap_response(
                success=False,
                message=t("webhook.missing_ticker", lang=lang),
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )
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
            status_label = t("webhook.alert_status.active", lang=lang)
            inactive_label = t("webhook.alert_status.inactive", lang=lang)
            lines.append(
                f"  {a['metric']} {op_str} {a['threshold']} ({status_label if a['is_active'] else inactive_label})"
            )
        return _wrap_response(
            success=True,
            message="\n".join(lines),
            interpretation=t("webhook.interpretation.alerts_ready", lang=lang),
            params=params,
            data={"alerts": alerts},
        )

    if action == "fear_greed":
        fg = get_fear_greed_index()
        fg_label = format_fear_greed_label(
            fg.get("composite_level", "N/A"),
            fg.get("composite_score", 50),
            lang=lang,
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
        fg_label_prefix = t("webhook.fear_greed_prefix", lang=lang)
        msg = f"{fg_label_prefix}：{fg_label}\n{vix_text}, {cnn_text}"
        return _wrap_response(
            success=True,
            message=msg,
            interpretation=t("webhook.interpretation.fear_greed_ready", lang=lang),
            params=params,
            data=fg,
        )

    if action == "add_stock":
        t_ticker = params.get("ticker", ticker)
        if not t_ticker:
            return _wrap_response(
                success=False,
                message=t("webhook.missing_ticker", lang=lang),
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )
        cat_str = str(params.get("category", DEFAULT_IMPORT_CATEGORY))
        thesis = str(params.get("thesis") or t(DEFAULT_WEBHOOK_THESIS, lang=lang))
        tags = params.get("tags", [])
        try:
            stock = create_stock(
                session, str(t_ticker), StockCategory(cat_str), thesis, tags
            )
            return _wrap_response(
                success=True,
                message=t(
                    "stock.added", lang=lang, ticker=stock.ticker, category=cat_str
                ),
                interpretation=t("webhook.interpretation.add_stock_ready", lang=lang),
                params=params,
            )
        except StockAlreadyExistsError:
            return _wrap_response(
                success=False,
                message=t("stock.already_exists", lang=lang, ticker=str(t_ticker)),
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )
        except ValueError:
            return _wrap_response(
                success=False,
                message=t("webhook.invalid_category", lang=lang, category=cat_str),
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )

    if action == "withdraw":
        amount = params.get("amount")
        if not amount:
            return _wrap_response(
                success=False,
                message=t("webhook.missing_amount", lang=lang),
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )
        try:
            amount_float = float(amount)
        except (ValueError, TypeError):
            return _wrap_response(
                success=False,
                message=t("webhook.invalid_amount", lang=lang, amount=amount),
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
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
            )

    if action == "fx_watch":
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
            return _wrap_response(
                success=False,
                message=t("webhook.fx_watch_failed", lang=lang, error=str(e)),
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )

    if action == "guru_sync":
        try:
            results = sync_all_gurus(session)
            synced = sum(1 for r in results if r.get("status") == "synced")
            skipped = sum(1 for r in results if r.get("status") == "skipped")
            errors = sum(1 for r in results if r.get("status") == "error")
            msg = t(
                "webhook.guru_sync_complete",
                lang=lang,
                total=len(results),
                synced=synced,
                skipped=skipped,
                errors=errors,
            )
            return _wrap_response(
                success=True,
                message=msg,
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
            return _wrap_response(
                success=False,
                message=t("webhook.guru_sync_failed", lang=lang, error=str(e)),
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )

    if action == "guru_summary":
        try:
            result = send_filing_season_digest(session)
            msg = t(
                "webhook.guru_summary_complete",
                lang=lang,
                status=result.get("status", ""),
                count=result.get("guru_count", 0),
            )
            return _wrap_response(
                success=True,
                message=msg,
                interpretation=t(
                    "webhook.interpretation.guru_summary_ready",
                    lang=lang,
                ),
                params=params,
                data=result,
            )
        except Exception as e:
            logger.error("guru_summary 執行失敗：%s", e)
            return _wrap_response(
                success=False,
                message=t("webhook.guru_summary_failed", lang=lang, error=str(e)),
                interpretation=t("webhook.interpretation.action_failed", lang=lang),
                params=params,
            )

    # Fallback — should not reach here if registry is in sync
    supported = ", ".join(sorted(WEBHOOK_ACTION_REGISTRY.keys()))
    return _wrap_response(
        success=False,
        message=t(
            "webhook.unsupported_action", lang=lang, action=action, supported=supported
        ),
        interpretation=t("webhook.interpretation.action_failed", lang=lang),
        params=params,
    )
