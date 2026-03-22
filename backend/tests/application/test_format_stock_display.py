"""
Tests for format_stock_display utility in application.formatters.
"""

from application.formatters import format_stock_display


class TestFormatStockDisplay:
    """Tests for the format_stock_display utility."""

    def test_returns_name_and_ticker_when_name_available(self):
        assert format_stock_display("Apple Inc.", "AAPL") == "Apple Inc. (AAPL)"

    def test_returns_ticker_only_when_name_is_none(self):
        assert format_stock_display(None, "AAPL") == "AAPL"

    def test_returns_ticker_only_when_name_is_empty_string(self):
        assert format_stock_display("", "AAPL") == "AAPL"

    def test_works_with_mutual_fund_numeric_ticker(self):
        assert (
            format_stock_display("eMAXIS Slim 米国株式(S&P500)", "01312179")
            == "eMAXIS Slim 米国株式(S&P500) (01312179)"
        )

    def test_works_with_japanese_ticker(self):
        assert format_stock_display("Toyota Motor", "7203.T") == "Toyota Motor (7203.T)"

    def test_works_with_taiwanese_ticker(self):
        assert (
            format_stock_display("Taiwan Semiconductor", "2330.TW")
            == "Taiwan Semiconductor (2330.TW)"
        )

    def test_works_with_crypto_ticker(self):
        assert format_stock_display("Bitcoin", "BTC-USD") == "Bitcoin (BTC-USD)"

    def test_returns_ticker_only_when_name_is_whitespace(self):
        assert format_stock_display("   ", "AAPL") == "AAPL"

    def test_strips_leading_trailing_whitespace_from_name(self):
        assert format_stock_display("  Apple Inc.  ", "AAPL") == "Apple Inc. (AAPL)"
