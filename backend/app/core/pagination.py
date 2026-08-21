from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Annotated, Generic, Literal, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel, Field

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

SortOrder = Literal["asc", "desc"]
ItemT = TypeVar("ItemT")
ResponseItemT = TypeVar("ResponseItemT")


@dataclass(frozen=True, slots=True)
class PaginationParams:
    page: int
    page_size: int
    sort_order: SortOrder

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True, slots=True)
class PageResult(Generic[ItemT]):
    items: Sequence[ItemT]
    page: int
    page_size: int
    total: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: Sequence[ItemT],
        pagination: PaginationParams,
        total: int,
    ) -> "PageResult[ItemT]":
        total_pages = (
            (total + pagination.page_size - 1) // pagination.page_size
            if total > 0
            else 0
        )
        return cls(
            items=items,
            page=pagination.page,
            page_size=pagination.page_size,
            total=total,
            total_pages=total_pages,
        )


class PageResponse(BaseModel, Generic[ResponseItemT]):
    items: list[ResponseItemT]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=MAX_PAGE_SIZE)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


def to_page_response(
    result: PageResult[ItemT],
    items: Iterable[ResponseItemT],
) -> PageResponse[ResponseItemT]:
    return PageResponse[ResponseItemT](
        items=list(items),
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


def get_pagination_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    sort_order: Annotated[SortOrder, Query()] = "desc",
) -> PaginationParams:
    return PaginationParams(
        page=page,
        page_size=page_size,
        sort_order=sort_order,
    )


Pagination = Annotated[PaginationParams, Depends(get_pagination_params)]
