"""Tests for the toushin-lib ISIN lookup adapter."""

from unittest.mock import MagicMock

import infrastructure.market_data.toushin_lib_adapter as adapter_module


def _make_search_response(items: list[dict]) -> dict:
    return {
        "searchResultInfo": {
            "resultInfoMapList": items,
            "recordsTotal": str(len(items)),
        }
    }


class TestFetchIsinMapping:
    def setup_method(self):
        adapter_module.invalidate_isin_cache()

    def test_should_return_fund_code_to_isin_mapping(self, monkeypatch):
        payload = _make_search_response(
            [
                {
                    "associFundCd": "01311143",
                    "isinCd": "JP90C000A808",
                    "fundNm": "Fund A",
                },
                {
                    "associFundCd": "01311237",
                    "isinCd": "JP90C000PSP2",
                    "fundNm": "Fund B",
                },
            ]
        )
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = lambda self: self
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        monkeypatch.setattr(adapter_module.httpx, "Client", lambda **kw: mock_client)

        result = adapter_module.fetch_isin_mapping(force_refresh=True)

        assert result["01311143"] == "JP90C000A808"
        assert result["01311237"] == "JP90C000PSP2"
        assert len(result) == 2

    def test_should_cache_results(self, monkeypatch):
        payload = _make_search_response(
            [{"associFundCd": "01311143", "isinCd": "JP90C000A808", "fundNm": "A"}]
        )
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = lambda self: self
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        monkeypatch.setattr(adapter_module.httpx, "Client", lambda **kw: mock_client)

        result1 = adapter_module.fetch_isin_mapping(force_refresh=True)
        result2 = adapter_module.fetch_isin_mapping()

        assert result1 == result2
        assert mock_client.post.call_count == 1

    def test_should_return_empty_on_network_error(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.__enter__ = lambda self: self
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = RuntimeError("network down")

        monkeypatch.setattr(adapter_module.httpx, "Client", lambda **kw: mock_client)
        monkeypatch.setattr(adapter_module.time, "sleep", lambda _: None)

        result = adapter_module.fetch_isin_mapping(force_refresh=True)
        assert result == {}

    def test_should_skip_entries_with_missing_fields(self, monkeypatch):
        payload = _make_search_response(
            [
                {"associFundCd": "01311143", "isinCd": "JP90C000A808", "fundNm": "A"},
                {"associFundCd": "", "isinCd": "JP90C000XXX0", "fundNm": "B"},
                {"associFundCd": "01311237", "isinCd": "", "fundNm": "C"},
            ]
        )
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = lambda self: self
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        monkeypatch.setattr(adapter_module.httpx, "Client", lambda **kw: mock_client)

        result = adapter_module.fetch_isin_mapping(force_refresh=True)
        assert len(result) == 1
        assert "01311143" in result


class TestLookupIsin:
    def setup_method(self):
        adapter_module.invalidate_isin_cache()

    def test_should_find_isin(self, monkeypatch):
        payload = _make_search_response(
            [{"associFundCd": "01311143", "isinCd": "JP90C000A808", "fundNm": "A"}]
        )
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = lambda self: self
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        monkeypatch.setattr(adapter_module.httpx, "Client", lambda **kw: mock_client)

        assert adapter_module.lookup_isin("01311143") == "JP90C000A808"

    def test_should_return_none_for_unknown(self, monkeypatch):
        payload = _make_search_response([])
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = lambda self: self
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        monkeypatch.setattr(adapter_module.httpx, "Client", lambda **kw: mock_client)

        assert adapter_module.lookup_isin("UNKNOWN") is None


class TestResolveFundCodeFromName:
    def setup_method(self):
        adapter_module.invalidate_isin_cache()

    def test_should_resolve_name_to_code(self, monkeypatch):
        payload = _make_search_response(
            [
                {
                    "associFundCd": "0331220C",
                    "isinCd": "JP90C000L110",
                    "fundNm": "\uff45\uff2d\uff21\uff38\uff29\uff33\u3000\uff33\uff06\uff30\uff15\uff10\uff10\u30a4\u30f3\u30c7\u30c3\u30af\u30b9",
                },
            ]
        )
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = lambda self: self
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        monkeypatch.setattr(adapter_module.httpx, "Client", lambda **kw: mock_client)

        result = adapter_module.resolve_fund_code_from_name(
            "\uff45\uff2d\uff21\uff38\uff29\uff33\u3000\uff33\uff06\uff30\uff15\uff10\uff10\u30a4\u30f3\u30c7\u30c3\u30af\u30b9"
        )
        assert result == "0331220C"

    def test_should_return_none_for_ambiguous_name(self, monkeypatch):
        payload = _make_search_response(
            [
                {"associFundCd": "AAA11111", "isinCd": "JP1", "fundNm": "Same Name"},
                {"associFundCd": "BBB22222", "isinCd": "JP2", "fundNm": "Same Name"},
            ]
        )
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = lambda self: self
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        monkeypatch.setattr(adapter_module.httpx, "Client", lambda **kw: mock_client)

        result = adapter_module.resolve_fund_code_from_name("Same Name")
        assert result is None


class TestBackoffAndStaleCache:
    def setup_method(self):
        adapter_module.invalidate_isin_cache()

    def test_should_serve_stale_cache_during_backoff(self, monkeypatch):
        adapter_module._isin_cache = {"01311143": "JP90C000A808"}  # type: ignore[attr-defined]
        adapter_module._name_to_code_cache = {"funda": "01311143"}  # type: ignore[attr-defined]
        adapter_module._cache_ts = 0.0  # type: ignore[attr-defined]
        adapter_module._consecutive_failures = 2  # type: ignore[attr-defined]
        adapter_module._last_fetch_failed_ts = adapter_module.time.monotonic()  # type: ignore[attr-defined]

        monkeypatch.setattr(
            adapter_module,
            "_fetch_raw_data",
            lambda: (_ for _ in ()).throw(
                AssertionError("should not fetch during backoff")
            ),
        )

        result = adapter_module.fetch_isin_mapping()
        assert result == {"01311143": "JP90C000A808"}

    def test_should_backoff_after_failed_fetch(self, monkeypatch):
        calls = 0

        def _fail_fetch():
            nonlocal calls
            calls += 1
            return {}, {}, False

        monkeypatch.setattr(adapter_module, "_fetch_raw_data", _fail_fetch)

        first = adapter_module.fetch_isin_mapping()
        second = adapter_module.fetch_isin_mapping()

        assert first == {}
        assert second == {}
        assert calls == 1
