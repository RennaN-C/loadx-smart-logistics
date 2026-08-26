import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.responses import error_response
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.loading.schemas import (
    LoadingItemStatusChange,
    LoadingSessionCreate,
    LoadingSessionRead,
    LoadingSessionStatusChange,
)
from app.modules.loading.service import (
    LoadingChecklistIncompleteError,
    LoadingItemNotFoundError,
    LoadingItemSessionMismatchError,
    LoadingPlanNotApprovedError,
    LoadingService,
    LoadingSessionNotFoundError,
    LoadingStatusTransitionError,
)
from app.modules.users.models import User

router = APIRouter(prefix="/loading-sessions", tags=["loading"])
Operator = Annotated[User, Depends(require_roles("CHECKER", "LOGISTICS_MANAGER"))]
Reader = Annotated[User, Depends(require_roles("ADMIN", "CHECKER", "LOGISTICS_MANAGER"))]


def get_loading_service(db: Annotated[Session, Depends(get_db)]) -> LoadingService:
    return LoadingService(db)


@router.post("", response_model=LoadingSessionRead, status_code=status.HTTP_201_CREATED)
def create_session(data: LoadingSessionCreate, _user: Operator, service: Annotated[LoadingService, Depends(get_loading_service)]):
    try:
        return service.create_session(data.load_plan_id)
    except LoadingPlanNotApprovedError:
        return error_response(409, "LOADING_PLAN_NOT_APPROVED", "O carregamento exige plano aprovado.")


@router.get("/{session_id}", response_model=LoadingSessionRead)
def get_session(session_id: uuid.UUID, _user: Reader, service: Annotated[LoadingService, Depends(get_loading_service)]):
    try:
        return service.get_session(session_id)
    except LoadingSessionNotFoundError:
        return error_response(404, "LOADING_SESSION_NOT_FOUND", "Sessão de carregamento não encontrada.")


@router.patch("/{session_id}/status", response_model=LoadingSessionRead)
def change_status(session_id: uuid.UUID, data: LoadingSessionStatusChange, _user: Operator, service: Annotated[LoadingService, Depends(get_loading_service)]):
    try:
        return service.change_status(session_id, data.status)
    except LoadingSessionNotFoundError:
        return error_response(404, "LOADING_SESSION_NOT_FOUND", "Sessão de carregamento não encontrada.")
    except LoadingChecklistIncompleteError:
        return error_response(409, "LOADING_CHECKLIST_INCOMPLETE", "Todos os itens devem ser conferidos.")
    except LoadingStatusTransitionError:
        return error_response(409, "LOADING_STATUS_TRANSITION_NOT_ALLOWED", "Transição de carregamento não permitida.")


@router.patch("/{session_id}/items/{item_id}", response_model=LoadingSessionRead)
def change_item_status(session_id: uuid.UUID, item_id: uuid.UUID, data: LoadingItemStatusChange, _user: Operator, service: Annotated[LoadingService, Depends(get_loading_service)]):
    try:
        return service.change_item_status(session_id, item_id, data.status)
    except LoadingSessionNotFoundError:
        return error_response(404, "LOADING_SESSION_NOT_FOUND", "Sessão de carregamento não encontrada.")
    except LoadingItemNotFoundError:
        return error_response(404, "LOADING_ITEM_NOT_FOUND", "Item de carregamento não encontrado.")
    except LoadingItemSessionMismatchError:
        return error_response(409, "LOADING_ITEM_SESSION_MISMATCH", "Item não pertence à sessão.")
    except LoadingStatusTransitionError:
        return error_response(409, "LOADING_STATUS_TRANSITION_NOT_ALLOWED", "Transição de carregamento não permitida.")
