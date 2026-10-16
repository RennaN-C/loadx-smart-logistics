"""HTTP validation for the common OC95 search parameter."""

from typing import Annotated

from fastapi import Query
from pydantic import BeforeValidator

from app.shared.search import MAX_SEARCH_LENGTH, normalize_search

SearchQuery = Annotated[
    str | None,
    Query(
        max_length=MAX_SEARCH_LENGTH,
        description="Substring literal, sem distinção de maiúsculas; trim, até 120 caracteres.",
    ),
    BeforeValidator(normalize_search),
]
