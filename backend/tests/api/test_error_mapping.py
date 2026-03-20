"""Unit tests for application->HTTP error mapping."""

from api.error_mapping import to_http_exception
from application.errors import ApplicationError


def test_to_http_exception_should_use_status_hint_mapping() -> None:
    err = ApplicationError(
        error_code="PROFILE_NOT_FOUND",
        message_key="api.profile_not_found",
        status_hint="not_found",
    )
    http_exc = to_http_exception(err, lang="en")

    assert http_exc.status_code == 404
    assert http_exc.detail["error_code"] == "PROFILE_NOT_FOUND"


def test_to_http_exception_should_prioritize_explicit_status_code() -> None:
    err = ApplicationError(
        error_code="ELIGIBILITY_REFRESH_FAILED",
        message_key="eligibility.refresh_failed",
        status_hint="validation",
        status_code=502,
    )
    http_exc = to_http_exception(err, lang="en")

    assert http_exc.status_code == 502


def test_to_http_exception_should_interpolate_params() -> None:
    err = ApplicationError(
        error_code="GURU_NOT_FOUND",
        message_key="guru.error_not_found",
        status_hint="not_found",
        params={"guru_id": "123"},
    )
    http_exc = to_http_exception(err, lang="en")

    assert "123" in http_exc.detail["detail"]
