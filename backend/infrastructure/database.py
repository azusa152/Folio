"""
Infrastructure — 資料庫連線與 Session 管理。
使用 SQLite (透過 SQLModel / SQLAlchemy)。
"""

import os
import unicodedata
from collections.abc import Generator

from sqlalchemy import event
from sqlalchemy.pool import NullPool, StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from logging_config import get_logger

logger = get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/radar.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")
IS_IN_MEMORY_SQLITE = DATABASE_URL in {
    "sqlite://",
    "sqlite:///:memory:",
} or DATABASE_URL.endswith(":memory:")

engine_kwargs: dict[str, object] = {"echo": False}
if IS_SQLITE:
    # SQLite 需要 check_same_thread=False 以支援多執行緒存取
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    # File-based SQLite: use NullPool to avoid QueuePool exhaustion under threaded workloads.
    # In-memory SQLite tests rely on a shared single connection.
    engine_kwargs["poolclass"] = StaticPool if IS_IN_MEMORY_SQLITE else NullPool

engine = create_engine(DATABASE_URL, **engine_kwargs)


if IS_SQLITE and not IS_IN_MEMORY_SQLITE:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, connection_record) -> None:
        """Tune SQLite for concurrent access in multi-thread workloads."""
        del connection_record
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()


logger.info("資料庫連線位置：%s", DATABASE_URL)


