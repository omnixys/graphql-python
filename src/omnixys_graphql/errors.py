"""GraphQL error handling: typed exceptions, factories, and error formatting.

Mirrors the ``@omnixys/contracts-ts`` error contract and the GraphQL error
mapper from ``@omnixys/graphql-ts``. Every error carries stable ``extensions``
(code, summary, httpStatus, retryable, timestamp, metadata) so clients can react
without parsing messages.
"""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

from strawberry.exceptions import StrawberryGraphQLError

from omnixys_graphql.contracts.error_code import ErrorCode
from omnixys_graphql.contracts.error_definition import (
    get_error_definition,
    get_public_error_metadata,
    is_known_error_code,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from graphql import GraphQLFormattedError

__all__ = [
    "AccessBlockedError",
    "BaseGraphQLException",
    "ConflictGraphQLError",
    "DependencyUnavailableGraphQLError",
    "EventNotFoundException",
    "ForbiddenGraphQLError",
    "GraphQLExceptionDetails",
    "GraphQLFormatErrorOptions",
    "GraphQLServiceError",
    "InternalGraphQLError",
    "InvalidCredentialsException",
    "NotFoundGraphQLError",
    "NotificationNotFoundException",
    "RateLimitGraphQLError",
    "SeatNotFoundException",
    "SeatOccupiedException",
    "StepUpRequiredError",
    "TicketNotFoundException",
    "TicketRevokedException",
    "UnauthenticatedGraphQLError",
    "UserAlreadyExistsException",
    "UserNotFoundException",
    "ValidationGraphQLError",
    "access_blocked",
    "conflict_graphql_error",
    "create_graphql_exception",
    "create_graphql_format_error",
    "dependency_unavailable_graphql_error",
    "forbidden_graphql_error",
    "format_graphql_error",
    "internal_graphql_error",
    "not_found_graphql_error",
    "rate_limit_graphql_error",
    "sanitize_details",
    "step_up_required",
    "to_graphql_error",
    "unauthenticated_graphql_error",
    "validation_graphql_error",
]

GraphQLExceptionDetails = dict[str, Any]

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:authorization|cookie|password|secret|token|credential|private.?key|api.?key)",
    re.IGNORECASE,
)

_INTERNAL_STATUS_THRESHOLD = 500
_MAX_SANITIZE_DEPTH = 5
_MAX_SANITIZE_ITEMS = 50

_INTERNAL_CODE_BY_STATUS: dict[int, ErrorCode] = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.UNAUTHENTICATED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    429: ErrorCode.RATE_LIMIT_EXCEEDED,
}


def code_for_http_status(status: int) -> ErrorCode:
    """Map an HTTP status to the canonical framework error code."""
    if status in (400, 422):
        return ErrorCode.VALIDATION_ERROR
    if status in (502, 503, 504):
        return ErrorCode.DEPENDENCY_UNAVAILABLE
    return _INTERNAL_CODE_BY_STATUS.get(status, ErrorCode.INTERNAL_SERVER_ERROR)


def sanitize_details(details: GraphQLExceptionDetails | None) -> dict[str, Any]:
    """Drop sensitive keys and cap depth/size of ``details`` before exposing them."""
    if not details:
        return {}
    return _sanitize_record(details, 0, set())


def _sanitize_record(value: dict[str, Any], depth: int, seen: set[int]) -> dict[str, Any]:
    if id(value) in seen:
        return {}
    seen.add(id(value))
    safe: dict[str, Any] = {}
    for key, entry in value.items():
        if _SENSITIVE_KEY_PATTERN.search(str(key)):
            continue
        sanitized = _sanitize_value(entry, depth + 1, seen)
        if sanitized is not None:
            safe[key] = sanitized
    return safe


def _sanitize_value(value: Any, depth: int, seen: set[int]) -> Any:
    if depth > _MAX_SANITIZE_DEPTH:
        return "[truncated]"
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return _sanitize_record(value, depth, seen)
    if isinstance(value, list):
        return [
            _sanitize_value(entry, depth + 1, seen)
            for entry in value[:_MAX_SANITIZE_ITEMS]
            if _sanitize_value(entry, depth + 1, seen) is not None
        ]
    return None


def _with_identifier(
    key: str,
    value: str | None,
    details: GraphQLExceptionDetails,
) -> GraphQLExceptionDetails:
    if value is None:
        return details
    return {key: value, **details}


