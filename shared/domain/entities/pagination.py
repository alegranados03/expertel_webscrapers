from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class QuerySetPagination:
    def __init__(self, page: int = 1, page_size: int = 10):
        self.page = page
        self.page_size = page_size

    @property
    def array_slice(self) -> slice:
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        return slice(start, end)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class QuerySet(Generic[T]):
    def __init__(self, data: list[T], count: int | None = None):
        self.data = data
        self.count = count or len(data)

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.data[index]

    def first(self) -> T | None:
        return self.data[0] if self.data else None

    def last(self) -> T | None:
        return self.data[-1] if self.data else None

    def exists(self) -> bool:
        return len(self.data) > 0


class PaginationData(BaseModel):
    previous_page: str | None = Field(None, alias="previousPage")
    next_page: str | None = Field(None, alias="nextPage")
    current_page: int = Field(..., alias="currentPage")
    total_pages: int = Field(..., alias="totalPages")
    total_items_on_page: int = Field(..., alias="totalItemsOnPage")
    total_items: int = Field(..., alias="totalItems")
    page_size: int = Field(..., alias="pageSize")


class PaginatedQuerySet(BaseModel, Generic[T]):
    pagination_data: PaginationData
    query_params: dict = Field(default_factory=lambda: {})
    results: list[T]