def _run_migrations() -> None:
    """執行資料庫遷移：為既有資料表新增缺少的欄位。"""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    migrations = [
        "ALTER TABLE stock ADD COLUMN current_tags VARCHAR DEFAULT '';",
        "ALTER TABLE thesislog ADD COLUMN tags VARCHAR DEFAULT '';",
        "ALTER TABLE stock ADD COLUMN display_order INTEGER DEFAULT 0;",
        "ALTER TABLE stock ADD COLUMN last_scan_signal VARCHAR DEFAULT 'NORMAL';",
        # Phase: ETF -> Trend_Setter 分類遷移（新五類分類系統）
        "UPDATE stock SET category = 'Trend_Setter' WHERE category = 'ETF';",
        # Holding: 新增券商欄位
        "ALTER TABLE holding ADD COLUMN broker VARCHAR;",
        # Holding: 新增幣別欄位
        "ALTER TABLE holding ADD COLUMN currency VARCHAR DEFAULT 'USD';",
        # Holding: 一次性正規化 ticker（避免查詢大小寫回退掃描）
        "UPDATE holding SET ticker = UPPER(TRIM(ticker)) WHERE ticker IS NOT NULL;",
        # Holding: 根據 ticker 後綴回填幣別
        "UPDATE holding SET currency = 'TWD' WHERE ticker LIKE '%.TW' AND currency = 'USD';",
        "UPDATE holding SET currency = 'JPY' WHERE ticker LIKE '%.T' AND currency = 'USD';",
        "UPDATE holding SET currency = 'HKD' WHERE ticker LIKE '%.HK' AND currency = 'USD';",
        # Holding: 新增現金標記欄位
        "ALTER TABLE holding ADD COLUMN is_cash BOOLEAN DEFAULT 0;",
        # Holding: 現金持倉以 ticker 作為幣別
        "UPDATE holding SET currency = ticker WHERE is_cash = 1 AND currency = 'USD';",
        # Holding: 新增帳戶類型欄位
        "ALTER TABLE holding ADD COLUMN account_type VARCHAR;",
        # Holding: 新增帳戶 ID 欄位
        "ALTER TABLE holding ADD COLUMN account_id INTEGER;",
        # Transaction: 新增帳戶 ID 欄位（用於券商現金結算）
        'ALTER TABLE "transaction" ADD COLUMN account_id INTEGER;',
        # ScanLog: 新增市場情緒原因說明欄位
        "ALTER TABLE scanlog ADD COLUMN market_status_details VARCHAR DEFAULT '';",
        # UserInvestmentProfile: 新增本幣欄位（用於匯率曝險計算）
        "ALTER TABLE userinvestmentprofile ADD COLUMN home_currency VARCHAR DEFAULT 'TWD';",
        # UserPreferences: 新增通知偏好 JSON 欄位
        "ALTER TABLE userpreferences ADD COLUMN notification_preferences VARCHAR DEFAULT '{}';",
        # UserPreferences: 新增語言偏好欄位 (i18n support)
        "ALTER TABLE userpreferences ADD COLUMN language VARCHAR DEFAULT 'zh-TW';",
        # FX Watch: 新增獨立切換開關與欄位重命名
        "ALTER TABLE fxwatchconfig ADD COLUMN alert_on_recent_high BOOLEAN DEFAULT 1;",
        "ALTER TABLE fxwatchconfig ADD COLUMN alert_on_consecutive_increase BOOLEAN DEFAULT 1;",
        "ALTER TABLE fxwatchconfig ADD COLUMN recent_high_days INTEGER DEFAULT 30;",
        "UPDATE fxwatchconfig SET recent_high_days = lookback_days WHERE recent_high_days = 30;",
        # Stock: 新增 is_etf 欄位（ETF 不參與市場情緒計算）
        "ALTER TABLE stock ADD COLUMN is_etf BOOLEAN DEFAULT 0;",
        # 回填已知 ETF
        "UPDATE stock SET is_etf = 1 WHERE ticker IN ('VTI', 'VT', 'SOXX');",
        # GuruHolding: 新增 sector 欄位（GICS 行業板塊）
        "ALTER TABLE guruholding ADD COLUMN sector VARCHAR;",
        # Holding: 新增購入時匯率欄位（Phase 6 FX return tracking）
        "ALTER TABLE holding ADD COLUMN purchase_fx_rate REAL;",
        # Holding: 新增加密貨幣對應 CoinGecko ID 欄位
        "ALTER TABLE holding ADD COLUMN coingecko_id VARCHAR;",
        # Stock: 新增加密貨幣對應 CoinGecko ID 欄位（Radar 追蹤用）
        "ALTER TABLE stock ADD COLUMN coingecko_id VARCHAR;",
        # Guru: 新增投資風格與級別欄位（Smart Money Phase 1）
        "ALTER TABLE guru ADD COLUMN style VARCHAR;",
        "ALTER TABLE guru ADD COLUMN tier VARCHAR;",
        # PortfolioSnapshot: 新增多基準指數 JSON 欄位（Portfolio Enhancement）
        "ALTER TABLE portfoliosnapshot ADD COLUMN benchmark_values TEXT DEFAULT '{}';",
        # PortfolioSnapshot: 新增個股市值 JSON 欄位
        "ALTER TABLE portfoliosnapshot ADD COLUMN holding_values TEXT DEFAULT '{}';",
        # PortfolioSnapshot: 新增總成本基礎欄位
        "ALTER TABLE portfoliosnapshot ADD COLUMN cost_basis_total REAL;",
        # PortfolioSnapshot: 新增地理區域市值 JSON 欄位
        "ALTER TABLE portfoliosnapshot ADD COLUMN geographic_values TEXT DEFAULT '{}';",
        # Stock: 新增訊號起始時間欄位（Signal Duration Tracking）
        "ALTER TABLE stock ADD COLUMN signal_since DATETIME;",
        # UserPreferences: 新增通知頻率限制 JSON 欄位（Rate Limiting）
        "ALTER TABLE userpreferences ADD COLUMN notification_rate_limits VARCHAR DEFAULT '{}';",
        # UserPreferences: terminology display mode (Phase 7)
        "ALTER TABLE userpreferences ADD COLUMN terminology_mode VARCHAR DEFAULT 'simplified';",
        # FX Watch: target-rate alert support
        "ALTER TABLE fxwatchconfig ADD COLUMN target_rate REAL;",
        "ALTER TABLE fxwatchconfig ADD COLUMN target_direction VARCHAR;",
        # Account: 新增税制口座ラッパー欄位（NISA / iDeCo / Tokutei）
        "ALTER TABLE account ADD COLUMN tax_wrapper TEXT;",
        # Account: 新增市場欄位（US / JP / TW / HK ...）
        "ALTER TABLE account ADD COLUMN market VARCHAR;",
        # Account: 依帳戶幣別回填市場（既有資料遷移）
        (
            "UPDATE account SET market = CASE UPPER(COALESCE(currency, 'USD')) "
            "WHEN 'JPY' THEN 'JP' "
            "WHEN 'TWD' THEN 'TW' "
            "WHEN 'HKD' THEN 'HK' "
            "WHEN 'EUR' THEN 'EU' "
            "WHEN 'GBP' THEN 'UK' "
            "WHEN 'CNY' THEN 'CN' "
            "WHEN 'SGD' THEN 'SG' "
            "WHEN 'THB' THEN 'TH' "
            "ELSE 'US' END "
            "WHERE market IS NULL OR TRIM(market) = '';"
        ),
        # Contribution ledger: append-only quota accounting for NISA/iDeCo
        (
            "CREATE TABLE IF NOT EXISTS contributionledgerentry ("
            "id INTEGER PRIMARY KEY, "
            "user_id VARCHAR NOT NULL DEFAULT 'default', "
            "tax_wrapper VARCHAR NOT NULL, "
            "entry_type VARCHAR NOT NULL, "
            "fiscal_year INTEGER NOT NULL, "
            "amount REAL NOT NULL, "
            "transaction_id INTEGER, "
            "effective_date DATE NOT NULL, "
            "note VARCHAR NOT NULL DEFAULT '', "
            "created_at DATETIME NOT NULL, "
            'FOREIGN KEY(transaction_id) REFERENCES "transaction"(id)'
            ");"
        ),
        "CREATE INDEX IF NOT EXISTS ix_contrib_user_wrapper_year ON contributionledgerentry (user_id, tax_wrapper, fiscal_year);",
        "CREATE INDEX IF NOT EXISTS ix_contrib_transaction ON contributionledgerentry (transaction_id);",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_contrib_transaction_entry_type ON contributionledgerentry (transaction_id, entry_type) WHERE transaction_id IS NOT NULL;",
        # Eligible asset master for wrapper placement validation.
        (
            "CREATE TABLE IF NOT EXISTS eligibleasset ("
            "id INTEGER PRIMARY KEY, "
            "tax_wrapper VARCHAR NOT NULL, "
            "ticker VARCHAR NOT NULL, "
            "fund_name VARCHAR NOT NULL DEFAULT '', "
            "asset_type VARCHAR NOT NULL DEFAULT 'mutual_fund', "
            "broker VARCHAR, "
            "trust_fee_pct REAL, "
            "is_active BOOLEAN NOT NULL DEFAULT 1, "
            "updated_at DATETIME NOT NULL"
            ");"
        ),
        "CREATE INDEX IF NOT EXISTS ix_eligible_wrapper_ticker ON eligibleasset (tax_wrapper, ticker);",
        "CREATE INDEX IF NOT EXISTS ix_eligible_wrapper_broker ON eligibleasset (tax_wrapper, broker);",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_eligible_wrapper_ticker_broker ON eligibleasset (tax_wrapper, ticker, broker);",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_eligible_wrapper_ticker_null_broker ON eligibleasset (tax_wrapper, ticker) WHERE broker IS NULL;",
        # Add isin_code to eligible asset (for toushin-lib NAV lookup).
        "ALTER TABLE eligibleasset ADD COLUMN isin_code VARCHAR;",
        # One-time canonicalization: ensure asset_type is lowercase-trimmed.
        # Rows already canonical are untouched; runs as a cheap SQL scan.
        (
            "UPDATE eligibleasset SET asset_type = "
            "CASE WHEN LOWER(TRIM(COALESCE(asset_type, ''))) = '' THEN 'mutual_fund' "
            "ELSE LOWER(TRIM(asset_type)) END "
            "WHERE asset_type IS NULL OR TRIM(asset_type) = '' "
            "OR asset_type != LOWER(TRIM(asset_type));"
        ),
        # Eligible asset sync metadata.
        (
            "CREATE TABLE IF NOT EXISTS eligibleassetsyncstate ("
            "tax_wrapper VARCHAR PRIMARY KEY, "
            "source VARCHAR NOT NULL DEFAULT 'unknown', "
            "last_refreshed_at DATETIME NOT NULL, "
            "updated_at DATETIME NOT NULL"
            ");"
        ),
        # Mutual fund NAV cache for daily toushin-lib sync.
        (
            "CREATE TABLE IF NOT EXISTS mutualfundnav ("
            "id INTEGER PRIMARY KEY, "
            "fund_code VARCHAR NOT NULL, "
            "isin_code VARCHAR NOT NULL, "
            "nav REAL NOT NULL, "
            "nav_previous REAL, "
            "nav_date DATE NOT NULL, "
            "net_assets REAL, "
            "fetched_at DATETIME NOT NULL"
            ");"
        ),
        "CREATE INDEX IF NOT EXISTS ix_mfnav_fund_code ON mutualfundnav (fund_code);",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_mfnav_fund_code_date ON mutualfundnav (fund_code, nav_date);",
    ]

    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.debug("Migration 成功：%s", sql.strip())
            except OperationalError:
                # SQLite 在欄位已存在時（duplicate column name）拋出 OperationalError，
                # 屬預期的冪等行為，靜默跳過。UPDATE 語句零列更新不會觸發此路徑。
                conn.rollback()