class BaseGraphQLException(StrawberryGraphQLError):
    """GraphQL error carrying the full catalog-derived extensions payload."""

    def __init__(
        self,
        code: str,
        message: str,
        details: GraphQLExceptionDetails | None = None,
        *,
        extensions: GraphQLExceptionDetails | None = None,
    ) -> None:
        definition = get_error_definition(code)
        safe_details = get_public_error_metadata(code, sanitize_details(details))
        ext: GraphQLExceptionDetails = {
            "code": code,
            "summary": definition.summary,
            "httpStatus": definition.http_status,
            "retryable": definition.retryable,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metadata": safe_details,
        }
        if extensions:
            ext.update(extensions)
        super().__init__(message, extensions=ext)


class GraphQLServiceError(BaseGraphQLException):
    """Backwards-compatible alias kept for existing callers."""

    def __init__(
        self,
        message: str,
        code: str = ErrorCode.INTERNAL_SERVER_ERROR.value,
        status_code: int = 500,
        extensions: GraphQLExceptionDetails | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            extensions={
                "statusCode": status_code,
                **(extensions or {}),
            },
        )


def create_graphql_exception(
    code: str,
    message: str | None = None,
    metadata: GraphQLExceptionDetails | None = None,
) -> BaseGraphQLException:
    """Create a ``BaseGraphQLException`` from the catalog definition of ``code``."""
    definition = get_error_definition(code)
    return BaseGraphQLException(code, message or definition.default_message, metadata)


def validation_graphql_error(
    message: str | None = None,
    metadata: GraphQLExceptionDetails | None = None,
) -> BaseGraphQLException:
    return create_graphql_exception(ErrorCode.VALIDATION_ERROR.value, message, metadata)


def unauthenticated_graphql_error(message: str | None = None) -> BaseGraphQLException:
    return create_graphql_exception(ErrorCode.UNAUTHENTICATED.value, message)


def forbidden_graphql_error(message: str | None = None) -> BaseGraphQLException:
    return create_graphql_exception(ErrorCode.FORBIDDEN.value, message)


def not_found_graphql_error(
    code: str,
    message: str | None = None,
    metadata: GraphQLExceptionDetails | None = None,
) -> BaseGraphQLException:
    return create_graphql_exception(code, message, metadata)


def conflict_graphql_error(
    code: str,
    message: str | None = None,
    metadata: GraphQLExceptionDetails | None = None,
) -> BaseGraphQLException:
    return create_graphql_exception(code, message, metadata)


def rate_limit_graphql_error(message: str | None = None) -> BaseGraphQLException:
    return create_graphql_exception(ErrorCode.RATE_LIMIT_EXCEEDED.value, message)


def dependency_unavailable_graphql_error(
    code: str = ErrorCode.SERVICE_UNAVAILABLE.value,
    message: str | None = None,
) -> BaseGraphQLException:
    return create_graphql_exception(code, message)


def internal_graphql_error(code: str = ErrorCode.INTERNAL_SERVER_ERROR.value) -> BaseGraphQLException:
    return create_graphql_exception(code)


def access_blocked(reasons: list[str]) -> BaseGraphQLException:
    """Build an ``ACCESS_BLOCKED`` error carrying the blocking reasons."""
    return BaseGraphQLException(
        ErrorCode.ACCESS_BLOCKED.value,
        "Access blocked",
        extensions={"reasons": reasons},
    )


def step_up_required(step_up: str, reasons: list[str]) -> BaseGraphQLException:
    """Build a ``STEP_UP_REQUIRED`` error requesting a higher auth level."""
    return BaseGraphQLException(
        ErrorCode.STEP_UP_REQUIRED.value,
        "Step-up authentication required",
        extensions={"stepUp": step_up, "reasons": reasons},
    )


class UserNotFoundException(BaseGraphQLException):
    def __init__(self, user_id: str | None = None, details: GraphQLExceptionDetails | None = None) -> None:
        super().__init__(
            ErrorCode.USER_NOT_FOUND.value,
            "User was not found",
            _with_identifier("userId", user_id, details or {}),
        )


class UserAlreadyExistsException(BaseGraphQLException):
    def __init__(self, identifier: str | None = None, details: GraphQLExceptionDetails | None = None) -> None:
        super().__init__(
            ErrorCode.USER_ALREADY_EXISTS.value,
            "User already exists",
            _with_identifier("identifier", identifier, details or {}),
        )


