"""
Domain — 資料庫實體 (SQLModel Tables)。
定義核心業務實體及資產配置相關資料表。
"""

import json as _json
import logging
from datetime import UTC, date, datetime

from pydantic import field_validator
from sqlalchemy import Index, UniqueConstraint, text
from sqlalchemy.types import TypeDecorator
from sqlmodel import Column, Field, SQLModel, String

from domain.constants import (
    DEFAULT_LANGUAGE,
    DEFAULT_NOTIFICATION_PREFERENCES,
    DEFAULT_NOTIFICATION_RATE_LIMITS,
    DEFAULT_USER_ID,
)
from domain.enums import HoldingAction, ScanSignal, StockCategory, TransactionType

logger = logging.getLogger(__name__)


def _normalize_stock_category(value: object) -> StockCategory:
    """Normalize persisted category values and guard against unknown legacy strings.

    Accepts both enum values (e.g. ``"Growth"``, ``"Trend_Setter"``) and uppercase
    enum member names stored by older DB rows (e.g. ``"GROWTH"``, ``"TREND_SETTER"``).
    """
    if isinstance(value, StockCategory):
        return value
    raw = str(value or "").strip()
    if not raw:
        return StockCategory.GROWTH
    # 1. Match by enum value (e.g., "Growth", "Trend_Setter", "MUTUAL_FUND").
    try:
        return StockCategory(raw)
    except ValueError:
        pass
    # 2. Match by enum member name (e.g., "GROWTH", "TREND_SETTER") for legacy DB rows.
    try:
        return StockCategory[raw]
    except KeyError:
        pass
    # 3. Truly unknown value — log and fallback gracefully.
    logger.warning(
        "Unknown stock category '%s' encountered; fallback to '%s'",
        raw,
        StockCategory.GROWTH.value,
    )
    return StockCategory.GROWTH


