"""Contract tests for analytics routes — drawdown, risk metrics, contribution."""

from datetime import UTC, datetime

from sqlmodel import Session

from domain.entities import PortfolioSnapshot


def _seed_snapshots(session: Session, count: int = 5) -> None:
    """Seed portfolio snapshots for testing."""
    for i in range(count):
        session.add(
            PortfolioSnapshot(
                snapshot_date=datetime(2025, 1, i + 1, tzinfo=UTC).date(),
                total_value=10000 + i * 100,
                cost_basis_total=9000 + i * 50,
            )
        )
    session.commit()


class TestDrawdownEndpoint:
    """Tests for GET /analytics/drawdown."""

    def test_drawdown_should_return_200_with_empty_list(self, client):
        resp = client.get("/analytics/drawdown")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_drawdown_should_return_series_with_snapshots(self, client, db_session):
        _seed_snapshots(db_session)
        resp = client.get("/analytics/drawdown")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        assert "date" in data[0]
        assert "drawdown_pct" in data[0]
        assert "total_value" in data[0]
        assert "peak_value" in data[0]

    def test_drawdown_should_filter_by_date_range(self, client, db_session):
        _seed_snapshots(db_session, count=10)
        resp = client.get(
            "/analytics/drawdown",
            params={"start": "2025-01-03", "end": "2025-01-07"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

    def test_drawdown_should_return_422_when_only_start_provided(self, client):
        resp = client.get("/analytics/drawdown", params={"start": "2025-01-01"})
        assert resp.status_code == 422

    def test_drawdown_should_return_422_when_only_end_provided(self, client):
        resp = client.get("/analytics/drawdown", params={"end": "2025-01-31"})
        assert resp.status_code == 422

    def test_drawdown_should_return_422_when_start_after_end(self, client):
        resp = client.get(
            "/analytics/drawdown",
            params={"start": "2025-01-31", "end": "2025-01-01"},
        )
        assert resp.status_code == 422

    def test_drawdown_should_include_cache_control_header(self, client):
        resp = client.get("/analytics/drawdown")
        assert "Cache-Control" in resp.headers


class TestRiskMetricsEndpoint:
    """Tests for GET /analytics/risk-metrics."""

    def test_risk_metrics_should_return_200_with_zero_metrics(self, client):
        resp = client.get("/analytics/risk-metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert "annualized_return" in body
        assert "annualized_volatility" in body
        assert "sharpe_ratio" in body
        assert "sortino_ratio" in body
        assert "max_drawdown_pct" in body
        assert "calmar_ratio" in body
        assert "trading_days" in body

    def test_risk_metrics_should_compute_with_snapshots(self, client, db_session):
        _seed_snapshots(db_session, count=10)
        resp = client.get("/analytics/risk-metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["trading_days"] > 0

    def test_risk_metrics_should_return_422_when_only_start_provided(self, client):
        resp = client.get("/analytics/risk-metrics", params={"start": "2025-01-01"})
        assert resp.status_code == 422

    def test_risk_metrics_should_return_422_when_only_end_provided(self, client):
        resp = client.get("/analytics/risk-metrics", params={"end": "2025-01-31"})
        assert resp.status_code == 422

    def test_risk_metrics_should_return_422_when_start_after_end(self, client):
        resp = client.get(
            "/analytics/risk-metrics",
            params={"start": "2025-12-31", "end": "2025-01-01"},
        )
        assert resp.status_code == 422


class TestContributionGrowthEndpoint:
    """Tests for GET /analytics/contribution-growth."""

    def test_contribution_growth_should_return_200_empty(self, client):
        resp = client.get("/analytics/contribution-growth")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_contribution_growth_should_return_series(self, client, db_session):
        _seed_snapshots(db_session)
        resp = client.get("/analytics/contribution-growth")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        assert "date" in data[0]
        assert "market_value" in data[0]
        assert "cost_basis" in data[0]

    def test_contribution_growth_should_return_422_when_only_start(self, client):
        resp = client.get(
            "/analytics/contribution-growth",
            params={"start": "2025-01-01"},
        )
        assert resp.status_code == 422

    def test_contribution_growth_should_return_422_when_only_end(self, client):
        resp = client.get(
            "/analytics/contribution-growth",
            params={"end": "2025-01-31"},
        )
        assert resp.status_code == 422

    def test_contribution_growth_should_return_422_when_start_after_end(self, client):
        resp = client.get(
            "/analytics/contribution-growth",
            params={"start": "2025-12-31", "end": "2025-01-01"},
        )
        assert resp.status_code == 422
