"""
Tests for holding_service.
Uses db_session fixture (in-memory SQLite) — no mocks required for pure CRUD.
"""

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from application.portfolio.holding_service import (
    create_cash_holding,
    create_holding,
    delete_holding,
    export_holdings,
    import_holdings,
    list_holdings,
    update_holding,
)
from domain.constants import DEFAULT_USER_ID
from domain.entities import Account, Holding, Transaction
from domain.enums import StockCategory, TransactionType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LANG = "zh-TW"


def _seed_account(
    session: Session, *, name: str = "Default", broker: str = "Default"
) -> Account:
    account = Account(
        user_id=DEFAULT_USER_ID,
        name=name,
        broker=broker,
        account_type="brokerage",
        currency="USD",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def _make_payload(account_id: int, **kwargs) -> dict:
    defaults = {
        "ticker": "AAPL",
        "category": StockCategory.TREND_SETTER,
        "quantity": 10.0,
        "cost_basis": 150.0,
        "broker": None,
        "account_id": account_id,
        "currency": "usd",
        "account_type": None,
        "is_cash": False,
    }
    defaults.update(kwargs)
    return defaults


def _seed_holding(
    session: Session, ticker: str = "AAPL", quantity: float = 5.0
) -> Holding:
    account = _seed_account(session, name=f"{ticker}-account", broker="Test")
    h = Holding(
        user_id=DEFAULT_USER_ID,
        ticker=ticker,
        category=StockCategory.TREND_SETTER,
        quantity=quantity,
        currency="USD",
        account_id=account.id,
    )
    session.add(h)
    session.commit()
    session.refresh(h)
    return h


# ---------------------------------------------------------------------------
# list_holdings
# ---------------------------------------------------------------------------


class TestListHoldings:
    def test_returns_empty_when_no_holdings(self, db_session: Session) -> None:
        result = list_holdings(db_session)
        assert result == []

    def test_returns_all_holdings_as_dicts(self, db_session: Session) -> None:
        _seed_holding(db_session, "AAPL")
        _seed_holding(db_session, "MSFT")
        result = list_holdings(db_session)
        assert len(result) == 2
        tickers = {r["ticker"] for r in result}
        assert tickers == {"AAPL", "MSFT"}

    def test_dict_contains_required_keys(self, db_session: Session) -> None:
        _seed_holding(db_session)
        result = list_holdings(db_session)
        keys = set(result[0].keys())
        assert {
            "id",
            "ticker",
            "category",
            "quantity",
            "currency",
            "updated_at",
        } <= keys


# ---------------------------------------------------------------------------
# create_holding
# ---------------------------------------------------------------------------


class TestCreateHolding:
    def test_creates_holding_with_valid_payload(self, db_session: Session) -> None:
        account = _seed_account(db_session)
        result = create_holding(db_session, _make_payload(account.id), _LANG)
        assert result["ticker"] == "AAPL"
        assert result["currency"] == "USD"  # uppercased
        assert result["quantity"] == 10.0
        assert result["id"] is not None

    def test_normalises_ticker_and_currency_to_uppercase(
        self, db_session: Session
    ) -> None:
        account = _seed_account(db_session)
        result = create_holding(
            db_session,
            _make_payload(account.id, ticker="msft", currency="usd"),
            _LANG,
        )
        assert result["ticker"] == "MSFT"
        assert result["currency"] == "USD"

    def test_persists_to_database(self, db_session: Session) -> None:
        account = _seed_account(db_session)
        create_holding(db_session, _make_payload(account.id), _LANG)
        assert len(list_holdings(db_session)) == 1

    def test_creates_opening_balance_transaction(self, db_session: Session) -> None:
        account = _seed_account(db_session)
        create_holding(db_session, _make_payload(account.id), _LANG)
        txns = db_session.exec(select(Transaction)).all()
        assert len(txns) == 1
        assert txns[0].transaction_type == TransactionType.OPENING_BALANCE
        assert txns[0].ticker == "AAPL"

    def test_crypto_holding_requires_usd_currency(self, db_session: Session) -> None:
        account = _seed_account(db_session)
        with pytest.raises(HTTPException) as exc_info:
            create_holding(
                db_session,
                _make_payload(
                    account.id, category=StockCategory.CRYPTO, currency="TWD"
                ),
                _LANG,
            )
        assert exc_info.value.status_code == 400

    def test_crypto_holding_normalizes_coingecko_id(self, db_session: Session) -> None:
        account = _seed_account(db_session)
        result = create_holding(
            db_session,
            _make_payload(
                account.id,
                ticker="btc-usd",
                category=StockCategory.CRYPTO,
                currency="USD",
                coingecko_id=" Bitcoin ",
            ),
            _LANG,
        )
        assert result["coingecko_id"] == "bitcoin"


# ---------------------------------------------------------------------------
# create_cash_holding
# ---------------------------------------------------------------------------


class TestCreateCashHolding:
    def test_creates_cash_holding(self, db_session: Session) -> None:
        account = _seed_account(db_session)
        payload = {
            "currency": "twd",
            "amount": 100000.0,
            "broker": None,
            "account_id": account.id,
            "account_type": None,
        }
        result = create_cash_holding(db_session, payload, _LANG)
        assert result["ticker"] == "TWD"
        assert result["currency"] == "TWD"
        assert result["is_cash"] is True
        assert result["cost_basis"] == 1.0
        assert result["category"] == StockCategory.CASH


# ---------------------------------------------------------------------------
# update_holding
# ---------------------------------------------------------------------------


class TestUpdateHolding:
    def test_updates_existing_holding(self, db_session: Session) -> None:
        holding = _seed_holding(db_session)
        payload = {"quantity": 20.0, "cost_basis": 180.0}
        result = update_holding(db_session, holding.id, payload, _LANG)  # type: ignore[arg-type]
        assert result["quantity"] == 20.0
        assert result["cost_basis"] == 180.0

    def test_quantity_change_creates_adjustment_transaction(
        self, db_session: Session
    ) -> None:
        holding = _seed_holding(db_session, quantity=5.0)
        update_holding(
            db_session,
            holding.id,
            {"quantity": 8.0},
            _LANG,  # type: ignore[arg-type]
        )
        txns = db_session.exec(select(Transaction)).all()
        assert len(txns) == 1
        assert txns[0].transaction_type == TransactionType.ADJUSTMENT
        assert txns[0].quantity == 3.0

    def test_quantity_decrease_with_zero_basis_keeps_decrease_direction(
        self, db_session: Session
    ) -> None:
        holding = _seed_holding(db_session, quantity=9.0)
        holding.cost_basis = 0.0
        db_session.add(holding)
        db_session.commit()

        update_holding(
            db_session,
            holding.id,
            {"quantity": 4.0},
            _LANG,  # type: ignore[arg-type]
        )

        txns = db_session.exec(select(Transaction)).all()
        assert len(txns) == 1
        assert txns[0].transaction_type == TransactionType.ADJUSTMENT
        assert txns[0].quantity == 5.0
        assert txns[0].total_amount < 0

    def test_raises_404_for_nonexistent_id(self, db_session: Session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            update_holding(db_session, 99999, _make_payload(1), _LANG)
        assert exc_info.value.status_code == 404

    def test_normalises_ticker_and_currency(self, db_session: Session) -> None:
        holding = _seed_holding(db_session)
        payload = {"ticker": "tsla", "currency": "jpy"}
        result = update_holding(db_session, holding.id, payload, _LANG)  # type: ignore[arg-type]
        assert result["ticker"] == "TSLA"
        assert result["currency"] == "JPY"

    def test_crypto_update_rejects_non_usd_currency(self, db_session: Session) -> None:
        holding = _seed_holding(db_session, ticker="BTC-USD")
        payload = {
            "category": StockCategory.CRYPTO,
            "currency": "JPY",
            "coingecko_id": "bitcoin",
        }
        with pytest.raises(HTTPException) as exc_info:
            update_holding(db_session, holding.id, payload, _LANG)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# delete_holding
# ---------------------------------------------------------------------------


class TestDeleteHolding:
    def test_deletes_existing_holding(self, db_session: Session) -> None:
        holding = _seed_holding(db_session)
        result = delete_holding(db_session, holding.id, _LANG)  # type: ignore[arg-type]
        assert "message" in result
        assert len(list_holdings(db_session)) == 0

    def test_delete_creates_zeroing_adjustment_transaction(
        self, db_session: Session
    ) -> None:
        holding = _seed_holding(db_session, quantity=7.0)
        delete_holding(db_session, holding.id, _LANG)  # type: ignore[arg-type]
        txns = db_session.exec(select(Transaction)).all()
        assert len(txns) == 1
        assert txns[0].transaction_type == TransactionType.ADJUSTMENT
        assert txns[0].quantity == 7.0
        assert txns[0].total_amount < 0

    def test_raises_404_for_nonexistent_id(self, db_session: Session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            delete_holding(db_session, 99999, _LANG)
        assert exc_info.value.status_code == 404

    def test_delete_without_account_id_should_succeed_without_adjustment(
        self, db_session: Session
    ) -> None:
        orphan = Holding(
            user_id=DEFAULT_USER_ID,
            ticker="ORPHAN",
            category=StockCategory.TREND_SETTER,
            quantity=3.0,
            currency="USD",
            account_id=None,
        )
        db_session.add(orphan)
        db_session.commit()
        db_session.refresh(orphan)

        result = delete_holding(db_session, orphan.id, _LANG)  # type: ignore[arg-type]

        assert "message" in result
        assert (
            db_session.exec(select(Holding).where(Holding.id == orphan.id)).first()
            is None
        )
        txns = db_session.exec(select(Transaction)).all()
        assert txns == []


# ---------------------------------------------------------------------------
# export_holdings
# ---------------------------------------------------------------------------


class TestExportHoldings:
    def test_returns_import_compatible_format(self, db_session: Session) -> None:
        _seed_holding(db_session)
        result = export_holdings(db_session)
        assert len(result) == 1
        item = result[0]
        # Should NOT include id or updated_at (import format)
        assert "id" not in item
        assert "updated_at" not in item
        assert "ticker" in item
        assert "category" in item

    def test_returns_empty_list_when_no_holdings(self, db_session: Session) -> None:
        assert export_holdings(db_session) == []


# ---------------------------------------------------------------------------
# import_holdings
# ---------------------------------------------------------------------------


class TestImportHoldings:
    def _import_payload(self, account_id: int) -> list[dict]:
        return [
            {
                "ticker": "VTI",
                "category": StockCategory.TREND_SETTER,
                "quantity": 50.0,
                "currency": "USD",
                "account_id": account_id,
                "is_cash": False,
            }
        ]

    def test_imports_holdings_successfully(self, db_session: Session) -> None:
        account = _seed_account(db_session)
        result = import_holdings(db_session, self._import_payload(account.id), _LANG)
        assert result["imported"] == 1
        assert result["errors"] == []
        txns = db_session.exec(select(Transaction)).all()
        assert len(txns) == 1
        assert txns[0].transaction_type == TransactionType.OPENING_BALANCE

    def test_replaces_existing_holdings(self, db_session: Session) -> None:
        account = _seed_account(db_session)
        _seed_holding(db_session, "AAPL")
        _seed_holding(db_session, "MSFT")
        import_holdings(db_session, self._import_payload(account.id), _LANG)
        remaining = list_holdings(db_session)
        assert len(remaining) == 1
        assert remaining[0]["ticker"] == "VTI"
        txns = db_session.exec(select(Transaction)).all()
        opening_count = sum(
            1 for txn in txns if txn.transaction_type == TransactionType.OPENING_BALANCE
        )
        adjustment_count = sum(
            1 for txn in txns if txn.transaction_type == TransactionType.ADJUSTMENT
        )
        assert opening_count == 1
        assert adjustment_count == 2

    def test_raises_400_when_data_exceeds_limit(self, db_session: Session) -> None:
        account = _seed_account(db_session)
        big_data = [self._import_payload(account.id)[0]] * 1001
        with pytest.raises(HTTPException) as exc_info:
            import_holdings(db_session, big_data, _LANG)
        assert exc_info.value.status_code == 400

    def test_records_errors_for_invalid_items(self, db_session: Session) -> None:
        account = _seed_account(db_session)
        bad_item = {"ticker": "BAD"}  # missing required fields
        result = import_holdings(
            db_session,
            [bad_item],
            _LANG,
            account_id=account.id,
        )
        assert result["imported"] == 0
        assert len(result["errors"]) == 1

    def test_import_crypto_with_non_usd_currency_records_error(
        self, db_session: Session
    ) -> None:
        account = _seed_account(db_session)
        payload = [
            {
                "ticker": "BTC-USD",
                "category": StockCategory.CRYPTO,
                "quantity": 1.25,
                "currency": "TWD",
                "account_id": account.id,
                "is_cash": False,
            }
        ]
        result = import_holdings(db_session, payload, _LANG)
        assert result["imported"] == 0
        assert len(result["errors"]) == 1

    def test_replace_account_only_replaces_target_account(
        self, db_session: Session
    ) -> None:
        _seed_account(db_session, name="A", broker="A")
        account_b = _seed_account(db_session, name="B", broker="B")

        _seed_holding(db_session, "AAPL")
        account_holding = Holding(
            user_id=DEFAULT_USER_ID,
            ticker="MSFT",
            category=StockCategory.TREND_SETTER,
            quantity=3,
            currency="USD",
            account_id=account_b.id,
        )
        db_session.add(account_holding)
        db_session.commit()

        payload = [
            {
                "ticker": "TSLA",
                "category": StockCategory.GROWTH,
                "quantity": 2,
                "currency": "USD",
            }
        ]
        import_holdings(
            db_session,
            payload,
            _LANG,
            mode="replace_account",
            account_id=account_b.id,
        )

        holdings = list_holdings(db_session)
        tickers = {item["ticker"] for item in holdings}
        assert "AAPL" in tickers
        assert "MSFT" not in tickers
        tsla = next(item for item in holdings if item["ticker"] == "TSLA")
        assert tsla["account_id"] == account_b.id
        txns = db_session.exec(select(Transaction)).all()
        closing_for_msft = [
            txn
            for txn in txns
            if txn.transaction_type == TransactionType.ADJUSTMENT
            and txn.ticker == "MSFT"
        ]
        assert len(closing_for_msft) == 1

    def test_append_mode_keeps_existing_holdings(self, db_session: Session) -> None:
        account = _seed_account(db_session)
        _seed_holding(db_session, "AAPL")
        payload = [
            {
                "ticker": "TSM",
                "category": StockCategory.GROWTH,
                "quantity": 8,
                "currency": "USD",
                "account_id": account.id,
            }
        ]

        import_holdings(db_session, payload, _LANG, mode="append")
        holdings = list_holdings(db_session)
        tickers = {item["ticker"] for item in holdings}
        assert tickers == {"AAPL", "TSM"}
