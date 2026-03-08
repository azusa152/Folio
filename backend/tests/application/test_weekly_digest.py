"""
Unit tests for send_weekly_digest() and get_portfolio_summary()
in application.messaging.notification_service.

All external I/O is mocked — no Telegram calls, no yfinance requests.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from sqlmodel import Session

from domain.entities import ScanLog, Stock
from domain.enums import ScanSignal, StockCategory
from tests.conftest import MOCK_FEAR_GREED

NOTIFICATION_MODULE = "application.messaging.notification_service"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_stock(
    session: Session,
    ticker: str,
    signal: str = ScanSignal.NORMAL.value,
    category: StockCategory = StockCategory.GROWTH,
) -> Stock:
    s = Stock(ticker=ticker, category=category, last_scan_signal=signal, is_active=True)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


def _add_scan_log(
    session: Session,
    ticker: str,
    signal: str,
    days_ago: float = 1.0,
) -> ScanLog:
    log = ScanLog(
        stock_ticker=ticker,
        signal=signal,
        market_status="BULLISH",
        scanned_at=datetime.now(UTC) - timedelta(days=days_ago),
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


# Shared patch targets
_FG_PATCH = f"{NOTIFICATION_MODULE}.get_fear_greed_index"
_TG_PATCH = f"{NOTIFICATION_MODULE}.send_telegram_message_dual"
_NOTIF_PATCH = f"{NOTIFICATION_MODULE}.is_notification_enabled"
_REBALANCE_PATCH = "application.portfolio.rebalance_service.calculate_rebalance"
_RESONANCE_PATCH = "application.guru.resonance_service.compute_portfolio_resonance"
_WOW_LOAD_PATCH = f"{NOTIFICATION_MODULE}._load_wow_state"
_WOW_SAVE_PATCH = f"{NOTIFICATION_MODULE}._save_wow_state"

MOCK_REBALANCE = {
    "total_value": 100_000.0,
    "total_value_change_pct": 1.4,
    "holdings_detail": [
        {"ticker": "NVDA", "change_pct": 5.2, "category": "Growth"},
        {"ticker": "MSFT", "change_pct": 2.1, "category": "Moat"},
        {"ticker": "BABA", "change_pct": -3.1, "category": "Growth"},
    ],
    "categories": {
        "Growth": {
            "target_pct": 40.0,
            "current_pct": 47.5,
            "drift_pct": 7.5,
            "market_value": 47_500.0,
        },
        "Moat": {
            "target_pct": 30.0,
            "current_pct": 28.0,
            "drift_pct": -2.0,
            "market_value": 28_000.0,
        },
    },
}

MOCK_RESONANCE = [
    {
        "guru_id": 1,
        "guru_display_name": "Warren Buffett",
        "overlapping_tickers": ["AAPL"],
        "overlap_count": 1,
        "holdings": [
            {
                "ticker": "AAPL",
                "action": "NEW_POSITION",
                "weight_pct": 2.5,
                "change_pct": 0.0,
            }
        ],
    }
]


# ---------------------------------------------------------------------------
# send_weekly_digest — existing behaviour
# ---------------------------------------------------------------------------


class TestSendWeeklyDigest:
    def test_should_include_health_score(self, db_session: Session):
        """Message must contain traffic-light health indicator when stocks are present."""
        from application.messaging.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)
        _add_stock(db_session, "MSFT", ScanSignal.NORMAL.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_TG_PATCH) as mock_send,
            patch(_NOTIF_PATCH, return_value=True),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_WOW_LOAD_PATCH, return_value={}),
            patch(_WOW_SAVE_PATCH),
        ):
            result = send_weekly_digest(db_session)

        assert result["health_score"] == 100.0
        sent_message = mock_send.call_args[0][0]
        assert "🟢" in sent_message

    def test_should_list_abnormal_stocks(self, db_session: Session):
        """Non-normal owned stocks must appear in the Telegram message."""
        from application.messaging.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)
        _add_stock(db_session, "BABA", ScanSignal.THESIS_BROKEN.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_TG_PATCH) as mock_send,
            patch(_NOTIF_PATCH, return_value=True),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_WOW_LOAD_PATCH, return_value={}),
            patch(_WOW_SAVE_PATCH),
        ):
            result = send_weekly_digest(db_session)

        assert result["health_score"] == 0.0
        sent_message = mock_send.call_args[0][0]
        assert "BABA" in sent_message
        assert ScanSignal.THESIS_BROKEN.value in sent_message

    def test_should_report_signal_changes(self, db_session: Session):
        """Signal changes for owned tickers must appear with transition direction."""
        from application.messaging.notification_service import send_weekly_digest

        _add_stock(db_session, "NVDA", ScanSignal.OVERSOLD.value)
        _add_scan_log(db_session, "NVDA", ScanSignal.NORMAL.value, days_ago=3)
        _add_scan_log(db_session, "NVDA", ScanSignal.OVERSOLD.value, days_ago=1)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_TG_PATCH) as mock_send,
            patch(_NOTIF_PATCH, return_value=True),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_WOW_LOAD_PATCH, return_value={}),
            patch(_WOW_SAVE_PATCH),
        ):
            send_weekly_digest(db_session)

        sent_message = mock_send.call_args[0][0]
        assert "NVDA" in sent_message
        assert "NORMAL" in sent_message
        assert "OVERSOLD" in sent_message
        assert "notification.change_label" not in sent_message
        assert "notification.times_label" not in sent_message
        assert "notification.signal_change_detail" not in sent_message

    def test_should_handle_empty_portfolio(self, db_session: Session):
        """When watchlist is empty the no_stocks key must render as real text."""
        from application.messaging.notification_service import send_weekly_digest

        with patch(_TG_PATCH) as mock_send:
            result = send_weekly_digest(db_session)

        mock_send.assert_called_once()
        sent_message = mock_send.call_args[0][0]
        # Must not echo back raw i18n keys
        assert "notification.no_stocks" not in sent_message
        assert "notification.weekly_digest_title" not in sent_message
        # Result dict message must also be a real string
        assert "notification." not in result["message"]

    def test_should_skip_when_notification_disabled(self, db_session: Session):
        """When weekly_digest notification is disabled, Telegram must not be called."""
        from application.messaging.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_TG_PATCH) as mock_send,
            patch(_NOTIF_PATCH, return_value=False),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_WOW_LOAD_PATCH, return_value={}),
            patch(_WOW_SAVE_PATCH),
        ):
            send_weekly_digest(db_session)

        mock_send.assert_not_called()

    def test_should_report_all_normal(self, db_session: Session):
        """When all stocks are normal the all_normal translation must appear verbatim."""
        from application.messaging.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)
        _add_stock(db_session, "MSFT", ScanSignal.NORMAL.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_TG_PATCH) as mock_send,
            patch(_NOTIF_PATCH, return_value=True),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_WOW_LOAD_PATCH, return_value={}),
            patch(_WOW_SAVE_PATCH),
        ):
            send_weekly_digest(db_session)

        sent_message = mock_send.call_args[0][0]
        assert "notification.all_normal" not in sent_message
        assert "✅" in sent_message


# ---------------------------------------------------------------------------
# _format_health_line — traffic-light levels
# ---------------------------------------------------------------------------


class TestFormatHealthLine:
    def test_should_return_green_when_all_clear(self):
        from application.messaging.notification_service import _format_health_line

        result = _format_health_line(100.0, 5, 5, "en")
        assert "🟢" in result

    def test_should_return_yellow_when_attention_needed(self):
        from application.messaging.notification_service import _format_health_line

        result = _format_health_line(85.0, 6, 7, "en")
        assert "🟡" in result

    def test_should_return_red_when_review_needed(self):
        from application.messaging.notification_service import _format_health_line

        result = _format_health_line(50.0, 2, 4, "en")
        assert "🔴" in result

    def test_should_return_yellow_at_boundary(self):
        from application.messaging.notification_service import _format_health_line

        result = _format_health_line(70.0, 7, 10, "en")
        assert "🟡" in result


# ---------------------------------------------------------------------------
# send_weekly_digest — enriched sections (portfolio value, movers, drift, owned-stock filter)
# ---------------------------------------------------------------------------


class TestSendWeeklyDigestEnriched:
    def test_should_include_portfolio_value_with_wow(self, db_session: Session):
        """When previous total exists, WoW line must be in the message."""
        from application.messaging.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)

        wow_state = {"last_total_value": 95_000.0}

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_TG_PATCH) as mock_send,
            patch(_NOTIF_PATCH, return_value=True),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_WOW_LOAD_PATCH, return_value=wow_state),
            patch(_WOW_SAVE_PATCH),
        ):
            send_weekly_digest(db_session)

        sent_message = mock_send.call_args[0][0]
        assert "100,000" in sent_message
        assert "5.3" in sent_message
        assert "WoW" in sent_message

    def test_should_include_portfolio_value_no_prev(self, db_session: Session):
        """When no previous total, just the current value must appear (no WoW %)."""
        from application.messaging.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_TG_PATCH) as mock_send,
            patch(_NOTIF_PATCH, return_value=True),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_WOW_LOAD_PATCH, return_value={}),
            patch(_WOW_SAVE_PATCH),
        ):
            send_weekly_digest(db_session)

        sent_message = mock_send.call_args[0][0]
        assert "100,000" in sent_message

    def test_should_include_top_movers(self, db_session: Session):
        """Top movers section must list gainers and losers by ticker."""
        from application.messaging.notification_service import send_weekly_digest

        _add_stock(db_session, "NVDA", ScanSignal.NORMAL.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_TG_PATCH) as mock_send,
            patch(_NOTIF_PATCH, return_value=True),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_WOW_LOAD_PATCH, return_value={}),
            patch(_WOW_SAVE_PATCH),
        ):
            send_weekly_digest(db_session)

        sent_message = mock_send.call_args[0][0]
        assert "NVDA" in sent_message
        assert "BABA" in sent_message
        assert "notification.top_movers_title" not in sent_message

    def test_should_include_drift_when_over_threshold(self, db_session: Session):
        """Drift section must appear when a category exceeds DRIFT_THRESHOLD_PCT."""
        from application.messaging.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_TG_PATCH) as mock_send,
            patch(_NOTIF_PATCH, return_value=True),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_WOW_LOAD_PATCH, return_value={}),
            patch(_WOW_SAVE_PATCH),
        ):
            send_weekly_digest(db_session)

        sent_message = mock_send.call_args[0][0]
        assert "notification.drift_title" not in sent_message
        assert "⚖️" in sent_message
        assert "7.5" in sent_message

    def test_should_skip_drift_when_under_threshold(self, db_session: Session):
        """Drift section must NOT appear when all categories are within threshold."""
        from application.messaging.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)

        rebalance_no_drift = {
            **MOCK_REBALANCE,
            "categories": {
                "Growth": {
                    "target_pct": 40.0,
                    "current_pct": 42.0,
                    "drift_pct": 2.0,
                    "market_value": 42_000.0,
                },
                "Moat": {
                    "target_pct": 30.0,
                    "current_pct": 31.0,
                    "drift_pct": 1.0,
                    "market_value": 31_000.0,
                },
            },
        }

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_TG_PATCH) as mock_send,
            patch(_NOTIF_PATCH, return_value=True),
            patch(_REBALANCE_PATCH, return_value=rebalance_no_drift),
            patch(_WOW_LOAD_PATCH, return_value={}),
            patch(_WOW_SAVE_PATCH),
        ):
            send_weekly_digest(db_session)

        sent_message = mock_send.call_args[0][0]
        assert "⚖️" not in sent_message

    def test_should_exclude_watchlist_only_signals(self, db_session: Session):
        """Signals for stocks not in holdings must be excluded from digest."""
        from application.messaging.notification_service import send_weekly_digest

        _add_stock(db_session, "NVDA", ScanSignal.NORMAL.value)
        _add_stock(db_session, "PLTR", ScanSignal.THESIS_BROKEN.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_TG_PATCH) as mock_send,
            patch(_NOTIF_PATCH, return_value=True),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_WOW_LOAD_PATCH, return_value={}),
            patch(_WOW_SAVE_PATCH),
        ):
            send_weekly_digest(db_session)

        sent_message = mock_send.call_args[0][0]
        assert "PLTR" not in sent_message

    def test_should_gracefully_handle_rebalance_failure(self, db_session: Session):
        """When rebalance data is unavailable, digest must still send without crashing."""
        from application.messaging.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_TG_PATCH) as mock_send,
            patch(_NOTIF_PATCH, return_value=True),
            patch(_REBALANCE_PATCH, side_effect=RuntimeError("yfinance error")),
            patch(_WOW_LOAD_PATCH, return_value={}),
            patch(_WOW_SAVE_PATCH),
        ):
            result = send_weekly_digest(db_session)

        mock_send.assert_called_once()
        assert result["health_score"] == 100.0


# ---------------------------------------------------------------------------
# get_portfolio_summary
# ---------------------------------------------------------------------------


class TestGetPortfolioSummary:
    def test_should_include_categories(self, db_session: Session):
        """Summary must group stocks by category and not echo raw i18n keys."""
        from application.messaging.notification_service import get_portfolio_summary

        _add_stock(
            db_session, "AAPL", ScanSignal.NORMAL.value, StockCategory.TREND_SETTER
        )
        _add_stock(
            db_session, "MSFT", ScanSignal.NORMAL.value, StockCategory.TREND_SETTER
        )

        with patch(_FG_PATCH, return_value=MOCK_FEAR_GREED):
            summary = get_portfolio_summary(db_session)

        assert "AAPL" in summary
        assert "MSFT" in summary
        assert "notification.portfolio_summary_health" not in summary

    def test_should_handle_empty(self, db_session: Session):
        """Empty portfolio must return a real string, not a raw i18n key."""
        from application.messaging.notification_service import get_portfolio_summary

        summary = get_portfolio_summary(db_session)

        assert "notification.portfolio_summary_no_stocks" not in summary
        assert len(summary) > 0

    def test_should_show_abnormal_section_for_non_normal_stocks(
        self, db_session: Session
    ):
        """Stocks with active signals must appear in the abnormal section."""
        from application.messaging.notification_service import get_portfolio_summary

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value, StockCategory.MOAT)
        _add_stock(
            db_session, "BABA", ScanSignal.THESIS_BROKEN.value, StockCategory.MOAT
        )
        _add_stock(db_session, "NIO", ScanSignal.OVERSOLD.value, StockCategory.GROWTH)

        with patch(_FG_PATCH, return_value=MOCK_FEAR_GREED):
            summary = get_portfolio_summary(db_session)

        # Raw key must not leak
        assert "notification.portfolio_summary_abnormal" not in summary
        assert "notification.portfolio_summary_normal" not in summary
        # Abnormal tickers and their signals must be present
        assert "BABA" in summary
        assert ScanSignal.THESIS_BROKEN.value in summary
        assert "NIO" in summary
        assert ScanSignal.OVERSOLD.value in summary
        # Normal ticker must not appear in the abnormal section
        # (it will appear in the category group, but not after the abnormal header)
        abnormal_section = summary.split("BABA")[1] if "BABA" in summary else ""
        assert "AAPL" not in abnormal_section

    def test_should_include_portfolio_value_with_daily_change(
        self, db_session: Session
    ):
        """Portfolio value line with total value and daily change % must appear."""
        from application.messaging.notification_service import get_portfolio_summary

        _add_stock(db_session, "NVDA", ScanSignal.NORMAL.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_RESONANCE_PATCH, return_value=[]),
        ):
            summary = get_portfolio_summary(db_session)

        # Total value must be present
        assert "100,000" in summary
        # Daily change % from total_value_change_pct=1.4 must appear
        assert "1.4" in summary
        # Raw key must not appear
        assert "notification.portfolio_summary_value" not in summary

    def test_should_include_top_movers(self, db_session: Session):
        """Top movers (gainers + losers) must appear when rebalance holdings have change_pct."""
        from application.messaging.notification_service import get_portfolio_summary

        _add_stock(db_session, "NVDA", ScanSignal.NORMAL.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_RESONANCE_PATCH, return_value=[]),
        ):
            summary = get_portfolio_summary(db_session)

        # Both a gainer and a loser from MOCK_REBALANCE must appear
        assert "NVDA" in summary
        assert "BABA" in summary
        # Top movers section header must not be a raw key
        assert "notification.top_movers_title" not in summary
        # Section header emoji must be present
        assert "🏆" in summary

    def test_should_include_drift_warnings_when_over_threshold(
        self, db_session: Session
    ):
        """Drift section must appear when a category exceeds DRIFT_THRESHOLD_PCT."""
        from application.messaging.notification_service import get_portfolio_summary

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)

        # MOCK_REBALANCE has Growth drift = +7.5% (above threshold of 5%)
        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_RESONANCE_PATCH, return_value=[]),
        ):
            summary = get_portfolio_summary(db_session)

        assert "notification.drift_title" not in summary
        assert "⚖️" in summary
        assert "7.5" in summary

    def test_should_omit_drift_when_under_threshold(self, db_session: Session):
        """Drift section must NOT appear when all categories are within threshold."""
        from application.messaging.notification_service import get_portfolio_summary

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)

        rebalance_no_drift = {
            **MOCK_REBALANCE,
            "categories": {
                "Growth": {
                    "target_pct": 40.0,
                    "current_pct": 42.0,
                    "drift_pct": 2.0,
                    "market_value": 42_000.0,
                },
            },
        }

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_REBALANCE_PATCH, return_value=rebalance_no_drift),
            patch(_RESONANCE_PATCH, return_value=[]),
        ):
            summary = get_portfolio_summary(db_session)

        assert "⚖️" not in summary

    def test_should_include_smart_money_alert(self, db_session: Session):
        """Smart Money section must appear when guru has a NEW_POSITION action."""
        from application.messaging.notification_service import get_portfolio_summary

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_RESONANCE_PATCH, return_value=MOCK_RESONANCE),
        ):
            summary = get_portfolio_summary(db_session)

        assert "AAPL" in summary
        assert "Buffett" in summary
        assert "notification.smart_money_title" not in summary
        assert "🧠" in summary

    def test_should_omit_smart_money_when_no_alert_actions(self, db_session: Session):
        """Smart Money section must be absent when no NEW_POSITION/SOLD_OUT actions."""
        from application.messaging.notification_service import get_portfolio_summary

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)

        resonance_unchanged = [
            {
                "guru_id": 1,
                "guru_display_name": "Warren Buffett",
                "overlapping_tickers": ["AAPL"],
                "overlap_count": 1,
                "holdings": [
                    {
                        "ticker": "AAPL",
                        "action": "UNCHANGED",
                        "weight_pct": 2.5,
                        "change_pct": 0.0,
                    }
                ],
            }
        ]

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_RESONANCE_PATCH, return_value=resonance_unchanged),
        ):
            summary = get_portfolio_summary(db_session)

        assert "🧠" not in summary

    def test_should_handle_rebalance_failure_gracefully(self, db_session: Session):
        """When rebalance raises, summary must still return without value/movers/drift sections."""
        from application.messaging.notification_service import get_portfolio_summary

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)

        with (
            patch(_FG_PATCH, return_value=MOCK_FEAR_GREED),
            patch(_REBALANCE_PATCH, side_effect=RuntimeError("yfinance error")),
            patch(_RESONANCE_PATCH, return_value=[]),
        ):
            summary = get_portfolio_summary(db_session)

        # Must still return a non-empty summary
        assert len(summary) > 0
        assert "AAPL" in summary
        # Value section must not appear
        assert "💰" not in summary
