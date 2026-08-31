import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.modules.load_planning import service as service_module
from app.modules.load_planning.optimizer.engine import (
    LoadPlanVolumeLimitExceededError,
)
from app.modules.load_planning.schemas import TruckComparisonCreate
from app.modules.load_planning.service import (
    InvalidLoadPlanInputError,
    LoadPlanningService,
    LoadPlanOrdersNotFoundError,
    LoadPlanTruckInactiveError,
    LoadPlanTruckNotFoundError,
)


def make_service() -> tuple[LoadPlanningService, Mock]:
    db = Mock(spec=Session)
    service = LoadPlanningService(db)
    service.truck_service = Mock()
    service.order_service = Mock()
    service.product_service = Mock()
    return service, db


def make_truck(truck_id: uuid.UUID, *, active: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id=truck_id,
        active=active,
        internal_width_cm=100,
        internal_height_cm=100,
        internal_length_cm=100,
        max_weight_kg=Decimal("1000.00"),
    )


def make_ready_order(
    order_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    quantity: int = 1,
) -> SimpleNamespace:
    item = SimpleNamespace(
        id=uuid.uuid4(),
        order_id=order_id,
        product_id=product_id,
        quantity=quantity,
        delivery_sequence=1,
    )
    return SimpleNamespace(id=order_id, status="READY", items=[item])


def make_product(product_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=product_id,
        name="Volume tecnico",
        width_cm=10,
        height_cm=10,
        length_cm=10,
        weight_kg=Decimal("1.000"),
        fragile=False,
        stackable=True,
        rotation_allowed=False,
    )


def duplicate_uuid_list() -> list[uuid.UUID]:
    identifier = uuid.uuid4()
    return [identifier, identifier]


@pytest.mark.parametrize(
    ("order_ids", "truck_ids", "field_name"),
    [
        ([uuid.uuid4()], [uuid.uuid4()], "truck_ids"),
        (
            [uuid.uuid4()],
            [uuid.uuid4() for _ in range(11)],
            "truck_ids",
        ),
        (
            [uuid.uuid4()],
            duplicate_uuid_list(),
            "truck_ids",
        ),
        (
            duplicate_uuid_list(),
            [uuid.uuid4(), uuid.uuid4()],
            "order_ids",
        ),
    ],
)
def test_compare_trucks_defensively_rejects_cardinality_and_duplicates(
    order_ids: list[uuid.UUID],
    truck_ids: list[uuid.UUID],
    field_name: str,
) -> None:
    service, _db = make_service()
    data = TruckComparisonCreate.model_construct(
        order_ids=order_ids,
        truck_ids=truck_ids,
    )

    with pytest.raises(InvalidLoadPlanInputError) as exc_info:
        service.compare_trucks(data)

    assert exc_info.value.field_name == field_name
    service.truck_service.get_trucks.assert_not_called()
    service.order_service.get_orders.assert_not_called()


def test_compare_trucks_maps_workload_once_and_preserves_requested_truck_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, db = make_service()
    first_truck_id = uuid.uuid4()
    second_truck_id = uuid.uuid4()
    order_id = uuid.uuid4()
    product_id = uuid.uuid4()
    first_truck = make_truck(first_truck_id)
    second_truck = make_truck(second_truck_id)
    order = make_ready_order(order_id, product_id, quantity=3)
    product = make_product(product_id)
    service.truck_service.get_trucks.return_value = (first_truck, second_truck)
    service.order_service.get_orders.return_value = (order,)
    service.product_service.get_products.return_value = (product,)
    calls: list[tuple[object, object]] = []

    def capture_comparison(candidates: object, workload: object) -> tuple[()]:
        calls.append((candidates, workload))
        return ()

    monkeypatch.setattr(
        service_module,
        "compare_truck_candidates",
        capture_comparison,
    )

    result = service.compare_trucks(
        TruckComparisonCreate(
            order_ids=[order_id],
            truck_ids=[second_truck_id, first_truck_id],
        )
    )

    assert result == ()
    assert len(calls) == 1
    candidates, workload = calls[0]
    assert [candidate.truck_id for candidate in candidates] == [
        second_truck_id,
        first_truck_id,
    ]
    assert len(workload) == 1
    assert workload[0].quantity == 3
    service.truck_service.get_trucks.assert_called_once_with(
        (second_truck_id, first_truck_id)
    )
    service.order_service.get_orders.assert_called_once_with(
        (order_id,),
        for_update=False,
    )
    service.product_service.get_products.assert_called_once_with(
        (product_id,),
        for_update=False,
    )
    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    db.refresh.assert_not_called()
    db.rollback.assert_not_called()


@pytest.mark.parametrize("failure", ["missing", "inactive"])
def test_compare_trucks_fails_the_whole_preflight_for_invalid_trucks(
    failure: str,
) -> None:
    service, _db = make_service()
    first_truck_id = uuid.uuid4()
    second_truck_id = uuid.uuid4()
    order_id = uuid.uuid4()
    first_truck = make_truck(first_truck_id)
    if failure == "missing":
        service.truck_service.get_trucks.return_value = (first_truck,)
        expected_error = LoadPlanTruckNotFoundError
    else:
        service.truck_service.get_trucks.return_value = (
            first_truck,
            make_truck(second_truck_id, active=False),
        )
        expected_error = LoadPlanTruckInactiveError

    with pytest.raises(expected_error):
        service.compare_trucks(
            TruckComparisonCreate(
                order_ids=[order_id],
                truck_ids=[first_truck_id, second_truck_id],
            )
        )

    service.order_service.get_orders.assert_not_called()
    service.product_service.get_products.assert_not_called()


def test_compare_trucks_fails_the_whole_preflight_for_missing_order() -> None:
    service, _db = make_service()
    truck_ids = [uuid.uuid4(), uuid.uuid4()]
    missing_order_id = uuid.uuid4()
    service.truck_service.get_trucks.return_value = tuple(
        make_truck(truck_id) for truck_id in truck_ids
    )
    service.order_service.get_orders.return_value = ()

    with pytest.raises(LoadPlanOrdersNotFoundError):
        service.compare_trucks(
            TruckComparisonCreate(
                order_ids=[missing_order_id],
                truck_ids=truck_ids,
            )
        )

    service.product_service.get_products.assert_not_called()


def test_compare_trucks_rejects_more_than_200_expanded_volumes_before_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _db = make_service()
    truck_ids = [uuid.uuid4(), uuid.uuid4()]
    order_id = uuid.uuid4()
    product_id = uuid.uuid4()
    service.truck_service.get_trucks.return_value = tuple(
        make_truck(truck_id) for truck_id in truck_ids
    )
    service.order_service.get_orders.return_value = (
        make_ready_order(order_id, product_id, quantity=201),
    )
    engine = Mock()
    monkeypatch.setattr(service_module, "compare_truck_candidates", engine)

    with pytest.raises(LoadPlanVolumeLimitExceededError) as exc_info:
        service.compare_trucks(
            TruckComparisonCreate(
                order_ids=[order_id],
                truck_ids=truck_ids,
            )
        )

    assert exc_info.value.volume_count == 201
    service.product_service.get_products.assert_not_called()
    engine.assert_not_called()
