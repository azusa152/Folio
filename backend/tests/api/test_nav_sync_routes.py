"""Contract tests for POST /nav/sync endpoint."""

from unittest.mock import patch


def test_nav_sync_should_return_200_with_synced_and_failed(client):
    with (
        patch(
            "api.routes.wrapper_routes.sync_mutual_fund_navs",
            return_value={"synced": 3, "failed": 1},
        ),
        patch("api.routes.wrapper_routes.invalidate_enriched_cache"),
    ):
        resp = client.post("/nav/sync")

    assert resp.status_code == 200
    body = resp.json()
    assert body["synced"] == 3
    assert body["failed"] == 1


def test_nav_sync_should_return_zeros_when_no_funds(client):
    with (
        patch(
            "api.routes.wrapper_routes.sync_mutual_fund_navs",
            return_value={"synced": 0, "failed": 0},
        ),
        patch("api.routes.wrapper_routes.invalidate_enriched_cache"),
    ):
        resp = client.post("/nav/sync")

    assert resp.status_code == 200
    body = resp.json()
    assert body["synced"] == 0
    assert body["failed"] == 0


def test_nav_sync_should_return_422_when_sync_raises(client):
    with (
        patch(
            "api.routes.wrapper_routes.sync_mutual_fund_navs",
            side_effect=RuntimeError("boom"),
        ),
        patch("api.routes.wrapper_routes.invalidate_enriched_cache"),
    ):
        resp = client.post("/nav/sync")

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error_code"] == "NAV_SYNC_FAILED"
