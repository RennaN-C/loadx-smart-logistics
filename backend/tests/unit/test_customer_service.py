import uuid
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.modules.customers.models import Customer
from app.modules.customers.schemas import CustomerCreate, CustomerUpdate
from app.modules.customers.service import (
    CustomerDocumentAlreadyExistsError,
    CustomerNotFoundError,
    CustomerService,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Customer.__table__])
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=[Customer.__table__])


def make_customer_create(document: str = "00000000000191") -> CustomerCreate:
    return CustomerCreate(
        name="Cliente Demonstracao",
        document=document,
        phone="5500000000000",
        address="Rua Exemplo, 100",
        city="Sao Paulo",
        state="sp",
        notes="Cliente ficticio para testes",
    )


def test_create_customer_persists_normalized_state(db_session: Session) -> None:
    service = CustomerService(db_session)

    customer = service.create_customer(make_customer_create())

    assert customer.id is not None
    assert customer.document == "00000000000191"
    assert customer.state == "SP"


def test_create_customer_rejects_duplicate_document(db_session: Session) -> None:
    service = CustomerService(db_session)
    service.create_customer(make_customer_create("00000000000191"))

    with pytest.raises(CustomerDocumentAlreadyExistsError):
        service.create_customer(make_customer_create("00000000000191"))


def test_update_customer_rejects_duplicate_document(db_session: Session) -> None:
    service = CustomerService(db_session)
    first_customer = service.create_customer(make_customer_create("00000000000191"))
    service.create_customer(make_customer_create("00000000000272"))

    with pytest.raises(CustomerDocumentAlreadyExistsError):
        service.update_customer(first_customer.id, CustomerUpdate(document="00000000000272"))


def test_get_customer_raises_when_not_found(db_session: Session) -> None:
    service = CustomerService(db_session)

    with pytest.raises(CustomerNotFoundError):
        service.get_customer(uuid.uuid4())
