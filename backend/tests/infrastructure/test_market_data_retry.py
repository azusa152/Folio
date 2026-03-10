"""
Tests for yfinance retry logic and cache error-skipping behavior.

Covers:
- _cached_fetch does NOT write error results to L2/disk cache.
- _cached_fetch still writes error results to L1 cache.
- _cached_fetch writes successful results to both L1 and L2.
- Retry decorator retries on CurlError / ConnectionError / OSError.
- Non-network errors (e.g., ValueError) are NOT retried.
"""

import os
import tempfile

# Set environment variables BEFORE any app imports
os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import domain.constants

domain.constants.DISK_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "folio_test_cache_retry"
)

from unittest.mock import MagicMock, patch  # noqa: E402

import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from cachetools import TTLCache  # noqa: E402
from curl_cffi.curl import CurlError  # noqa: E402
from tenacity import stop_after_attempt, wait_none  # noqa: E402

from infrastructure.market_data.market_data import (  # noqa: E402
    _ETF_NOT_FOUND_SENTINEL,
    _ETF_SECTOR_WEIGHTS_NOT_FOUND,
    _cached_fetch,
    _etf_holdings_cache,
    _fetch_etf_top_holdings,
    _is_error_dict,
    _is_moat_error,
    _yf_retry,
    get_etf_sector_weights,
    get_etf_top_holdings,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DISK_PREFIX = "test_signals"
DISK_TTL = 60


def _fresh_l1() -> TTLCache:
    """Create a fresh L1 cache for test isolation."""
    return TTLCache(maxsize=100, ttl=300)


# ---------------------------------------------------------------------------
# _cached_fetch — error results should NOT be written to disk
# ---------------------------------------------------------------------------


class TestCachedFetchErrorSkip:
    """Verify that _cached_fetch skips L2/disk writes for error results."""

    def test_cached_fetch_should_skip_disk_write_for_error_result(self):
        # Arrange
        l1 = _fresh_l1()
        error_result = {"error": "⚠️ Could not resolve host"}

        with (
            patch(
                "infrastructure.market_data.market_data._disk_get", return_value=None
            ),
            patch("infrastructure.market_data.market_data._disk_set") as mock_disk_set,
        ):
            fetcher = MagicMock(return_value=error_result)

            # Act
            result = _cached_fetch(
                l1,
                "NVDA",
                DISK_PREFIX,
                DISK_TTL,
                fetcher,
                is_error=_is_error_dict,
            )

            # Assert — result is returned correctly
            assert result == error_result
            # Assert — fetcher was called
            fetcher.assert_called_once_with("NVDA")
            # Assert — disk_set was NOT called (error not persisted to L2)
            mock_disk_set.assert_not_called()

    def test_cached_fetch_should_still_write_error_result_to_l1(self):
        # Arrange
        l1 = _fresh_l1()
        error_result = {"error": "⚠️ DNS failure"}

        with (
            patch(
                "infrastructure.market_data.market_data._disk_get", return_value=None
            ),
            patch("infrastructure.market_data.market_data._disk_set"),
        ):
            fetcher = MagicMock(return_value=error_result)

            # Act
            _cached_fetch(
                l1,
                "NVDA",
                DISK_PREFIX,
                DISK_TTL,
                fetcher,
                is_error=_is_error_dict,
            )

            # Assert — error result is in L1
            assert l1.get("NVDA") == error_result

    def test_cached_fetch_should_write_success_result_to_both_caches(self):
        # Arrange
        l1 = _fresh_l1()
        success_result = {"ticker": "NVDA", "price": 120.0, "rsi": 55.0}

        with (
            patch(
                "infrastructure.market_data.market_data._disk_get", return_value=None
            ),
            patch("infrastructure.market_data.market_data._disk_set") as mock_disk_set,
        ):
            fetcher = MagicMock(return_value=success_result)

            # Act
            result = _cached_fetch(
                l1,
                "NVDA",
                DISK_PREFIX,
                DISK_TTL,
                fetcher,
                is_error=_is_error_dict,
            )

            # Assert — result is correct
            assert result == success_result
            # Assert — L1 has the result
            assert l1.get("NVDA") == success_result
            # Assert — disk_set WAS called (success persisted to L2)
            mock_disk_set.assert_called_once_with(
                f"{DISK_PREFIX}:NVDA",
                success_result,
                DISK_TTL,
            )

    def test_cached_fetch_should_write_to_disk_when_no_is_error_callback(self):
        # Arrange — no is_error callback (backward compatibility)
        l1 = _fresh_l1()
        error_result = {"error": "⚠️ Some error"}

        with (
            patch(
                "infrastructure.market_data.market_data._disk_get", return_value=None
            ),
            patch("infrastructure.market_data.market_data._disk_set") as mock_disk_set,
        ):
            fetcher = MagicMock(return_value=error_result)

            # Act
            _cached_fetch(l1, "NVDA", DISK_PREFIX, DISK_TTL, fetcher)

            # Assert — without is_error, everything goes to disk (old behavior)
            mock_disk_set.assert_called_once()

    def test_cached_fetch_should_return_l1_cached_without_calling_fetcher(self):
        # Arrange — pre-populate L1
        l1 = _fresh_l1()
        cached_result = {"ticker": "NVDA", "price": 130.0}
        l1["NVDA"] = cached_result
        fetcher = MagicMock()

        # Act
        result = _cached_fetch(
            l1,
            "NVDA",
            DISK_PREFIX,
            DISK_TTL,
            fetcher,
            is_error=_is_error_dict,
        )

        # Assert
        assert result == cached_result
        fetcher.assert_not_called()

    def test_cached_fetch_should_return_l2_cached_without_calling_fetcher(self):
        # Arrange — L1 empty, L2 has data
        l1 = _fresh_l1()
        disk_result = {"ticker": "NVDA", "price": 125.0}
        fetcher = MagicMock()

        with patch(
            "infrastructure.market_data.market_data._disk_get", return_value=disk_result
        ):
            # Act
            result = _cached_fetch(
                l1,
                "NVDA",
                DISK_PREFIX,
                DISK_TTL,
                fetcher,
                is_error=_is_error_dict,
            )

            # Assert
            assert result == disk_result
            assert l1.get("NVDA") == disk_result
            fetcher.assert_not_called()

    def test_cached_fetch_should_purge_stale_l2_error_and_call_fetcher(self):
        """When L2 disk has a stale error entry (written before is_error was
        added), _cached_fetch should delete it from disk and fall through to
        the fetcher for fresh data."""
        l1 = _fresh_l1()
        stale_error = {"error": "⚠️ old stale entry"}
        fresh_result = {"ticker": "VTI", "price": 250.0}
        fetcher = MagicMock(return_value=fresh_result)

        with (
            patch(
                "infrastructure.market_data.market_data._disk_get",
                return_value=stale_error,
            ),
            patch(
                "infrastructure.market_data.market_data._disk_cache"
            ) as mock_disk_cache,
            patch("infrastructure.market_data.market_data._disk_set"),
        ):
            result = _cached_fetch(
                l1,
                "VTI",
                DISK_PREFIX,
                DISK_TTL,
                fetcher,
                is_error=_is_error_dict,
            )

        assert result == fresh_result
        fetcher.assert_called_once_with("VTI")
        mock_disk_cache.delete.assert_called_once_with(f"{DISK_PREFIX}:VTI")

    def test_cached_fetch_should_purge_deserialized_etf_sentinel_from_l2(self):
        """A deserialized empty list from disk is a *different object* than
        _ETF_NOT_FOUND_SENTINEL, but equality (==) should still recognise it
        as an error and purge + re-fetch."""
        l1 = _fresh_l1()
        deserialized_sentinel = []  # different object than _ETF_NOT_FOUND_SENTINEL
        assert deserialized_sentinel is not _ETF_NOT_FOUND_SENTINEL
        assert deserialized_sentinel == _ETF_NOT_FOUND_SENTINEL

        fresh_holdings = [{"symbol": "AAPL", "weight": 0.07, "name": "Apple Inc."}]
        fetcher = MagicMock(return_value=fresh_holdings)

        with (
            patch(
                "infrastructure.market_data.market_data._disk_get",
                return_value=deserialized_sentinel,
            ),
            patch(
                "infrastructure.market_data.market_data._disk_cache"
            ) as mock_disk_cache,
            patch("infrastructure.market_data.market_data._disk_set"),
        ):
            result = _cached_fetch(
                l1,
                "VTI",
                DISK_PREFIX,
                DISK_TTL,
                fetcher,
                is_error=lambda d: d == _ETF_NOT_FOUND_SENTINEL,
            )

        assert result == fresh_holdings
        fetcher.assert_called_once_with("VTI")
        mock_disk_cache.delete.assert_called_once_with(f"{DISK_PREFIX}:VTI")


# ---------------------------------------------------------------------------
# _is_error_dict — predicate tests
# ---------------------------------------------------------------------------


class TestIsErrorDict:
    """Verify the _is_error_dict predicate."""

    def test_should_return_true_for_dict_with_error_key(self):
        assert _is_error_dict({"error": "something went wrong"}) is True

    def test_should_return_false_for_success_dict(self):
        assert _is_error_dict({"ticker": "NVDA", "price": 120.0}) is False

    def test_should_return_false_for_non_dict(self):
        assert _is_error_dict([1, 2, 3]) is False
        assert _is_error_dict("error") is False
        assert _is_error_dict(None) is False

    def test_should_return_false_for_empty_dict(self):
        assert _is_error_dict({}) is False


# ---------------------------------------------------------------------------
# _is_moat_error — predicate tests
# ---------------------------------------------------------------------------


class TestIsMoatError:
    """Verify the _is_moat_error predicate."""

    def test_should_return_true_for_not_available_moat(self):
        assert (
            _is_moat_error({"moat": "N/A", "details": "N/A failed to get new data"})
            is True
        )

    def test_should_return_false_for_healthy_moat(self):
        assert _is_moat_error({"moat": "護城河穩固", "details": "..."}) is False

    def test_should_return_false_for_non_dict(self):
        assert _is_moat_error(None) is False
        assert _is_moat_error("N/A") is False


# ---------------------------------------------------------------------------
# Retry decorator — behavior tests
# ---------------------------------------------------------------------------


class TestYfRetry:
    """Verify that the retry decorator retries on network errors."""

    def test_should_retry_on_curl_error_and_succeed(self):
        # Arrange — fails twice with CurlError, succeeds on 3rd
        mock_fn = MagicMock(
            side_effect=[
                CurlError("Could not resolve host"),
                CurlError("Connection timed out"),
                {"ticker": "NVDA", "price": 120.0},
            ]
        )
        retried_fn = _yf_retry(mock_fn)

        # Act
        result = retried_fn("NVDA")

        # Assert
        assert result == {"ticker": "NVDA", "price": 120.0}
        assert mock_fn.call_count == 3

    def test_should_retry_on_connection_error_and_succeed(self):
        # Arrange — fails once with ConnectionError, succeeds on 2nd
        mock_fn = MagicMock(
            side_effect=[
                ConnectionError("Connection refused"),
                {"ticker": "AAPL", "price": 180.0},
            ]
        )
        retried_fn = _yf_retry(mock_fn)

        # Act
        result = retried_fn("AAPL")

        # Assert
        assert result == {"ticker": "AAPL", "price": 180.0}
        assert mock_fn.call_count == 2

    def test_should_retry_on_os_error_and_succeed(self):
        # Arrange — fails once with OSError, succeeds on 2nd
        mock_fn = MagicMock(
            side_effect=[
                OSError("Network unreachable"),
                {"ticker": "TSLA", "price": 250.0},
            ]
        )
        retried_fn = _yf_retry(mock_fn)

        # Act
        result = retried_fn("TSLA")

        # Assert
        assert result == {"ticker": "TSLA", "price": 250.0}
        assert mock_fn.call_count == 2

    def test_should_give_up_after_max_attempts(self):
        # Arrange — always fails
        mock_fn = MagicMock(side_effect=CurlError("Could not resolve host"))
        retried_fn = _yf_retry(mock_fn)

        # Act & Assert
        with pytest.raises(CurlError):
            retried_fn("NVDA")

        # Assert — called exactly YFINANCE_RETRY_ATTEMPTS times (3)
        assert mock_fn.call_count == domain.constants.YFINANCE_RETRY_ATTEMPTS

    def test_should_not_retry_on_non_network_error(self):
        # Arrange — ValueError is not a network error
        mock_fn = MagicMock(side_effect=ValueError("Bad data"))
        retried_fn = _yf_retry(mock_fn)

        # Act & Assert
        with pytest.raises(ValueError, match="Bad data"):
            retried_fn("NVDA")

        # Assert — called only once (no retry)
        assert mock_fn.call_count == 1

    def test_should_not_retry_on_key_error(self):
        # Arrange — KeyError (data quality issue, not network)
        mock_fn = MagicMock(side_effect=KeyError("missing column"))
        retried_fn = _yf_retry(mock_fn)

        # Act & Assert
        with pytest.raises(KeyError):
            retried_fn("NVDA")

        assert mock_fn.call_count == 1


class TestEtfCacheErrorHandling:
    """Verify ETF cache helpers use error-aware disk caching."""

    def test_get_etf_top_holdings_should_pass_is_error_callback(self):
        with patch(
            "infrastructure.market_data.market_data._cached_fetch",
            return_value=_ETF_NOT_FOUND_SENTINEL,
        ) as mock_cached_fetch:
            get_etf_top_holdings("VTI")

        is_error_cb = mock_cached_fetch.call_args.kwargs["is_error"]
        assert callable(is_error_cb)
        assert is_error_cb(_ETF_NOT_FOUND_SENTINEL) is True
        assert is_error_cb([]) is True  # deserialized copy also matches (==)
        assert is_error_cb([{"symbol": "AAPL", "weight": 0.1}]) is False

    def test_get_etf_sector_weights_should_pass_is_error_callback(self):
        with patch(
            "infrastructure.market_data.market_data._cached_fetch",
            return_value=_ETF_SECTOR_WEIGHTS_NOT_FOUND,
        ) as mock_cached_fetch:
            get_etf_sector_weights("VTI")

        is_error_cb = mock_cached_fetch.call_args.kwargs["is_error"]
        assert callable(is_error_cb)
        assert is_error_cb(_ETF_SECTOR_WEIGHTS_NOT_FOUND) is True
        assert is_error_cb({}) is True  # deserialized copy also matches (==)
        assert is_error_cb({"Technology": 0.3}) is False

    def test_get_etf_top_holdings_should_purge_stale_negative_cache_for_known_etf(self):
        _etf_holdings_cache["VTI"] = _ETF_NOT_FOUND_SENTINEL
        with (
            patch(
                "infrastructure.market_data.market_data._cached_fetch",
                return_value=_ETF_NOT_FOUND_SENTINEL,
            ),
            patch(
                "infrastructure.market_data.market_data._disk_cache"
            ) as mock_disk_cache,
        ):
            get_etf_top_holdings("VTI", is_known_etf=True)

        mock_disk_cache.delete.assert_called_once_with("etf_holdings:VTI")
        assert "VTI" not in _etf_holdings_cache


class TestEtfHoldingsRetry:
    """Verify ETF holdings fetch retries transient failures."""

    def test_fetch_etf_top_holdings_should_retry_on_empty_top_holdings(self):
        class _FundsEmpty:
            top_holdings = pd.DataFrame()

        class _FundsOk:
            top_holdings = pd.DataFrame(
                [{"Holding Percent": 0.1, "Name": "Apple Inc."}],
                index=["AAPL"],
            )

        class _TickerEmpty:
            funds_data = _FundsEmpty()

        class _TickerOk:
            funds_data = _FundsOk()

        retried_fn = _fetch_etf_top_holdings.retry_with(
            stop=stop_after_attempt(2), wait=wait_none()
        )
        with patch(
            "infrastructure.market_data.market_data._yf_ticker_obj",
            side_effect=[_TickerEmpty(), _TickerOk()],
        ) as mock_ticker_obj:
            result = retried_fn("VTI")

        assert result is not None
        assert result[0]["symbol"] == "AAPL"
        assert mock_ticker_obj.call_count == 2

    def test_get_etf_top_holdings_should_return_none_when_retry_exhausted(self):
        with patch(
            "infrastructure.market_data.market_data._yf_ticker_obj",
            side_effect=OSError("temporary network error"),
        ):
            result = get_etf_top_holdings("VTI")

        assert result is None
