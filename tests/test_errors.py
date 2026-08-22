"""Behavioral tests for GraphQL error classes and factories."""

from __future__ import annotations

from strawberry.exceptions import StrawberryGraphQLError

from omnixys_graphql import (
    BaseGraphQLException,
    EventNotFoundException,
    GraphQLServiceError,
    InvalidCredentialsException,
    UserAlreadyExistsException,
    UserNotFoundException,
    access_blocked,
    conflict_graphql_error,
    create_graphql_exception,
    dependency_unavailable_graphql_error,
    forbidden_graphql_error,
    internal_graphql_error,
    not_found_graphql_error,
    rate_limit_graphql_error,
    sanitize_details,
    step_up_required,
    to_graphql_error,
    unauthenticated_graphql_error,
    validation_graphql_error,
)


def _extensions(exc: BaseGraphQLException) -> dict:
    assert isinstance(exc.extensions, dict)
    return exc.extensions


def test_is_a_strawberry_graphql_error() -> None:
    exc = validation_graphql_error("bad input")
    assert isinstance(exc, StrawberryGraphQLError)


def test_validation_error_extensions() -> None:
    exc = validation_graphql_error("bad input", {"field": "email"})
    ext = _extensions(exc)
    assert ext["code"] == "VALIDATION_ERROR"
    assert ext["httpStatus"] == 400
    assert ext["retryable"] is False
    assert ext["summary"] == "Validation failed."
    assert ext["metadata"] == {"field": "email"}
    assert "timestamp" in ext


def test_unauthenticated_error() -> None:
    ext = _extensions(unauthenticated_graphql_error("please sign in"))
    assert ext["code"] == "UNAUTHENTICATED"
    assert ext["httpStatus"] == 401


def test_forbidden_error() -> None:
    ext = _extensions(forbidden_graphql_error())
    assert ext["code"] == "FORBIDDEN"
    assert ext["httpStatus"] == 403


def test_not_found_error_default_message() -> None:
    exc = not_found_graphql_error("EVENT_NOT_FOUND")
    assert str(exc) == "The requested resource was not found."
    assert _extensions(exc)["code"] == "EVENT_NOT_FOUND"
    assert _extensions(exc)["httpStatus"] == 404


def test_conflict_error() -> None:
    exc = conflict_graphql_error("EVENT_ALREADY_EXISTS")
    assert _extensions(exc)["code"] == "EVENT_ALREADY_EXISTS"
    assert _extensions(exc)["httpStatus"] == 409


def test_rate_limit_error_is_retryable() -> None:
    ext = _extensions(rate_limit_graphql_error())
    assert ext["code"] == "RATE_LIMIT_EXCEEDED"
    assert ext["httpStatus"] == 429
    assert ext["retryable"] is True


def test_dependency_unavailable_error() -> None:
    ext = _extensions(dependency_unavailable_graphql_error())
    assert ext["code"] == "SERVICE_UNAVAILABLE"
    assert ext["httpStatus"] == 503
    assert ext["retryable"] is True


def test_internal_graphql_error() -> None:
    ext = _extensions(internal_graphql_error())
    assert ext["code"] == "INTERNAL_SERVER_ERROR"
    assert ext["httpStatus"] == 500


def test_create_graphql_exception_uses_catalog_message() -> None:
    exc = create_graphql_exception("SEAT_OCCUPIED")
    assert str(exc) == "The request conflicts with the current state."


def test_metadata_is_filtered_to_public_keys() -> None:
    exc = create_graphql_exception("EVENT_NOT_FOUND", metadata={"eventId": "e1", "secret": 42})
    assert _extensions(exc)["metadata"] == {"eventId": "e1"}


def test_metadata_is_sanitized() -> None:
    exc = create_graphql_exception("VALIDATION_ERROR", metadata={"field": "email", "password": "hunter2"})
    assert "password" not in _extensions(exc)["metadata"]


