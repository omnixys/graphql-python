"""Strawberry schema extension that standardizes GraphQL errors.

Resolvers that raise ``BaseGraphQLException`` already carry structured
``extensions``, but arbitrary exceptions (or plain ``GraphQLError``s) are
rendered by graphql-core with raw messages. Attach ``GraphQLFormatErrorExtension``
to your schema to normalize every error to the catalog contract and to keep
internal messages and sensitive metadata out of client responses.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from graphql import GraphQLError
from strawberry.extensions import SchemaExtension

from omnixys_graphql.contracts.error_code import ErrorCode
from omnixys_graphql.contracts.error_definition import (
    get_error_definition,
    get_public_error_metadata,
    is_known_error_code,
)
from omnixys_graphql.errors import (
    GraphQLFormatErrorOptions,
    _internal_code_for_service,
    sanitize_details,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["GraphQLFormatErrorExtension"]

_INTERNAL_STATUS_THRESHOLD = 500


def _normalize_known_code(code: str | None) -> str | None:
    if code is None:
        return None
    if is_known_error_code(code):
        return code
    if code in ("BAD_USER_INPUT", "GRAPHQL_VALIDATION_FAILED"):
        return ErrorCode.VALIDATION_ERROR.value
    if code == "DOWNSTREAM_SERVICE_ERROR":
        return ErrorCode.DEPENDENCY_UNAVAILABLE.value
    return None


def standardize_graphql_error(error: GraphQLError, options: GraphQLFormatErrorOptions) -> GraphQLError:
    """Return a ``GraphQLError`` whose message and extensions follow the catalog."""
    original = getattr(error, "original_error", None) or error
    raw_code = _code_of(error) or _code_of(original)
    code = _normalize_known_code(raw_code) or _internal_code_for_service(options.service_name)
    definition = get_error_definition(code)
    safe_client_error = raw_code is not None and is_known_error_code(raw_code)

    if options.expose_internal_errors or (safe_client_error and definition.http_status < _INTERNAL_STATUS_THRESHOLD):
        message = error.message
    else:
        message = definition.default_message

    extensions: dict[str, Any] = {
        "code": code,
        "summary": definition.summary,
        "httpStatus": definition.http_status,
        "retryable": definition.retryable,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    error_extensions = getattr(error, "extensions", None)
    if isinstance(error_extensions, dict):
        metadata = error_extensions.get("metadata") or error_extensions.get("details")
        if isinstance(metadata, dict):
            extensions["metadata"] = get_public_error_metadata(code, sanitize_details(metadata))

    return GraphQLError(
        message=message,
        nodes=getattr(error, "nodes", None),
        source=getattr(error, "source", None),
        positions=getattr(error, "positions", None),
        path=getattr(error, "path", None),
        original_error=getattr(error, "original_error", None),
        extensions=extensions,
    )


def _code_of(error: Any) -> str | None:
    extensions = getattr(error, "extensions", None)
    if not isinstance(extensions, dict):
        return None
    code = extensions.get("code")
    return str(code) if isinstance(code, str) and code else None


class GraphQLFormatErrorExtension(SchemaExtension):
    """Replace every error in the operation result with a standardized one."""

    def __init__(self, options: GraphQLFormatErrorOptions | None = None) -> None:
        super().__init__()
        self._options = options or GraphQLFormatErrorOptions()

    def on_operation(self) -> Iterator[None]:
        yield

        result = getattr(self.execution_context, "result", None)
        if result is None:
            return
        if hasattr(result, "errors") and getattr(result, "errors", None):
            result.errors = [standardize_graphql_error(error, self._options) for error in result.errors]
        elif hasattr(result, "initial_result"):
            initial = result.initial_result
            if hasattr(initial, "errors") and getattr(initial, "errors", None):
                initial.errors = [standardize_graphql_error(error, self._options) for error in initial.errors]
