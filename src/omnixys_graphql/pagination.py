from __future__ import annotations

from typing import TypeVar

import strawberry

T = TypeVar("T")


@strawberry.input
class PageInput:
    page: int = 1
    size: int = 20


@strawberry.type
class PagePayload[T]:
    items: list[T]
    total: int
    page: int
    size: int

    @strawberry.field
    def has_next(self) -> bool:
        return self.page * self.size < self.total
