from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, TypeVar

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ApiError
from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.integrations.password_recovery.delivery import (
    dispatch_recovery,
    get_recovery_delivery,
)
from app.modules.access_profiles.service import ProfileService
from app.modules.auth.dependencies import CSRF_HEADER_NAME, get_current_session
from app.modules.auth.identity_service import IdentityService
from app.modules.auth.recovery_service import PasswordRecoveryService
from app.modules.auth.router import account_operation, clear_session_cookie
from app.modules.auth.schemas import (
    MfaChallengeInput,
    MfaChallengeRead,
    MfaProvisionRead,
    MfaReauth,
    MfaStatusRead,
    MfaVerify,
    RecoveryCodesRead,
    RecoveryConfirm,
    RecoveryRequest,
)
from app.modules.auth.sessions import ResolvedAuthSession
from app.modules.auth.totp import IdentityUnavailableError
from app.modules.users.schemas import UserRead

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses=openapi_error_responses(400, 401, 403, 422, 429, 503),
)
Db = Annotated[Session, Depends(get_db)]
Current = Annotated[ResolvedAuthSession, Depends(get_current_session)]


T = TypeVar("T")


def identity_operation(operation: Callable[[], T]) -> T:
    try:
        return account_operation(operation)
    except IdentityUnavailableError:
        raise ApiError(
            503,
            "AUTH_IDENTITY_UNAVAILABLE",
            "Serviço de identidade indisponível. Contate o suporte.",
        ) from None


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/password-recovery", status_code=202)
def request_recovery(
    data: RecoveryRequest, request: Request, tasks: BackgroundTasks, db: Db
) -> dict[str, str]:
    delivery = identity_operation(get_recovery_delivery)
    result = identity_operation(
        lambda: PasswordRecoveryService(db).request(data.email, client_ip(request))
    )
    if result:
        tasks.add_task(dispatch_recovery, delivery, *result)
    return {
        "message": "Se a conta for elegível, você receberá instruções de recuperação."
    }


@router.post("/password-recovery/confirm", status_code=204)
def confirm_recovery(
    data: RecoveryConfirm, request: Request, response: Response, db: Db
) -> None:
    identity_operation(
        lambda: PasswordRecoveryService(db).confirm(
            data.token, data.new_password, client_ip(request)
        )
    )
    clear_session_cookie(response)


@router.post("/mfa/setup")
def setup_mfa(data: MfaChallengeInput, request: Request, db: Db) -> MfaProvisionRead:
    uri = identity_operation(
        lambda: IdentityService(db).setup(data.challenge_token, client_ip(request))
    )
    return MfaProvisionRead(provisioning_uri=uri)


class MfaLoginRead(RecoveryCodesRead):
    user: UserRead


def trusted_cookie_expiry(value: datetime) -> datetime:
    """Serialize database expiry in UTC without shifting a naive UTC value."""
    return (
        value.replace(tzinfo=UTC)
        if value.tzinfo is None
        else value.astimezone(UTC)
    )


@router.post("/mfa/verify")
def verify_mfa(
    data: MfaVerify, request: Request, response: Response, db: Db
) -> MfaLoginRead:
    result = identity_operation(
        lambda: IdentityService(db).complete(
            data.challenge_token,
            data.code,
            client_ip(request),
            trust_device=data.trust_device,
            previous_device_token=request.cookies.get(
                settings.trusted_device_cookie_name
            ),
        )
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=result.session.token,
        max_age=8 * 60 * 60,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    if result.trusted_device is not None:
        response.set_cookie(
            key=settings.trusted_device_cookie_name,
            value=result.trusted_device.token,
            max_age=settings.trusted_device_days * 86400,
            path="/",
            expires=trusted_cookie_expiry(result.trusted_device.device.expires_at),
            secure=settings.session_cookie_secure,
            httponly=True,
            samesite="lax",
        )
    response.headers[CSRF_HEADER_NAME] = result.session.csrf_token
    ProfileService(db).resolve(result.user)
    return MfaLoginRead(
        user=UserRead.model_validate(result.user), recovery_codes=result.recovery_codes
    )


@router.get("/me/mfa")
def mfa_status(current: Current, db: Db) -> MfaStatusRead:
    return MfaStatusRead(**IdentityService(db).status(current))


@router.post("/me/mfa/enroll")
def enroll_mfa(
    data: MfaReauth, request: Request, response: Response, current: Current, db: Db
) -> MfaChallengeRead:
    result = identity_operation(
        lambda: IdentityService(db).enroll_own(
            current, data.password, client_ip(request)
        )
    )
    clear_session_cookie(response)
    return MfaChallengeRead(**result.__dict__)


@router.post("/me/mfa/recovery-codes")
def regenerate_codes(
    data: MfaReauth, request: Request, current: Current, db: Db
) -> RecoveryCodesRead:
    codes = identity_operation(
        lambda: IdentityService(db).manage(
            current, data.password, data.code, "regenerate", client_ip(request)
        )
    )
    return RecoveryCodesRead(recovery_codes=codes)


@router.post("/me/mfa/disable", status_code=204)
def disable_mfa(
    data: MfaReauth, request: Request, response: Response, current: Current, db: Db
) -> None:
    identity_operation(
        lambda: IdentityService(db).manage(
            current, data.password, data.code, "disable", client_ip(request)
        )
    )
    clear_session_cookie(response)
