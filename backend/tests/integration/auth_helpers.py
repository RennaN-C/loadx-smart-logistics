import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.auth.dependencies import CSRF_HEADER_NAME
from app.modules.auth.sessions import AuthSessionService

SessionFactory = Callable[[], Session]


def issue_session_headers(
    session_factory: SessionFactory,
    user_id: uuid.UUID,
) -> dict[str, str]:
    db = session_factory()
    try:
        issued = AuthSessionService(db).create_session(user_id)
    finally:
        db.close()
    return {
        "Cookie": f"{settings.session_cookie_name}={issued.token}",
        CSRF_HEADER_NAME: issued.csrf_token,
    }
