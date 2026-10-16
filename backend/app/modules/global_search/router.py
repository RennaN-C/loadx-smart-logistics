from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BeforeValidator
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.deliveries.service import TripAccessForbiddenError
from app.modules.global_search.schemas import SearchResponse
from app.modules.global_search.service import GlobalSearchService
from app.modules.users.models import User
from app.shared.search import MAX_SEARCH_LENGTH, normalize_search

router = APIRouter(prefix="/search", tags=["search"])
SearchTerm = Annotated[
    str,
    Query(
        min_length=2,
        max_length=MAX_SEARCH_LENGTH,
        description="Substring literal após trim; acentos preservados, sem distinção de caixa.",
    ),
    BeforeValidator(lambda value: normalize_search(value) or ""),
]


def get_search_service(db: Annotated[Session, Depends(get_db)]) -> GlobalSearchService:
    return GlobalSearchService(db)


@router.get(
    "", response_model=SearchResponse, responses=openapi_error_responses(401, 403, 422)
)
def search_records(
    search: SearchTerm,
    current_user: Annotated[
        User, Depends(require_roles("ADMIN", "LOGISTICS_MANAGER", "CHECKER", "DRIVER"))
    ],
    service: Annotated[GlobalSearchService, Depends(get_search_service)],
    limit_per_category: Annotated[int, Query(ge=1, le=10)] = 5,
) -> SearchResponse:
    try:
        return service.search(search, limit_per_category, current_user=current_user)
    except TripAccessForbiddenError as exc:
        raise ApiError(
            status_code=403, code="AUTH_FORBIDDEN", message="Acesso não permitido."
        ) from exc
