"""Application service for smart routing and DeTAX suggestions."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from application.portfolio.eligibility_service import check_asset_eligibility
from application.portfolio.wrapper_service import get_all_wrapper_quotas
from domain.constants import DEFAULT_USER_ID, SKIP_PRICE_FETCH_CATEGORIES
from domain.enums import StockCategory, TransactionType
from domain.portfolio.detax import DeTaxOpportunity, find_detax_opportunities
from domain.portfolio.routing import RoutingSuggestion, suggest_purchase_routing
from domain.portfolio.tax_wrapper import QuotaStatus
from infrastructure import repositories as repo
from infrastructure.market_data.market_data import get_technical_signals

if TYPE_CHECKING:
    from sqlmodel import Session

    from domain.entities import Transaction

ROUTING_WRAPPERS = ("nisa_growth", "nisa_tsumitate", "ideco")
ROUTING_WRAPPERS_WITH_OVERFLOW = ("nisa_growth", "nisa_tsumitate", "ideco", "tokutei")
STOCK_INCREASE_TYPES = {
    TransactionType.BUY,
    TransactionType.OPENING_BALANCE,
    TransactionType.TRANSFER_IN,
}
STOCK_DECREASE_TYPES = {
    TransactionType.SELL,
    TransactionType.TRANSFER_OUT,
}


def _is_cash_ticker(ticker: str, currency: str) -> bool:
    return ticker.strip().upper() == currency.strip().upper()


def _is_japanese_routing_account(account: Any) -> bool:
    """Return True when an account is eligible for JP wrapper routing."""
    wrapper = (account.tax_wrapper or "").strip().lower()
    market = (account.market or "").strip().upper()
    return wrapper in ROUTING_WRAPPERS_WITH_OVERFLOW and market == "JP"


def _resolve_unit_price(txn: Transaction) -> float | None:
    if txn.price is not None and float(txn.price) > 0:
        return float(txn.price)
    qty = abs(float(txn.quantity or 0))
    total_amount = abs(float(txn.total_amount or 0))
    if qty <= 0 or total_amount <= 0:
        return None
    return total_amount / qty


def _compute_realized_gains_ytd(
    transactions: list[Transaction],
    tokutei_account_ids: set[int],
    *,
    start_of_year: date,
    today: date,
) -> float:
    positions: dict[tuple[int, str], tuple[float, float | None]] = {}
    realized_gain = 0.0

    ordered = sorted(
        transactions,
        key=lambda txn: (
            txn.transaction_date,
            txn.created_at,
            txn.id or 0,
        ),
    )
    for txn in ordered:
        if txn.account_id is None:
            continue
        account_id = int(txn.account_id)
        if account_id not in tokutei_account_ids:
            continue

        ticker = str(txn.ticker or "").strip().upper()
        currency = str(txn.currency or "").strip().upper()
        if not ticker or _is_cash_ticker(ticker, currency):
            continue

        key = (account_id, ticker)
        current_qty, avg_cost = positions.get(key, (0.0, None))
        qty = abs(float(txn.quantity or 0))
        if qty <= 0:
            continue
        fee = abs(float(txn.fee or 0))
        unit_price = _resolve_unit_price(txn)

        if txn.transaction_type in STOCK_INCREASE_TYPES:
            if unit_price is None:
                positions[key] = (current_qty + qty, avg_cost)
                continue
            acquisition_cost = (unit_price * qty) + fee
            if current_qty <= 0 or avg_cost is None:
                positions[key] = (qty, acquisition_cost / qty)
                continue
            new_qty = current_qty + qty
            new_avg = ((current_qty * avg_cost) + acquisition_cost) / new_qty
            positions[key] = (new_qty, new_avg)
            continue

        if txn.transaction_type in STOCK_DECREASE_TYPES:
            if current_qty <= 0:
                continue
            sell_qty = min(qty, current_qty)
            applied_fee = fee * (sell_qty / qty) if qty > 0 else 0.0
            if (
                txn.transaction_type == TransactionType.SELL
                and unit_price is not None
                and avg_cost is not None
                and start_of_year <= txn.transaction_date <= today
            ):
                realized_gain += ((unit_price - avg_cost) * sell_qty) - applied_fee
            new_qty = max(0.0, current_qty - sell_qty)
            positions[key] = (new_qty, avg_cost if new_qty > 0 else None)
            continue

        if txn.transaction_type == TransactionType.ADJUSTMENT:
            sign = 1.0 if float(txn.total_amount or 0) >= 0 else -1.0
            delta_qty = qty * sign
            if delta_qty > 0:
                if unit_price is None:
                    positions[key] = (current_qty + delta_qty, avg_cost)
                    continue
                acquisition_cost = unit_price * delta_qty
                if current_qty <= 0 or avg_cost is None:
                    positions[key] = (delta_qty, acquisition_cost / delta_qty)
                    continue
                new_qty = current_qty + delta_qty
                new_avg = ((current_qty * avg_cost) + acquisition_cost) / new_qty
                positions[key] = (new_qty, new_avg)
            elif delta_qty < 0 and current_qty > 0:
                reduce_qty = min(abs(delta_qty), current_qty)
                new_qty = max(0.0, current_qty - reduce_qty)
                positions[key] = (new_qty, avg_cost if new_qty > 0 else None)

    return round(max(0.0, realized_gain), 2)


def suggest_transaction_routing(
    session: Session,
    ticker: str,
    total_amount: float,
    user_id: str = DEFAULT_USER_ID,
) -> list[RoutingSuggestion]:
    """Suggest how to split a BUY amount across wrappers."""
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker or total_amount <= 0:
        return []

    all_accounts = [
        account
        for account in repo.find_all_accounts(session, active_only=True)
        if account.user_id == user_id
    ]
    accounts = [
        account for account in all_accounts if _is_japanese_routing_account(account)
    ]
    if not accounts:
        return []

    wrapper_account_id: dict[str, int] = {}
    for account in accounts:
        if account.id is None:
            continue
        wrapper = (account.tax_wrapper or "").strip().lower()
        existing = wrapper_account_id.get(wrapper)
        account_id = int(account.id)
        if existing is None or account_id < existing:
            wrapper_account_id[wrapper] = account_id

    wrappers_present = {
        (account.tax_wrapper or "").strip().lower()
        for account in accounts
        if account.tax_wrapper
    }

    today = date.today()
    quota_payload = get_all_wrapper_quotas(session, user_id, today.year, today)
    quotas: dict[str, QuotaStatus] = {
        wrapper: QuotaStatus(
            wrapper_annual_remaining=float(payload["wrapper_annual_remaining"]),
            combined_annual_remaining=float(payload["combined_annual_remaining"]),
            lifetime_remaining=float(payload["lifetime_remaining"]),
            growth_sub_limit_remaining=(
                float(payload["growth_sub_limit_remaining"])
                if payload.get("growth_sub_limit_remaining") is not None
                else None
            ),
        )
        for wrapper, payload in quota_payload.items()
    }
    if "ideco" in wrappers_present:
        # Phase 4: iDeCo contribution caps are introduced in Phase 6.
        # Use planned purchase amount as a temporary routing capacity so iDeCo
        # can participate in the split when the wrapper account exists.
        ideco_capacity = max(0.0, float(total_amount))
        quotas["ideco"] = QuotaStatus(
            wrapper_annual_remaining=ideco_capacity,
            combined_annual_remaining=ideco_capacity,
            lifetime_remaining=ideco_capacity,
            growth_sub_limit_remaining=None,
        )

    eligibility: dict[str, bool] = {}
    for wrapper in ROUTING_WRAPPERS:
        if wrapper not in wrappers_present:
            eligibility[wrapper] = False
            continue

        wrapper_account = next(
            (
                account
                for account in accounts
                if (account.tax_wrapper or "").strip().lower() == wrapper
            ),
            None,
        )
        eligibility_result = check_asset_eligibility(
            session=session,
            ticker=normalized_ticker,
            wrapper=wrapper,
            broker=wrapper_account.broker if wrapper_account else None,
        )
        eligibility[wrapper] = eligibility_result.eligible

    base_suggestions = suggest_purchase_routing(
        ticker=normalized_ticker,
        total_amount=float(total_amount),
        quotas=quotas,
        eligibility=eligibility,
    )
    return [
        RoutingSuggestion(
            wrapper=item.wrapper,
            amount=item.amount,
            reason=item.reason,
            account_id=wrapper_account_id.get(item.wrapper),
        )
        for item in base_suggestions
    ]


def get_detax_suggestions(
    session: Session,
    user_id: str = DEFAULT_USER_ID,
) -> list[DeTaxOpportunity]:
    """Return DeTAX opportunities for Tokutei holdings with current losses."""
    today = date.today()
    start_of_year = date(today.year, 1, 1)

    accounts = [
        account
        for account in repo.find_all_accounts(session, active_only=True)
        if account.user_id == user_id
    ]
    tokutei_account_ids = {
        int(account.id)
        for account in accounts
        if account.id is not None
        and (account.tax_wrapper or "").strip().lower() == "tokutei"
    }
    if not tokutei_account_ids:
        return []

    raw_holdings = repo.find_holdings_for_active_accounts(
        session,
        include_unlinked=False,
        user_id=user_id,
    )
    tokutei_holdings: list[Any] = [
        holding
        for holding in raw_holdings
        if holding.account_id is not None
        and int(holding.account_id) in tokutei_account_ids
        and not holding.is_cash
    ]
    if not tokutei_holdings:
        return []

    holdings_with_prices: list[Any] = []
    for holding in tokutei_holdings:
        cat_val = (
            holding.category.value
            if hasattr(holding.category, "value")
            else str(holding.category)
        )
        if cat_val == StockCategory.MUTUAL_FUND.value:
            nav_row = repo.get_latest_nav(session, holding.ticker)
            current_price = nav_row.nav if nav_row else None
        elif cat_val in SKIP_PRICE_FETCH_CATEGORIES:
            continue
        else:
            signals = get_technical_signals(holding.ticker)
            current_price = (
                float(signals["price"])
                if signals
                and isinstance(signals.get("price"), (int, float))
                and float(signals["price"]) > 0
                else None
            )
        if current_price is None:
            continue
        holdings_with_prices.append(
            holding.model_copy(update={"current_price": current_price})
        )

    if not holdings_with_prices:
        return []

    transactions = repo.find_all_transactions(
        session,
        limit=None,
    )
    realized_gains = _compute_realized_gains_ytd(
        transactions,
        tokutei_account_ids,
        start_of_year=start_of_year,
        today=today,
    )

    return find_detax_opportunities(
        tokutei_holdings=holdings_with_prices,
        realized_gains_ytd=realized_gains,
    )
