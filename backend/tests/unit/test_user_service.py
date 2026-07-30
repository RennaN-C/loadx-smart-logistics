import uuid
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import verify_password
from app.database.base import Base
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.users.service import (
    UserEmailAlreadyExistsError,
    UserNotFoundError,
    UserService,
)


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


def make_user_create(email: str = "ADMIN@EXAMPLE.TEST", password: str = "senha-local") -> UserCreate:
    return UserCreate(
        name="Admin Local",
        email=email,
        password=password,
        role="admin",
    )


def test_create_user_persists_normalized_fields_and_password_hash(db_session: Session) -> None:
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


def test_get_user_raises_when_not_found(db_session: Session) -> None:
    service = UserService(db_session)

    with pytest.raises(UserNotFoundError):
        service.get_user(uuid.uuid4())
