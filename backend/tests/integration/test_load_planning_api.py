import uuid
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.customers.models import Customer
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.products.service import ProductService
from app.modules.status_history.models import StatusHistory
from app.modules.status_history.schemas import StatusHistoryCreate
from app.modules.status_history.service import StatusHistoryService
from app.modules.trucks.models import Truck
from app.modules.users.models import User
from tests.integration.auth_helpers import issue_session_headers

SessionFactory = Callable[[], Session]


@dataclass(frozen=True)
class AuthenticatedUser:
    id: uuid.UUID
    headers: dict[str, str]


@dataclass(frozen=True)
class PlanningScenario:
    truck_id: uuid.UUID
    truck_plate: str
    product_id: uuid.UUID
    product_code: str
    order_id: uuid.UUID
    order_item_id: uuid.UUID


def create_authenticated_user(
    session_factory: SessionFactory,
    role: str,
) -> AuthenticatedUser:
    user_id = uuid.uuid4()
    db = session_factory()
    try:
        db.add(
            User(
                id=user_id,
                name=f"Usuario {role}",
                email=f"{role.lower()}-{uuid.uuid4().hex}@example.test",
                password_hash="not-used-by-token-authentication",
                role=role,
                active=True,
            )
        )
        db.commit()
    finally:
        db.close()

    return AuthenticatedUser(
        id=user_id,
        headers=issue_session_headers(session_factory, user_id),
    )


@pytest.fixture
def manager(session_factory: SessionFactory) -> AuthenticatedUser:
    return create_authenticated_user(session_factory, "LOGISTICS_MANAGER")


