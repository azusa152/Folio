"""Contract tests for POST /nav/sync endpoint."""

from unittest.mock import patch


def test_nav_sync_should_return_200_with_synced_and_failed(client):
    with (
        patch(
            "api.routes.wrapper_routes.refresh_official_wrappers_best_effort",
            return_value={"nisa_growth": {"added": 1, "updated": 0, "deactivated": 0}},
        ),
        patch(
            "api.routes.wrapper_routes.sync_mutual_fund_navs",
            return_value={
                "synced": 3,
                "failed": 1,
                "failed_tickers": ["ABC12345"],
                "failed_details": [{"ticker": "ABC12345", "reason": "missing_isin"}],
            },
        ),
        patch("api.routes.wrapper_routes.invalidate_enriched_cache"),
    ):
        resp = client.post("/nav/sync")

    assert resp.status_code == 200
    body = resp.json()
    assert body["synced"] == 3
    assert body["failed"] == 1
    assert body["failed_tickers"] == ["ABC12345"]
    assert body["failed_details"] == [{"ticker": "ABC12345", "reason": "missing_isin"}]
    assert body["pre_refresh"]["attempted"] is True
    assert body["pre_refresh"]["success"] is True
    assert body["pre_refresh"]["wrappers_synced"] == ["nisa_growth"]
    assert body["pre_refresh"]["error"] is None


def test_nav_sync_should_return_zeros_when_no_funds(client):
    with (
        patch(
            "api.routes.wrapper_routes.refresh_official_wrappers_best_effort",
            return_value={},
        ),
        patch(
            "api.routes.wrapper_routes.sync_mutual_fund_navs",
            return_value={
                "synced": 0,
                "failed": 0,
                "failed_tickers": [],
                "failed_details": [],
            },
        ),
        patch("api.routes.wrapper_routes.invalidate_enriched_cache"),
    ):
        resp = client.post("/nav/sync")

    assert resp.status_code == 200
    body = resp.json()
    assert body["synced"] == 0
    assert body["failed"] == 0
    assert body["failed_tickers"] == []
    assert body["failed_details"] == []
    assert body["pre_refresh"]["attempted"] is True
    assert body["pre_refresh"]["success"] is True


def test_nav_sync_should_return_422_when_sync_raises(client):
    with (
        patch(
            "api.routes.wrapper_routes.refresh_official_wrappers_best_effort",
            return_value={},
        ),
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


def test_nav_sync_should_fail_open_when_pre_refresh_raises(client):
    with (
        patch(
            "api.routes.wrapper_routes.refresh_official_wrappers_best_effort",
            side_effect=RuntimeError("pre-refresh down"),
        ),
        patch(
            "api.routes.wrapper_routes.sync_mutual_fund_navs",
            return_value={
                "synced": 1,
                "failed": 0,
                "failed_tickers": [],
                "failed_details": [],
            },
        ),
        patch("api.routes.wrapper_routes.invalidate_enriched_cache"),
    ):
        resp = client.post("/nav/sync")

    assert resp.status_code == 200
    body = resp.json()
    assert body["synced"] == 1
    assert body["failed"] == 0
    assert body["pre_refresh"]["attempted"] is True
    assert body["pre_refresh"]["success"] is False
    assert body["pre_refresh"]["wrappers_synced"] == []
    assert body["pre_refresh"]["error"] == "pre-refresh down"
