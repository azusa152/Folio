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


def test_load_tsumitate_rows_should_prefer_asset_class_signature(monkeypatch):
    monkeypatch.setattr(
        eligible_sync_service,
        "_resolve_xlsx_urls",
        lambda _url: ["company.xlsx", "asset.xlsx"],
    )
    monkeypatch.setattr(
        eligible_sync_service, "_download_to_temp", lambda url: Path(f"/tmp/{url}")
    )
    monkeypatch.setattr(
        eligible_sync_service,
        "is_tsumitate_asset_class_xlsx",
        lambda path: str(path).endswith("asset.xlsx"),
    )
    monkeypatch.setattr(
        eligible_sync_service,
        "parse_tsumitate_xlsx",
        lambda path: [
            {"ticker": Path(path).name, "fund_name": "X", "asset_type": "mutual_fund"}
        ],
    )

    rows = eligible_sync_service._load_tsumitate_rows()
    assert rows[0]["ticker"] == "asset.xlsx"


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
        eligible_sync_service, "is_tsumitate_asset_class_xlsx", lambda _path: True
    )
    monkeypatch.setattr(
        eligible_sync_service,
        "parse_tsumitate_xlsx",
        lambda _path: [
            {"ticker": "GOOD", "fund_name": "Good Fund", "asset_type": "mutual_fund"}
        ],
    )

    rows = eligible_sync_service._load_tsumitate_rows()
    assert rows[0]["ticker"] == "GOOD"


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