def _load_system_personas() -> None:
    """從 JSON 檔案載入系統預設投資人格範本（upsert）。"""
    import json
    import pathlib

    from domain.entities import SystemTemplate

    persona_path = (
        pathlib.Path(__file__).parent.parent / "config" / "system_personas.json"
    )
    if not persona_path.exists():
        logger.warning("system_personas.json 不存在，跳過載入。")
        return

    with open(persona_path, encoding="utf-8") as f:
        personas = json.load(f)

    with Session(engine) as session:
        for p in personas:
            existing = session.get(SystemTemplate, p["id"])
            if existing:
                existing.name = p["name"]
                existing.description = p["description"]
                existing.quote = p["quote"]
                existing.is_empty = p.get("isEmpty", False)
                existing.default_config = json.dumps(p["defaultConfig"])
            else:
                session.add(
                    SystemTemplate(
                        id=p["id"],
                        name=p["name"],
                        description=p["description"],
                        quote=p["quote"],
                        is_empty=p.get("isEmpty", False),
                        default_config=json.dumps(p["defaultConfig"]),
                    )
                )
        session.commit()
    logger.info("系統人格範本載入完成（%d 筆）。", len(personas))


def _encrypt_plaintext_tokens() -> None:
    """
    加密遷移：將 UserTelegramSettings.custom_bot_token 的明文改為加密存儲。

    僅在 FERNET_KEY 環境變數已設定時執行。已加密的 token 不會重複加密。
    """
    import os

    # Skip if FERNET_KEY not set (encryption not enabled)
    if not os.getenv("FERNET_KEY"):
        logger.debug("FERNET_KEY 未設定，跳過 Token 加密遷移。")
        return

    try:
        from domain.entities import UserTelegramSettings
        from infrastructure.external.crypto import encrypt_token, is_encrypted

        with Session(engine) as session:
            settings_list = session.exec(select(UserTelegramSettings)).all()
            encrypted_count = 0

            for settings in settings_list:
                if settings.custom_bot_token and not is_encrypted(
                    settings.custom_bot_token
                ):
                    # Token is plaintext, encrypt it
                    try:
                        encrypted = encrypt_token(settings.custom_bot_token)
                        settings.custom_bot_token = encrypted
                        encrypted_count += 1
                        logger.info("Token 加密完成：user_id=%s", settings.user_id)
                    except Exception as e:
                        logger.error(
                            "Token 加密失敗：user_id=%s, error=%s",
                            settings.user_id,
                            e,
                        )

            if encrypted_count > 0:
                session.commit()
                logger.info("Token 加密遷移完成：%d 筆。", encrypted_count)
            else:
                logger.debug("無需加密的明文 Token。")

    except Exception as e:
        logger.error("Token 加密遷移失敗：%s", e, exc_info=True)


