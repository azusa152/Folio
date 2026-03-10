import logging
import os
import tempfile

# Set environment variables BEFORE app/module imports
os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

from logging_config import _YfinanceNoiseFilter


class TestYfinanceNoiseFilter:
    """Verify known noisy yfinance lines are suppressed."""

    def test_should_drop_transient_ssl_transport_error_line(self):
        filt = _YfinanceNoiseFilter()
        record = logging.LogRecord(
            name="yfinance",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg=(
                "Failed to get ticker 'QQQ' reason: Failed to perform, curl: (35) "
                "BoringSSL SSL_connect: SSL_ERROR_SYSCALL in connection to "
                "query1.finance.yahoo.com:443"
            ),
            args=(),
            exc_info=None,
        )
        assert filt.filter(record) is False

    def test_should_drop_misleading_possibly_delisted_line(self):
        filt = _YfinanceNoiseFilter()
        record = logging.LogRecord(
            name="yfinance",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="$QQQ: possibly delisted; no price data found  (period=3mo)",
            args=(),
            exc_info=None,
        )
        assert filt.filter(record) is False

    def test_should_keep_other_yfinance_warning_lines(self):
        filt = _YfinanceNoiseFilter()
        record = logging.LogRecord(
            name="yfinance",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg="download returned partial history for some symbols",
            args=(),
            exc_info=None,
        )
        assert filt.filter(record) is True

    def test_should_not_affect_non_yfinance_loggers(self):
        filt = _YfinanceNoiseFilter()
        record = logging.LogRecord(
            name="application.stock.stock_service",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="custom application error should remain visible",
            args=(),
            exc_info=None,
        )
        assert filt.filter(record) is True
