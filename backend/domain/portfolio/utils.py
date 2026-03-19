"""Pure domain utilities for portfolio calculations."""


def is_cash_ticker(ticker: str, currency: str) -> bool:
    """Return True when a ticker represents a cash position in the given currency."""
    return ticker.strip().upper() == currency.strip().upper()
