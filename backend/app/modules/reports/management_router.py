"""Filtered management reports backed by the same database aggregation."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_permission
from app.modules.reports.management_service import (
    ManagementFilters,
    ManagementReportService,
    ManagementSummary,
)
from app.modules.users.models import User

router = APIRouter(prefix="/reports", tags=["reports"])
Reader = Annotated[User, Depends(require_permission("loadx.reports.read"))]
Db = Annotated[Session, Depends(get_db)]


def report_filters(
    start: datetime,
    end: datetime,
    truck_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
) -> ManagementFilters:
    return ManagementFilters(
        start=start, end=end, truck_id=truck_id, driver_id=driver_id
    )


Filters = Annotated[ManagementFilters, Depends(report_filters)]


@router.get(
    "/management-summary",
    responses=openapi_error_responses(401, 403, 422),
)
def management_summary(
    _current_user: Reader, db: Db, filters: Filters
) -> ManagementSummary:
    return ManagementReportService(db).summary(filters)


@router.get(
    "/management-summary.csv",
    responses=openapi_error_responses(401, 403, 422),
)
def management_csv(_current_user: Reader, db: Db, filters: Filters) -> Response:
    summary = ManagementReportService(db).summary(filters)
    return Response(
        content=ManagementReportService.csv_content(summary),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="loadx-management.csv"'},
    )


@router.get(
    "/management-summary.pdf",
    responses=openapi_error_responses(401, 403, 422),
)
def management_pdf(_current_user: Reader, db: Db, filters: Filters) -> Response:
    summary = ManagementReportService(db).summary(filters)
    return Response(
        content=ManagementReportService.pdf_content(summary),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="loadx-management.pdf"'},
    )
