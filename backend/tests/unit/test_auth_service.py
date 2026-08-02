from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import verify_password
from app.database.base import Base
from app.modules.auth.schemas import AuthLogin
from app.modules.auth.service import (
    AuthBootstrapAlreadyCompletedError,
    AuthInactiveUserError,
    AuthInvalidCredentialsError,
    AuthInvalidTokenError,
    AuthService,
)
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.users.service import UserService


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__])
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=[User.__table__])


def make_user_create(
    active: bool = True,
    email: str = "admin@example.test",
) -> UserCreate:
    return UserCreate(
        name="Admin Local",
        email=email,
        password="senha-local",
        role="ADMIN",
        active=active,
    )


def test_login_returns_bearer_token_for_active_user(db_session: Session) -> None:
    UserService(db_session).create_user(make_user_create())
    service = AuthService(db_session)

    token = service.login(AuthLogin(email="ADMIN@EXAMPLE.TEST", password="senha-local"))

    assert token.access_token
    assert token.token_type == "bearer"


def test_bootstrap_first_admin_creates_fixed_active_admin(
    db_session: Session,
) -> None:
    service = AuthService(db_session)

    user = service.bootstrap_first_admin(
        name="Admin Inicial",
        email="ADMIN@EXAMPLE.TEST",
        password="senha-local",
    )

    assert user.email == "admin@example.test"
    assert user.role == "ADMIN"
    assert user.active is True
    assert user.password_hash != "senha-local"
    assert verify_password("senha-local", user.password_hash) is True


def test_bootstrap_first_admin_rejects_database_with_any_user(
    db_session: Session,
) -> None:
    UserService(db_session).create_user(make_user_create())
    service = AuthService(db_session)

    with pytest.raises(AuthBootstrapAlreadyCompletedError):
        service.bootstrap_first_admin(
            name="Outro Admin",
            email="outro-admin@example.test",
            password="senha-local",
        )

    assert len(service.user_service.list_users()) == 1


def test_login_rejects_invalid_password(db_session: Session) -> None:
    UserService(db_session).create_user(make_user_create())
    service = AuthService(db_session)

    with pytest.raises(AuthInvalidCredentialsError):
        service.login(AuthLogin(email="admin@example.test", password="senha-errada"))


def test_login_rejects_inactive_user(db_session: Session) -> None:
    UserService(db_session).create_user(make_user_create(active=False))
    service = AuthService(db_session)

    with pytest.raises(AuthInactiveUserError):
        service.login(AuthLogin(email="admin@example.test", password="senha-local"))


def test_get_current_user_from_token_returns_user(db_session: Session) -> None:
    user = UserService(db_session).create_user(make_user_create())
    service = AuthService(db_session)
    token = service.login(AuthLogin(email="admin@example.test", password="senha-local"))

    current_user = service.get_current_user_from_token(token.access_token)

    assert current_user.id == user.id


def test_get_current_user_from_token_rejects_invalid_token(db_session: Session) -> None:
    service = AuthService(db_session)

    with pytest.raises(AuthInvalidTokenError):
        service.get_current_user_from_token("invalid-token")


def test_get_current_user_from_token_rejects_inactive_user(db_session: Session) -> None:
    user_service = UserService(db_session)
    user = user_service.create_user(make_user_create())
    service = AuthService(db_session)
    token = service.login(AuthLogin(email="admin@example.test", password="senha-local"))
    user_service.create_user(make_user_create(email="second-admin@example.test"))
    user_service.update_user(user.id, UserUpdate(active=False))

    with pytest.raises(AuthInactiveUserError):
        service.get_current_user_from_token(token.access_token)


def test_get_current_user_from_token_uses_current_database_role(
    db_session: Session,
) -> None:
    user_service = UserService(db_session)
    user = user_service.create_user(make_user_create())
    service = AuthService(db_session)
    token = service.login(AuthLogin(email="admin@example.test", password="senha-local"))
    user_service.create_user(make_user_create(email="second-admin@example.test"))
    user_service.update_user(user.id, UserUpdate(role="CHECKER"))

    current_user = service.get_current_user_from_token(token.access_token)

    assert current_user.role == "CHECKER"
