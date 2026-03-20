"""Domain logic for smart purchase routing across tax wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.portfolio.tax_wrapper import QuotaStatus


@dataclass(frozen=True)
class RoutingSuggestion:
    wrapper: str
    amount: float
    reason: str  # i18n key
    account_id: int | None = None


def suggest_purchase_routing(
    total_amount: float,
    quotas: dict[str, QuotaStatus],
    eligibility: dict[str, bool],
) -> list[RoutingSuggestion]:
    """Suggest a wrapper split that maximizes tax benefit for a planned BUY."""
    if total_amount <= 0:
        return []

    suggestions: list[RoutingSuggestion] = []
    remaining = float(total_amount)

    priority = [
        ("nisa_growth", "routing.nisa_growth_tax_free"),
        ("nisa_tsumitate", "routing.nisa_tsumitate_tax_free"),
        ("ideco", "routing.ideco_tax_deferred"),
    ]

    for wrapper, reason in priority:
        if remaining <= 0:
            break
        if not eligibility.get(wrapper, False):
            continue

        quota = quotas.get(wrapper)
        if quota is None:
            continue

        available = min(
            float(quota.wrapper_annual_remaining),
            float(quota.combined_annual_remaining),
            float(quota.lifetime_remaining),
        )
        if wrapper == "nisa_growth" and quota.growth_sub_limit_remaining is not None:
            available = min(available, float(quota.growth_sub_limit_remaining))
        if available <= 0:
            continue

        allocation = min(remaining, available)
        suggestions.append(
            RoutingSuggestion(
                wrapper=wrapper,
                amount=round(allocation, 2),
                reason=reason,
            )
        )
        remaining -= allocation

    if remaining > 0:
        suggestions.append(
            RoutingSuggestion(
                wrapper="tokutei",
                amount=round(remaining, 2),
                reason="routing.tokutei_overflow",
            )
        )

    return suggestions
