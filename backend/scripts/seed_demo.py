"""
Seed representative demo data for local development and onboarding.

Creates a sample watchlist, accounts, holdings, and transaction history so
that a fresh Folio install is immediately explorable without manual data entry.

The seed is **idempotent**: running it twice adds nothing new.

Usage (inside Docker):

    docker compose exec backend uv run --frozen --no-dev python -m scripts.seed_demo

Usage (local DB, e.g. devcontainer):

    FOLIO_ALLOW_LOCAL_DB=1 uv run python -m scripts.seed_demo [--dry-run]

Makefile shortcut:

    make seed-demo
"""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime

from logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Demo data fixtures
# ---------------------------------------------------------------------------

_DEMO_STOCKS = [
    # Trend Setters — bellwether / market leaders
    {
        "ticker": "NVDA",
        "category": "Trend_Setter",
        "current_thesis": "AI accelerator monopoly; data-centre capex cycle still early.",
        "current_tags": "AI,Semis,Megacap",
        "display_order": 1,
        "is_etf": False,
    },
    {
        "ticker": "TSM",
        "category": "Trend_Setter",
        "current_thesis": "Sole manufacturer of bleeding-edge nodes; geopolitical risk is the price of entry.",
        "current_tags": "Semis,Taiwan",
        "display_order": 2,
        "is_etf": False,
    },
    # Moat — wide-moat compounders
    {
        "ticker": "MSFT",
        "category": "Moat",
        "current_thesis": "Azure + Office 365 flywheel; Copilot upsell adds pricing power.",
        "current_tags": "SaaS,Cloud,AI",
        "display_order": 10,
        "is_etf": False,
    },
    {
        "ticker": "V",
        "category": "Moat",
        "current_thesis": "Payment network duopoly; asset-light, high-margin, global reach.",
        "current_tags": "Fintech,Payments",
        "display_order": 11,
        "is_etf": False,
    },
    # Growth — high-growth, higher risk
    {
        "ticker": "SHOP",
        "category": "Growth",
        "current_thesis": "Commerce OS; take-rate expansion into payments and fulfilment.",
        "current_tags": "E-commerce,SaaS",
        "display_order": 20,
        "is_etf": False,
    },
    # ETFs — broad market / factor
    {
        "ticker": "VT",
        "category": "ETF",
        "current_thesis": "Total world market cap weight; core satellite anchor.",
        "current_tags": "ETF,Global",
        "display_order": 30,
        "is_etf": True,
    },
    {
        "ticker": "2631.T",
        "category": "Mutual_Fund",
        "current_thesis": "JPX-listed global equity index (iShares Core MSCI World). NISA-eligible.",
        "current_tags": "ETF,Global,JP",
        "display_order": 31,
        "is_etf": True,
    },
]

_DEMO_ACCOUNTS = [
    {
        "name": "Interactive Brokers (US)",
        "broker": "Interactive Brokers",
        "account_type": "brokerage",
        "tax_wrapper": None,
        "currency": "USD",
        "market": "US",
        "institution": "Interactive Brokers LLC",
        "note": "Demo: primary US brokerage account",
    },
    {
        "name": "SBI 証券 — NISA 成長投資枠",
        "broker": "SBI証券",
        "account_type": "brokerage",
        "tax_wrapper": "nisa_growth",
        "currency": "JPY",
        "market": "JP",
        "institution": "SBI証券",
        "note": "Demo: NISA growth (成長投資枠) account",
    },
    {
        "name": "SBI 証券 — NISA つみたて投資枠",
        "broker": "SBI証券",
        "account_type": "brokerage",
        "tax_wrapper": "nisa_tsumitate",
        "currency": "JPY",
        "market": "JP",
        "institution": "SBI証券",
        "note": "Demo: NISA tsumitate (つみたて投資枠) account",
    },
]

