import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.modules.auth.models import AuthSession
from app.modules.auth.sessions import AuthSessionService
from app.modules.drivers.models import Driver
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.users.service import (
    UserDriverAlreadyLinkedError,
    UserDriverNotFoundError,
    UserDriverRoleRequiredError,
    UserEmailAlreadyExistsError,
    UserLastActiveAdminRequiredError,
    UserNotFoundError,
    UserService,
)

SQLITE_TABLES = (Driver.__table__, User.__table__, AuthSession.__table__)


def make_user_create(
    email: str = "ADMIN@EXAMPLE.TEST",
    password: str = "senha-local-segura",
    role: str = "admin",
    active: bool = True,
    driver_id: uuid.UUID | None = None,
) -> UserCreate:
    return UserCreate(
        name="Admin Local",
        email=email,
        password=password,
        role=role,
        active=active,
        driver_id=driver_id,
    )


def make_driver() -> Driver:
    return Driver(
        name="Motorista Teste",
        document="00000000000",
        phone="+5500000000000",
        license_number="CNH-TESTE",
        license_category="D",
        active=True,
    )


def test_create_user_persists_normalized_fields_and_password_hash(
    db_session: Session,
) -> None:
    service = UserService(db_session)

    user = service.create_user(make_user_create())

    assert user.id is not None
    assert user.email == "admin@example.test"
    assert user.role == "ADMIN"
    assert user.password_hash != "senha-local-segura"
    assert verify_password("senha-local-segura", user.password_hash) is True


def test_create_user_rejects_duplicate_email(db_session: Session) -> None:
    service = UserService(db_session)
    service.create_user(make_user_create("admin@example.test"))

    with pytest.raises(UserEmailAlreadyExistsError):
        service.create_user(make_user_create("ADMIN@EXAMPLE.TEST"))


def test_create_driver_user_persists_unique_driver_link(db_session: Session) -> None:
    driver = make_driver()
    db_session.add(driver)
    db_session.commit()
    service = UserService(db_session)

    user = service.create_user(
        make_user_create(
            email="driver@example.test",
            role="DRIVER",
            driver_id=driver.id,
        )
    )

    assert user.driver_id == driver.id


def test_create_user_rejects_driver_link_for_non_driver_role(
    db_session: Session,
) -> None:
    driver = make_driver()
    db_session.add(driver)
    db_session.commit()

    with pytest.raises(UserDriverRoleRequiredError):
        UserService(db_session).create_user(
            make_user_create(driver_id=driver.id),
        )


def test_create_user_rejects_missing_driver_link(db_session: Session) -> None:
    with pytest.raises(UserDriverNotFoundError):
        UserService(db_session).create_user(
            make_user_create(
                email="driver@example.test",
                role="DRIVER",
                driver_id=uuid.uuid4(),
            )
        )


def test_create_user_rejects_driver_linked_to_another_user(
    db_session: Session,
) -> None:
    driver = make_driver()
    db_session.add(driver)
    db_session.commit()
    service = UserService(db_session)
    service.create_user(
        make_user_create(
            email="first-driver@example.test",
            role="DRIVER",
            driver_id=driver.id,
        )
    )

    with pytest.raises(UserDriverAlreadyLinkedError):
        service.create_user(
            make_user_create(
                email="second-driver@example.test",
                role="DRIVER",
                driver_id=driver.id,
            )
        )


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
    assert verify_password("senha-local-segura", updated_user.password_hash) is False


@pytest.mark.parametrize(
    "update",
    [
        UserUpdate(password="nova-senha-local"),
        UserUpdate(active=False),
        UserUpdate(role="CHECKER"),
    ],
)
def test_sensitive_user_update_revokes_all_sessions_atomically(
    db_session: Session,
    update: UserUpdate,
) -> None:
    service = UserService(db_session)
    user = service.create_user(make_user_create())
    if update.active is False or update.role == "CHECKER":
        service.create_user(make_user_create("second-admin@example.test"))
    session_service = AuthSessionService(db_session)
    first = session_service.create_session(user.id)
    second = session_service.create_session(user.id)

    service.update_user(user.id, update)

    db_session.refresh(first.auth_session)
    db_session.refresh(second.auth_session)
    assert first.auth_session.revoked_at is not None
    assert second.auth_session.revoked_at is not None


def test_update_driver_link_revokes_sessions_and_allows_explicit_unlink(
    db_session: Session,
) -> None:
    driver = make_driver()
    db_session.add(driver)
    db_session.commit()
    service = UserService(db_session)
    user = service.create_user(
        make_user_create(email="driver@example.test", role="DRIVER")
    )
    issued = AuthSessionService(db_session).create_session(user.id)

    linked = service.update_user(user.id, UserUpdate(driver_id=driver.id))

    assert linked.driver_id == driver.id
    db_session.refresh(issued.auth_session)
    assert issued.auth_session.revoked_at is not None

    unlinked = service.update_user(user.id, UserUpdate(driver_id=None))
    assert unlinked.driver_id is None


def test_update_role_requires_clearing_existing_driver_link(
    db_session: Session,
) -> None:
    driver = make_driver()
    db_session.add(driver)
    db_session.commit()
    service = UserService(db_session)
    user = service.create_user(
        make_user_create(
            email="driver@example.test",
            role="DRIVER",
            driver_id=driver.id,
        )
    )

    with pytest.raises(UserDriverRoleRequiredError):
        service.update_user(user.id, UserUpdate(role="CHECKER"))

    updated = service.update_user(
        user.id,
        UserUpdate(role="CHECKER", driver_id=None),
    )
    assert updated.role == "CHECKER"
    assert updated.driver_id is None


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
