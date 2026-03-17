from pathlib import Path

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

    rows = eligible_sync_service._load_tsumitate_rows()
    assert rows[0]["ticker"] == "SBI・iシェアーズ・TOPIXインデックス・ファンド"


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
    monkeypatch.setattr(eligible_sync_service, "parse_tsumitate_xlsx", lambda _p: [])

    rows = eligible_sync_service._load_tsumitate_rows()
    tickers = {row["ticker"] for row in rows}
    assert tickers == {"1599.T", "89311199"}
