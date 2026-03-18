"""Tests for the toushin-lib NAV adapter."""

from datetime import date
from unittest.mock import MagicMock

import httpx

from infrastructure.market_data import toushin_adapter

SAMPLE_CSV = (
    "年月日,基準価額(円),純資産総額（百万円）,分配金\n"
    "2026年03月14日,15432,1200,0\n"
    "2026年03月13日,15380,1190,0\n"
    "2026年03月12日,15350,1185,0\n"
)

SAMPLE_CSV_SHIFT_JIS = SAMPLE_CSV.encode("shift_jis")


def _make_response(content: bytes, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        content=content,
        headers={"content-type": "text/csv; charset=Shift_JIS"},
        request=httpx.Request("GET", "https://example.com"),
    )


class TestFetchFundNavCsv:
    def test_should_parse_shift_jis_csv(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _make_response(SAMPLE_CSV_SHIFT_JIS)

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_client)

        rows = toushin_adapter.fetch_fund_nav_csv("0131310B", "JP90C000HR46")

        assert rows is not None
        assert len(rows) == 3
        assert rows[0]["date"] == date(2026, 3, 14)
        assert rows[0]["nav"] == 15432.0
        assert rows[0]["net_assets"] == 1200.0
        assert rows[1]["date"] == date(2026, 3, 13)

    def test_should_return_none_on_network_error(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectError("timeout")

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_client)

        result = toushin_adapter.fetch_fund_nav_csv("0131310B", "JP90C000HR46")
        assert result is None
        assert mock_client.get.call_count == 1

    def test_should_return_empty_list_on_empty_csv(self, monkeypatch):
        empty_csv = "年月日,基準価額(円),純資産総額(百万円),分配金\n".encode(
            "shift_jis"
        )
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _make_response(empty_csv)

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_client)

        result = toushin_adapter.fetch_fund_nav_csv("0131310B", "JP90C000HR46")
        assert result == []

    def test_should_parse_slash_date_format_for_backward_compat(self, monkeypatch):
        slash_csv = (
            "年月日,基準価額(円),純資産総額（百万円）,分配金\n"
            "2026/03/14,15432,1200,0\n"
            "2026/03/13,15380,1190,0\n"
        ).encode("shift_jis")

        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _make_response(slash_csv)

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_client)

        rows = toushin_adapter.fetch_fund_nav_csv("0131310B", "JP90C000HR46")
        assert rows is not None
        assert len(rows) == 2
        assert rows[0]["date"] == date(2026, 3, 14)

    def test_should_parse_net_assets_with_full_width_parentheses_header(
        self, monkeypatch
    ):
        full_width_header_csv = (
            "年月日,基準価額(円),純資産総額（百万円）,分配金\n"
            "2026年03月14日,15432,1200,0\n"
        ).encode("shift_jis")

        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _make_response(full_width_header_csv)

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_client)

        rows = toushin_adapter.fetch_fund_nav_csv("0131310B", "JP90C000HR46")
        assert rows is not None
        assert len(rows) == 1
        assert rows[0]["net_assets"] == 1200.0

    def test_should_retry_once_on_ssl_then_succeed(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = [
            httpx.ConnectError("[SSL: UNEXPECTED_EOF_WHILE_READING] EOF"),
            _make_response(SAMPLE_CSV_SHIFT_JIS),
        ]

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_client)

        rows = toushin_adapter.fetch_fund_nav_csv("0131310B", "JP90C000HR46")
        assert rows is not None
        assert len(rows) == 3
        assert mock_client.get.call_count == 2

    def test_should_return_none_after_ssl_retry_exhausted(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = [
            httpx.ConnectError("[SSL: UNEXPECTED_EOF_WHILE_READING] EOF"),
            httpx.ConnectError("[SSL: UNEXPECTED_EOF_WHILE_READING] EOF"),
        ]

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_client)

        result = toushin_adapter.fetch_fund_nav_csv("0131310B", "JP90C000HR46")
        assert result is None
        assert mock_client.get.call_count == 2


class TestHeaderNormalization:
    def test_should_strip_bom_and_normalize_parentheses(self):
        header = "\ufeff純資産総額（百万円）"
        assert toushin_adapter._normalize_header_key(header) == "純資産総額(百万円)"


class TestFetchLatestNav:
    def test_should_return_latest_with_previous(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _make_response(SAMPLE_CSV_SHIFT_JIS)

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_client)

        result = toushin_adapter.fetch_latest_nav("0131310B", "JP90C000HR46")

        assert result is not None
        assert result["nav"] == 15432.0
        assert result["nav_previous"] == 15380.0
        assert result["date"] == date(2026, 3, 14)

    def test_should_return_none_on_no_data(self, monkeypatch):
        monkeypatch.setattr(toushin_adapter, "fetch_fund_nav_csv", lambda fc, ic: None)
        result = toushin_adapter.fetch_latest_nav("0131310B", "JP90C000HR46")
        assert result is None
