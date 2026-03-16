"""Tax wrapper API schemas."""

from datetime import date

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
