"""Domain logic for DeTAX (tax-loss harvesting opportunities)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from domain.core.constants import TOKUTEI_TAX_RATE

DETAX_MIN_BENEFIT_JPY = 4_000


class HoldingLike(Protocol):
    ticker: str
    account_id: int | None
    quantity: float
    cost_basis: float | None
    current_price: float | None


@dataclass(frozen=True)
class DeTaxOpportunity:
    ticker: str
    account_id: int
    unrealized_loss: float
    estimated_tax_saved: float
    sell_quantity: float
    reason: str  # i18n key


def find_detax_opportunities(
    tokutei_holdings: list[HoldingLike],
    realized_gains_ytd: float,
) -> list[DeTaxOpportunity]:
    """Find Tokutei holdings with losses that can offset realized gains."""
    if realized_gains_ytd <= 0:
        return []

    opportunities: list[DeTaxOpportunity] = []
    remaining_gains = float(realized_gains_ytd)

    losers = [
        h
        for h in tokutei_holdings
        if h.account_id is not None
        and h.quantity > 0
        and h.cost_basis is not None
        and h.current_price is not None
        and h.current_price < h.cost_basis
    ]
    losers.sort(
        key=lambda h: (h.cost_basis - h.current_price) * h.quantity,
        reverse=True,
    )

    for holding in losers:
        if remaining_gains <= 0:
            break

        loss_per_unit = float(holding.cost_basis - holding.current_price)
        total_loss = loss_per_unit * float(holding.quantity)
        harvestable = min(total_loss, remaining_gains)
        estimated_tax_saved = harvestable * TOKUTEI_TAX_RATE
        if estimated_tax_saved < DETAX_MIN_BENEFIT_JPY:
            continue

        sell_quantity = (
            float(holding.quantity)
            if harvestable >= total_loss
            else (harvestable / loss_per_unit)
        )
        opportunities.append(
            DeTaxOpportunity(
                ticker=holding.ticker,
                account_id=int(holding.account_id),
                unrealized_loss=round(-harvestable, 2),
                estimated_tax_saved=round(estimated_tax_saved, 2),
                sell_quantity=round(sell_quantity, 6),
                reason="detax.harvest_loss",
            )
        )
        remaining_gains -= harvestable

    return opportunities
