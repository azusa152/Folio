"""Tests for Fund Sector Weight API routes.

Covers: GET/PUT/DELETE /funds/{fund_code}/sector-weights.
"""

import pytest
from fastapi.testclient import TestClient

_FUND_CODE = "01311143"
_WEIGHTS_PAYLOAD = {
    "weights": [
        {"sector": "Technology", "weight": 0.30},
        {"sector": "Industrials", "weight": 0.25},
        {"sector": "Healthcare", "weight": 0.15},
    ],
    "source": "seed",
}


class TestFundSectorWeightsGet:
    def test_should_return_empty_when_no_weights_set(self, client: TestClient) -> None:
        response = client.get(f"/funds/{_FUND_CODE}/sector-weights")

        assert response.status_code == 200
        data = response.json()
        assert data["fund_code"] == _FUND_CODE
        assert data["weights"] == []
        assert data["total_weight"] == 0.0

    def test_should_return_stored_weights(self, client: TestClient) -> None:
        client.put(f"/funds/{_FUND_CODE}/sector-weights", json=_WEIGHTS_PAYLOAD)

        response = client.get(f"/funds/{_FUND_CODE}/sector-weights")

        assert response.status_code == 200
        data = response.json()
        assert data["fund_code"] == _FUND_CODE
        assert len(data["weights"]) == 3
        assert data["source"] == "seed"
        sectors = {w["sector"] for w in data["weights"]}
        assert sectors == {"Technology", "Industrials", "Healthcare"}

    def test_should_normalize_fund_code_to_uppercase(self, client: TestClient) -> None:
        client.put(f"/funds/{_FUND_CODE}/sector-weights", json=_WEIGHTS_PAYLOAD)

        response = client.get(f"/funds/{_FUND_CODE.lower()}/sector-weights")

        assert response.status_code == 200
        data = response.json()
        assert data["fund_code"] == _FUND_CODE.upper()

    def test_should_include_correct_total_weight(self, client: TestClient) -> None:
        client.put(f"/funds/{_FUND_CODE}/sector-weights", json=_WEIGHTS_PAYLOAD)

        response = client.get(f"/funds/{_FUND_CODE}/sector-weights")

        data = response.json()
        assert data["total_weight"] == pytest.approx(0.70, rel=0.01)


class TestFundSectorWeightsPut:
    def test_should_create_weights(self, client: TestClient) -> None:
        response = client.put(
            f"/funds/{_FUND_CODE}/sector-weights", json=_WEIGHTS_PAYLOAD
        )

        assert response.status_code == 200
        data = response.json()
        assert data["fund_code"] == _FUND_CODE
        assert len(data["weights"]) == 3

    def test_should_replace_existing_weights(self, client: TestClient) -> None:
        client.put(f"/funds/{_FUND_CODE}/sector-weights", json=_WEIGHTS_PAYLOAD)
        new_payload = {
            "weights": [{"sector": "Energy", "weight": 0.90}],
            "source": "manual",
        }

        response = client.put(f"/funds/{_FUND_CODE}/sector-weights", json=new_payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data["weights"]) == 1
        assert data["weights"][0]["sector"] == "Energy"

    def test_should_return_422_for_empty_weights(self, client: TestClient) -> None:
        response = client.put(
            f"/funds/{_FUND_CODE}/sector-weights",
            json={"weights": [], "source": "manual"},
        )

        assert response.status_code == 422

    def test_should_return_422_when_total_weight_exceeds_one(
        self, client: TestClient
    ) -> None:
        response = client.put(
            f"/funds/{_FUND_CODE}/sector-weights",
            json={
                "weights": [
                    {"sector": "Technology", "weight": 0.80},
                    {"sector": "Industrials", "weight": 0.80},
                ],
                "source": "manual",
            },
        )

        assert response.status_code == 422

    def test_should_return_422_for_invalid_source(self, client: TestClient) -> None:
        response = client.put(
            f"/funds/{_FUND_CODE}/sector-weights",
            json={
                "weights": [{"sector": "Technology", "weight": 0.50}],
                "source": "foobar",
            },
        )

        assert response.status_code == 422


class TestFundSectorWeightsDelete:
    def test_should_delete_existing_weights(self, client: TestClient) -> None:
        client.put(f"/funds/{_FUND_CODE}/sector-weights", json=_WEIGHTS_PAYLOAD)

        response = client.delete(f"/funds/{_FUND_CODE}/sector-weights")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 3

        # Verify they're gone
        get_resp = client.get(f"/funds/{_FUND_CODE}/sector-weights")
        assert get_resp.json()["weights"] == []

    def test_should_return_zero_when_nothing_to_delete(
        self, client: TestClient
    ) -> None:
        response = client.delete("/funds/NONEXISTENT/sector-weights")

        assert response.status_code == 200
        assert response.json()["deleted"] == 0
