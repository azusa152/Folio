"""
API — Portfolio / Holding / Rebalance / Withdrawal / StressTest / Currency Schemas。
"""

from typing import Literal

from pydantic import BaseModel, Field

from domain.enums import StockCategory

# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class WithdrawRequest(BaseModel):
    """POST /withdraw 請求 Body。"""

    target_amount: float
    display_currency: str = "USD"
    notify: bool = True


# ---------------------------------------------------------------------------
# Response Schemas — Holdings
# ---------------------------------------------------------------------------


class HoldingResponse(BaseModel):
    """GET /holdings 回傳的單一持倉。"""

    id: int
    ticker: str
    coingecko_id: str | None = None
    category: StockCategory
    quantity: float
    cost_basis: float | None = None
    broker: str | None = None
    account_id: int | None = None
    currency: str = "USD"
    account_type: str | None = None
    is_cash: bool
    purchase_fx_rate: float | None = None
    updated_at: str


class SellablePositionItem(BaseModel):
    """單一可賣出部位（SELL / DIVIDEND picker 用）。"""

    ticker: str
    fund_name: str
    quantity: float
    cost_basis: float | None = None
    current_price: float | None = None
    market_value: float | None = None
    currency: str = "USD"
    value_source: Literal["live_price", "cost_basis", "unavailable"] = "unavailable"


class SellablePositionsResponse(BaseModel):
    """指定帳戶可賣出部位清單。"""

    items: list[SellablePositionItem] = []
    count: int = 0


# ---------------------------------------------------------------------------
# Response Schemas — Rebalance / Portfolio Analysis
# ---------------------------------------------------------------------------


class CategoryAllocation(BaseModel):
    """單一分類的配置分析。"""

    target_pct: float
    current_pct: float
    drift_pct: float
    market_value: float


class HoldingDetail(BaseModel):
    """再平衡分析中的持倉明細（account+ticker）。"""

    account_id: int | None = None
    account_name: str | None = None
    ticker: str
    category: str
    currency: str = "USD"
    quantity: float
    market_value: float
    weight_pct: float
    avg_cost: float | None = None
    cost_total: float | None = None  # avg_cost * quantity * fx，以 display_currency 計
    current_price: float | None = None
    change_pct: float | None = None
    change_value: float | None = None
    total_gain_value: float | None = None
    total_gain_pct: float | None = None
    purchase_fx_rate: float | None = None
    current_fx_rate: float | None = None


class XRayEntry(BaseModel):
    """X-Ray: 單一標的真實曝險（直接持倉 + ETF 間接曝險）。"""

    symbol: str
    name: str = ""
    direct_value: float = 0.0
    direct_weight_pct: float = 0.0
    indirect_value: float = 0.0
    indirect_weight_pct: float = 0.0
    total_value: float = 0.0
    total_weight_pct: float = 0.0
    indirect_sources: list[str] = []  # e.g. ["VTI (5.2%)", "QQQ (8.1%)"]


class XRaySkippedETF(BaseModel):
    """X-Ray 無法穿透的 ETF 摘要。"""

    ticker: str
    weight_pct: float = 0.0


class SectorExposureItem(BaseModel):
    """行業板塊曝險單筆資料（股票持倉用）。"""

    sector: str
    value: float
    weight_pct: float  # 佔總投資組合 %
    equity_pct: float  # 佔股票部位 %


class WrapperAllocationItem(BaseModel):
    wrapper: str
    categories: dict[str, float]
    total: float


class PlacementSuggestionItem(BaseModel):
    ticker: str
    category: str
    from_wrapper: str
    to_wrapper: str
    amount: float
    reason: str


class TaxSavingsEstimateItem(BaseModel):
    annual_nisa_benefit: float
    annual_detax_benefit: float
    annual_ideco_deduction: float
    total_annual: float
    projected_10yr: float
    projected_20yr: float


class TsumitateMigrationItem(BaseModel):
    monthly_amount: float
    source_wrapper: str
    eligible_tickers: list[str]
    reason: str


