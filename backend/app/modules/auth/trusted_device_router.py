"""Own credential management: session ownership, Origin and CSRF stay central."""

import uuid
from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Request, Response
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.responses import openapi_error_responses
from app.modules.auth.identity_router import Current, Db, identity_operation
from app.modules.auth.schemas import TrustedDeviceListRead
from app.modules.auth.totp import IdentityUnavailableError
from app.modules.auth.trusted_device_service import TrustedDeviceService

router = APIRouter(
    prefix="/auth/me/trusted-devices",
    tags=["auth"],
    responses=openapi_error_responses(400, 401, 403, 422, 429, 503),
)
T = TypeVar("T")


def operation(db: Db, action: Callable[[], T]) -> T:
    try:
        return identity_operation(action)
    except SQLAlchemyError:
        db.rollback()
        return identity_operation(lambda: unavailable())


def unavailable() -> None:
    raise IdentityUnavailableError


def clear_device_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.trusted_device_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.get("")
def list_devices(request: Request, current: Current, db: Db) -> TrustedDeviceListRead:
    return operation(
        db,
        lambda: TrustedDeviceService(db).list_own(
            current, request.cookies.get(settings.trusted_device_cookie_name)
        ),
    )


@router.delete("/current", status_code=204)
def forget_current(
    request: Request, response: Response, current: Current, db: Db
) -> None:
    operation(
        db,
        lambda: TrustedDeviceService(db).revoke_own(
            current,
            current_token=request.cookies.get(settings.trusted_device_cookie_name),
        ),
    )
    clear_device_cookie(response)


@router.post("/revoke-all", status_code=204)
def revoke_all(response: Response, current: Current, db: Db) -> None:
    operation(
        db, lambda: TrustedDeviceService(db).revoke_own(current, all_devices=True)
    )
    clear_device_cookie(response)


@router.delete("/{device_id}", status_code=204)
def revoke_device(
    device_id: uuid.UUID, request: Request, response: Response, current: Current, db: Db
) -> None:
    forgotten = operation(
        db,
        lambda: TrustedDeviceService(db).revoke_own(
            current,
            device_id=device_id,
            current_token=request.cookies.get(settings.trusted_device_cookie_name),
        ),
    )
    if forgotten:
        clear_device_cookie(response)
