"""Behavioral tests for GraphQL response formatting and pagination."""

from __future__ import annotations

from omnixys_graphql import (
    EventNotFoundException,
    PageInput,
    PagePayload,
    create_graphql_format_error,
    format_graphql_error,
    internal_graphql_error,
)


def test_format_graphql_error_keeps_extensions_and_locations() -> None:
    exc = EventNotFoundException("e1")
    formatted = format_graphql_error(exc)
    assert formatted["message"] == "Event was not found"
    assert formatted["extensions"]["code"] == "EVENT_NOT_FOUND"


def test_format_graphql_error_defaults_for_plain_errors() -> None:
    formatted = format_graphql_error(RuntimeError("boom"))
    assert formatted["extensions"] == {"code": "INTERNAL_ERROR", "statusCode": 500}


def test_format_error_standardizes_known_code() -> None:
    formatter = create_graphql_format_error()
    exc = EventNotFoundException("e1")
    formatted = formatter({"message": str(exc), "extensions": {}}, exc)
    assert formatted["extensions"]["code"] == "EVENT_NOT_FOUND"  # type: ignore[index]
    assert formatted["extensions"]["httpStatus"] == 404  # type: ignore[index]
    assert formatted["message"] == "Event was not found"


def test_format_error_hides_internal_details_by_default() -> None:
    formatter = create_graphql_format_error()
    formatted = formatter({"message": "stack trace here", "extensions": {}}, RuntimeError("boom"))
    assert formatted["extensions"]["code"] == "INTERNAL_SERVER_ERROR"  # type: ignore[index]
    assert formatted["message"] == "An unexpected error occurred."


def test_format_error_exposes_internal_details_when_configured() -> None:
    from omnixys_graphql import GraphQLFormatErrorOptions

    formatter = create_graphql_format_error(GraphQLFormatErrorOptions(expose_internal_errors=True))
    formatted = formatter({"message": "internal detail", "extensions": {}}, RuntimeError("boom"))
    assert formatted["message"] == "internal detail"


def test_format_error_uses_service_internal_code() -> None:
    from omnixys_graphql import GraphQLFormatErrorOptions

    formatter = create_graphql_format_error(GraphQLFormatErrorOptions(service_name="ticket-service"))
    formatted = formatter({"message": "x", "extensions": {}}, RuntimeError("boom"))
    assert formatted["extensions"]["code"] == "TICKET_INTERNAL_ERROR"  # type: ignore[index]


def test_format_error_preserves_metadata() -> None:
    formatter = create_graphql_format_error()
    formatted = formatter({"message": "x", "extensions": {}}, EventNotFoundException("e1"))
    assert formatted["extensions"]["metadata"] == {"eventId": "e1"}  # type: ignore[index]


def test_format_error_strips_sensitive_metadata() -> None:
    from omnixys_graphql import create_graphql_exception

    formatter = create_graphql_format_error()
    exc = create_graphql_exception("USER_NOT_FOUND", metadata={"userId": "u1", "password": "x"})
    formatted = formatter({"message": str(exc), "extensions": {}}, exc)
    metadata = formatted["extensions"]["metadata"]  # type: ignore[index]
    assert metadata == {"userId": "u1"}


def test_format_error_default_message_for_internal_exception() -> None:
    formatter = create_graphql_format_error()
    formatted = formatter({"message": "secret internals", "extensions": {}}, internal_graphql_error())
    assert formatted["message"] == "An unexpected error occurred."


def test_format_error_keeps_message_for_client_error() -> None:
    formatter = create_graphql_format_error()
    exc = EventNotFoundException("e1")
    formatted = formatter({"message": "Event was not found", "extensions": {}}, exc)
    assert formatted["message"] == "Event was not found"


def test_page_input_defaults() -> None:
    page = PageInput()
    assert page.page == 1
    assert page.size == 20


def test_page_payload_has_next() -> None:
    payload = PagePayload(items=[1, 2, 3], total=10, page=1, size=3)
    assert payload.has_next() is True
    assert payload.page * payload.size < payload.total


def test_page_payload_no_more_pages() -> None:
    payload = PagePayload(items=[1, 2, 3], total=3, page=1, size=3)
    assert payload.has_next() is False
