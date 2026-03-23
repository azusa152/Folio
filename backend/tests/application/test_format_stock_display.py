"""
Tests for format_stock_display and resolve_display_names utilities in application.formatters.
"""

from unittest.mock import MagicMock, patch

from application.formatters import format_stock_display, resolve_display_names


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


class TestResolveDisplayNames:
    """Tests for the resolve_display_names batch helper."""

    def test_returns_empty_dict_for_empty_input(self):
        result = resolve_display_names([])
        assert result == {}

    def test_returns_empty_dict_for_whitespace_only_tickers(self):
        result = resolve_display_names(["", "  ", "\t"])
        assert result == {}

    def test_session_none_skips_fund_lookup_uses_cache_only(self):
        with patch(
            "infrastructure.market_data.market_data.get_ticker_name_cached",
            return_value="Apple Inc.",
        ) as mock_cache:
            result = resolve_display_names(["AAPL"], session=None)
        assert result.get("AAPL") == "Apple Inc."
        mock_cache.assert_called_once_with("AAPL")

    def test_normalizes_keys_to_uppercase(self):
        """Keys in the returned dict must be uppercase regardless of input casing."""
        with patch(
            "infrastructure.market_data.market_data.get_ticker_name_cached",
            return_value="Apple Inc.",
        ):
            result = resolve_display_names(["aapl"], session=None)
        assert "AAPL" in result
        assert "aapl" not in result

    def test_mixed_case_input_deduplicates_to_single_key(self):
        """'aapl' and 'AAPL' should resolve to exactly one uppercase key."""
        with patch(
            "infrastructure.market_data.market_data.get_ticker_name_cached",
            return_value="Apple Inc.",
        ):
            result = resolve_display_names(["aapl", "AAPL"], session=None)
        assert list(result.keys()) == ["AAPL"]

    def test_fund_name_takes_priority_over_cache(self):
        """EligibleAsset fund name should win over yfinance cache name."""
        mock_session = MagicMock()
        with (
            patch(
                "infrastructure.persistence.repositories.eligible_repo.find_fund_names_by_tickers",
                return_value={"01311143": "eMAXIS Slim S&P500"},
            ),
            patch(
                "infrastructure.market_data.market_data.get_ticker_name_cached",
                return_value="Some Cache Name",
            ) as mock_cache,
        ):
            result = resolve_display_names(["01311143"], session=mock_session)
        assert result["01311143"] == "eMAXIS Slim S&P500"
        # Cache should not be called for a ticker that already has a fund name
        mock_cache.assert_not_called()

    def test_cache_fallback_used_when_no_fund_name(self):
        """Tickers absent from fund DB fall back to disk-cached yfinance name."""
        mock_session = MagicMock()
        with (
            patch(
                "infrastructure.persistence.repositories.eligible_repo.find_fund_names_by_tickers",
                return_value={},
            ),
            patch(
                "infrastructure.market_data.market_data.get_ticker_name_cached",
                return_value="Apple Inc.",
            ),
        ):
            result = resolve_display_names(["AAPL"], session=mock_session)
        assert result["AAPL"] == "Apple Inc."

    def test_tickers_with_no_name_are_absent_from_result(self):
        """Tickers that cannot be resolved should not appear in the result dict."""
        mock_session = MagicMock()
        with (
            patch(
                "infrastructure.persistence.repositories.eligible_repo.find_fund_names_by_tickers",
                return_value={},
            ),
            patch(
                "infrastructure.market_data.market_data.get_ticker_name_cached",
                return_value=None,
            ),
        ):
            result = resolve_display_names(["UNKNOWN"], session=mock_session)
        assert "UNKNOWN" not in result
        assert result == {}

    def test_whitespace_only_cache_name_is_excluded(self):
        """A cache result that is only whitespace must not be stored."""
        with patch(
            "infrastructure.market_data.market_data.get_ticker_name_cached",
            return_value="   ",
        ):
            result = resolve_display_names(["AAPL"], session=None)
        assert result == {}

    def test_strips_whitespace_from_stored_names(self):
        """Names from both fund DB and cache should be stripped before storing."""
        with patch(
            "infrastructure.market_data.market_data.get_ticker_name_cached",
            return_value="  Apple Inc.  ",
        ):
            result = resolve_display_names(["AAPL"], session=None)
        assert result["AAPL"] == "Apple Inc."
