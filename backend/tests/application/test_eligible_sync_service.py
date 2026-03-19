from pathlib import Path
from unittest.mock import patch

from application.portfolio import eligible_sync_service


def test_resolve_xlsx_urls_should_accept_direct_link_with_query(monkeypatch):
    class _FailClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError(
                "httpx.Client should not be called for direct xlsx URLs"
            )

    monkeypatch.setattr(eligible_sync_service.httpx, "Client", _FailClient)
    url = "https://example.com/files/eligible.xlsx?download=1"
    assert eligible_sync_service._resolve_xlsx_urls(url) == [url]


def test_resolve_xlsx_urls_should_retry_on_ssl_error(monkeypatch):
    call_count = 0

    class _MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, _url):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("[SSL: UNEXPECTED_EOF_WHILE_READING] boom")

            class _Resp:
                text = '<a href="unlisted_fund_for_investor.xlsx">link</a>'

                def raise_for_status(self):
                    pass

            return _Resp()

    monkeypatch.setattr(eligible_sync_service.httpx, "Client", _MockClient)
    monkeypatch.setattr(eligible_sync_service.time, "sleep", lambda _: None)

    urls = eligible_sync_service._resolve_xlsx_urls("https://example.com/index")
    assert urls == ["https://example.com/unlisted_fund_for_investor.xlsx"]
    assert call_count == 3


def test_resolve_xlsx_urls_should_raise_non_ssl_error(monkeypatch):
    class _MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, _url):
            raise RuntimeError("http status issue")

    monkeypatch.setattr(eligible_sync_service.httpx, "Client", _MockClient)

    import pytest

    with pytest.raises(RuntimeError, match="http status issue"):
        eligible_sync_service._resolve_xlsx_urls("https://example.com/index")


def test_load_tsumitate_rows_should_use_tsumitate_target_filter(monkeypatch):
    monkeypatch.setattr(
        eligible_sync_service,
        "_resolve_xlsx_urls",
        lambda _url: ["unlisted_fund_for_investor.xlsx"],
    )
    monkeypatch.setattr(
        eligible_sync_service, "_download_to_temp", lambda url: Path(f"/tmp/{url}")
    )
    monkeypatch.setattr(
        eligible_sync_service,
        "parse_tsumitate_from_growth_xlsx",
        lambda path: [
            {"ticker": Path(path).name, "fund_name": "X", "asset_type": "mutual_fund"}
        ],
    )
    monkeypatch.setattr(eligible_sync_service, "parse_growth_xlsx", lambda _path: [])

    rows = eligible_sync_service._load_tsumitate_rows()
    assert rows[0]["ticker"] == "unlisted_fund_for_investor.xlsx"


def test_load_tsumitate_rows_should_skip_failed_candidate_and_continue(monkeypatch):
    monkeypatch.setattr(
        eligible_sync_service,
        "_resolve_xlsx_urls",
        lambda _url: ["bad.xlsx", "good.xlsx"],
    )

    def _download(url: str):
        if url == "bad.xlsx":
            raise RuntimeError("download failed")
        return Path("/tmp/good.xlsx")

    monkeypatch.setattr(eligible_sync_service, "_download_to_temp", _download)
    monkeypatch.setattr(
        eligible_sync_service,
        "parse_tsumitate_from_growth_xlsx",
        lambda _path: [
            {"ticker": "GOOD", "fund_name": "Good Fund", "asset_type": "mutual_fund"}
        ],
    )
    monkeypatch.setattr(eligible_sync_service, "parse_growth_xlsx", lambda _path: [])

    rows = eligible_sync_service._load_tsumitate_rows()
    assert rows[0]["ticker"] == "GOOD"


