import uuid
from collections.abc import Callable, Iterable

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.auth.dependencies import CSRF_HEADER_NAME
from app.modules.auth.models import AuthSession
from app.modules.auth.sessions import AuthSessionService
from app.modules.organizations.models import OrganizationMembership
from app.modules.organizations.repository import OrganizationMembershipRepository
from app.modules.users.models import User

SessionFactory = Callable[[], Session]


def delete_fixture_organization_context(
    db: Session, user_ids: Iterable[uuid.UUID]
) -> None:
    """Remove fixture session references before memberships and their users."""
    identities = tuple(user_ids)
    db.execute(delete(AuthSession).where(AuthSession.user_id.in_(identities)))
    db.execute(
        delete(OrganizationMembership).where(
            OrganizationMembership.user_id.in_(identities)
        )
    )


def issue_session_headers(
    session_factory: SessionFactory,
    user_id: uuid.UUID,
) -> dict[str, str]:
    db = session_factory()
    try:
        # Raw fixture users need the same legacy membership as migrated users.
        # Production session issuance never creates or repairs a membership.
        user = db.get(User, user_id)
        memberships = OrganizationMembershipRepository(db)
        if user is not None and not memberships.has_membership_for_user(user_id):
            memberships.sync_legacy_membership(user)
        issued = AuthSessionService(db).create_session(user_id)
    finally:
        db.close()
    return {
        "Cookie": f"{settings.session_cookie_name}={issued.token}",
        CSRF_HEADER_NAME: issued.csrf_token,
    }
