"""OC95 collection contracts against the migrated PostgreSQL database."""

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import get_args

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.pagination import PaginationParams
from app.modules.customers.models import Customer
from app.modules.customers.service import CustomerService
from app.modules.drivers.models import Driver
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.schemas import ORDER_STATUS_VALUES, OrderStatus
from app.modules.orders.service import OrderService
from app.modules.products.models import Product
from app.modules.trucks.models import Truck
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService
from tests.integration.auth_helpers import issue_session_headers

SessionFactory = Callable[[], Session]
RESOURCES = ("orders", "trucks", "products", "customers", "drivers")
REGISTRIES = RESOURCES[1:]
STAMP = datetime(2026, 10, 1, tzinfo=timezone.utc)


@pytest.fixture
def manager_headers(session_factory: SessionFactory) -> dict[str, str]:
    with session_factory() as db:
        user = UserService(db).create_user(
            UserCreate(
                name="Pessoa fictícia",
                email="oc95@example.test",
                password="senha-local-segura",
                role="LOGISTICS_MANAGER",
            )
        )
    return issue_session_headers(session_factory, user.id)


@pytest.fixture
def collection(session_factory: SessionFactory) -> list[str]:
    """Matches start beyond the default first page, with tied timestamps."""
    ids = [uuid.UUID(int=9500 + i) for i in range(25)]
    with session_factory() as db:
        for i, identity in enumerate(ids):
            name = f"Alvo São Luís %_\\ {i}" if i >= 20 else f"Base {i}"
            common = {"id": identity, "active": i != 24, "created_at": STAMP}
            db.add(
                Customer(
                    **common,
                    name=name,
                    document=f"{i:014}",
                    phone="11900000000",
                    address="SEGREDO-endereco",
                    city=f"Cidade {i}",
                    state="SP",
                    notes="SEGREDO-notes",
                )
            )
            db.add(
                Driver(
                    **common,
                    name=name,
                    document=f"{i:011}",
                    phone="11900000000",
                    license_number=f"{1000 + i:011}",
                    license_category="D",
                )
            )
            db.add(
                Truck(
                    **common,
                    plate=f"PL-{i}",
                    model=name,
                    internal_width_cm=240,
                    internal_height_cm=260,
                    internal_length_cm=600,
                    max_weight_kg=8000,
                )
            )
            db.add(
                Product(
                    **common,
                    code=f"CODE-{i}",
                    name=name,
                    description="SEGREDO-descricao",
                    width_cm=10,
                    height_cm=10,
                    length_cm=10,
                    weight_kg=1,
                    fragile=i in (20, 24),
                    stackable=i != 21,
                    rotation_allowed=i != 22,
                )
            )
        db.flush()
        for i, identity in enumerate(ids):
            db.add(
                Order(
                    id=identity,
                    customer_id=identity,
                    status="READY" if i % 2 else "DRAFT",
                    priority="NORMAL",
                    delivery_address="SEGREDO-destino",
                    created_at=STAMP,
                    items=[
                        OrderItem(product_id=ids[0], quantity=2, delivery_sequence=1),
                        OrderItem(product_id=ids[1], quantity=3, delivery_sequence=1),
                    ],
                )
            )
        db.commit()
    return [str(identity) for identity in ids]