def test_load_tsumitate_rows_should_fallback_to_legacy_fsa_parser(monkeypatch):
    monkeypatch.setattr(
        eligible_sync_service,
        "_resolve_xlsx_urls",
        lambda _url: ["legacy-fsa.xlsx"],
    )
    monkeypatch.setattr(
        eligible_sync_service,
        "_download_to_temp",
        lambda _url: Path("/tmp/legacy-fsa.xlsx"),
    )
    monkeypatch.setattr(
        eligible_sync_service,
        "parse_tsumitate_from_growth_xlsx",
        lambda _path: [],
    )
    monkeypatch.setattr(
        eligible_sync_service,
        "parse_tsumitate_xlsx",
        lambda _path: [
            {
                "ticker": "SBI・iシェアーズ・TOPIXインデックス・ファンド",
                "fund_name": "SBI・iシェアーズ・TOPIXインデックス・ファンド",
                "asset_type": "mutual_fund",
            }
        ],
    )
    monkeypatch.setattr(eligible_sync_service, "parse_growth_xlsx", lambda _path: [])

    rows = eligible_sync_service._load_tsumitate_rows()
    assert rows[0]["ticker"] == "SBI・iシェアーズ・TOPIXインデックス・ファンド"


def test_load_tsumitate_rows_should_recover_ticker_and_isin_on_exact_name_match(
    monkeypatch,
):
    monkeypatch.setattr(
        eligible_sync_service,
        "_resolve_xlsx_urls",
        lambda _url: ["legacy-fsa.xlsx"],
    )
    monkeypatch.setattr(
        eligible_sync_service,
        "_download_to_temp",
        lambda _url: Path("/tmp/legacy-fsa.xlsx"),
    )
    monkeypatch.setattr(
        eligible_sync_service,
        "parse_tsumitate_from_growth_xlsx",
        lambda _path: [],
    )
    monkeypatch.setattr(
        eligible_sync_service,
        "parse_tsumitate_xlsx",
        lambda _path: [
            {
                "ticker": "SBI・iシェアーズ・TOPIXインデックス・ファンド",
                "fund_name": "SBI・iシェアーズ・TOPIXインデックス・ファンド",
                "asset_type": "mutual_fund",
            }
        ],
    )
    monkeypatch.setattr(
        eligible_sync_service,
        "parse_growth_xlsx",
        lambda _path: [
            {
                "ticker": "89311199",
                "fund_name": "SBI・iシェアーズ・TOPIXインデックス・ファンド",
                "isin_code": "JP90C000AAAA",
                "asset_type": "mutual_fund",
            }
        ],
    )

    rows = eligible_sync_service._load_tsumitate_rows()
    assert rows[0]["ticker"] == "89311199"
    assert rows[0]["isin_code"] == "JP90C000AAAA"


def test_load_growth_rows_should_skip_failed_candidate_and_continue(monkeypatch):
    monkeypatch.setattr(
        eligible_sync_service,
        "_resolve_xlsx_urls",
        lambda _url: ["bad.xlsx", "listed_fund_for_investor.xlsx"],
    )

    def _download(url: str):
        if url == "bad.xlsx":
            raise RuntimeError("download failed")
        return Path("/tmp/good-growth.xlsx")

    monkeypatch.setattr(eligible_sync_service, "_download_to_temp", _download)
    monkeypatch.setattr(
        eligible_sync_service,
        "parse_growth_xlsx",
        lambda _path: [
            {"ticker": "1306.T", "fund_name": "TOPIX ETF", "asset_type": "etf"}
        ],
    )

    rows = eligible_sync_service._load_growth_rows()
    assert rows[0]["ticker"] == "1306.T"