class RebalanceResponse(BaseModel):
    """GET /rebalance 回傳的再平衡分析。"""

    total_value: float
    previous_total_value: float | None = None
    total_value_change: float | None = None
    total_value_change_pct: float | None = None
    display_currency: str = "USD"
    categories: dict[str, CategoryAllocation]
    advice: list[str]
    holdings_detail: list[HoldingDetail] = []
    xray: list[XRayEntry] = []
    xray_coverage_pct: float = Field(
        default=0.0,
        description="X-Ray coverage over equity exposure (cash/bond excluded)",
    )
    xray_skipped_etfs: list[XRaySkippedETF] = Field(default_factory=list)
    health_score: int = 100
    health_level: str = "healthy"  # "healthy" | "caution" | "alert"
    sector_exposure: list[SectorExposureItem] = []
    wrapper_allocations: list[WrapperAllocationItem] | None = None
    placement_suggestions: list[PlacementSuggestionItem] | None = None
    tax_savings_estimate: TaxSavingsEstimateItem | None = None
    tax_efficiency_score: float | None = None
    tsumitate_migration: TsumitateMigrationItem | None = None
    geographic_allocation: dict[str, float] = Field(
        default_factory=dict, description="Market value by geographic region"
    )
    asset_class_allocation: dict[str, float] = Field(
        default_factory=dict, description="Market value by asset class"
    )
    calculated_at: str = ""
    source: Literal["live", "snapshot"] = Field(
        default="live",
        description="Data source: 'live' (full real-time computation) or 'snapshot' (last daily snapshot, returned during cold start)",
    )
    snapshot_at: str | None = Field(
        default=None,
        description="ISO date of the portfolio snapshot when source='snapshot'",
    )


class XRayAlertResponse(BaseModel):
    """POST /rebalance/xray-alert 回應。"""

    message: str
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# Response Schemas — Currency Exposure
# ---------------------------------------------------------------------------


class CurrencyBreakdown(BaseModel):
    """幣別曝險分析：單一幣別的持倉分佈。"""

    currency: str
    value: float  # 以本幣計算的市值
    percentage: float  # 佔總投資組合的百分比
    is_home: bool


class FXMovement(BaseModel):
    """近期匯率變動。"""

    pair: str  # e.g. "USD/TWD"
    current_rate: float
    change_pct: float  # 期間內百分比變動
    direction: str  # "up" / "down" / "flat"
    impact_home_value: float = 0.0  # 估算對本幣資產價值的影響
    impact_cash_home_value: float = 0.0  # 估算對現金部位的影響
    impact_investment_home_value: float = 0.0  # 估算對投資部位（股票/加密貨幣）的影響


class FXRateAlertItem(BaseModel):
    """匯率變動警報項目（三層級偵測）。"""

    pair: str  # e.g. "USD/TWD"
    alert_type: str  # "daily_spike" / "short_term_swing" / "long_term_trend"
    change_pct: float  # signed percentage change
    direction: str  # "up" / "down"
    current_rate: float
    period_label: str  # "1 日" / "5 日" / "3 個月"


class CurrencyExposureResponse(BaseModel):
    """GET /currency-exposure 回傳的匯率曝險分析。"""

    home_currency: str
    total_value_home: float
    breakdown: list[CurrencyBreakdown]
    non_home_pct: float
    cash_breakdown: list[CurrencyBreakdown] = []
    cash_non_home_pct: float = 0.0
    total_cash_home: float = 0.0
    net_cash_impact: float = 0.0
    net_investment_impact: float = 0.0
    fx_movement_period: str = ""
    fx_movements: list[FXMovement]
    fx_rate_alerts: list[FXRateAlertItem] = []
    risk_level: str  # "low" / "medium" / "high"
    advice: list[str]
    calculated_at: str = ""


class FXAlertResponse(BaseModel):
    """POST /currency-exposure/alert 回應。"""

    message: str
    alerts: list[str] = []


# ---------------------------------------------------------------------------
# Response Schemas — Smart Withdrawal
# ---------------------------------------------------------------------------


class SellRecommendationResponse(BaseModel):
    """單筆賣出建議。"""

    ticker: str
    category: str
    quantity_to_sell: float
    sell_value: float
    reason: str
    unrealized_pl: float | None = None
    priority: int  # 1=再平衡, 2=節稅, 3=流動性


class WithdrawResponse(BaseModel):
    """POST /withdraw 回傳的提款計劃。"""

    recommendations: list[SellRecommendationResponse] = []
    total_sell_value: float = 0.0
    target_amount: float = 0.0
    shortfall: float = 0.0
    post_sell_drifts: dict[str, dict] = {}
    message: str = ""


# ---------------------------------------------------------------------------
# Response Schemas — Stress Test
# ---------------------------------------------------------------------------


class StressTestHoldingBreakdown(BaseModel):
    """壓力測試：單檔持倉損失細項。"""

    ticker: str
    category: str
    beta: float
    market_value: float
    expected_drop_pct: float
    expected_loss: float


class StressTestPainLevel(BaseModel):
    """壓力測試：痛苦等級分類。"""

    level: str
    label: str
    emoji: str


class StressTestResponse(BaseModel):
    """GET /stress-test 回傳結構：組合壓力測試結果。"""

    portfolio_beta: float
    scenario_drop_pct: float
    total_value: float
    total_loss: float
    total_loss_pct: float
    display_currency: str
    pain_level: StressTestPainLevel
    advice: list[str]
    disclaimer: str
    holdings_breakdown: list[StressTestHoldingBreakdown]
