from dataclasses import dataclass

from domain.portfolio.detax import find_detax_opportunities


@dataclass(frozen=True)
class _Holding:
    ticker: str
    account_id: int
    quantity: float
    cost_basis: float
    current_price: float


def test_no_opportunities_when_no_gains():
    opportunities = find_detax_opportunities(
        tokutei_holdings=[_Holding("AAPL", 1, 10, 150, 120)],
        realized_gains_ytd=0,
    )
    assert opportunities == []


def test_single_loser_harvested():
    opportunities = find_detax_opportunities(
        tokutei_holdings=[_Holding("AAPL", 1, 1_000, 150, 120)],
        realized_gains_ytd=50_000,
    )
    assert len(opportunities) == 1
    assert opportunities[0].ticker == "AAPL"
    assert opportunities[0].estimated_tax_saved > 0


def test_multiple_losers_sorted_by_loss():
    opportunities = find_detax_opportunities(
        tokutei_holdings=[
            _Holding("SMALL", 1, 300, 100, 90),  # 3,000 loss
            _Holding("BIG", 1, 500, 100, 50),  # 25,000 loss
        ],
        realized_gains_ytd=50_000,
    )
    assert len(opportunities) >= 1
    assert opportunities[0].ticker == "BIG"


def test_min_benefit_threshold():
    # Tax saved = loss * tax rate. Keep it below threshold.
    opportunities = find_detax_opportunities(
        tokutei_holdings=[_Holding("LOW", 1, 10, 100, 99)],
        realized_gains_ytd=10_000,
    )
    assert opportunities == []


def test_partial_harvest_when_gains_less_than_loss():
    opportunities = find_detax_opportunities(
        tokutei_holdings=[_Holding("LOSS", 1, 1_000, 100, 0)],
        realized_gains_ytd=30_000,
    )
    assert len(opportunities) == 1
    # Should not sell full quantity because gains cap the harvest.
    assert opportunities[0].sell_quantity < 1_000
