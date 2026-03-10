"""Analytics API schemas."""

from pydantic import BaseModel, Field


class DrawdownPointResponse(BaseModel):
    date: str
    drawdown_pct: float
    total_value: float
    peak_value: float


class RiskMetricsResponse(BaseModel):
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    max_drawdown_pct: float
    calmar_ratio: float | None = None
    trading_days: int


class InsightResponse(BaseModel):
    key: str
    severity: str
    vars: dict = Field(default_factory=dict)
    category: str


class ContributionGrowthPoint(BaseModel):
    date: str
    market_value: float
    cost_basis: float | None = None
