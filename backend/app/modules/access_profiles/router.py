import uuid
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.access_profiles.catalog import CATALOG
from app.modules.access_profiles.schemas import (
    PermissionRead,
    ProfileRead,
    ProfileUpdate,
    ProfileWrite,
)
from app.modules.access_profiles.service import ProfileService
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import User

router = APIRouter(
    prefix="/access-profiles",
    tags=["access-profiles"],
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
Admin = Annotated[User, Depends(require_roles("ADMIN"))]


def get_service(db: Annotated[Session, Depends(get_db)]) -> ProfileService:
    return ProfileService(db)


Service = Annotated[ProfileService, Depends(get_service)]


@router.get("/permissions", response_model=list[PermissionRead])
def catalog(_admin: Admin):
    return [asdict(item) for item in CATALOG]


@router.get("", response_model=PageResponse[ProfileRead])
def list_profiles(pagination: Pagination, _admin: Admin, service: Service):
    result = service.list_profiles(pagination)
    return to_page_response(result, result.items)


@router.post("", response_model=ProfileRead, status_code=201)
def create_profile(data: ProfileWrite, admin: Admin, service: Service):
    return service.save(data, actor_id=admin.id)


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(profile_id: uuid.UUID, _admin: Admin, service: Service):
    return service.get_profile(profile_id)


@router.patch("/{profile_id}", response_model=ProfileRead)
def update_profile(
    profile_id: uuid.UUID, data: ProfileUpdate, admin: Admin, service: Service
):
    return service.save(data, actor_id=admin.id, identity=profile_id)
