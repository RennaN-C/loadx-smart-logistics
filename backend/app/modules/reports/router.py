import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.deliveries.service import TripAccessForbiddenError, TripNotFoundError
from app.modules.load_planning.service import LoadPlanNotFoundError
from app.modules.reports.service import ReportLoadingNotFoundError, ReportService
from app.modules.users.models import User

router = APIRouter(prefix="/reports", tags=["reports"])
ReportUser = Annotated[User, Depends(require_roles("ADMIN", "LOGISTICS_MANAGER"))]


def get_report_service(db: Annotated[Session, Depends(get_db)]) -> ReportService:
    return ReportService(db)


@router.get(
    "/load-plans/{load_plan_id}",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}},
        **openapi_error_responses(401, 403, 404, 422),
    },
)
def download_loading_report(
    load_plan_id: uuid.UUID,
    _current_user: ReportUser,
    service: Annotated[ReportService, Depends(get_report_service)],
) -> Response:
    try:
        content = service.build_loading_report(load_plan_id)
    except LoadPlanNotFoundError:
        return error_response(404, "LOAD_PLAN_NOT_FOUND", "Plano não encontrado.")
    except ReportLoadingNotFoundError:
        return error_response(
            404, "LOADING_SESSION_NOT_FOUND", "Carregamento não encontrado."
        )
    return _pdf_response(content, f"loading-report-{load_plan_id}.pdf")


@router.get(
    "/trips/{trip_id}",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}},
        **openapi_error_responses(401, 403, 404, 422),
    },
)
def download_trip_report(
    trip_id: uuid.UUID,
    current_user: ReportUser,
    service: Annotated[ReportService, Depends(get_report_service)],
) -> Response:
    try:
        content = service.build_trip_report(trip_id, current_user=current_user)
    except (TripNotFoundError, LoadPlanNotFoundError):
        return error_response(404, "TRIP_NOT_FOUND", "Viagem não encontrada.")
    except TripAccessForbiddenError:
        return error_response(403, "AUTH_FORBIDDEN", "Acesso negado.")
    return _pdf_response(content, f"trip-report-{trip_id}.pdf")


def _pdf_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
