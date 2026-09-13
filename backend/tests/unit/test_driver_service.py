import uuid

import pytest
from sqlalchemy.orm import Session

from app.modules.drivers.models import Driver
from app.modules.drivers.schemas import DriverCreate, DriverUpdate
from app.modules.drivers.service import (
    DriverDocumentAlreadyExistsError,
    DriverLicenseNumberAlreadyExistsError,
    DriverNotFoundError,
    DriverService,
)

SQLITE_TABLES = (Driver.__table__,)


def make_driver_create(
    document: str = "12345678909",
    license_number: str = "12345678900",
) -> DriverCreate:
    return DriverCreate(
        name="Motorista Demonstracao",
        document=document,
        phone="11900000000",
        license_number=license_number,
        license_category="d",
    )


def test_create_driver_persists_normalized_license_category(
    db_session: Session,
) -> None:
    service = DriverService(db_session)

    driver = service.create_driver(make_driver_create())

    assert driver.id is not None
    assert driver.document == "12345678909"
    assert driver.license_category == "D"
    assert driver.active is True


def test_create_driver_rejects_duplicate_document(db_session: Session) -> None:
    service = DriverService(db_session)

    service.create_driver(
        make_driver_create(
            document="12345678909",
            license_number="12345678900",
        )
    )

    with pytest.raises(DriverDocumentAlreadyExistsError):
        service.create_driver(
            make_driver_create(
                document="12345678909",
                license_number="98765432109",
            )
        )


def test_create_driver_rejects_duplicate_license_number(
    db_session: Session,
) -> None:
    service = DriverService(db_session)

    service.create_driver(
        make_driver_create(
            document="12345678909",
            license_number="12345678900",
        )
    )

    with pytest.raises(DriverLicenseNumberAlreadyExistsError):
        service.create_driver(
            make_driver_create(
                document="98765432100",
                license_number="12345678900",
            )
        )


def test_update_driver_rejects_duplicate_document(db_session: Session) -> None:
    service = DriverService(db_session)

    first_driver = service.create_driver(
        make_driver_create(
            document="12345678909",
            license_number="12345678900",
        )
    )

    service.create_driver(
        make_driver_create(
            document="98765432100",
            license_number="98765432109",
        )
    )

    with pytest.raises(DriverDocumentAlreadyExistsError):
        service.update_driver(
            first_driver.id,
            DriverUpdate(document="98765432100"),
        )


def test_update_driver_rejects_duplicate_license_number(
    db_session: Session,
) -> None:
    service = DriverService(db_session)

    first_driver = service.create_driver(
        make_driver_create(
            document="12345678909",
            license_number="12345678900",
        )
    )

    service.create_driver(
        make_driver_create(
            document="98765432100",
            license_number="98765432109",
        )
    )

    with pytest.raises(DriverLicenseNumberAlreadyExistsError):
        service.update_driver(
            first_driver.id,
            DriverUpdate(license_number="98765432109"),
        )


def test_get_driver_raises_when_not_found(db_session: Session) -> None:
    service = DriverService(db_session)

    with pytest.raises(DriverNotFoundError):
        service.get_driver(uuid.uuid4())