# (ticker, category, qty, cost_basis, currency, account_name, is_cash)
_DEMO_HOLDINGS = [
    ("NVDA", "Trend_Setter", 20.0, 480.0, "USD", "Interactive Brokers (US)", False),
    ("MSFT", "Moat", 15.0, 320.0, "USD", "Interactive Brokers (US)", False),
    ("V", "Moat", 25.0, 210.0, "USD", "Interactive Brokers (US)", False),
    ("SHOP", "Growth", 30.0, 85.0, "USD", "Interactive Brokers (US)", False),
    ("VT", "ETF", 50.0, 105.0, "USD", "Interactive Brokers (US)", False),
    ("USD", "Cash", 8500.0, 1.0, "USD", "Interactive Brokers (US)", True),
    ("2631.T", "ETF", 100.0, 2150.0, "JPY", "SBI 証券 — NISA 成長投資枠", False),
    ("JPY", "Cash", 150000.0, 1.0, "JPY", "SBI 証券 — NISA 成長投資枠", True),
]

# (ticker, type, qty, price, total, currency, date_str, account_name, note)
_DEMO_TRANSACTIONS: list[tuple] = [
    (
        "NVDA",
        "BUY",
        20.0,
        480.0,
        9600.0,
        "USD",
        "2024-01-15",
        "Interactive Brokers (US)",
        "Demo: initial NVDA buy",
    ),
    (
        "MSFT",
        "BUY",
        15.0,
        320.0,
        4800.0,
        "USD",
        "2024-01-15",
        "Interactive Brokers (US)",
        "Demo: initial MSFT buy",
    ),
    (
        "V",
        "BUY",
        25.0,
        210.0,
        5250.0,
        "USD",
        "2024-02-01",
        "Interactive Brokers (US)",
        "Demo: initial Visa buy",
    ),
    (
        "SHOP",
        "BUY",
        30.0,
        85.0,
        2550.0,
        "USD",
        "2024-03-10",
        "Interactive Brokers (US)",
        "Demo: initial SHOP buy",
    ),
    (
        "VT",
        "BUY",
        50.0,
        105.0,
        5250.0,
        "USD",
        "2024-03-10",
        "Interactive Brokers (US)",
        "Demo: initial VT buy",
    ),
    (
        "MSFT",
        "DIVIDEND",
        15.0,
        0.75,
        11.25,
        "USD",
        "2024-06-13",
        "Interactive Brokers (US)",
        "Demo: MSFT Q2 dividend",
    ),
    (
        "USD",
        "DEPOSIT",
        8500.0,
        1.0,
        8500.0,
        "USD",
        "2024-01-10",
        "Interactive Brokers (US)",
        "Demo: initial cash deposit",
    ),
    (
        "2631.T",
        "BUY",
        100.0,
        2150.0,
        215000.0,
        "JPY",
        "2024-04-01",
        "SBI 証券 — NISA 成長投資枠",
        "Demo: NISA 成長 ETF buy",
    ),
    (
        "JPY",
        "DEPOSIT",
        150000.0,
        1.0,
        150000.0,
        "JPY",
        "2024-04-01",
        "SBI 証券 — NISA 成長投資枠",
        "Demo: NISA cash deposit",
    ),
]


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------


