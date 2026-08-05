import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.users.service import (
    UserEmailAlreadyExistsError,
    UserLastActiveAdminRequiredError,
    UserNotFoundError,
    UserService,
)

SQLITE_TABLES = (User.__table__,)


def make_user_create(
    email: str = "ADMIN@EXAMPLE.TEST",
    password: str = "senha-local",
    role: str = "admin",
    active: bool = True,
) -> UserCreate:
    return UserCreate(
        name="Admin Local",
        email=email,
        password=password,
        role=role,
        active=active,
    )


def test_create_user_persists_normalized_fields_and_password_hash(
    db_session: Session,
) -> None:
    service = UserService(db_session)

    user = service.create_user(make_user_create())

    assert user.id is not None
    assert user.email == "admin@example.test"
    assert user.role == "ADMIN"
    assert user.password_hash != "senha-local"
    assert verify_password("senha-local", user.password_hash) is True


def test_create_user_rejects_duplicate_email(db_session: Session) -> None:
    service = UserService(db_session)
    service.create_user(make_user_create("admin@example.test"))

    with pytest.raises(UserEmailAlreadyExistsError):
        service.create_user(make_user_create("ADMIN@EXAMPLE.TEST"))


def test_update_user_rejects_duplicate_email(db_session: Session) -> None:
    service = UserService(db_session)
    first_user = service.create_user(make_user_create("admin@example.test"))
    service.create_user(make_user_create("manager@example.test"))

    with pytest.raises(UserEmailAlreadyExistsError):
        service.update_user(first_user.id, UserUpdate(email="MANAGER@EXAMPLE.TEST"))


def test_update_user_changes_password_hash(db_session: Session) -> None:
    service = UserService(db_session)
    user = service.create_user(make_user_create())
    original_hash = user.password_hash

    updated_user = service.update_user(user.id, UserUpdate(password="nova-senha-local"))

    assert updated_user.password_hash != original_hash
    assert verify_password("nova-senha-local", updated_user.password_hash) is True
    assert verify_password("senha-local", updated_user.password_hash) is False


@pytest.mark.parametrize(
    "update",
    [UserUpdate(active=False), UserUpdate(role="CHECKER")],
)
def test_update_user_rejects_removing_last_active_admin(
    db_session: Session,
    update: UserUpdate,
) -> None:
    service = UserService(db_session)
    admin = service.create_user(make_user_create())

    with pytest.raises(UserLastActiveAdminRequiredError):
        service.update_user(admin.id, update)

    unchanged_admin = service.get_user(admin.id)
    assert unchanged_admin.role == "ADMIN"
    assert unchanged_admin.active is True


def test_update_user_ignores_inactive_admin_when_protecting_last_active_admin(
    db_session: Session,
) -> None:
    service = UserService(db_session)
    active_admin = service.create_user(make_user_create())
    service.create_user(make_user_create("inactive@example.test", active=False))

    with pytest.raises(UserLastActiveAdminRequiredError):
        service.update_user(active_admin.id, UserUpdate(active=False))


def test_update_user_allows_removing_admin_when_another_active_admin_exists(
    db_session: Session,
) -> None:
    service = UserService(db_session)
    first_admin = service.create_user(make_user_create())
    service.create_user(make_user_create("second-admin@example.test"))

    updated_user = service.update_user(
        first_admin.id,
        UserUpdate(role="CHECKER", active=False),
    )

    assert updated_user.role == "CHECKER"
    assert updated_user.active is False


def test_get_user_raises_when_not_found(db_session: Session) -> None:
    service = UserService(db_session)

    with pytest.raises(UserNotFoundError):
        service.get_user(uuid.uuid4())
