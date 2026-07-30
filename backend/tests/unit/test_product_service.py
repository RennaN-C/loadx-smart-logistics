import uuid
from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductUpdate
from app.modules.products.service import (
    ProductCodeAlreadyExistsError,
    ProductNotFoundError,
    ProductService,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Product.__table__])
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=[Product.__table__])


def make_product_create(code: str = "CX-A") -> ProductCreate:
    return ProductCreate(
        code=code,
        name="Caixa A",
        description="Produto de demonstracao",
        width_cm=60,
        height_cm=50,
        length_cm=40,
        weight_kg=Decimal("12.500"),
        fragile=False,
        stackable=True,
        rotation_allowed=True,
    )


def test_create_product_persists_normalized_code(db_session: Session) -> None:
    service = ProductService(db_session)

    product = service.create_product(make_product_create("cx-a"))

    assert product.id is not None
    assert product.code == "CX-A"
    assert product.stackable is True
    assert product.rotation_allowed is True


def test_create_product_rejects_duplicate_code(db_session: Session) -> None:
    service = ProductService(db_session)
    service.create_product(make_product_create("CX-A"))

    with pytest.raises(ProductCodeAlreadyExistsError):
        service.create_product(make_product_create("cx-a"))


def test_update_product_rejects_duplicate_code(db_session: Session) -> None:
    service = ProductService(db_session)
    first_product = service.create_product(make_product_create("CX-A"))
    service.create_product(make_product_create("CX-B"))

    with pytest.raises(ProductCodeAlreadyExistsError):
        service.update_product(first_product.id, ProductUpdate(code="CX-B"))


def test_get_product_raises_when_not_found(db_session: Session) -> None:
    service = ProductService(db_session)

    with pytest.raises(ProductNotFoundError):
        service.get_product(uuid.uuid4())
