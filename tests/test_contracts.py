"""Behavioral tests for the error catalog (ErrorCode + definitions)."""

from __future__ import annotations

import pytest

from omnixys_graphql.contracts import ERROR_DEFINITIONS, ErrorCode
from omnixys_graphql.contracts.error_definition import (
    get_error_definition,
    get_public_error_metadata,
    is_known_error_code,
)


def test_error_codes_are_stable_strings() -> None:
    assert ErrorCode.USER_NOT_FOUND.value == "USER_NOT_FOUND"
    assert ErrorCode.INTERNAL_SERVER_ERROR.value == "INTERNAL_SERVER_ERROR"
    assert ErrorCode.RATE_LIMIT_EXCEEDED.value == "RATE_LIMIT_EXCEEDED"


def test_error_code_dunder_string() -> None:
    assert str(ErrorCode.VALIDATION_ERROR) == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    ("code", "http_status", "retryable"),
    [
        (ErrorCode.VALIDATION_ERROR, 400, False),
        (ErrorCode.UNAUTHENTICATED, 401, False),
        (ErrorCode.FORBIDDEN, 403, False),
        (ErrorCode.NOT_FOUND, 404, False),
        (ErrorCode.CONFLICT, 409, False),
        (ErrorCode.RATE_LIMIT_EXCEEDED, 429, True),
        (ErrorCode.SERVICE_UNAVAILABLE, 503, True),
        (ErrorCode.INTERNAL_SERVER_ERROR, 500, False),
        (ErrorCode.USER_NOT_FOUND, 404, False),
        (ErrorCode.EVENT_CLOSED, 400, False),
        (ErrorCode.EVENT_ALREADY_EXISTS, 409, False),
    ],
)
def test_explicit_definitions(code: ErrorCode, http_status: int, retryable: bool) -> None:
    definition = get_error_definition(code.value)
    assert definition.http_status == http_status
    assert definition.retryable is retryable
    assert definition.summary
    assert definition.default_message


def test_inferred_not_found_definition() -> None:
    definition = get_error_definition(ErrorCode.TICKET_NOT_FOUND.value)
    assert definition.http_status == 404


def test_inferred_forbidden_definition() -> None:
    definition = get_error_definition(ErrorCode.EVENT_ACCESS_DENIED.value)
    assert definition.http_status == 403


def test_inferred_conflict_definition() -> None:
    definition = get_error_definition(ErrorCode.INVITATION_ALREADY_EXISTS.value)
    assert definition.http_status == 409


def test_inferred_unavailable_definition_is_retryable() -> None:
    definition = get_error_definition(ErrorCode.MINIO_UNAVAILABLE.value)
    assert definition.http_status == 503
    assert definition.retryable is True


def test_inferred_invalid_definition() -> None:
    definition = get_error_definition(ErrorCode.EVENT_TOKEN_INVALID.value)
    assert definition.http_status == 400


def test_unknown_code_gets_default_definition() -> None:
    definition = get_error_definition("NOT_A_REAL_CODE")
    assert definition.http_status == 500
    assert definition.default_message == "An unexpected error occurred."


def test_is_known_error_code() -> None:
    assert is_known_error_code("USER_NOT_FOUND") is True
    assert is_known_error_code("NOT_A_REAL_CODE") is False


def test_every_enum_member_has_a_definition() -> None:
    for code in ErrorCode:
        assert code.value in ERROR_DEFINITIONS
        definition = ERROR_DEFINITIONS[code.value]
        assert definition.code == code.value


def test_public_metadata_filters_keys() -> None:
    metadata = get_public_error_metadata(
        "USER_NOT_FOUND",
        {"userId": "u1", "internalNote": "secret", "email": "a@b.c"},
    )
    assert metadata == {"userId": "u1"}


def test_public_metadata_empty_when_none() -> None:
    assert get_public_error_metadata("USER_NOT_FOUND", None) == {}


def test_public_metadata_unknown_code_allows_nothing() -> None:
    assert get_public_error_metadata("NOPE", {"anything": 1}) == {}


def test_validation_error_exposes_field_keys() -> None:
    metadata = get_public_error_metadata("VALIDATION_ERROR", {"field": "email", "constraint": "email"})
    assert metadata == {"field": "email", "constraint": "email"}