def read(
    client: TestClient, headers: dict[str, str], resource: str, **params: object
) -> dict:
    response = client.get(f"/api/v1/{resource}", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("resource", RESOURCES)
def test_search_precedes_pagination_and_counts_filtered_collection(
    client, manager_headers, collection, resource
):
    baseline = read(client, manager_headers, resource, sort_order="asc")
    assert collection[20] not in [row["id"] for row in baseline["items"]]
    body = read(
        client,
        manager_headers,
        resource,
        search="  aLvO  ",
        page_size=2,
        sort_order="asc",
    )
    count = 5 if resource == "orders" else 4
    assert body["total"] == count and body["total_pages"] == (count + 1) // 2
    assert body["page"] == 1 and body["page_size"] == 2
    assert [row["id"] for row in body["items"]] == collection[20:22]
    next_page = read(
        client,
        manager_headers,
        resource,
        search="alvo",
        page=2,
        page_size=2,
        sort_order="asc",
    )
    assert [row["id"] for row in next_page["items"]] == collection[22:24]
    assert next_page["total"] == count


@pytest.mark.parametrize("resource", RESOURCES)
@pytest.mark.parametrize(
    "term", ["%", "_", "\\", "sÃO luÍs", "%_\\", "Alvo São Luís %_\\ 21"]
)
def test_search_is_literal_and_case_insensitive_including_unicode(
    client, manager_headers, collection, resource, term
):
    body = read(client, manager_headers, resource, search=term, sort_order="asc")
    expected = (
        collection[21:22]
        if term.endswith("21")
        else collection[20 : 25 if resource == "orders" else 24]
    )
    assert [row["id"] for row in body["items"]] == expected and body["total"] == len(
        expected
    )


@pytest.mark.parametrize("resource", RESOURCES)
@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_filtered_ordering_uses_created_at_and_uuid_tiebreak(
    client, manager_headers, collection, resource, direction
):
    body = read(client, manager_headers, resource, search="alvo", sort_order=direction)
    expected = collection[20 : 25 if resource == "orders" else 24]
    assert [row["id"] for row in body["items"]] == (
        expected if direction == "asc" else expected[::-1]
    )


@pytest.mark.parametrize("resource", RESOURCES)
def test_empty_results_out_of_range_and_unfiltered_regression(
    client, manager_headers, collection, resource
):
    empty = read(client, manager_headers, resource, search="inexistente")
    assert empty["items"] == [] and empty["total"] == empty["total_pages"] == 0
    beyond = read(client, manager_headers, resource, search="alvo", page=9, page_size=2)
    assert beyond["items"] == [] and beyond["page"] == 9 and beyond["total"] > 0
    baseline = read(client, manager_headers, resource)
    for term in ("", " " * 200):
        assert read(client, manager_headers, resource, search=term) == baseline
    assert baseline["total"] == (25 if resource == "orders" else 24)
    assert (
        len(baseline["items"]) == 20
        and baseline["page_size"] == 20
        and baseline["total_pages"] == 2
    )


@pytest.mark.parametrize("resource", REGISTRIES)
@pytest.mark.parametrize(
    "archive_status,expected_indexes",
    [("active", range(20, 24)), ("archived", range(24, 25)), ("all", range(20, 25))],
)
def test_search_combines_with_archive_status(
    client, manager_headers, collection, resource, archive_status, expected_indexes
):
    body = read(
        client,
        manager_headers,
        resource,
        search="alvo",
        archive_status=archive_status,
        sort_order="asc",
    )
    assert [row["id"] for row in body["items"]] == [
        collection[i] for i in expected_indexes
    ]
    assert body["total"] == len(expected_indexes)


@pytest.mark.parametrize(
    "resource,term,index",
    [
        ("trucks", "pl-21", 21),
        ("products", "code-21", 21),
        ("customers", "cidade 21", 21),
        ("orders", str(uuid.UUID(int=9521)), 21),
    ],
)
def test_search_uses_each_approved_identifying_field(
    client, manager_headers, collection, resource, term, index
):
    assert [
        row["id"]
        for row in read(client, manager_headers, resource, search=term)["items"]
    ] == [collection[index]]


def test_order_search_by_customer_reference_and_name_has_no_duplicates(
    client, manager_headers, collection, session_factory
):
    with session_factory() as db:
        order = db.get(Order, uuid.UUID(collection[22]))
        order.customer_id = uuid.UUID(collection[21])
        db.commit()
    for term in (collection[21], "Alvo São Luís %_\\ 21"):
        body = read(client, manager_headers, "orders", search=term, sort_order="asc")
        assert [row["id"] for row in body["items"]] == collection[21:23] and body[
            "total"
        ] == 2
        assert all(
            row["item_count"] == 2 and row["volume_count"] == 5 for row in body["items"]
        )
        assert all(
            "customer_name" not in row and "delivery_address" not in row
            for row in body["items"]
        )
    assert collection[21] not in [
        row["id"]
        for row in read(client, manager_headers, "customers", sort_order="asc")["items"]
    ]


@pytest.mark.parametrize("status", sorted(ORDER_STATUS_VALUES))
def test_order_status_and_search_combine_by_and(
    client, manager_headers, collection, status
):
    assert set(get_args(OrderStatus)) == ORDER_STATUS_VALUES
    for term in (None, "alvo"):
        params = {"status": status, "page_size": 100, "sort_order": "asc"}
        if term is not None:
            params["search"] = term
        body = read(client, manager_headers, "orders", **params)
        expected = [
            identity
            for i, identity in enumerate(collection)
            if (term is None or i >= 20) and status == ("READY" if i % 2 else "DRAFT")
        ]
        assert [row["id"] for row in body["items"]] == expected and body[
            "total"
        ] == len(expected)


@pytest.mark.parametrize(
    "restriction,indexes", [("restricted", [20, 21, 22]), ("free", [23])]
)
def test_product_restriction_preserves_each_flag_and_archive_combination(
    client, manager_headers, collection, restriction, indexes
):
    body = read(
        client,
        manager_headers,
        "products",
        search="alvo",
        restriction=restriction,
        sort_order="asc",
        page_size=2,
    )
    assert [row["id"] for row in body["items"]] == [collection[i] for i in indexes[:2]]
    assert (
        body["total"] == len(indexes) and body["total_pages"] == (len(indexes) + 1) // 2
    )
    archived = read(
        client,
        manager_headers,
        "products",
        search="alvo",
        restriction=restriction,
        archive_status="archived",
    )
    assert archived["total"] == (1 if restriction == "restricted" else 0)


@pytest.mark.parametrize(
    "resource,params",
    [
        ("orders", {"status": "BOGUS"}),
        ("orders", {"status": "ready"}),
        ("products", {"restriction": "all"}),
        *[(resource, {"search": "x" * 121}) for resource in RESOURCES],
    ],
)
def test_invalid_filters_use_standard_422(client, manager_headers, resource, params):
    response = client.get(f"/api/v1/{resource}", params=params, headers=manager_headers)
    assert response.status_code == 422 and response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["details"][0]["field"] in params


@pytest.mark.parametrize(
    "resource,term",
    [
        ("customers", "SEGREDO-endereco"),
        ("customers", "SEGREDO-notes"),
        ("customers", "11900000000"),
        ("customers", "00000000000021"),
        ("drivers", "11900000000"),
        ("drivers", "00000001021"),
        ("drivers", "00000000021"),
        ("orders", "SEGREDO-destino"),
        ("products", "SEGREDO-descricao"),
    ],
)
def test_search_never_uses_prohibited_fields(
    client, manager_headers, collection, resource, term
):
    assert read(client, manager_headers, resource, search=term)["total"] == 0


@pytest.mark.parametrize("role", ["ADMIN", "LOGISTICS_MANAGER", "CHECKER", "DRIVER"])
@pytest.mark.parametrize("resource", RESOURCES)
def test_filters_preserve_rbac(client, session_factory, role, resource):
    with session_factory() as db:
        user = UserService(db).create_user(
            UserCreate(
                name="Teste fictício",
                email=f"{role.lower()}@example.test",
                password="senha-local-segura",
                role=role,
            )
        )
    headers = issue_session_headers(session_factory, user.id)
    response = client.get(
        f"/api/v1/{resource}", params={"search": "alvo"}, headers=headers
    )
    allowed = role in ("ADMIN", "LOGISTICS_MANAGER") or (
        role == "CHECKER" and resource in ("orders", "products", "trucks")
    )
    assert response.status_code == (200 if allowed else 403)
    assert (
        client.get(f"/api/v1/{resource}", params={"search": "alvo"}).status_code == 401
    )


def test_order_query_count_does_not_grow_with_matches(
    client, manager_headers, collection, postgres_engine
):
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if "FROM orders" in statement or "FROM order_items" in statement:
            statements.append(statement)

    event.listen(postgres_engine, "before_cursor_execute", capture)
    try:
        body = read(client, manager_headers, "orders", search="alvo")
    finally:
        event.remove(postgres_engine, "before_cursor_execute", capture)
    assert body["total"] == 5 and len(statements) == 3


@pytest.mark.parametrize("resource", RESOURCES)
@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_created_at_precedes_uuid_in_filtered_ordering(
    client, manager_headers, collection, session_factory, resource, direction
):
    models = {
        "orders": Order,
        "trucks": Truck,
        "products": Product,
        "customers": Customer,
        "drivers": Driver,
    }
    with session_factory() as db:
        db.get(models[resource], uuid.UUID(collection[20])).created_at = datetime(
            2026, 10, 2, tzinfo=timezone.utc
        )
        db.commit()
    expected = collection[21 : 25 if resource == "orders" else 24] + collection[20:21]
    if direction == "desc":
        expected.reverse()
    body = read(client, manager_headers, resource, search="alvo", sort_order=direction)
    assert [row["id"] for row in body["items"]] == expected


@pytest.fixture
def named_customer_order(session_factory: SessionFactory) -> dict[str, str]:
    """One unique customer name; order and customer have different references."""
    with session_factory() as db:
        customer = Customer(
            name="Cliente Restrito OC95 Áurea",
            document="00000000000191",
            address="Rua fictícia",
            city="Cidade fictícia",
            state="SP",
        )
        product = Product(
            code="OC95-RBAC",
            name="Produto fictício",
            width_cm=10,
            height_cm=10,
            length_cm=10,
            weight_kg=1,
        )
        db.add_all([customer, product])
        db.flush()
        order = Order(
            customer_id=customer.id,
            status="READY",
            priority="NORMAL",
            delivery_address="Destino fictício",
            items=[OrderItem(product_id=product.id, quantity=1, delivery_sequence=1)],
        )
        db.add(order)
        db.commit()
        return {
            "order_id": str(order.id),
            "customer_id": str(customer.id),
            "customer_name": customer.name,
        }


def role_headers(session_factory: SessionFactory, role: str) -> dict[str, str]:
    with session_factory() as db:
        user = UserService(db).create_user(
            UserCreate(
                name="Leitor fictício",
                email=f"oc95-{role.lower()}@example.test",
                password="senha-local-segura",
                role=role,
            )
        )
    return issue_session_headers(session_factory, user.id)


@pytest.mark.parametrize("role", ["ADMIN", "LOGISTICS_MANAGER", "CHECKER", "DRIVER"])
def test_order_customer_name_search_respects_customer_readers(
    client, session_factory, named_customer_order, role
):
    response = client.get(
        "/api/v1/orders",
        params={
            "search": named_customer_order["customer_name"],
            "status": "READY",
            "page_size": 1,
        },
        headers=role_headers(session_factory, role),
    )
    if role == "DRIVER":
        assert response.status_code == 403
        assert response.json()["code"] == "AUTH_FORBIDDEN"
        return
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1 and body["page_size"] == 1
    if role == "CHECKER":
        assert body["items"] == []
        assert body["total"] == body["total_pages"] == 0
    else:
        assert [item["id"] for item in body["items"]] == [
            named_customer_order["order_id"]
        ]
        assert body["total"] == body["total_pages"] == 1
        assert "customer_name" not in body["items"][0]


@pytest.mark.parametrize("reference", ["order_id", "customer_id"])
def test_checker_can_still_search_order_and_customer_uuids(
    client, session_factory, named_customer_order, reference
):
    body = read(
        client,
        role_headers(session_factory, "CHECKER"),
        "orders",
        search=named_customer_order[reference],
        status="READY",
    )
    assert [item["id"] for item in body["items"]] == [named_customer_order["order_id"]]
    assert body["total"] == body["total_pages"] == 1


def test_checker_cannot_enable_or_build_customer_name_search(
    client, session_factory, named_customer_order, monkeypatch
):
    def reject_name_lookup(*args: object, **kwargs: object) -> None:
        pytest.fail("CHECKER must not construct the customer-name query")

    monkeypatch.setattr(CustomerService, "matching_name_ids", reject_name_lookup)
    body = read(
        client,
        role_headers(session_factory, "CHECKER"),
        "orders",
        search=named_customer_order["customer_name"],
        allow_customer_name_search="true",
    )
    assert body["items"] == [] and body["total"] == body["total_pages"] == 0


@pytest.mark.parametrize("capability", [{}, {"allow_customer_name_search": False}])
def test_order_service_customer_name_search_is_denied_by_default(
    session_factory, named_customer_order, monkeypatch, capability
):
    def reject_name_lookup(*args: object, **kwargs: object) -> None:
        pytest.fail("Customer-name queries require an explicit capability")

    monkeypatch.setattr(CustomerService, "matching_name_ids", reject_name_lookup)
    with session_factory() as db:
        result = OrderService(db).list_orders(
            PaginationParams(1, 20, "desc"),
            search=named_customer_order["customer_name"],
            **capability,
        )
    assert not result.items and result.total == result.total_pages == 0
