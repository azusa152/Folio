"""Tests for user preferences routes (GET/PUT /settings/preferences)."""


class TestGetPreferences:
    """Tests for GET /settings/preferences."""

    def test_get_preferences_should_return_defaults_when_no_record(self, client):
        # Act
        resp = client.get("/settings/preferences")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["privacy_mode"] is False


class TestUpdatePreferences:
    """Tests for PUT /settings/preferences."""

    def test_update_preferences_should_set_privacy_mode_true(self, client):
        # Act
        resp = client.put("/settings/preferences", json={"privacy_mode": True})

        # Assert
        assert resp.status_code == 200
        assert resp.json()["privacy_mode"] is True

        # Verify persistence
        get_resp = client.get("/settings/preferences")
        assert get_resp.json()["privacy_mode"] is True

    def test_update_preferences_should_toggle_back_to_false(self, client):
        # Arrange — set to True first
        client.put("/settings/preferences", json={"privacy_mode": True})

        # Act — toggle back to False
        resp = client.put("/settings/preferences", json={"privacy_mode": False})

        # Assert
        assert resp.status_code == 200
        assert resp.json()["privacy_mode"] is False

        # Verify persistence
        get_resp = client.get("/settings/preferences")
        assert get_resp.json()["privacy_mode"] is False

    def test_update_preferences_should_upsert_on_first_call(self, client):
        # Act — no record exists yet, PUT should create one
        resp = client.put("/settings/preferences", json={"privacy_mode": True})

        # Assert — 200, not 404
        assert resp.status_code == 200
        assert resp.json()["privacy_mode"] is True

    def test_update_preferences_should_return_422_for_invalid_body(self, client):
        # Act — missing required field
        resp = client.put("/settings/preferences", json={})

        # Assert
        assert resp.status_code == 422

    def test_update_preferences_should_return_422_for_wrong_type(self, client):
        # Act — wrong type for privacy_mode
        resp = client.put("/settings/preferences", json={"privacy_mode": "not_a_bool"})

        # Assert
        assert resp.status_code == 422
