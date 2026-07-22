from __future__ import annotations

from typing import TYPE_CHECKING, Any

from strawberry.fastapi import GraphQLRouter

from graphql.errors import format_graphql_error

if TYPE_CHECKING:
    from collections.abc import Callable

    from dishka import AsyncContainer
    from fastapi import FastAPI


def create_context_getter() -> Callable[..., dict[str, Any]]:
    async def get_context(request: Any, response: Any) -> dict[str, Any]:
        dishka_container: AsyncContainer | None = getattr(request.state, "dishka_container", None)
        return {
            "request": request,
            "response": response,
            "dishka": dishka_container,
        }

    return get_context  # type: ignore[return-value]


def create_graphql_router(
    schema: Any,
    *,
    graphiql: bool = False,
    path: str = "/graphql",
    allow_queries_via_get: bool = True,
    **kwargs: Any,
) -> GraphQLRouter:
    return GraphQLRouter(
        schema=schema,
        path=path,
        graphiql=graphiql,
        allow_queries_via_get=allow_queries_via_get,
        context_getter=create_context_getter(),  # type: ignore[arg-type]
        process_error=format_graphql_error,
        **kwargs,
    )


def include_graphql_router(
    app: FastAPI,
    schema: Any,
    *,
    path: str = "/graphql",
    **kwargs: Any,
) -> GraphQLRouter:
    router = create_graphql_router(schema=schema, path=path, **kwargs)
    app.include_router(router, prefix="")
    return router
