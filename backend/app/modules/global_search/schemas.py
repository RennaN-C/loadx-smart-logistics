import uuid
from typing import Literal

from pydantic import BaseModel, Field

SearchCategory = Literal["order", "customer", "truck", "driver", "trip"]


class SearchResult(BaseModel):
    category: SearchCategory
    id: uuid.UUID
    title: str
    href: str = Field(pattern=r"^/(orders\?|contacts\?|trucks\?|trips/)")


class SearchResponse(BaseModel):
    results: list[SearchResult]