def _run_smart_money_migrations() -> None:
    """Smart Money Tracker 索引遷移（補充查詢效能所需的 index）。"""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    migrations = [
        "CREATE INDEX IF NOT EXISTS ix_gurufiling_guru_id ON gurufiling (guru_id);",
        "CREATE INDEX IF NOT EXISTS ix_guruholding_guru_id ON guruholding (guru_id);",
        "CREATE INDEX IF NOT EXISTS ix_guruholding_ticker ON guruholding (ticker);",
        "CREATE INDEX IF NOT EXISTS ix_guruholding_filing_id ON guruholding (filing_id);",
    ]

    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.debug("Smart Money 索引遷移成功：%s", sql.strip())
            except OperationalError:
                conn.rollback()


def _run_backtest_migrations() -> None:
    """Backtest/ScanLog 索引遷移（補充查詢效能所需的 index）。"""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    migrations = [
        "CREATE INDEX IF NOT EXISTS ix_scanlog_stock_ticker_scanned_at ON scanlog (stock_ticker, scanned_at);",
    ]

    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.debug("Backtest 索引遷移成功：%s", sql.strip())
            except OperationalError:
                conn.rollback()


def _run_ledger_indexes() -> None:
    """Ledger 索引遷移（補充 account+ticker 查詢效能所需 index）。"""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    migrations = [
        "CREATE INDEX IF NOT EXISTS ix_holding_account_ticker ON holding (account_id, ticker);",
        "CREATE INDEX IF NOT EXISTS ix_holding_account_cash_currency ON holding (account_id, is_cash, currency);",
        'CREATE INDEX IF NOT EXISTS ix_transaction_account_ticker ON "transaction" (account_id, ticker);',
        'CREATE INDEX IF NOT EXISTS ix_transaction_date ON "transaction" (transaction_date);',
    ]

    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.debug("Ledger 索引遷移成功：%s", sql.strip())
            except OperationalError:
                conn.rollback()


