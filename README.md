# omnixys-graphql

Shared GraphQL toolkit for Omnixys Python services: strawberry/FastAPI wiring,
a transport-independent error contract, typed error factories, sanitization,
and pagination primitives.

## Installation

```bash
pip install omnixys-graphql
```

## Features

- **Error catalog** — the full `@omnixys/contracts-ts` `ErrorCode` enum and
  `ERROR_DEFINITIONS` (summary, default message, HTTP status, retryability,
  public metadata keys) ported to Python.
- **Typed errors** — `BaseGraphQLException` and domain exceptions
  (`UserNotFoundException`, `EventNotFoundException`, …) that render stable
  `extensions` (code, summary, httpStatus, retryable, timestamp, metadata).
- **Factory helpers** — `validation_graphql_error`, `unauthenticated_graphql_error`,
  `forbidden_graphql_error`, `not_found_graphql_error`, `conflict_graphql_error`,
  `rate_limit_graphql_error`, `dependency_unavailable_graphql_error`,
  `internal_graphql_error`, `access_blocked`, `step_up_required`.
- **Error formatting** — `create_graphql_format_error` standardizes every
  response error, collapses internal details to safe defaults, and strips
  sensitive metadata; unknown codes map to a service-level internal code.
- **Pagination** — `PageInput` / `PagePayload` strawberry types.
- **Router wiring** — `create_graphql_router` / `include_graphql_router` with a
  Dishka-aware context getter.

> Note: the package imports as `omnixys_graphql`. It deliberately does **not**
> shadow the `graphql` module name, which belongs to `graphql-core` (required by
> strawberry).

## Quick start

```python
import strawberry
from fastapi import FastAPI
from omnixys_graphql import create_graphql_router, include_graphql_router

@strawberry.type
class Query:
    @strawberry.field
    def ping(self) -> str:
        return "pong"

schema = strawberry.Schema(query=Query)
app = FastAPI()
include_graphql_router(app, schema, graphiql=True)
```

## Error handling

Raise a typed error from a resolver and it renders with stable extensions:

```python
from omnixys_graphql import EventNotFoundException, UserNotFoundException

@strawberry.type
class Query:
    @strawberry.field
    def event(self, event_id: str) -> str:
        raise EventNotFoundException(event_id)
```

Response extensions:

```json
{
  "code": "EVENT_NOT_FOUND",
  "summary": "Event not found.",
  "httpStatus": 404,
  "retryable": false,
  "timestamp": "2026-01-01T00:00:00Z",
  "metadata": { "eventId": "evt_123" }
}
```

Only metadata keys listed for the code survive; `sanitize_details` also drops
anything sensitive (`password`, `token`, `authorization`, …), truncates nesting
beyond depth 5, and caps arrays at 50 entries.

## Factories

```python
from omnixys_graphql import (
    access_blocked,
    forbidden_graphql_error,
    rate_limit_graphql_error,
    step_up_required,
    validation_graphql_error,
)

raise validation_graphql_error("bad input", {"field": "email"})
raise forbidden_graphql_error("no permission")
raise rate_limit_graphql_error()
raise access_blocked(["2fa_pending"])
raise step_up_required("mfa", ["low_risk_score"])
```

## Standardizing responses

Attach `GraphQLFormatErrorExtension` to your schema to normalize every error to
the catalog contract:

```python
from strawberry import Schema
from omnixys_graphql import GraphQLFormatErrorOptions, GraphQLFormatErrorExtension

schema = Schema(
    query=Query,
    extensions=[
        lambda: GraphQLFormatErrorExtension(
            GraphQLFormatErrorOptions(service_name="event-service"),
        ),
    ],
)
```

The extension keeps client-safe messages (`httpStatus < 500`) as-is and replaces
internal messages with the catalog default, so stack traces never leak. Unknown
codes normalize to the service internal code (e.g. `EVENT_INTERNAL_ERROR`).
Use the lambda factory so a fresh extension is built per request.

## Error catalog

```python
from omnixys_graphql import (
    ERROR_CATALOG_VERSION,
    ErrorCode,
    get_error_definition,
    get_public_error_metadata,
    is_known_error_code,
)

definition = get_error_definition(ErrorCode.RATE_LIMIT_EXCEEDED.value)
assert definition.http_status == 429
assert definition.retryable is True

metadata = get_public_error_metadata("EVENT_NOT_FOUND", {"eventId": "e1", "secret": 1})
assert metadata == {"eventId": "e1"}
```

## Pagination

```python
from omnixys_graphql import PageInput, PagePayload

payload = PagePayload(items=[1, 2, 3], total=10, page=1, size=3)
assert payload.has_next() is True
```

## Development

```bash
uv sync
uv run pytest -q
uv run ruff check .
uv run mypy src/
```

## License

GPL-3.0-or-later
