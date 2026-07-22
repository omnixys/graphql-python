from __future__ import annotations

from typing import Any

from strawberry.exceptions import StrawberryGraphQLError


class GraphQLServiceError(StrawberryGraphQLError):
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        ext: dict[str, Any] = {
            "code": code,
            "statusCode": status_code,
        }
        if extensions:
            ext.update(extensions)
        super().__init__(message, extensions=ext)


def to_graphql_error(message: str, code: str = "INTERNAL_ERROR", status_code: int = 500) -> GraphQLServiceError:
    return GraphQLServiceError(message=message, code=code, status_code=status_code)


def format_graphql_error(exc: Any) -> dict[str, Any]:
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
