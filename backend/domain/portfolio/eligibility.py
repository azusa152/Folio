"""
Domain — Asset eligibility rules for tax wrappers.

Rules are pure functions; approved asset sets are injected by callers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reasons: list[str]
    suggested_wrapper: str | None = None
    asset_type: str | None = None


# Growth NISA exclusion flags.
GROWTH_EXCLUDED_FLAGS = {
    "leveraged",
    "inverse",
    "monthly_distribution",
    "supervisory",
}


def check_tsumitate_eligibility(
    ticker: str,
    approved_tickers: set[str],
) -> EligibilityResult:
    """Tsumitate NISA: only approved mutual funds."""
    if ticker in approved_tickers:
        return EligibilityResult(eligible=True, reasons=[])
    return EligibilityResult(
        eligible=False,
        reasons=["eligibility.not_in_tsumitate_approved_list"],
        suggested_wrapper="nisa_growth",
    )


def check_growth_eligibility(
    ticker: str,
    asset_type: str,
    flags: set[str],
    trust_period_years: int | None,
) -> EligibilityResult:
    """Growth NISA: stocks/ETFs/MFs/REITs minus exclusion flags."""
    _ = ticker  # Future-proofing: ticker-level exclusions can be added here later.
    reasons: list[str] = []
    if asset_type not in {"stock", "etf", "mutual_fund", "reit"}:
        reasons.append("eligibility.invalid_asset_type")
    if flags & GROWTH_EXCLUDED_FLAGS:
        reasons.append("eligibility.excluded_flag")
    if trust_period_years is not None and trust_period_years < 20:
        reasons.append("eligibility.trust_period_too_short")
    if reasons:
        return EligibilityResult(
            eligible=False,
            reasons=reasons,
            suggested_wrapper="tokutei",
        )
    return EligibilityResult(eligible=True, reasons=[])


def check_ideco_eligibility(
    ticker: str,
    broker_lineup: set[str],
) -> EligibilityResult:
    """iDeCo: broker-specific product lineup."""
    if ticker in broker_lineup:
        return EligibilityResult(eligible=True, reasons=[])
    return EligibilityResult(
        eligible=False,
        reasons=["eligibility.not_in_ideco_lineup"],
        suggested_wrapper="tokutei",
    )


def check_eligibility(
    ticker: str,
    wrapper: str,
    asset_type: str = "stock",
    flags: set[str] | None = None,
    trust_period_years: int | None = None,
    approved_tickers: set[str] | None = None,
    broker_lineup: set[str] | None = None,
) -> EligibilityResult:
    """Dispatch to wrapper-specific eligibility rules."""
    if wrapper in {"tokutei", "ippan"}:
        return EligibilityResult(eligible=True, reasons=[])
    if wrapper == "nisa_tsumitate":
        return check_tsumitate_eligibility(ticker, approved_tickers or set())
    if wrapper == "nisa_growth":
        return check_growth_eligibility(
            ticker=ticker,
            asset_type=asset_type,
            flags=flags or set(),
            trust_period_years=trust_period_years,
        )
    if wrapper == "ideco":
        return check_ideco_eligibility(ticker, broker_lineup or set())
    return EligibilityResult(eligible=True, reasons=[])