def test_load_tsumitate_rows_should_merge_listed_and_unlisted_sources(monkeypatch):
    monkeypatch.setattr(
        eligible_sync_service,
        "_resolve_xlsx_urls",
        lambda _url: [
            "listed_fund_for_investor.xlsx",
            "unlisted_fund_for_investor.xlsx",
        ],
    )

    def _download(url: str):
        return Path(f"/tmp/{url}")

    monkeypatch.setattr(eligible_sync_service, "_download_to_temp", _download)

    def _parse_tsumitate(path: Path):
        name = path.name
        if name == "listed_fund_for_investor.xlsx":
            return [
                {"ticker": "1599.T", "fund_name": "Listed Fund", "asset_type": "etf"}
            ]
        return [
            {
                "ticker": "89311199",
                "fund_name": "Unlisted Fund",
                "asset_type": "mutual_fund",
            }
        ]

    monkeypatch.setattr(
        eligible_sync_service,
        "parse_tsumitate_from_growth_xlsx",
        _parse_tsumitate,
    )
    monkeypatch.setattr(eligible_sync_service, "parse_growth_xlsx", lambda _path: [])
    monkeypatch.setattr(eligible_sync_service, "parse_tsumitate_xlsx", lambda _p: [])

    rows = eligible_sync_service._load_tsumitate_rows()
    tickers = {row["ticker"] for row in rows}
    assert tickers == {"1599.T", "89311199"}


class TestEnrichIsin:
    def test_should_fill_missing_isin_from_toushin_lib(self):
        rows = [
            {"ticker": "01311143", "fund_name": "Fund A", "isin_code": None},
            {"ticker": "01311237", "fund_name": "Fund B", "isin_code": None},
        ]
        mapping = {"01311143": "JP90C000A808", "01311237": "JP90C000PSP2"}

        with patch.object(
            eligible_sync_service, "fetch_isin_mapping", return_value=mapping
        ):
            result = eligible_sync_service._enrich_isin(rows)

        assert result[0]["isin_code"] == "JP90C000A808"
        assert result[1]["isin_code"] == "JP90C000PSP2"

    def test_should_skip_rows_with_existing_isin(self):
        rows = [
            {"ticker": "01311143", "fund_name": "Fund A", "isin_code": "EXISTING"},
            {"ticker": "01311237", "fund_name": "Fund B", "isin_code": None},
        ]
        mapping = {"01311143": "JP90C000A808", "01311237": "JP90C000PSP2"}

        with patch.object(
            eligible_sync_service, "fetch_isin_mapping", return_value=mapping
        ):
            result = eligible_sync_service._enrich_isin(rows)

        assert result[0]["isin_code"] == "EXISTING"
        assert result[1]["isin_code"] == "JP90C000PSP2"

    def test_should_handle_lookup_failure_gracefully(self):
        rows = [
            {"ticker": "01311143", "fund_name": "Fund A", "isin_code": None},
        ]

        with patch.object(
            eligible_sync_service,
            "fetch_isin_mapping",
            side_effect=RuntimeError("network"),
        ):
            result = eligible_sync_service._enrich_isin(rows)

        assert result[0]["isin_code"] is None

    def test_should_return_unchanged_when_all_have_isin(self):
        rows = [
            {"ticker": "01311143", "fund_name": "A", "isin_code": "JP90C000A808"},
        ]

        result = eligible_sync_service._enrich_isin(rows)
        assert result[0]["isin_code"] == "JP90C000A808"


class TestDownloadRetry:
    def test_should_retry_on_ssl_error(self, monkeypatch):
        call_count = 0

        class _MockClient:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def get(self, url):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise RuntimeError("[SSL: UNEXPECTED_EOF_WHILE_READING] boom")

                class _Resp:
                    content = b"xlsx data"
                    status_code = 200

                    def raise_for_status(self):
                        pass

                return _Resp()

        monkeypatch.setattr(eligible_sync_service.httpx, "Client", _MockClient)

        monkeypatch.setattr(eligible_sync_service.time, "sleep", lambda _: None)
        result = eligible_sync_service._download_to_temp(
            "https://example.com/file.xlsx"
        )
        assert result.suffix == ".xlsx"
        assert call_count == 3
        result.unlink(missing_ok=True)

    def test_should_raise_non_ssl_error_immediately(self, monkeypatch):
        class _MockClient:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def get(self, url):
                raise RuntimeError("not an SSL error")

        monkeypatch.setattr(eligible_sync_service.httpx, "Client", _MockClient)

        import pytest

        with pytest.raises(RuntimeError, match="not an SSL error"):
            eligible_sync_service._download_to_temp("https://example.com/file.xlsx")