class _StockCategoryType(TypeDecorator):
    """Resilient DB type for stock category values.

    Stores category as plain text but always returns a valid ``StockCategory``
    on read, preventing crashes from legacy/unknown raw DB values.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: object, dialect) -> str:
        return _normalize_stock_category(value).value

    def process_result_value(self, value: object, dialect) -> StockCategory:
        return _normalize_stock_category(value)


class Stock(SQLModel, table=True):
    """追蹤清單中的個股。"""

    ticker: str = Field(primary_key=True, description="股票代號")
    category: StockCategory = Field(
        sa_column=Column(_StockCategoryType(), nullable=False), description="分類"
    )
    coingecko_id: str | None = Field(
        default=None, description="CoinGecko 幣種 ID（加密貨幣用）"
    )
    current_thesis: str = Field(default="", description="最新觀點")
    current_tags: str = Field(default="", description="最新標籤（逗號分隔）")
    display_order: int = Field(default=0, description="顯示順位（數字越小越前面）")
    last_scan_signal: str = Field(
        default=ScanSignal.NORMAL.value, description="上次掃描訊號"
    )
    signal_since: datetime | None = Field(default=None, description="目前訊號起始時間")
    is_active: bool = Field(default=True, description="是否追蹤中")
    is_etf: bool = Field(default=False, description="是否為 ETF（市場情緒排除用）")

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: object) -> StockCategory:
        return _normalize_stock_category(value)


class ThesisLog(SQLModel, table=True):
    """觀點版控紀錄。"""

    id: int | None = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    content: str = Field(description="觀點內容")
    tags: str = Field(default="", description="該版本的標籤快照（逗號分隔）")
    version: int = Field(description="版本號")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="建立時間",
    )


class RemovalLog(SQLModel, table=True):
    """移除紀錄（含版控，同一檔股票可多次移除）。"""

    id: int | None = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    reason: str = Field(description="移除原因")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="移除時間",
    )


class ScanLog(SQLModel, table=True):
    """掃描紀錄（每次掃描、每檔股票一筆）。"""

    id: int | None = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    signal: str = Field(description="掃描訊號（ScanSignal value）")
    market_status: str = Field(description="掃描時的市場情緒")
    market_status_details: str = Field(default="", description="市場情緒原因說明")
    details: str = Field(default="", description="警報詳情（JSON）")
    scanned_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="掃描時間",
    )


class PriceAlert(SQLModel, table=True):
    """自訂價格警報。"""

    id: int | None = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    metric: str = Field(description="指標名稱：rsi, price, bias")
    operator: str = Field(description="比較運算：lt, gt")
    threshold: float = Field(description="門檻值")
    is_active: bool = Field(default=True, description="是否啟用")
    last_triggered_at: datetime | None = Field(default=None, description="上次觸發時間")


# ---------------------------------------------------------------------------
# Asset Allocation — 投資組合配置相關
# ---------------------------------------------------------------------------


class SystemTemplate(SQLModel, table=True):
    """系統預設的投資組合人格範本（唯讀參考資料）。"""

    id: str = Field(
        primary_key=True, description="範本 ID（如 conservative, balanced）"
    )
    name: str = Field(description="範本名稱")
    description: str = Field(default="", description="範本說明")
    quote: str = Field(default="", description="引言")
    is_empty: bool = Field(default=False, description="是否為空白自訂範本")
    default_config: str = Field(default="{}", description="預設配置（JSON 字串）")


class UserInvestmentProfile(SQLModel, table=True):
    """使用者的投資組合目標配置。"""

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(default=DEFAULT_USER_ID, description="使用者 ID")
    name: str = Field(default="", description="配置名稱")
    source_template_id: str | None = Field(default=None, description="來源範本 ID")
    home_currency: str = Field(
        default="TWD", description="使用者的本幣（用於匯率曝險計算）"
    )
    config: str = Field(
        default="{}", description='配置（JSON 字串，如 {"Bond": 50, ...}）'
    )
    is_active: bool = Field(default=True, description="是否為啟用中的配置")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="建立時間",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="更新時間",
    )


class Account(SQLModel, table=True):
    """證券 / 銀行帳戶（用於持倉分組）。"""

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(default=DEFAULT_USER_ID, description="使用者 ID")
    name: str = Field(description="帳戶顯示名稱（如：IB 美股帳戶）")
    broker: str = Field(description="券商或銀行名稱")
    account_type: str = Field(
        default="brokerage",
        description="帳戶類型（brokerage / retirement / savings / crypto）",
    )
    tax_wrapper: str | None = Field(
        default=None,
        description="税制ラッパー種別（tokutei / nisa_tsumitate / nisa_growth / ideco / ippan）",
    )
    currency: str = Field(default="USD", description="帳戶基準幣別")
    market: str | None = Field(
        default=None,
        description="帳戶主要市場代碼（例如 US / JP / TW / HK）",
    )
    institution: str = Field(default="", description="金融機構全名（選填）")
    note: str = Field(default="", description="備註")
    is_active: bool = Field(default=True, description="是否啟用")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="建立時間",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="更新時間",
    )


class Holding(SQLModel, table=True):
    """使用者的實際持倉（用於資產配置計算）。"""

    __table_args__ = (
        Index("ix_holding_account_ticker", "account_id", "ticker"),
        Index(
            "ix_holding_account_cash_currency",
            "account_id",
            "is_cash",
            "currency",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(default=DEFAULT_USER_ID, description="使用者 ID")
    ticker: str = Field(description="資產代號（股票代號或幣別如 USD）")
    coingecko_id: str | None = Field(
        default=None, description="CoinGecko 幣種 ID（加密貨幣用，可選）"
    )
    category: StockCategory = Field(
        sa_column=Column(_StockCategoryType(), nullable=False), description="資產分類"
    )
    quantity: float = Field(description="持有數量（股數或金額）")
    cost_basis: float | None = Field(default=None, description="成本基礎（每單位）")
    broker: str | None = Field(default=None, description="券商名稱")
    account_id: int | None = Field(
        default=None, foreign_key="account.id", description="所屬帳戶 ID（選填）"
    )
    currency: str = Field(default="USD", description="持倉幣別（如 USD, TWD, JPY）")
    account_type: str | None = Field(
        default=None, description="帳戶類型（活存/定存/貨幣市場基金）"
    )
    is_cash: bool = Field(default=False, description="是否為現金類資產")
    purchase_fx_rate: float | None = Field(
        default=None, description="購入時匯率（1 單位持倉幣別 = ? 單位 USD）"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="更新時間",
    )

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: object) -> StockCategory:
        return _normalize_stock_category(value)


class Transaction(SQLModel, table=True):
    """持倉交易紀錄（含買賣、股息、入出金與對帳調整類型）。"""

    __table_args__ = (
        Index("ix_transaction_user_date", "user_id", "transaction_date"),
        Index("ix_transaction_holding_date", "holding_id", "transaction_date"),
        Index("ix_transaction_account_ticker", "account_id", "ticker"),
        Index("ix_transaction_account_date", "account_id", "transaction_date"),
        Index("ix_transaction_date", "transaction_date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(default=DEFAULT_USER_ID, description="使用者 ID")
    account_id: int | None = Field(
        default=None, foreign_key="account.id", description="關聯帳戶 ID（可選）"
    )
    holding_id: int | None = Field(
        default=None, foreign_key="holding.id", description="關聯持倉 ID（可選）"
    )
    ticker: str = Field(description="資產代號")
    transaction_type: TransactionType = Field(
        description=(
            "交易類型 (BUY/SELL/DIVIDEND/DEPOSIT/WITHDRAWAL/"
            "OPENING_BALANCE/ADJUSTMENT/STOCK_SPLIT/TRANSFER_IN/TRANSFER_OUT)"
        )
    )
    quantity: float = Field(description="交易數量")
    price: float | None = Field(default=None, description="每單位成交價格")
    total_amount: float = Field(description="交易總金額")
    currency: str = Field(default="USD", description="交易幣別")
    fx_rate: float | None = Field(
        default=None, description="交易時匯率（1 單位交易幣別 = ? USD）"
    )
    fee: float = Field(default=0.0, description="手續費")
    note: str = Field(default="", description="備註")
    transaction_date: date = Field(description="交易日期")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="建立時間",
    )


class StockSplitEvent(SQLModel, table=True):
    """偵測到的股票分割事件（待處理/已套用/已忽略）。"""

    __table_args__ = (
        UniqueConstraint("ticker", "split_date", "ratio", name="uq_stock_split_event"),
        Index("ix_stock_split_event_ticker_date", "ticker", "split_date"),
        Index("ix_stock_split_event_status", "status"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ticker: str = Field(description="股票代號")
    split_date: date = Field(description="分割生效日")
    ratio: float = Field(description="分割倍率（4:1=4.0，1:20=0.05）")
    status: str = Field(default="pending", description="pending/applied/dismissed")
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="偵測時間",
    )
    applied_at: datetime | None = Field(default=None, description="套用時間")


class DividendEvent(SQLModel, table=True):
    """偵測到的股息事件（待處理/已套用/已忽略）。"""

    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "ex_dividend_date",
            "amount_per_share",
            name="uq_dividend_event",
        ),
        Index("ix_dividend_event_ticker_date", "ticker", "ex_dividend_date"),
        Index("ix_dividend_event_status", "status"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ticker: str = Field(description="股票代號")
    ex_dividend_date: date = Field(description="除息日")
    amount_per_share: float = Field(description="每股股息（原幣別）")
    status: str = Field(default="pending", description="pending/applied/dismissed")
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="偵測時間",
    )
    applied_at: datetime | None = Field(default=None, description="套用時間")


class DriftAcknowledgment(SQLModel, table=True):
    """漂移/X-Ray 告警確認狀態，用於抑制重複提醒。"""

    __table_args__ = (
        UniqueConstraint("alert_type", "alert_key", name="uq_drift_ack_type_key"),
        Index("ix_drift_ack_type_key", "alert_type", "alert_key"),
        Index("ix_drift_ack_expires_at", "expires_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    alert_type: str = Field(description="drift/xray")
    alert_key: str = Field(description="drift=category, xray=symbol")
    acknowledged_value: float = Field(description="確認當下的偏離值（百分點）")
    acknowledged_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="確認時間",
    )
    expires_at: datetime = Field(description="抑制到期時間")


class ContributionLedgerEntry(SQLModel, table=True):
    """NISA / iDeCo 拠出金台帳エントリ（追記のみ・不変）。"""

    __table_args__ = (
        Index(
            "ix_contrib_user_wrapper_year",
            "user_id",
            "tax_wrapper",
            "fiscal_year",
        ),
        Index("ix_contrib_transaction", "transaction_id"),
        Index(
            "uq_contrib_transaction_entry_type",
            "transaction_id",
            "entry_type",
            unique=True,
            sqlite_where=text("transaction_id IS NOT NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(default=DEFAULT_USER_ID, description="使用者 ID")
    tax_wrapper: str = Field(description="税制ラッパー種別")
    entry_type: str = Field(
        description="エントリ種別（CONTRIBUTION / RESTORATION / ADJUSTMENT）"
    )
    fiscal_year: int = Field(description="対象年度（暦年）")
    amount: float = Field(
        description="簿価金額（JPY）。拠出=正、復活=負、調整=正負いずれか"
    )
    transaction_id: int | None = Field(
        default=None,
        foreign_key="transaction.id",
        description="元取引ID（冪等性キー）",
    )
    effective_date: date = Field(
        description="発効日（復活の場合、ポリシーにより翌年1/1 or 売却当日）"
    )
    note: str = Field(default="", description="備考")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="作成日時",
    )


class EligibleAsset(SQLModel, table=True):
    """NISA / iDeCo 対象資産マスター。"""

    __table_args__ = (
        Index(
            "uq_eligible_wrapper_ticker_broker",
            "tax_wrapper",
            "ticker",
            "broker",
            unique=True,
        ),
        Index(
            "uq_eligible_wrapper_ticker_null_broker",
            "tax_wrapper",
            "ticker",
            unique=True,
            sqlite_where=text("broker IS NULL"),
        ),
        Index("ix_eligible_wrapper_ticker", "tax_wrapper", "ticker"),
        Index("ix_eligible_wrapper_broker", "tax_wrapper", "broker"),
    )

    id: int | None = Field(default=None, primary_key=True)
    tax_wrapper: str = Field(description="対象ラッパー種別")
    ticker: str = Field(description="資産コード（ファンドコード or ティッカー）")
    fund_name: str = Field(default="", description="ファンド名称")
    asset_type: str = Field(
        default="mutual_fund",
        description="資産種別（mutual_fund / etf / stock / reit）",
    )
    broker: str | None = Field(
        default=None,
        description="証券会社（iDeCo用。NULLなら全社共通）",
    )
    trust_fee_pct: float | None = Field(
        default=None,
        description="信託報酬率（%）",
    )
    isin_code: str | None = Field(
        default=None,
        description="ISINコード（投信基準価額取得用）",
    )
    is_active: bool = Field(default=True, description="有効フラグ")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="更新日時",
    )


class MutualFundNav(SQLModel, table=True):
    """投資信託の日次基準価額（NAV）キャッシュ。"""

    __table_args__ = (
        Index("uq_mfnav_fund_code_date", "fund_code", "nav_date", unique=True),
    )

    id: int | None = Field(default=None, primary_key=True)
    fund_code: str = Field(index=True, description="投信協会ファンドコード（= ticker）")
    isin_code: str = Field(description="ISINコード")
    nav: float = Field(description="基準価額")
    nav_previous: float | None = Field(default=None, description="前日基準価額")
    nav_date: date = Field(description="基準価額日付")
    net_assets: float | None = Field(default=None, description="純資産総額（百万円）")
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="取得日時",
    )


class EligibleAssetSyncState(SQLModel, table=True):
    """NISA対象資産マスターの同期状態（ラッパー単位）。"""

    tax_wrapper: str = Field(primary_key=True, description="対象ラッパー種別")
    source: str = Field(default="unknown", description="更新ソース")
    last_refreshed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="最終更新日時",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="更新日時",
    )


class UserTelegramSettings(SQLModel, table=True):
    """使用者的 Telegram 通知設定（支援自訂 Bot）。"""

    user_id: str = Field(
        default=DEFAULT_USER_ID, primary_key=True, description="使用者 ID"
    )
    telegram_chat_id: str = Field(default="", description="Telegram Chat ID")
    custom_bot_token: str | None = Field(default=None, description="自訂 Bot Token")
    use_custom_bot: bool = Field(default=False, description="是否使用自訂 Bot")


class UserPreferences(SQLModel, table=True):
    """使用者偏好設定（跨裝置同步）。"""

    user_id: str = Field(
        default=DEFAULT_USER_ID, primary_key=True, description="使用者 ID"
    )
    language: str = Field(default=DEFAULT_LANGUAGE, description="偏好語言")
    privacy_mode: bool = Field(default=False, description="是否啟用隱私模式")
    terminology_mode: str = Field(
        default="simplified",
        description="術語顯示模式：simplified（簡化）或 expert（專業）",
    )
    notification_preferences: str = Field(
        default=_json.dumps(DEFAULT_NOTIFICATION_PREFERENCES),
        sa_column=Column(String, default=_json.dumps(DEFAULT_NOTIFICATION_PREFERENCES)),
        description="通知偏好 JSON（各類通知的啟用/停用）",
    )
    notification_rate_limits: str = Field(
        default=_json.dumps(DEFAULT_NOTIFICATION_RATE_LIMITS),
        sa_column=Column(String, default=_json.dumps(DEFAULT_NOTIFICATION_RATE_LIMITS)),
        description='通知頻率限制 JSON，格式：{"fx_alerts": {"max_count": 2, "window_hours": 24}}，空 dict 表示無限制',
    )

    def get_notification_prefs(self) -> dict[str, bool]:
        """解析通知偏好 JSON，缺少的 key 以預設值填補。"""
        try:
            stored = _json.loads(self.notification_preferences)
        except (TypeError, _json.JSONDecodeError):
            stored = {}
        return {**DEFAULT_NOTIFICATION_PREFERENCES, **stored}

    def set_notification_prefs(self, prefs: dict[str, bool]) -> None:
        """合併並序列化通知偏好。"""
        merged = {**DEFAULT_NOTIFICATION_PREFERENCES, **prefs}
        self.notification_preferences = _json.dumps(merged)

    def get_notification_rate_limits(self) -> dict[str, dict[str, int]]:
        """解析通知頻率限制 JSON。空 dict 表示全部無限制。"""
        try:
            stored = _json.loads(self.notification_rate_limits)
        except (TypeError, _json.JSONDecodeError):
            stored = {}
        return {**DEFAULT_NOTIFICATION_RATE_LIMITS, **stored}

    def set_notification_rate_limits(self, limits: dict[str, dict[str, int]]) -> None:
        """合併並序列化通知頻率限制（保留既有的其他類型設定）。"""
        existing = self.get_notification_rate_limits()
        merged = {**existing, **limits}
        self.notification_rate_limits = _json.dumps(merged)


# ---------------------------------------------------------------------------
# Smart Money Tracker (大師足跡追蹤)
# ---------------------------------------------------------------------------


class Guru(SQLModel, table=True):
    """追蹤的機構投資人（大師）。"""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(description="機構名稱 (e.g. Berkshire Hathaway)")
    cik: str = Field(unique=True, description="SEC CIK 代碼 (10-digit zero-padded)")
    display_name: str = Field(description="顯示名稱 (e.g. Warren Buffett)")
    is_active: bool = Field(default=True, description="是否追蹤中")
    is_default: bool = Field(default=False, description="是否為系統預設大師")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="建立時間",
    )
    style: str | None = Field(
        default=None,
        description="投資風格 (VALUE, GROWTH, MACRO, QUANT, ACTIVIST, MULTI_STRATEGY)",
    )
    tier: str | None = Field(
        default=None,
        description="等級排名 (TIER_1, TIER_2, TIER_3)",
    )


class GuruFiling(SQLModel, table=True):
    """大師的 13F 季度申報記錄。"""

    id: int | None = Field(default=None, primary_key=True)
    guru_id: int = Field(foreign_key="guru.id", description="對應大師 ID")
    accession_number: str = Field(unique=True, description="SEC 文件編號")
    report_date: str = Field(description="持倉基準日 (e.g. 2024-12-31)")
    filing_date: str = Field(description="SEC 公告日 (e.g. 2025-02-14)")
    total_value: float | None = Field(default=None, description="總持倉市值 (千美元)")
    holdings_count: int = Field(default=0, description="持倉數量")
    filing_url: str = Field(default="", description="SEC EDGAR 原始文件連結")
    synced_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="同步時間",
    )


class GuruHolding(SQLModel, table=True):
    """大師某次申報中的個別持倉。"""

    id: int | None = Field(default=None, primary_key=True)
    filing_id: int = Field(foreign_key="gurufiling.id", description="對應申報 ID")
    guru_id: int = Field(foreign_key="guru.id", description="對應大師 ID")
    cusip: str = Field(description="CUSIP 代碼")
    ticker: str | None = Field(default=None, description="對應的股票代號")
    company_name: str = Field(description="13F 中的公司名稱")
    value: float = Field(description="持倉市值 (千美元)")
    shares: float = Field(description="持股數量")
    action: str = Field(
        default=HoldingAction.UNCHANGED.value, description="與前季比較的動作"
    )
    change_pct: float | None = Field(default=None, description="持股數量變動百分比")
    weight_pct: float | None = Field(default=None, description="佔該大師總持倉比例")
    sector: str | None = Field(default=None, description="GICS 行業板塊（yfinance）")


# ---------------------------------------------------------------------------
# Portfolio Snapshots — 投資組合每日快照（供績效圖表使用）
# ---------------------------------------------------------------------------


class PortfolioSnapshot(SQLModel, table=True):
    """每日投資組合總市值快照（用於歷史績效追蹤）。"""

    id: int | None = Field(default=None, primary_key=True)
    snapshot_date: date = Field(
        index=True, unique=True, description="快照日期（每日唯一）"
    )
    total_value: float = Field(description="投資組合總市值")
    category_values: str = Field(
        default="{}", description="各類別市值 JSON（如 {'Trend_Setter': 45000, ...}）"
    )
    display_currency: str = Field(default="USD", description="顯示幣別")
    benchmark_value: float | None = Field(
        default=None, description="同日 S&P 500 收盤價（基準比較用，向下相容）"
    )
    benchmark_values: str = Field(
        default="{}",
        description='多基準指數收盤價 JSON，如 {"^GSPC": 5000, "VT": 120, "^N225": 38000, "^TWII": 18000}',
    )
    holding_values: str = Field(
        default="{}",
        description='個股市值 JSON（前 50 大），如 {"AAPL": 15000, "2330.TW": 8000}',
    )
    cost_basis_total: float | None = Field(
        default=None,
        description="所有持倉總成本基礎（供貢獻度圖表使用）",
    )
    geographic_values: str = Field(
        default="{}",
        description='依地理區域市值 JSON，如 {"US": 50000, "TW": 20000, "JP": 10000}',
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="建立時間",
    )


class FXWatchConfig(SQLModel, table=True):
    """外匯換匯時機監控配置。"""

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(default=DEFAULT_USER_ID, description="使用者 ID")
    base_currency: str = Field(description="基礎貨幣，例如 USD")
    quote_currency: str = Field(description="報價貨幣，例如 TWD")
    recent_high_days: int = Field(default=30, description="回溯天數（近期高點判定）")
    consecutive_increase_days: int = Field(default=3, description="連續上漲天數門檻")
    alert_on_recent_high: bool = Field(default=True, description="是否啟用近期高點警報")
    alert_on_consecutive_increase: bool = Field(
        default=True, description="是否啟用連續上漲警報"
    )
    target_rate: float | None = Field(
        default=None, description="目標匯率（達標時觸發警報）"
    )
    target_direction: str | None = Field(
        default=None, description="目標方向：above / below"
    )
    reminder_interval_hours: int = Field(
        default=24, description="提醒間隔（小時），避免重複通知"
    )
    is_active: bool = Field(default=True, description="是否啟用")
    last_alerted_at: datetime | None = Field(default=None, description="上次警報時間")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="建立時間"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="更新時間"
    )


# ---------------------------------------------------------------------------
# Notification Log (rate-limit tracking)
# ---------------------------------------------------------------------------


class NotificationLog(SQLModel, table=True):
    """通知發送日誌，用於頻率限制（每段時間最多 N 次）。"""

    id: int | None = Field(default=None, primary_key=True)
    notification_type: str = Field(
        index=True, description="通知類型，例如 'fx_alerts'、'fx_watch_alerts'"
    )
    sent_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None),
        index=True,
        description="發送時間（naive UTC，與 SQLite 相容）",
    )