class InvalidCredentialsException(BaseGraphQLException):
    def __init__(self, details: GraphQLExceptionDetails | None = None) -> None:
        super().__init__(ErrorCode.INVALID_CREDENTIALS.value, "Invalid credentials", details or {})


class EventNotFoundException(BaseGraphQLException):
    def __init__(self, event_id: str | None = None, details: GraphQLExceptionDetails | None = None) -> None:
        super().__init__(
            ErrorCode.EVENT_NOT_FOUND.value,
            "Event was not found",
            _with_identifier("eventId", event_id, details or {}),
        )


class TicketNotFoundException(BaseGraphQLException):
    def __init__(self, ticket_id: str | None = None, details: GraphQLExceptionDetails | None = None) -> None:
        super().__init__(
            ErrorCode.TICKET_NOT_FOUND.value,
            "Ticket was not found",
            _with_identifier("ticketId", ticket_id, details or {}),
        )


class TicketRevokedException(BaseGraphQLException):
    def __init__(self, ticket_id: str | None = None, details: GraphQLExceptionDetails | None = None) -> None:
        super().__init__(
            ErrorCode.TICKET_REVOKED.value,
            "Ticket has been revoked",
            _with_identifier("ticketId", ticket_id, details or {}),
        )


class SeatNotFoundException(BaseGraphQLException):
    def __init__(self, seat_id: str | None = None, details: GraphQLExceptionDetails | None = None) -> None:
        super().__init__(
            ErrorCode.SEAT_NOT_FOUND.value,
            "Seat was not found",
            _with_identifier("seatId", seat_id, details or {}),
        )


class SeatOccupiedException(BaseGraphQLException):
    def __init__(self, seat_id: str | None = None, details: GraphQLExceptionDetails | None = None) -> None:
        super().__init__(
            ErrorCode.SEAT_OCCUPIED.value,
            "Seat is already occupied",
            _with_identifier("seatId", seat_id, details or {}),
        )


class NotificationNotFoundException(BaseGraphQLException):
    def __init__(
        self,
        notification_id: str | None = None,
        details: GraphQLExceptionDetails | None = None,
    ) -> None:
        super().__init__(
            ErrorCode.NOTIFICATION_NOT_FOUND.value,
            "Notification was not found",
            _with_identifier("notificationId", notification_id, details or {}),
        )


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


def to_graphql_error(
    error: Any,
    *,
    expose_internal_errors: bool = False,
    service_name: str | None = None,
) -> BaseGraphQLException:
    """Normalize any raised error into a ``BaseGraphQLException``.

    Known client errors keep their code and message; unexpected errors are
    collapsed to a safe default message unless ``expose_internal_errors`` is
    set.
    """
    if isinstance(error, BaseGraphQLException):
        return error

    extensions: GraphQLExceptionDetails | None = getattr(error, "extensions", None)
    if isinstance(extensions, dict):
        raw_code = extensions.get("code")
        code = _normalize_known_code(str(raw_code) if raw_code is not None else None)
        if code is not None:
            status = extensions.get("httpStatus")
            definition = get_error_definition(code)
            http_status = status if isinstance(status, int) else definition.http_status
            if expose_internal_errors or http_status < _INTERNAL_STATUS_THRESHOLD:
                message = str(error)
            else:
                message = definition.default_message
            return BaseGraphQLException(code, message, extensions.get("metadata"))

    http_status_value = getattr(error, "status_code", None) or getattr(error, "status", None)
    if isinstance(http_status_value, int):
        code = code_for_http_status(http_status_value).value
    else:
        code = _internal_code_for_service(service_name)
    definition = get_error_definition(code)
    message = str(error) if expose_internal_errors else definition.default_message
    return BaseGraphQLException(code, message)