def seed_planning_scenario(
    session_factory: SessionFactory,
    *,
    order_status: str = "READY",
    quantity: int = 1,
    delivery_sequence: int = 1,
    truck_width_cm: int = 20,
    truck_height_cm: int = 10,
    truck_length_cm: int = 10,
    truck_max_weight_kg: Decimal = Decimal("100.00"),
    truck_active: bool = True,
    product_width_cm: int = 10,
    product_height_cm: int = 10,
    product_length_cm: int = 10,
    product_weight_kg: Decimal = Decimal("1.000"),
    rotation_allowed: bool = False,
) -> PlanningScenario:
    customer_id = uuid.uuid4()
    product_id = uuid.uuid4()
    truck_id = uuid.uuid4()
    order_id = uuid.uuid4()
    order_item_id = uuid.uuid4()
    unique_suffix = uuid.uuid4().hex[:8].upper()
    truck_plate = f"T{unique_suffix[:6]}"
    product_code = f"P-{unique_suffix}"

    db = session_factory()
    try:
        db.add_all(
            [
                Customer(
                    id=customer_id,
                    name="Cliente de Planejamento",
                    document=uuid.uuid4().hex,
                    phone="5500000000000",
                    address="Rua Exemplo, 100",
                    city="Sao Paulo",
                    state="SP",
                    notes="Dados ficticios para teste",
                ),
                Product(
                    id=product_id,
                    code=product_code,
                    name="Produto Original",
                    description="Produto ficticio para planejamento",
                    width_cm=product_width_cm,
                    height_cm=product_height_cm,
                    length_cm=product_length_cm,
                    weight_kg=product_weight_kg,
                    fragile=False,
                    stackable=True,
                    rotation_allowed=rotation_allowed,
                ),
                Truck(
                    id=truck_id,
                    plate=truck_plate,
                    model="Bau Original",
                    internal_width_cm=truck_width_cm,
                    internal_height_cm=truck_height_cm,
                    internal_length_cm=truck_length_cm,
                    max_weight_kg=truck_max_weight_kg,
                    active=truck_active,
                ),
                Order(
                    id=order_id,
                    customer_id=customer_id,
                    status=order_status,
                    priority="NORMAL",
                    delivery_address="Rua Exemplo, 100",
                    expected_delivery_at=None,
                    items=[
                        OrderItem(
                            id=order_item_id,
                            product_id=product_id,
                            quantity=quantity,
                            delivery_sequence=delivery_sequence,
                        )
                    ],
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    return PlanningScenario(
        truck_id=truck_id,
        truck_plate=truck_plate,
        product_id=product_id,
        product_code=product_code,
        order_id=order_id,
        order_item_id=order_item_id,
    )


def seed_additional_order(
    session_factory: SessionFactory,
    scenario: PlanningScenario,
    *,
    delivery_sequence: int,
) -> tuple[uuid.UUID, uuid.UUID]:
    order_id = uuid.uuid4()
    order_item_id = uuid.uuid4()
    db = session_factory()
    try:
        source_order = db.get(Order, scenario.order_id)
        assert source_order is not None
        db.add(
            Order(
                id=order_id,
                customer_id=source_order.customer_id,
                status="READY",
                priority="NORMAL",
                delivery_address="Rua Exemplo, 200",
                expected_delivery_at=None,
                items=[
                    OrderItem(
                        id=order_item_id,
                        product_id=scenario.product_id,
                        quantity=1,
                        delivery_sequence=delivery_sequence,
                    )
                ],
            )
        )
        db.commit()
    finally:
        db.close()
    return order_id, order_item_id


def create_load_plan(
    client: TestClient,
    scenario: PlanningScenario,
    manager: AuthenticatedUser,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/load-plans",
        json={
            "truck_id": str(scenario.truck_id),
            "order_ids": [str(scenario.order_id)],
        },
        headers=manager.headers,
    )
    assert response.status_code == 201
    return response.json()


def test_create_get_and_visualization_return_persisted_snapshot(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
) -> None:
    scenario = seed_planning_scenario(session_factory)

    created = create_load_plan(client, scenario, manager)

    assert created["status"] == "CALCULATED"
    assert created["truck_id"] == str(scenario.truck_id)
    assert created["order_ids"] == [str(scenario.order_id)]
    assert created["loaded_count"] == 1
    assert created["unloaded_count"] == 0
    assert created["algorithm_version"] == "heuristic-v1"
    assert isinstance(created["occupancy_percent"], (int, float))
    assert not isinstance(created["occupancy_percent"], bool)
    assert isinstance(created["total_weight_kg"], (int, float))
    assert not isinstance(created["total_weight_kg"], bool)
    assert created["items"][0]["order_item_id"] == str(scenario.order_item_id)
    assert isinstance(created["items"][0]["weight_kg"], (int, float))
    assert not isinstance(created["items"][0]["weight_kg"], bool)
    assert created["items"][0]["placed"] is True
    assert created["items"][0]["loading_sequence"] == 1

    detail_response = client.get(
        f"/api/v1/load-plans/{created['id']}",
        headers=manager.headers,
    )
    visualization_response = client.get(
        f"/api/v1/load-plans/{created['id']}/visualization",
        headers=manager.headers,
    )

    assert detail_response.status_code == 200
    assert detail_response.json() == created
    assert visualization_response.status_code == 200
    visualization = visualization_response.json()
    truck_snapshot = visualization["truck"]
    assert truck_snapshot["id"] == str(scenario.truck_id)
    assert truck_snapshot["plate"] == scenario.truck_plate
    assert truck_snapshot["model"] == "Bau Original"
    assert truck_snapshot["width_cm"] == 20
    assert truck_snapshot["height_cm"] == 10
    assert truck_snapshot["length_cm"] == 10
    assert truck_snapshot["max_weight_kg"] == 100.0
    assert isinstance(truck_snapshot["max_weight_kg"], float)
    assert len(visualization["items"]) == 1
    item_snapshot = visualization["items"][0]
    assert item_snapshot["order_item_id"] == str(scenario.order_item_id)
    assert item_snapshot["product_code"] == scenario.product_code
    assert item_snapshot["product_name"] == "Produto Original"
    assert visualization["unloaded_items"] == []


def test_multiple_orders_preserve_delivery_depth_and_approve_together(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
) -> None:
    earlier = seed_planning_scenario(
        session_factory,
        delivery_sequence=1,
        truck_width_cm=10,
        truck_length_cm=20,
    )
    later_order_id, later_order_item_id = seed_additional_order(
        session_factory,
        earlier,
        delivery_sequence=2,
    )

    response = client.post(
        "/api/v1/load-plans",
        json={
            "truck_id": str(earlier.truck_id),
            "order_ids": [str(later_order_id), str(earlier.order_id)],
        },
        headers=manager.headers,
    )

    assert response.status_code == 201
    created = response.json()
    assert set(created["order_ids"]) == {
        str(earlier.order_id),
        str(later_order_id),
    }
    assert created["loaded_count"] == 2
    assert created["unloaded_count"] == 0
    by_order_item = {item["order_item_id"]: item for item in created["items"]}
    earlier_item = by_order_item[str(earlier.order_item_id)]
    later_item = by_order_item[str(later_order_item_id)]
    assert later_item["z_cm"] < earlier_item["z_cm"]
    assert later_item["loading_sequence"] < earlier_item["loading_sequence"]

    approve_response = client.post(
        f"/api/v1/load-plans/{created['id']}/approve",
        headers=manager.headers,
    )
    assert approve_response.status_code == 200

    db = session_factory()
    try:
        orders = db.scalars(
            select(Order).where(Order.id.in_([earlier.order_id, later_order_id]))
        ).all()
        associations = db.scalars(
            select(LoadPlanOrder).where(
                LoadPlanOrder.load_plan_id == uuid.UUID(created["id"])
            )
        ).all()
        order_histories = db.scalars(
            select(StatusHistory).where(
                StatusHistory.entity_type == "ORDER",
                StatusHistory.entity_id.in_([earlier.order_id, later_order_id]),
                StatusHistory.new_status == "PLANNED",
            )
        ).all()
        assert {order.status for order in orders} == {"PLANNED"}
        assert {association.order_id for association in associations} == {
            earlier.order_id,
            later_order_id,
        }
        assert {history.entity_id for history in order_histories} == {
            earlier.order_id,
            later_order_id,
        }
    finally:
        db.close()


def test_partial_plan_cannot_be_approved(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
) -> None:
    scenario = seed_planning_scenario(
        session_factory,
        quantity=2,
        truck_width_cm=10,
    )
    created = create_load_plan(client, scenario, manager)

    assert created["status"] == "CALCULATED"
    assert created["loaded_count"] == 1
    assert created["unloaded_count"] == 1
    assert [item["placed"] for item in created["items"]] == [True, False]
    assert created["items"][1]["rejection_reason"] == "COLLISION"

    response = client.post(
        f"/api/v1/load-plans/{created['id']}/approve",
        headers=manager.headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "LOAD_PLAN_HAS_REJECTIONS"
    db = session_factory()
    try:
        load_plan = db.get(LoadPlan, uuid.UUID(created["id"]))
        order = db.get(Order, scenario.order_id)
        assert load_plan is not None
        assert order is not None
        assert load_plan.status == "CALCULATED"
        assert order.status == "READY"
    finally:
        db.close()


def test_plan_with_zero_placed_volumes_is_rejected(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
) -> None:
    scenario = seed_planning_scenario(
        session_factory,
        truck_width_cm=10,
        product_width_cm=20,
        product_height_cm=20,
        product_length_cm=20,
    )

    created = create_load_plan(client, scenario, manager)

    assert created["status"] == "REJECTED"
    assert created["loaded_count"] == 0
    assert created["unloaded_count"] == 1
    assert created["used_volume_cm3"] == 0
    assert created["items"][0]["placed"] is False
    assert created["items"][0]["rejection_reason"] == "TRUCK_DIMENSIONS_EXCEEDED"


def test_create_maps_missing_and_inactive_sources(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = seed_planning_scenario(session_factory)

    missing_truck_response = client.post(
        "/api/v1/load-plans",
        json={
            "truck_id": str(uuid.uuid4()),
            "order_ids": [str(valid.order_id)],
        },
        headers=manager.headers,
    )
    missing_order_response = client.post(
        "/api/v1/load-plans",
        json={
            "truck_id": str(valid.truck_id),
            "order_ids": [str(uuid.uuid4())],
        },
        headers=manager.headers,
    )

    inactive = seed_planning_scenario(session_factory, truck_active=False)
    inactive_truck_response = client.post(
        "/api/v1/load-plans",
        json={
            "truck_id": str(inactive.truck_id),
            "order_ids": [str(inactive.order_id)],
        },
        headers=manager.headers,
    )

    def return_no_products(
        _service: ProductService,
        _product_ids: object,
        **_kwargs: object,
    ) -> tuple[Product, ...]:
        return ()

    monkeypatch.setattr(ProductService, "get_products", return_no_products)
    missing_product_response = client.post(
        "/api/v1/load-plans",
        json={
            "truck_id": str(valid.truck_id),
            "order_ids": [str(valid.order_id)],
        },
        headers=manager.headers,
    )

    assert missing_truck_response.status_code == 404
    assert missing_truck_response.json()["code"] == "LOAD_PLAN_TRUCK_NOT_FOUND"
    assert missing_order_response.status_code == 404
    assert missing_order_response.json()["code"] == "LOAD_PLAN_ORDER_NOT_FOUND"
    assert inactive_truck_response.status_code == 409
    assert inactive_truck_response.json()["code"] == "LOAD_PLAN_TRUCK_INACTIVE"
    assert missing_product_response.status_code == 404
    assert missing_product_response.json()["code"] == "LOAD_PLAN_PRODUCT_NOT_FOUND"


def test_create_enforces_eligibility_identity_and_volume_limits(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
) -> None:
    ineligible = seed_planning_scenario(
        session_factory,
        order_status="DRAFT",
    )
    ineligible_response = client.post(
        "/api/v1/load-plans",
        json={
            "truck_id": str(ineligible.truck_id),
            "order_ids": [str(ineligible.order_id)],
        },
        headers=manager.headers,
    )

    assert ineligible_response.status_code == 409
    assert ineligible_response.json()["code"] == "LOAD_PLAN_ORDER_NOT_ELIGIBLE"

    exact_limit = seed_planning_scenario(
        session_factory,
        quantity=200,
        product_width_cm=21,
    )
    exact_limit_response = client.post(
        "/api/v1/load-plans",
        json={
            "truck_id": str(exact_limit.truck_id),
            "order_ids": [str(exact_limit.order_id)],
        },
        headers=manager.headers,
    )

    assert exact_limit_response.status_code == 201
    assert exact_limit_response.json()["status"] == "REJECTED"
    assert exact_limit_response.json()["loaded_count"] == 0
    assert exact_limit_response.json()["unloaded_count"] == 200

    duplicate_response = client.post(
        "/api/v1/load-plans",
        json={
            "truck_id": str(exact_limit.truck_id),
            "order_ids": [
                str(exact_limit.order_id),
                str(exact_limit.order_id),
            ],
        },
        headers=manager.headers,
    )

    assert duplicate_response.status_code == 422
    assert duplicate_response.json()["code"] == "VALIDATION_ERROR"

    over_limit = seed_planning_scenario(session_factory, quantity=201)
    limit_response = client.post(
        "/api/v1/load-plans",
        json={
            "truck_id": str(over_limit.truck_id),
            "order_ids": [str(over_limit.order_id)],
        },
        headers=manager.headers,
    )

    assert limit_response.status_code == 422
    assert limit_response.json()["code"] == "LOAD_PLAN_VOLUME_LIMIT_EXCEEDED"
    assert limit_response.json()["details"] == [
        {
            "field": "order_ids",
            "volume_count": 201,
            "max_volumes": 200,
        }
    ]
    db = session_factory()
    try:
        load_plans = db.scalars(select(LoadPlan)).all()
        assert len(load_plans) == 1
        assert load_plans[0].id == uuid.UUID(exact_limit_response.json()["id"])
    finally:
        db.close()


def test_create_rejects_internal_volume_outside_bigint_range(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
) -> None:
    scenario = seed_planning_scenario(
        session_factory,
        truck_width_cm=2_100_000,
        truck_height_cm=2_100_000,
        truck_length_cm=2_100_000,
    )

    response = client.post(
        "/api/v1/load-plans",
        json={
            "truck_id": str(scenario.truck_id),
            "order_ids": [str(scenario.order_id)],
        },
        headers=manager.headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_LOAD_PLAN_INPUT"
    assert response.json()["details"] == [
        {
            "field": "truck_id",
            "message": "internal volume exceeds the persisted BIGINT range",
        }
    ]

    db = session_factory()
    try:
        assert db.scalars(select(LoadPlan)).all() == []
    finally:
        db.close()


def test_approve_updates_plan_order_and_history_atomically(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
) -> None:
    scenario = seed_planning_scenario(session_factory)
    created = create_load_plan(client, scenario, manager)

    response = client.post(
        f"/api/v1/load-plans/{created['id']}/approve",
        headers=manager.headers,
    )

    assert response.status_code == 200
    approved = response.json()
    assert approved["status"] == "APPROVED"
    assert approved["approved_at"] is not None

    repeated_response = client.post(
        f"/api/v1/load-plans/{created['id']}/approve",
        headers=manager.headers,
    )
    assert repeated_response.status_code == 409
    assert repeated_response.json()["code"] == "LOAD_PLAN_INVALID_STATUS"

    plan_id = uuid.UUID(created["id"])
    db = session_factory()
    try:
        load_plan = db.get(LoadPlan, plan_id)
        order = db.get(Order, scenario.order_id)
        histories = db.scalars(
            select(StatusHistory).where(
                StatusHistory.entity_id.in_([plan_id, scenario.order_id])
            )
        ).all()
        assert load_plan is not None
        assert order is not None
        assert load_plan.status == "APPROVED"
        assert load_plan.approved_at is not None
        assert order.status == "PLANNED"
        assert {
            (
                history.entity_type,
                history.entity_id,
                history.old_status,
                history.new_status,
                history.changed_by,
            )
            for history in histories
        } == {
            ("LOAD_PLAN", plan_id, None, "CALCULATED", manager.id),
            ("LOAD_PLAN", plan_id, "CALCULATED", "APPROVED", manager.id),
            ("ORDER", scenario.order_id, "READY", "PLANNED", manager.id),
        }
    finally:
        db.close()


def test_load_plan_routes_require_authentication(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
) -> None:
    scenario = seed_planning_scenario(session_factory)
    created = create_load_plan(client, scenario, manager)
    detail_path = f"/api/v1/load-plans/{created['id']}"
    cases = (
        (
            "POST",
            "/api/v1/load-plans",
            {
                "truck_id": str(scenario.truck_id),
                "order_ids": [str(scenario.order_id)],
            },
        ),
        ("GET", detail_path, None),
        ("GET", f"{detail_path}/visualization", None),
        ("POST", f"{detail_path}/approve", None),
        ("POST", f"{detail_path}/recalculate", None),
    )

    for method, path, payload in cases:
        request_options: dict[str, object] = {}
        if payload is not None:
            request_options["json"] = payload
        response = client.request(method, path, **request_options)
        assert response.status_code == 401
        assert response.json()["code"] == "AUTH_INVALID_TOKEN"


def test_plan_specific_routes_return_not_found(
    client: TestClient,
    manager: AuthenticatedUser,
) -> None:
    missing_id = uuid.uuid4()
    detail_path = f"/api/v1/load-plans/{missing_id}"

    for method, path in (
        ("GET", detail_path),
        ("GET", f"{detail_path}/visualization"),
        ("POST", f"{detail_path}/approve"),
        ("POST", f"{detail_path}/recalculate"),
    ):
        response = client.request(method, path, headers=manager.headers)
        assert response.status_code == 404
        assert response.json()["code"] == "LOAD_PLAN_NOT_FOUND"


def test_only_manager_can_create_approve_or_recalculate(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
) -> None:
    scenario = seed_planning_scenario(session_factory)
    created = create_load_plan(client, scenario, manager)
    detail_path = f"/api/v1/load-plans/{created['id']}"
    create_payload = {
        "truck_id": str(scenario.truck_id),
        "order_ids": [str(scenario.order_id)],
    }

    for role in ("ADMIN", "CHECKER", "DRIVER"):
        user = create_authenticated_user(session_factory, role)
        create_response = client.post(
            "/api/v1/load-plans",
            json=create_payload,
            headers=user.headers,
        )
        approve_response = client.post(
            f"{detail_path}/approve",
            headers=user.headers,
        )
        recalculate_response = client.post(
            f"{detail_path}/recalculate",
            headers=user.headers,
        )
        for response in (
            create_response,
            approve_response,
            recalculate_response,
        ):
            assert response.status_code == 403
            assert response.json()["code"] == "AUTH_FORBIDDEN"

    db = session_factory()
    try:
        load_plan = db.get(LoadPlan, uuid.UUID(created["id"]))
        order = db.get(Order, scenario.order_id)
        assert load_plan is not None
        assert order is not None
        assert load_plan.status == "CALCULATED"
        assert order.status == "READY"
        assert len(db.scalars(select(LoadPlan)).all()) == 1
    finally:
        db.close()


def test_read_access_follows_plan_status_and_role(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
) -> None:
    scenario = seed_planning_scenario(session_factory)
    created = create_load_plan(client, scenario, manager)
    admin = create_authenticated_user(session_factory, "ADMIN")
    checker = create_authenticated_user(session_factory, "CHECKER")
    driver = create_authenticated_user(session_factory, "DRIVER")
    detail_path = f"/api/v1/load-plans/{created['id']}"
    visualization_path = f"{detail_path}/visualization"

    assert client.get(detail_path, headers=admin.headers).status_code == 200
    assert client.get(visualization_path, headers=admin.headers).status_code == 200
    for path in (detail_path, visualization_path):
        checker_response = client.get(path, headers=checker.headers)
        driver_response = client.get(path, headers=driver.headers)
        assert checker_response.status_code == 403
        assert checker_response.json()["code"] == "AUTH_FORBIDDEN"
        assert driver_response.status_code == 403
        assert driver_response.json()["code"] == "AUTH_FORBIDDEN"

    approve_response = client.post(
        f"{detail_path}/approve",
        headers=manager.headers,
    )
    assert approve_response.status_code == 200

    assert client.get(detail_path, headers=checker.headers).status_code == 200
    assert client.get(visualization_path, headers=checker.headers).status_code == 200
    for path in (detail_path, visualization_path):
        driver_response = client.get(path, headers=driver.headers)
        assert driver_response.status_code == 403
        assert driver_response.json()["code"] == "AUTH_FORBIDDEN"


def test_recalculate_creates_new_snapshot_and_preserves_approved_source(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
) -> None:
    scenario = seed_planning_scenario(session_factory)
    created = create_load_plan(client, scenario, manager)
    approve_response = client.post(
        f"/api/v1/load-plans/{created['id']}/approve",
        headers=manager.headers,
    )
    assert approve_response.status_code == 200
    approved_source = approve_response.json()
    source_visualization_response = client.get(
        f"/api/v1/load-plans/{created['id']}/visualization",
        headers=manager.headers,
    )
    assert source_visualization_response.status_code == 200
    source_visualization = source_visualization_response.json()

    db = session_factory()
    try:
        product = db.get(Product, scenario.product_id)
        truck = db.get(Truck, scenario.truck_id)
        order = db.get(Order, scenario.order_id)
        assert product is not None
        assert truck is not None
        assert order is not None
        assert order.status == "PLANNED"
        product.name = "Produto Recalculado"
        product.width_cm = 5
        truck.model = "Bau Recalculado"
        truck.internal_width_cm = 30
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/api/v1/load-plans/{created['id']}/recalculate",
        headers=manager.headers,
    )

    assert response.status_code == 201
    recalculated = response.json()
    assert recalculated["id"] != created["id"]
    assert recalculated["recalculated_from_id"] == created["id"]
    assert recalculated["status"] == "CALCULATED"
    assert recalculated["internal_volume_cm3"] == 3000
    assert recalculated["used_volume_cm3"] == 500
    assert recalculated["items"][0]["product_name"] == "Produto Recalculado"
    assert recalculated["items"][0]["original_width_cm"] == 5

    recalculated_visualization_response = client.get(
        f"/api/v1/load-plans/{recalculated['id']}/visualization",
        headers=manager.headers,
    )
    source_after_response = client.get(
        f"/api/v1/load-plans/{created['id']}",
        headers=manager.headers,
    )
    source_visualization_after_response = client.get(
        f"/api/v1/load-plans/{created['id']}/visualization",
        headers=manager.headers,
    )

    assert recalculated_visualization_response.status_code == 200
    recalculated_truck = recalculated_visualization_response.json()["truck"]
    assert recalculated_truck["model"] == "Bau Recalculado"
    assert recalculated_truck["width_cm"] == 30
    assert source_after_response.status_code == 200
    assert source_after_response.json() == approved_source
    assert source_visualization_after_response.status_code == 200
    assert source_visualization_after_response.json() == source_visualization

    child_approve_response = client.post(
        f"/api/v1/load-plans/{recalculated['id']}/approve",
        headers=manager.headers,
    )
    assert child_approve_response.status_code == 200
    assert child_approve_response.json()["status"] == "APPROVED"

    db = session_factory()
    try:
        order = db.get(Order, scenario.order_id)
        planned_histories = db.scalars(
            select(StatusHistory).where(
                StatusHistory.entity_type == "ORDER",
                StatusHistory.entity_id == scenario.order_id,
                StatusHistory.new_status == "PLANNED",
            )
        ).all()
        assert order is not None
        assert order.status == "PLANNED"
        assert len(planned_histories) == 1
    finally:
        db.close()


def test_patch_order_items_is_blocked_after_plan_snapshot(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
) -> None:
    scenario = seed_planning_scenario(session_factory)
    created = create_load_plan(client, scenario, manager)

    draft_response = client.patch(
        f"/api/v1/orders/{scenario.order_id}/status",
        json={"status": "DRAFT"},
        headers=manager.headers,
    )
    assert draft_response.status_code == 200

    header_response = client.patch(
        f"/api/v1/orders/{scenario.order_id}",
        json={"priority": "high"},
        headers=manager.headers,
    )
    assert header_response.status_code == 200
    assert header_response.json()["priority"] == "HIGH"
    assert header_response.json()["items"][0]["id"] == str(scenario.order_item_id)

    response = client.patch(
        f"/api/v1/orders/{scenario.order_id}",
        json={
            "items": [
                {
                    "product_id": str(scenario.product_id),
                    "quantity": 2,
                    "delivery_sequence": 1,
                }
            ]
        },
        headers=manager.headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "ORDER_ITEMS_REFERENCED_BY_LOAD_PLAN"
    db = session_factory()
    try:
        order = db.get(Order, scenario.order_id)
        load_plan_item = db.scalar(
            select(LoadPlanItem).where(
                LoadPlanItem.load_plan_id == uuid.UUID(created["id"])
            )
        )
        assert order is not None
        assert len(order.items) == 1
        assert order.items[0].id == scenario.order_item_id
        assert order.items[0].quantity == 1
        assert order.priority == "HIGH"
        assert load_plan_item is not None
        assert load_plan_item.order_item_id == scenario.order_item_id
    finally:
        db.close()


def test_create_rolls_back_plan_when_history_write_fails(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = seed_planning_scenario(session_factory)

    def fail_history(
        _service: StatusHistoryService,
        _data: StatusHistoryCreate,
    ) -> StatusHistory:
        raise RuntimeError("simulated history persistence failure")

    monkeypatch.setattr(
        StatusHistoryService,
        "stage_status_change",
        fail_history,
    )
    response = client.post(
        "/api/v1/load-plans",
        json={
            "truck_id": str(scenario.truck_id),
            "order_ids": [str(scenario.order_id)],
        },
        headers=manager.headers,
    )

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_SERVER_ERROR"
    db = session_factory()
    try:
        assert db.scalars(select(LoadPlan)).all() == []
        assert db.scalars(select(LoadPlanOrder)).all() == []
        assert db.scalars(select(LoadPlanItem)).all() == []
        assert db.scalars(select(StatusHistory)).all() == []
    finally:
        db.close()


def test_recalculate_rolls_back_child_when_history_write_fails(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = seed_planning_scenario(session_factory)
    source = create_load_plan(client, scenario, manager)
    approve_response = client.post(
        f"/api/v1/load-plans/{source['id']}/approve",
        headers=manager.headers,
    )
    assert approve_response.status_code == 200

    db = session_factory()
    try:
        history_count_before = len(db.scalars(select(StatusHistory)).all())
    finally:
        db.close()

    def fail_history(
        _service: StatusHistoryService,
        _data: StatusHistoryCreate,
    ) -> StatusHistory:
        raise RuntimeError("simulated history persistence failure")

    monkeypatch.setattr(
        StatusHistoryService,
        "stage_status_change",
        fail_history,
    )
    response = client.post(
        f"/api/v1/load-plans/{source['id']}/recalculate",
        headers=manager.headers,
    )

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_SERVER_ERROR"
    source_id = uuid.UUID(source["id"])
    db = session_factory()
    try:
        plans = db.scalars(select(LoadPlan)).all()
        persisted_source = db.get(LoadPlan, source_id)
        assert len(plans) == 1
        assert plans[0].id == source_id
        assert persisted_source is not None
        assert persisted_source.status == "APPROVED"
        assert (
            db.scalars(
                select(LoadPlan).where(LoadPlan.recalculated_from_id == source_id)
            ).all()
            == []
        )
        assert len(db.scalars(select(StatusHistory)).all()) == history_count_before
    finally:
        db.close()


def test_approve_rolls_back_all_changes_when_history_write_fails(
    client: TestClient,
    session_factory: SessionFactory,
    manager: AuthenticatedUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = seed_planning_scenario(session_factory)
    created = create_load_plan(client, scenario, manager)
    plan_id = uuid.UUID(created["id"])
    original_stage = StatusHistoryService.stage_status_change
    staged_calls = 0

    def fail_on_second_history(
        service: StatusHistoryService,
        data: StatusHistoryCreate,
    ) -> StatusHistory:
        nonlocal staged_calls
        staged_calls += 1
        if staged_calls == 2:
            raise RuntimeError("simulated history persistence failure")
        return original_stage(service, data)

    monkeypatch.setattr(
        StatusHistoryService,
        "stage_status_change",
        fail_on_second_history,
    )

    response = client.post(
        f"/api/v1/load-plans/{created['id']}/approve",
        headers=manager.headers,
    )

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_SERVER_ERROR"
    assert staged_calls == 2

    db = session_factory()
    try:
        load_plan = db.get(LoadPlan, plan_id)
        order = db.get(Order, scenario.order_id)
        histories = db.scalars(
            select(StatusHistory).where(
                StatusHistory.entity_id.in_([plan_id, scenario.order_id])
            )
        ).all()
        assert load_plan is not None
        assert order is not None
        assert load_plan.status == "CALCULATED"
        assert load_plan.approved_at is None
        assert order.status == "READY"
        assert [
            (
                history.entity_type,
                history.entity_id,
                history.old_status,
                history.new_status,
            )
            for history in histories
        ] == [("LOAD_PLAN", plan_id, None, "CALCULATED")]
    finally:
        db.close()
