from __future__ import annotations

import pytest

from scripts import assert_docker_runtime


def test_runtime_guard_should_reject_non_container_without_bypass(monkeypatch):
    monkeypatch.delenv("FOLIO_ALLOW_LOCAL_DB", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/radar.db")
    monkeypatch.setattr("scripts.os.path.exists", lambda path: False)

    with pytest.raises(SystemExit):
        assert_docker_runtime()


def test_runtime_guard_should_accept_container_with_expected_sqlite_url(monkeypatch):
    monkeypatch.delenv("FOLIO_ALLOW_LOCAL_DB", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/radar.db")
    monkeypatch.setattr("scripts.os.path.exists", lambda path: path == "/.dockerenv")

    assert_docker_runtime()


def test_runtime_guard_should_reject_unexpected_sqlite_path(monkeypatch):
    monkeypatch.delenv("FOLIO_ALLOW_LOCAL_DB", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/radar.db")
    monkeypatch.setattr("scripts.os.path.exists", lambda path: path == "/.dockerenv")

    with pytest.raises(SystemExit):
        assert_docker_runtime()


def test_runtime_guard_should_allow_bypass_for_local_debug(monkeypatch):
    monkeypatch.setenv("FOLIO_ALLOW_LOCAL_DB", "1")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/radar.db")
    monkeypatch.setattr("scripts.os.path.exists", lambda path: False)

    assert_docker_runtime()
