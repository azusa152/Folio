"""API schemas for fund sector weight overrides."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FundSectorWeightItem(BaseModel):
    """Shared read/write item. Weight uses ge=0.0 so stored rows never cause a 500 on GET."""

    sector: str = Field(min_length=1)
    weight: float = Field(ge=0.0, le=1.0)


class FundSectorWeightsRequest(BaseModel):
    weights: list[FundSectorWeightItem]
    source: Literal["manual", "proxy_etf", "seed"] = "manual"

    @model_validator(mode="after")
    def validate_weights(self) -> "FundSectorWeightsRequest":
        for item in self.weights:
            if item.weight <= 0.0:
                raise ValueError(
                    f"weight for sector '{item.sector}' must be > 0.0 (got {item.weight})."
                )
        total = sum(item.weight for item in self.weights)
        if total > 1.001:
            raise ValueError(
                f"Total weight {total:.4f} exceeds 1.0. "
                "For balanced funds, provide only the equity-portion weights (sum ≤ 1.0)."
            )
        return self


class FundSectorWeightsResponse(BaseModel):
    fund_code: str
    weights: list[FundSectorWeightItem]
    source: str
    total_weight: float
