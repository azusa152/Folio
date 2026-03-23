"""
Tests for ticker metadata cache functions (name/exchange).

Covers:
- get_ticker_name_cached/get_ticker_exchange_cached disk-cache-only behavior.
- _fetch_name_from_yf uses shortName first, then longName fallback.
- _fetch_exchange_from_yf returns exchange code or sentinel.
"""

from unittest.mock import patch

from domain.constants import (
    DISK_EXCHANGE_TTL,
    DISK_KEY_EXCHANGE,
    DISK_KEY_NAME,
    DISK_NAME_TTL,
)
from infrastructure.market_data.market_data import (
    _EXCHANGE_NOT_FOUND,
    _NAME_NOT_FOUND,
    _disk_set,
    _fetch_exchange_from_yf,
    _fetch_name_from_yf,
    get_ticker_exchange,
    get_ticker_exchange_cached,
    get_ticker_name,
    get_ticker_name_cached,
)


class TestGetTickerNameCached:
    def test_returns_name_on_cache_hit(self):
        _disk_set(f"{DISK_KEY_NAME}:AAPL", "Apple Inc.", DISK_NAME_TTL)
        assert get_ticker_name_cached("AAPL") == "Apple Inc."

    def test_returns_none_on_cache_miss(self):
        assert get_ticker_name_cached("NONEXISTENT_NAME_TICKER") is None

    def test_returns_none_for_name_not_found_sentinel(self):
        _disk_set(f"{DISK_KEY_NAME}:MISSING_NAME", _NAME_NOT_FOUND, DISK_NAME_TTL)
        assert get_ticker_name_cached("MISSING_NAME") is None

    @patch("infrastructure.market_data.market_data._fetch_name_from_yf")
    def test_never_calls_yfinance(self, mock_fetch):
        get_ticker_name_cached("AAPL")
        mock_fetch.assert_not_called()


class TestGetTickerExchangeCached:
    def test_returns_exchange_on_cache_hit(self):
        _disk_set(f"{DISK_KEY_EXCHANGE}:AAPL", "NMS", DISK_EXCHANGE_TTL)
        assert get_ticker_exchange_cached("AAPL") == "NMS"

    def test_returns_none_on_cache_miss(self):
        assert get_ticker_exchange_cached("NONEXISTENT_EXCHANGE_TICKER") is None

    def test_returns_none_for_exchange_not_found_sentinel(self):
        _disk_set(
            f"{DISK_KEY_EXCHANGE}:MISSING_EXCHANGE",
            _EXCHANGE_NOT_FOUND,
            DISK_EXCHANGE_TTL,
        )
        assert get_ticker_exchange_cached("MISSING_EXCHANGE") is None

    @patch("infrastructure.market_data.market_data._fetch_exchange_from_yf")
    def test_never_calls_yfinance(self, mock_fetch):
        get_ticker_exchange_cached("AAPL")
        mock_fetch.assert_not_called()


class TestGetTickerName:
    @patch("infrastructure.market_data.market_data._fetch_name_from_yf")
    @patch("infrastructure.market_data.market_data._disk_set")
    @patch("infrastructure.market_data.market_data._disk_get")
    def test_cache_miss_fetches_and_writes_disk(
        self, mock_disk_get, mock_disk_set, mock_fetch
    ):
        mock_disk_get.return_value = None
        mock_fetch.return_value = "Apple Inc."

        result = get_ticker_name("AAPL")

        assert result == "Apple Inc."
        mock_fetch.assert_called_once_with("AAPL")
        mock_disk_set.assert_called_once_with(
            f"{DISK_KEY_NAME}:AAPL", "Apple Inc.", DISK_NAME_TTL
        )

    @patch("infrastructure.market_data.market_data._fetch_name_from_yf")
    @patch("infrastructure.market_data.market_data._disk_get")
    def test_cache_hit_returns_without_fetch(self, mock_disk_get, mock_fetch):
        mock_disk_get.return_value = "Apple Inc."

        result = get_ticker_name("AAPL")

        assert result == "Apple Inc."
        mock_fetch.assert_not_called()


class TestGetTickerExchange:
    @patch("infrastructure.market_data.market_data._fetch_exchange_from_yf")
    @patch("infrastructure.market_data.market_data._disk_set")
    @patch("infrastructure.market_data.market_data._disk_get")
    def test_cache_miss_fetches_and_writes_disk(
        self, mock_disk_get, mock_disk_set, mock_fetch
    ):
        mock_disk_get.return_value = None
        mock_fetch.return_value = "NMS"

        result = get_ticker_exchange("AAPL")

        assert result == "NMS"
        mock_fetch.assert_called_once_with("AAPL")
        mock_disk_set.assert_called_once_with(
            f"{DISK_KEY_EXCHANGE}:AAPL", "NMS", DISK_EXCHANGE_TTL
        )

    @patch("infrastructure.market_data.market_data._fetch_exchange_from_yf")
    @patch("infrastructure.market_data.market_data._disk_get")
    def test_cache_hit_returns_without_fetch(self, mock_disk_get, mock_fetch):
        mock_disk_get.return_value = "NMS"

        result = get_ticker_exchange("AAPL")

        assert result == "NMS"
        mock_fetch.assert_not_called()


class TestFetchTickerMetadataFromYf:
    @patch("infrastructure.market_data.market_data._rate_limiter")
    @patch("infrastructure.market_data.market_data._yf_info")
    def test_fetch_name_prefers_short_name(self, mock_yf_info, _mock_rate_limiter):
        mock_yf_info.return_value = {
            "shortName": "Apple Inc.",
            "longName": "Apple Long",
        }
        assert _fetch_name_from_yf("AAPL") == "Apple Inc."

    @patch("infrastructure.market_data.market_data._rate_limiter")
    @patch("infrastructure.market_data.market_data._yf_info")
    def test_fetch_name_falls_back_to_long_name(self, mock_yf_info, _mock_rate_limiter):
        mock_yf_info.return_value = {"shortName": None, "longName": "Apple Long"}
        assert _fetch_name_from_yf("AAPL") == "Apple Long"

    @patch("infrastructure.market_data.market_data._rate_limiter")
    @patch("infrastructure.market_data.market_data._yf_info")
    def test_fetch_name_returns_sentinel_when_missing(
        self, mock_yf_info, _mock_rate_limiter
    ):
        mock_yf_info.return_value = {}
        assert _fetch_name_from_yf("UNKNOWN") == _NAME_NOT_FOUND

    @patch("infrastructure.market_data.market_data._rate_limiter")
    @patch("infrastructure.market_data.market_data._yf_info")
    def test_fetch_exchange_returns_exchange_code(
        self, mock_yf_info, _mock_rate_limiter
    ):
        mock_yf_info.return_value = {"exchange": "NMS"}
        assert _fetch_exchange_from_yf("AAPL") == "NMS"

    @patch("infrastructure.market_data.market_data._rate_limiter")
    @patch("infrastructure.market_data.market_data._yf_info")
    def test_fetch_exchange_returns_sentinel_when_missing(
        self, mock_yf_info, _mock_rate_limiter
    ):
        mock_yf_info.return_value = {}
        assert _fetch_exchange_from_yf("UNKNOWN") == _EXCHANGE_NOT_FOUND
