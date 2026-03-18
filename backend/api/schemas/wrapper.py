"""Tax wrapper API schemas."""

from datetime import date, datetime

from pydantic import BaseModel


class QuotaStatusResponse(BaseModel):
    wrapper: str
    wrapper_annual_remaining: float
    combined_annual_remaining: float
    lifetime_remaining: float
    growth_sub_limit_remaining: float | None = None
    wrapper_annual_used: float
    combined_annual_used: float
    lifetime_used: float
    growth_sub_limit_used: float | None = None


class AllQuotasResponse(BaseModel):
    year: int
    as_of: date
    restoration_policy: str
    quotas: dict[str, QuotaStatusResponse]


class RestorationForecastItem(BaseModel):
    tax_wrapper: str
    amount: float
    effective_date: date
    source_transaction_id: int | None = None


class RestorationForecastResponse(BaseModel):
    pending: list[RestorationForecastItem]
    total_pending: float
    restoration_policy: str


class EligibilityCheckResponse(BaseModel):
    ticker: str
    wrapper: str
    eligible: bool
    reasons: list[str]
    suggested_wrapper: str | None = None
    asset_type: str | None = None


class EligibleAssetItem(BaseModel):
    ticker: str
    fund_name: str
    asset_type: str
    broker: str | None = None
    trust_fee_pct: float | None = None


class EligibleAssetsResponse(BaseModel):
    wrapper: str
    count: int
    items: list[EligibleAssetItem]


class EligibleAssetsMetadataResponse(BaseModel):
    wrapper: str
    count: int
    last_refreshed_at: datetime | None = None
    source: str


class EligibleAssetsRefreshStats(BaseModel):
    added: int
    updated: int
    deactivated: int


class EligibleAssetsRefreshResponse(BaseModel):
    wrapper: str
    source: str
    stats: EligibleAssetsRefreshStats
    metadata: EligibleAssetsMetadataResponse


class EligibleAssetsUploadResponse(BaseModel):
    wrapper: str
    filename: str
    source: str
    stats: EligibleAssetsRefreshStats
    metadata: EligibleAssetsMetadataResponse


class ContributionEntryItem(BaseModel):
    id: int
    tax_wrapper: str
    entry_type: str
    fiscal_year: int
    amount: float
    transaction_id: int | None = None
    effective_date: date
    note: str
    created_at: datetime


class ContributionsResponse(BaseModel):
    count: int
    items: list[ContributionEntryItem]


class RoutingSuggestionItem(BaseModel):
    wrapper: str
    amount: float
    reason: str


class RoutingSuggestRequest(BaseModel):
    ticker: str
    total_amount: float


class RoutingSuggestResponse(BaseModel):
    ticker: str
    total_amount: float
    suggestions: list[RoutingSuggestionItem]


class DeTaxOpportunityItem(BaseModel):
    ticker: str
    account_id: int
    unrealized_loss: float
    estimated_tax_saved: float
    sell_quantity: float
    reason: str


class NavSyncFailedDetail(BaseModel):
    ticker: str
    reason: str


class NavSyncPreRefreshStatus(BaseModel):
    attempted: bool
    success: bool
    wrappers_synced: list[str]
    error: str | None = None


class NavSyncResponse(BaseModel):
    synced: int
    failed: int
    failed_tickers: list[str]
    failed_details: list[NavSyncFailedDetail]
    pre_refresh: NavSyncPreRefreshStatus | None = None


class DeTaxResponse(BaseModel):
    total_estimated_savings: float
    opportunities: list[DeTaxOpportunityItem]
