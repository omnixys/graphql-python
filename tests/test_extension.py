"""End-to-end tests: strawberry schema execution + format error extension."""

from __future__ import annotations

import strawberry

from omnixys_graphql import (
    EventNotFoundException,
    GraphQLFormatErrorExtension,
    GraphQLFormatErrorOptions,
    create_graphql_format_error,
)


@strawberry.type
class Query:
    @strawberry.field
    def ok(self) -> str:
        return "fine"

    @strawberry.field
    def fail_typed(self) -> str:
        raise EventNotFoundException("evt_1")

    @strawberry.field
    def fail_plain(self) -> str:
        raise RuntimeError("secret internals")


def _execute(schema: strawberry.Schema, query: str) -> dict:
    result = schema.execute_sync(query, root_value=None)
    errors = [
        {
            "message": error.message,
            "extensions": error.extensions or {},
            "path": error.path,
        }
        for error in (result.errors or [])
    ]
    return {"data": result.data, "errors": errors}


def test_typed_error_extensions_flow_through() -> None:
    schema = strawberry.Schema(query=Query)
    result = _execute(schema, "{ failTyped }")
    error = result["errors"][0]
    assert error["message"] == "Event was not found"
    assert error["extensions"]["code"] == "EVENT_NOT_FOUND"
    assert error["extensions"]["httpStatus"] == 404
    assert error["extensions"]["metadata"] == {"eventId": "evt_1"}


def test_plain_error_leaks_message_without_extension() -> None:
    schema = strawberry.Schema(query=Query)
    result = _execute(schema, "{ failPlain }")
    assert result["errors"][0]["message"] == "secret internals"


def test_format_extension_masks_internal_errors() -> None:
    schema = strawberry.Schema(
        query=Query,
        extensions=[lambda: GraphQLFormatErrorExtension()],
    )
    result = _execute(schema, "{ failPlain }")
    error = result["errors"][0]
    assert error["message"] == "An unexpected error occurred."
    assert error["extensions"]["code"] == "INTERNAL_SERVER_ERROR"
    assert error["extensions"]["httpStatus"] == 500
    assert error["extensions"]["retryable"] is False


def test_format_extension_exposes_internal_when_configured() -> None:
    schema = strawberry.Schema(
        query=Query,
        extensions=[
            lambda: GraphQLFormatErrorExtension(GraphQLFormatErrorOptions(expose_internal_errors=True)),
        ],
    )
    result = _execute(schema, "{ failPlain }")
    assert result["errors"][0]["message"] == "secret internals"


def test_format_extension_keeps_typed_client_error() -> None:
    schema = strawberry.Schema(
        query=Query,
        extensions=[lambda: GraphQLFormatErrorExtension()],
    )
    result = _execute(schema, "{ failTyped }")
    error = result["errors"][0]
    assert error["message"] == "Event was not found"
    assert error["extensions"]["code"] == "EVENT_NOT_FOUND"
    assert error["extensions"]["metadata"] == {"eventId": "evt_1"}


def test_format_extension_service_internal_code() -> None:
    schema = strawberry.Schema(
        query=Query,
        extensions=[
            lambda: GraphQLFormatErrorExtension(
                GraphQLFormatErrorOptions(service_name="ticket-service"),
            ),
        ],
    )
    result = _execute(schema, "{ failPlain }")
    assert result["errors"][0]["extensions"]["code"] == "TICKET_INTERNAL_ERROR"


def test_router_constructs_and_runs() -> None:
    from fastapi import FastAPI

    from omnixys_graphql import create_graphql_router, include_graphql_router

    schema = strawberry.Schema(query=Query)
    router = create_graphql_router(schema, graphiql=True)
    app = FastAPI()
    include_graphql_router(app, schema)
    assert router is not None
    assert any(type(route).__name__ == "_IncludedRouter" for route in app.routes)


def test_schema_executes_ok_field() -> None:
    schema = strawberry.Schema(query=Query)
    result = _execute(schema, "{ ok }")
    assert result["data"] == {"ok": "fine"}
    assert result["errors"] == []


def test_create_graphql_format_error_formatter_used_with_extension() -> None:
    formatter = create_graphql_format_error(GraphQLFormatErrorOptions())
    schema = strawberry.Schema(query=Query)
    result = _execute(schema, "{ failPlain }")
    error = result["errors"][0]
    formatted = formatter({"message": error["message"], "extensions": {}}, RuntimeError("secret internals"))
    assert formatted["message"] == "An unexpected error occurred."
    assert formatted["extensions"]["code"] == "INTERNAL_SERVER_ERROR"
