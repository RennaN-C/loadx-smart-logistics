from pydantic import BaseModel

from app.core.pagination import (
    PageResult,
    PaginationParams,
    get_pagination_params,
    to_page_response,
)


class ItemResponse(BaseModel):
    value: int


def test_pagination_params_calculate_offset() -> None:
    pagination = get_pagination_params(page=3, page_size=10, sort_order="asc")

    assert pagination == PaginationParams(page=3, page_size=10, sort_order="asc")
    assert pagination.offset == 20


def test_page_result_calculates_total_pages_and_response_envelope() -> None:
    pagination = PaginationParams(page=2, page_size=10, sort_order="desc")
    result = PageResult.create([1, 2], pagination, total=21)

    response = to_page_response(
        result,
        (ItemResponse(value=value) for value in result.items),
    )

    assert response.model_dump() == {
        "items": [{"value": 1}, {"value": 2}],
        "page": 2,
        "page_size": 10,
        "total": 21,
        "total_pages": 3,
    }


def test_empty_page_result_has_zero_total_pages() -> None:
    pagination = PaginationParams(page=1, page_size=20, sort_order="desc")

    result = PageResult.create([], pagination, total=0)

    assert result.total_pages == 0