def _seed(session, *, dry_run: bool = False) -> dict[str, int]:
    from sqlmodel import select

    from domain.core.entities import Account, Holding, Stock, Transaction
    from domain.core.enums import StockCategory, TransactionType

    counts: dict[str, int] = {
        "stocks": 0,
        "accounts": 0,
        "holdings": 0,
        "transactions": 0,
    }

    # --- Stocks ---
    existing_tickers = set(session.exec(select(Stock.ticker)).all())
    for s in _DEMO_STOCKS:
        if s["ticker"] in existing_tickers:
            continue
        stock = Stock(
            ticker=s["ticker"],
            category=StockCategory(s["category"]),
            current_thesis=s["current_thesis"],
            current_tags=s["current_tags"],
            display_order=s["display_order"],
            is_etf=s["is_etf"],
        )
        session.add(stock)
        counts["stocks"] += 1

    if not dry_run:
        session.flush()

    # --- Accounts ---
    existing_accounts_q = session.exec(select(Account.name)).all()
    existing_account_names = set(existing_accounts_q)
    account_id_by_name: dict[str, int] = {
        a.name: a.id for a in session.exec(select(Account)).all() if a.id is not None
    }

    for acc in _DEMO_ACCOUNTS:
        if acc["name"] in existing_account_names:
            continue
        account = Account(
            name=acc["name"],
            broker=acc["broker"],
            account_type=acc["account_type"],
            tax_wrapper=acc["tax_wrapper"],
            currency=acc["currency"],
            market=acc["market"],
            institution=acc["institution"],
            note=acc["note"],
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(account)
        counts["accounts"] += 1

    if not dry_run:
        session.flush()
        # Refresh account_id_by_name after flush
        account_id_by_name = {
            a.name: a.id
            for a in session.exec(select(Account)).all()
            if a.id is not None
        }

    # --- Holdings ---
    existing_holding_keys = {
        (h.account_id, h.ticker) for h in session.exec(select(Holding)).all()
    }
    holding_id_by_key: dict[tuple, int] = {}

    for ticker, cat, qty, cost, currency, acc_name, is_cash in _DEMO_HOLDINGS:
        acc_id = account_id_by_name.get(acc_name)
        key = (acc_id, ticker)
        if key in existing_holding_keys:
            # Collect existing holding IDs for transaction linking
            for h in session.exec(select(Holding)).all():
                if h.account_id == acc_id and h.ticker == ticker and h.id is not None:
                    holding_id_by_key[key] = h.id
            continue
        holding = Holding(
            ticker=ticker,
            category=StockCategory(cat),
            quantity=qty,
            cost_basis=cost,
            currency=currency,
            account_id=acc_id,
            is_cash=is_cash,
            updated_at=datetime.now(UTC),
        )
        session.add(holding)
        counts["holdings"] += 1

    if not dry_run:
        session.flush()
        for h in session.exec(select(Holding)).all():
            if h.id is not None and h.account_id is not None:
                holding_id_by_key[(h.account_id, h.ticker)] = h.id

    # --- Transactions ---
    existing_tx_notes = {
        tx.note
        for tx in session.exec(select(Transaction)).all()
        if tx.note.startswith("Demo:")
    }

    for (
        ticker,
        tx_type,
        qty,
        price,
        total,
        currency,
        date_str,
        acc_name,
        note,
    ) in _DEMO_TRANSACTIONS:
        if note in existing_tx_notes:
            continue
        acc_id = account_id_by_name.get(acc_name)
        holding_id = holding_id_by_key.get((acc_id, ticker)) if acc_id else None
        tx = Transaction(
            ticker=ticker,
            transaction_type=TransactionType(tx_type),
            quantity=qty,
            price=price,
            total_amount=total,
            currency=currency,
            account_id=acc_id,
            holding_id=holding_id,
            transaction_date=date.fromisoformat(date_str),
            note=note,
            created_at=datetime.now(UTC),
        )
        session.add(tx)
        counts["transactions"] += 1

    if not dry_run:
        session.commit()
    else:
        session.rollback()

    return counts


def run(*, dry_run: bool = False) -> dict[str, int]:
    from sqlmodel import Session

    from infrastructure.database import create_db_and_tables, engine

    create_db_and_tables()
    with Session(engine) as session:
        return _seed(session, dry_run=dry_run)


def main(args: list[str] | None = None) -> int:
    from scripts import assert_docker_runtime

    assert_docker_runtime()

    global logger
    from logging_config import get_logger

    logger = get_logger(__name__)

    parser = argparse.ArgumentParser(
        description="Seed representative demo data into Folio."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without committing"
    )
    parsed = parser.parse_args(args)

    counts = run(dry_run=parsed.dry_run)
    prefix = "[DRY RUN] " if parsed.dry_run else ""
    logger.info(
        "%sDemo seed complete: %d stocks, %d accounts, %d holdings, %d transactions added",
        prefix,
        counts["stocks"],
        counts["accounts"],
        counts["holdings"],
        counts["transactions"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
