import uuid
from collections.abc import Callable
from typing import Any
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.integrity import get_integrity_constraint_name
from app.modules.customers.service import (
    CustomerDocumentAlreadyExistsError,
    CustomerService,
)
from app.modules.drivers.service import (
    DriverDocumentAlreadyExistsError,
    DriverLicenseNumberAlreadyExistsError,
    DriverService,
)
from app.modules.orders.service import (
    OrderCustomerNotFoundError,
    OrderItemsReferencedByLoadPlanError,
    OrderProductNotFoundError,
    OrderService,
)
from app.modules.products.service import ProductCodeAlreadyExistsError, ProductService
from app.modules.status_history.service import (
    StatusHistoryChangedByNotFoundError,
    StatusHistoryService,
)
from app.modules.trucks.service import TruckPlateAlreadyExistsError, TruckService
from app.modules.users.service import (
    UserDriverAlreadyLinkedError,
    UserDriverNotFoundError,
    UserEmailAlreadyExistsError,
    UserService,
)


class FakeDiagnostics:
    def __init__(self, constraint_name: str | None) -> None:
        self.constraint_name = constraint_name


class FakeDatabaseError(Exception):
    def __init__(self, constraint_name: str | None) -> None:
        self.diag = FakeDiagnostics(constraint_name)


def make_integrity_error(constraint_name: str | None) -> IntegrityError:
    return IntegrityError(
        "test statement",
        {},
        FakeDatabaseError(constraint_name),
    )


def raising_operation(error: IntegrityError) -> Callable[[], Any]:
    def operation() -> Any:
        raise error

    return operation


def call_persist(service: Any, error: IntegrityError) -> Any:
    if isinstance(service, OrderService):
        return service._persist(raising_operation(error), product_ids=[])
    return service._persist(raising_operation(error))


def test_get_integrity_constraint_name_reads_psycopg_diagnostics() -> None:
    error = make_integrity_error("uq_users__email")

    assert get_integrity_constraint_name(error) == "uq_users__email"


def test_get_integrity_constraint_name_returns_none_without_named_constraint() -> None:
    error = make_integrity_error(None)

    assert get_integrity_constraint_name(error) is None


@pytest.mark.parametrize(
    ("service_factory", "constraint_name", "expected_error"),
    [
        (UserService, "uq_users__email", UserEmailAlreadyExistsError),
        (UserService, "uq_users__driver_id", UserDriverAlreadyLinkedError),
        (UserService, "fk_users__drivers", UserDriverNotFoundError),
        (
            CustomerService,
            "uq_customers__document",
            CustomerDocumentAlreadyExistsError,
        ),
        (
            DriverService,
            "uq_drivers__document",
            DriverDocumentAlreadyExistsError,
        ),
        (
            DriverService,
            "uq_drivers__license_number",
            DriverLicenseNumberAlreadyExistsError,
        ),
        (ProductService, "uq_products__code", ProductCodeAlreadyExistsError),
        (TruckService, "uq_trucks__plate", TruckPlateAlreadyExistsError),
        (OrderService, "fk_orders__customers", OrderCustomerNotFoundError),
        (
            OrderService,
            "fk_load_plan_items__order_items",
            OrderItemsReferencedByLoadPlanError,
        ),
        (
            OrderService,
            "fk_load_plan_items__order_item_provenance",
            OrderItemsReferencedByLoadPlanError,
        ),
        (
            StatusHistoryService,
            "fk_status_history__users",
            StatusHistoryChangedByNotFoundError,
        ),
    ],
)
def test_service_maps_only_known_constraint(
    service_factory: Callable[[Session], Any],
    constraint_name: str,
    expected_error: type[Exception],
) -> None:
    db = Mock(spec=Session)
    service = service_factory(db)

    with pytest.raises(expected_error):
        call_persist(service, make_integrity_error(constraint_name))

    db.rollback.assert_called_once_with()


def test_order_service_maps_product_fk_with_affected_ids() -> None:
    db = Mock(spec=Session)
    service = OrderService(db)
    product_ids = [uuid.uuid4(), uuid.uuid4()]
    error = make_integrity_error("fk_order_items__products")

    with pytest.raises(OrderProductNotFoundError) as exc_info:
        service._persist(raising_operation(error), product_ids=product_ids)

    assert exc_info.value.product_ids == product_ids
    db.rollback.assert_called_once_with()


@pytest.mark.parametrize(
    "service_factory",
    [
        UserService,
        CustomerService,
        DriverService,
        ProductService,
        TruckService,
        OrderService,
        StatusHistoryService,
    ],
)
def test_service_reraises_unknown_integrity_error(
    service_factory: Callable[[Session], Any],
) -> None:
    db = Mock(spec=Session)
    service = service_factory(db)
    error = make_integrity_error("ck_unrelated__rule")

    with pytest.raises(IntegrityError) as exc_info:
        call_persist(service, error)

    assert exc_info.value is error
    db.rollback.assert_called_once_with()
