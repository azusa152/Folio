from pathlib import Path

from openpyxl import Workbook

from infrastructure.external.eligible_fund_parser import (
    detect_and_parse,
    parse_eligible_assets_csv,
    parse_growth_xlsx,
    parse_tsumitate_xlsx,
)


def test_parse_eligible_assets_csv_should_normalize_fields(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "ticker,fund_name,asset_type,trust_fee_pct\n"
        " abc123 ,Sample Fund,mutual_fund,0.123\n",
        encoding="utf-8",
    )

    rows = parse_eligible_assets_csv(csv_path)
    assert len(rows) == 1
    assert rows[0]["ticker"] == "ABC123"
    assert rows[0]["fund_name"] == "Sample Fund"
    assert rows[0]["asset_type"] == "mutual_fund"
    assert rows[0]["trust_fee_pct"] == 0.123


def test_parse_tsumitate_xlsx_should_extract_rows(tmp_path: Path):
    xlsx_path = tmp_path / "tsumitate.xlsx"
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append([46010])
    ws.append(["金融庁"])
    ws.append(["つみたて投資枠対象商品届出一覧（対象資産別）"])
    ws.append(["【指定インデックス投資信託】"])
    ws.append(
        [
            "単一指数・複数指数の区分(※1)",
            "国内型・海外型の区分(※2)",
            "指定指数の名称又は指定指数の数(※3)",
            "ファンド名称(※4)",
            "運用会社",
        ]
    )
    ws.append(
        [
            "単一指数（株式型）",
            "国内型",
            "TOPIX",
            "SBI・iシェアーズ・TOPIXインデックス・ファンド",
            "SBIアセットマネジメント",
        ]
    )
    wb.save(xlsx_path)

    rows = parse_tsumitate_xlsx(xlsx_path)
    assert len(rows) == 1
    assert rows[0]["ticker"] == "SBI・iシェアーズ・TOPIXインデックス・ファンド"
    assert rows[0]["fund_name"] == "SBI・iシェアーズ・TOPIXインデックス・ファンド"


def test_parse_growth_xlsx_should_extract_rows(tmp_path: Path):
    xlsx_path = tmp_path / "growth.xlsx"
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["上場株式等の投資信託等"])
    ws.append(
        [
            "リスト更新日",
            "追加・変更の別",
            "上場投信・上場投資法人の別",
            "銘柄コード",
            "ファンド名称",
            "運用会社名",
            "設定日・設立日",
            "成長投資枠取扱可能日",
            "決算回数",
            "つみたて投資枠の対象・非対象",
        ]
    )
    ws.append(
        [
            20230621,
            "追加",
            "上場投信",
            "14980",
            "Ｏｎｅ ＥＴＦ ＥＳＧ",
            "アセットマネジメントOne株式会社",
            20171127,
            20240104,
            "年2回",
            "非対象",
        ]
    )
    wb.save(xlsx_path)

    rows = parse_growth_xlsx(xlsx_path)
    assert len(rows) == 1
    assert rows[0]["ticker"] == "1498.T"
    assert rows[0]["asset_type"] == "etf"


def test_detect_and_parse_should_route_by_extension(tmp_path: Path):
    csv_path = tmp_path / "manual.csv"
    csv_path.write_text(
        "ticker,fund_name,asset_type,trust_fee_pct\n1306.T,NEXT FUNDS TOPIX,etf,\n",
        encoding="utf-8",
    )

    rows = detect_and_parse(csv_path, wrapper="nisa_growth")
    assert len(rows) == 1
    assert rows[0]["ticker"] == "1306.T"
