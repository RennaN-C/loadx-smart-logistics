import uuid
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.modules.status_history.models import StatusHistory
from app.modules.status_history.schemas import StatusHistoryCreate
from app.modules.status_history.service import (
    StatusHistoryChangedByNotFoundError,
    StatusHistoryNotFoundError,
    StatusHistoryService,
)
from app.modules.users.models import User


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [User.__table__, StatusHistory.__table__]
    Base.metadata.create_all(engine, tables=tables)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=list(reversed(tables)))


def create_user(db: Session) -> User:
    user = User(
        name="Admin Local",
        email="admin@example.test",
        password_hash="hash-ficticio",
        role="ADMIN",
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_status_history_create(
    entity_id: uuid.UUID | None = None,
    changed_by: uuid.UUID | None = None,
) -> StatusHistoryCreate:
    return StatusHistoryCreate(
        entity_type="order",
        entity_id=entity_id or uuid.uuid4(),
        old_status="draft",
        new_status="ready",
        changed_by=changed_by,
    )


def test_record_status_change_persists_normalized_values(db_session: Session) -> None:
    user = create_user(db_session)
    service = StatusHistoryService(db_session)

    status_history = service.record_status_change(make_status_history_create(changed_by=user.id))

    assert status_history.id is not None
    assert status_history.entity_type == "ORDER"
    assert status_history.old_status == "DRAFT"
    assert status_history.new_status == "READY"
    assert status_history.changed_by == user.id


def test_record_status_change_allows_system_event_without_changed_by(db_session: Session) -> None:
    service = StatusHistoryService(db_session)

    status_history = service.record_status_change(make_status_history_create(changed_by=None))

    assert status_history.changed_by is None


def test_record_status_change_rejects_missing_changed_by_user(db_session: Session) -> None:
    service = StatusHistoryService(db_session)

    with pytest.raises(StatusHistoryChangedByNotFoundError):
        service.record_status_change(make_status_history_create(changed_by=uuid.uuid4()))


def test_list_status_history_filters_by_entity(db_session: Session) -> None:
    service = StatusHistoryService(db_session)
    expected_entity_id = uuid.uuid4()
    service.record_status_change(make_status_history_create(entity_id=expected_entity_id))
    service.record_status_change(make_status_history_create(entity_id=uuid.uuid4()))

    records = service.list_status_history("order", expected_entity_id)

    assert len(records) == 1
    assert records[0].entity_type == "ORDER"
    assert records[0].entity_id == expected_entity_id


def test_get_status_history_raises_when_not_found(db_session: Session) -> None:
    service = StatusHistoryService(db_session)

    with pytest.raises(StatusHistoryNotFoundError):
        service.get_status_history(uuid.uuid4())