def test_domain_exception_user_not_found() -> None:
    exc = UserNotFoundException("u1")
    ext = _extensions(exc)
    assert ext["code"] == "USER_NOT_FOUND"
    assert ext["metadata"] == {"userId": "u1"}
    assert str(exc) == "User was not found"


def test_domain_exception_user_already_exists() -> None:
    exc = UserAlreadyExistsException("ada")
    ext = _extensions(exc)
    assert ext["code"] == "USER_ALREADY_EXISTS"
    assert ext["metadata"] == {}


def test_domain_exception_invalid_credentials() -> None:
    exc = InvalidCredentialsException()
    assert _extensions(exc)["code"] == "INVALID_CREDENTIALS"
    assert _extensions(exc)["httpStatus"] == 401


def test_domain_exception_event_not_found_without_id() -> None:
    exc = EventNotFoundException()
    assert _extensions(exc)["metadata"] == {}


def test_access_blocked() -> None:
    exc = access_blocked(["2fa_pending", "terms_not_accepted"])
    ext = _extensions(exc)
    assert ext["code"] == "ACCESS_BLOCKED"
    assert ext["reasons"] == ["2fa_pending", "terms_not_accepted"]
    assert str(exc) == "Access blocked"


def test_step_up_required() -> None:
    exc = step_up_required("mfa", ["low_risk_score"])
    ext = _extensions(exc)
    assert ext["code"] == "STEP_UP_REQUIRED"
    assert ext["stepUp"] == "mfa"
    assert ext["reasons"] == ["low_risk_score"]


def test_to_graphql_error_returns_unchanged_base_exception() -> None:
    exc = validation_graphql_error("bad")
    assert to_graphql_error(exc) is exc


def test_to_graphql_error_uses_extensions_code() -> None:
    exc = to_graphql_error(EventNotFoundException("e1"))
    assert exc is not None
    assert exc.extensions["code"] == "EVENT_NOT_FOUND"  # type: ignore[index]
    assert "e1" in str(exc.extensions["metadata"])  # type: ignore[index]


def test_to_graphql_error_maps_http_status() -> None:
    class NotFound:
        status_code = 404

    exc = to_graphql_error(NotFound())
    assert exc.extensions["code"] == "NOT_FOUND"  # type: ignore[index]


def test_to_graphql_error_defaults_to_internal() -> None:
    exc = to_graphql_error(RuntimeError("boom"))
    assert exc.extensions["code"] == "INTERNAL_SERVER_ERROR"  # type: ignore[index]
    assert str(exc) == "An unexpected error occurred."


def test_to_graphql_error_exposes_internal_when_configured() -> None:
    exc = to_graphql_error(RuntimeError("boom"), expose_internal_errors=True)
    assert str(exc) == "boom"


def test_graphql_service_error_backwards_compat() -> None:
    exc = GraphQLServiceError("custom failure", code="EVENT_CLOSED", status_code=400)
    ext = _extensions(exc)
    assert ext["code"] == "EVENT_CLOSED"
    assert ext["statusCode"] == 400


def test_sanitize_details_removes_sensitive_keys() -> None:
    sanitized = sanitize_details({"userId": "u1", "Authorization": "Bearer x", "api_key": "k", "fine": 1})
    assert sanitized == {"userId": "u1", "fine": 1}


def test_sanitize_details_truncates_deep_nesting() -> None:
    deep: dict = {"level0": {}}
    node = deep["level0"]
    for _ in range(10):
        node["next"] = {}
        node = node["next"]
    sanitized = sanitize_details(deep)
    assert str(sanitized).find("[truncated]") >= 0


def test_sanitize_details_truncates_long_arrays() -> None:
    sanitized = sanitize_details({"items": list(range(100))})
    assert len(sanitized["items"]) == 50  # type: ignore[arg-type]


def test_sanitize_details_handles_none() -> None:
    assert sanitize_details(None) == {}