def _backfill_signal_since() -> None:
    """
    回填 Stock.signal_since：對已有非 NORMAL 訊號但 signal_since 為 NULL 的股票，
    從 ScanLog 往前找到最早連續同訊號的掃描時間作為起始點。
    """
    from domain.entities import ScanLog, Stock
    from domain.enums import ScanSignal

    with Session(engine) as session:
        # 先快速查詢是否有任何需要回填的股票，避免每次啟動都進行完整掃描
        candidates = session.exec(
            select(Stock).where(
                Stock.signal_since.is_(None),  # type: ignore[union-attr]
                Stock.last_scan_signal != ScanSignal.NORMAL.value,
            )
        ).all()

        if not candidates:
            logger.debug("signal_since 無需回填。")
            return

        updated = 0
        for stock in candidates:
            # Walk ScanLog backwards to find how far back this signal streak goes
            logs = (
                session.exec(
                    select(ScanLog)
                    .where(ScanLog.stock_ticker == stock.ticker)
                    .order_by(ScanLog.scanned_at.desc())  # type: ignore[union-attr]
                    .limit(200)
                )
            ).all()
            since = None
            for log in logs:
                if log.signal == stock.last_scan_signal:
                    since = log.scanned_at
                else:
                    break
            if since is not None:
                stock.signal_since = since
                updated += 1
        if updated:
            session.commit()
            logger.info("signal_since 回填完成：%d 筆。", updated)


def _normalize_eligible_fund_names() -> None:
    """One-time NFKC normalization for existing eligible-asset fund names."""
    from domain.entities import EligibleAsset

    with Session(engine) as session:
        assets = session.exec(select(EligibleAsset)).all()
        if not assets:
            logger.debug("eligible fund_name 正規化：無資料可更新。")
            return

        updated = 0
        for asset in assets:
            normalized_name = unicodedata.normalize("NFKC", str(asset.fund_name or ""))
            if normalized_name == asset.fund_name:
                continue
            asset.fund_name = normalized_name
            session.add(asset)
            updated += 1

        if updated:
            session.commit()
            logger.info("eligible fund_name NFKC 正規化完成：%d 筆。", updated)
        else:
            logger.debug("eligible fund_name 已為 NFKC，無需更新。")


def create_db_and_tables() -> None:
    """建立所有 SQLModel 定義的資料表（若不存在），並執行遷移與資料載入。"""
    # 確保所有 Entity 已被 import，SQLModel metadata 才會完整
    import domain.entities  # noqa: F401

    logger.info("建立資料表（若不存在）...")
    SQLModel.metadata.create_all(engine)
    logger.info("資料表就緒。")

    _run_migrations()
    _run_smart_money_migrations()
    _run_backtest_migrations()
    _run_ledger_indexes()

    logger.info("載入系統人格範本...")
    _load_system_personas()
    logger.info("人格範本就緒。")

    _encrypt_plaintext_tokens()
    _normalize_eligible_fund_names()
    _backfill_signal_since()


def get_session() -> Generator[Session, None, None]:
    """FastAPI Dependency：提供一個 DB Session，結束後自動關閉。"""
    with Session(engine) as session:
        yield session
