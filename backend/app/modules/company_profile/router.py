from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.company_profile.models import CompanyProfile
from app.modules.company_profile.schemas import CompanyProfileInput, CompanyProfileRead
from app.modules.company_profile.service import CompanyProfileService
from app.modules.users.models import User

router = APIRouter(
    prefix="/company-profile",
    tags=["company-profile"],
    responses=openapi_error_responses(401, 403, 422),
)
Admin = Annotated[User, Depends(require_roles("ADMIN"))]


def get_service(db: Annotated[Session, Depends(get_db)]) -> CompanyProfileService:
    return CompanyProfileService(db)


@router.get("", response_model=CompanyProfileRead | None)
def read_company_profile(
    _admin: Admin, service: Annotated[CompanyProfileService, Depends(get_service)]
) -> CompanyProfile | None:
    return service.get()


@router.put("", response_model=CompanyProfileRead)
def update_company_profile(
    data: CompanyProfileInput,
    admin: Admin,
    service: Annotated[CompanyProfileService, Depends(get_service)],
) -> CompanyProfile:
    return service.update(data, admin.id)