def create_graphql_format_error(
    options: GraphQLFormatErrorOptions | None = None,
) -> Callable[[GraphQLFormattedError, Any], GraphQLFormattedError]:
    """Build a GraphQL ``format_error`` callable that standardizes every error.

    Unknown codes are normalized to a service-level internal code; internal
    messages are replaced with the catalog default message unless
    ``expose_internal_errors`` is enabled.
    """
    opts = options or GraphQLFormatErrorOptions()

    def _format(formatted: GraphQLFormattedError, error: Any) -> GraphQLFormattedError:
        graphql_error = error if hasattr(error, "extensions") else None
        original = getattr(graphql_error, "original_error", None) or error
        raw_code = _raw_code_of(original, formatted)
        code = _normalize_known_code(raw_code) or _internal_code_for_service(opts.service_name)
        definition = get_error_definition(code)
        safe_client_error = raw_code is not None and is_known_error_code(raw_code)
        message = (
            str(formatted.get("message", ""))
            if opts.expose_internal_errors
            or (safe_client_error and definition.http_status < _INTERNAL_STATUS_THRESHOLD)
            else definition.default_message
        )
        extensions: dict[str, Any] = {
            "code": code,
            "summary": definition.summary,
            "httpStatus": definition.http_status,
            "retryable": definition.retryable,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        original_extensions = getattr(graphql_error, "extensions", None)
        if isinstance(original_extensions, dict):
            metadata = original_extensions.get("metadata") or original_extensions.get("details")
            if isinstance(metadata, dict):
                extensions["metadata"] = get_public_error_metadata(code, sanitize_details(metadata))
        return {
            **formatted,
            "message": message,
            "extensions": extensions,
        }

    return _format


def _raw_code_of(error: Any, formatted: GraphQLFormattedError) -> str | None:
    extensions = getattr(error, "extensions", None)
    if isinstance(extensions, dict):
        code = extensions.get("code")
        if isinstance(code, str) and code:
            return code
    formatted_extensions = formatted.get("extensions")
    if isinstance(formatted_extensions, dict):
        code = formatted_extensions.get("code")
        if isinstance(code, str) and code:
            return code
    return None


_SERVICE_INTERNAL_CODES: dict[str, str] = {
    "analytics": ErrorCode.ANALYTICS_INTERNAL_ERROR.value,
    "authentication": ErrorCode.AUTHENTICATION_INTERNAL_ERROR.value,
    "blog": ErrorCode.BLOG_INTERNAL_ERROR.value,
    "event": ErrorCode.EVENT_INTERNAL_ERROR.value,
    "gateway": ErrorCode.GATEWAY_INTERNAL_ERROR.value,
    "invitation": ErrorCode.INVITATION_INTERNAL_ERROR.value,
    "notification": ErrorCode.NOTIFICATION_INTERNAL_ERROR.value,
    "profile": ErrorCode.PROFILE_INTERNAL_ERROR.value,
    "seat": ErrorCode.SEAT_INTERNAL_ERROR.value,
    "shopping-cart": ErrorCode.SHOPPING_CART_INTERNAL_ERROR.value,
    "ticket": ErrorCode.TICKET_INTERNAL_ERROR.value,
    "user": ErrorCode.USER_INTERNAL_ERROR.value,
}


def _internal_code_for_service(service_name: str | None) -> str:
    if service_name is None:
        return ErrorCode.INTERNAL_SERVER_ERROR.value
    normalized = service_name.removeprefix("omnixys-").removesuffix("-service").replace("_", "-")
    return _SERVICE_INTERNAL_CODES.get(normalized, ErrorCode.INTERNAL_SERVER_ERROR.value)


def format_graphql_error(exc: Any) -> dict[str, Any]:
    """Format a GraphQL error into a response dict (kept for compatibility)."""
    formatted: dict[str, Any] = {
        "message": str(exc),
        "extensions": {
            "code": "INTERNAL_ERROR",
            "statusCode": 500,
        },
    }
    if hasattr(exc, "extensions") and isinstance(exc.extensions, dict):
        formatted["extensions"].update(exc.extensions)
    if hasattr(exc, "locations"):
        formatted["locations"] = exc.locations
    if hasattr(exc, "path"):
        formatted["path"] = exc.path
    return formatted


class GraphQLFormatErrorOptions:
    """Options controlling the ``create_graphql_format_error`` formatter."""

    def __init__(
        self,
        *,
        expose_internal_errors: bool = False,
        service_name: str | None = None,
    ) -> None:
        self.expose_internal_errors = expose_internal_errors
        self.service_name = service_name


# Public aliases following the TS naming for factory helpers.
ValidationGraphQLError = validation_graphql_error
UnauthenticatedGraphQLError = unauthenticated_graphql_error
ForbiddenGraphQLError = forbidden_graphql_error
NotFoundGraphQLError = not_found_graphql_error
ConflictGraphQLError = conflict_graphql_error
RateLimitGraphQLError = rate_limit_graphql_error
DependencyUnavailableGraphQLError = dependency_unavailable_graphql_error
InternalGraphQLError = internal_graphql_error
AccessBlockedError = access_blocked
StepUpRequiredError = step_up_required
