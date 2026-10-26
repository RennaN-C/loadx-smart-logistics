"""OC99 reusable addresses and immutable delivery snapshots on PostgreSQL."""

import uuid
from importlib import import_module

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ApiError
from app.modules.customers.address_schemas import CustomerAddressCreate
from app.modules.customers.address_service import CustomerAddressService
from app.modules.customers.models import CustomerAddress
from app.modules.status_history.models import AuditEvent
from app.modules.status_history.service import AuditService
from tests.integration.test_customers_api import make_customer_payload
from tests.integration.test_load_planning_api import create_authenticated_user
from tests.integration.test_orders_api import create_product


@pytest.fixture
def manager(session_factory):
    return create_authenticated_user(session_factory, "LOGISTICS_MANAGER")


@pytest.fixture
def customer(client, manager):
    result = client.post(
        "/api/v1/customers", headers=manager.headers, json=make_customer_payload()
    )
    assert result.status_code == 201
    return result.json()


def address_payload(**changes):
    return dict(
        label="Filial",
        address="Rua fictícia, 25",
        city="Campinas",
        state="sp",
        postal_code="13000-000",
        **changes,
    )


def addresses_url(customer):
    return f"/api/v1/customers/{customer['id']}/addresses"


def create_address(client, manager, customer, **changes):
    result = client.post(
        addresses_url(customer),
        headers=manager.headers,
        json=address_payload(**changes),
    )
    assert result.status_code == 201, result.text
    return result.json()


def test_legacy_create_and_patch_keep_stable_primary(client, manager, customer):
    rows = client.get(addresses_url(customer), headers=manager.headers).json()["items"]
    assert len(rows) == 1 and rows[0]["is_primary"]
    original = rows[0]
    assert original["address"] == customer["address"]
    assert (
        client.patch(
            f"/api/v1/customers/{customer['id']}",
            headers=manager.headers,
            json={"address": "Destino corrigido"},
        ).status_code
        == 200
    )
    updated = client.get(addresses_url(customer), headers=manager.headers).json()[
        "items"
    ][0]
    assert updated["id"] == original["id"] and updated["address"] == "Destino corrigido"


def test_primary_switch_archive_promote_and_reactivate(client, manager, customer):
    original = client.get(addresses_url(customer), headers=manager.headers).json()[
        "items"
    ][0]
    second = create_address(client, manager, customer, is_primary=True)
    assert (
        second["is_primary"]
        and second["postal_code"] == "13000000"
        and second["state"] == "SP"
    )
    assert (
        client.get(
            f"/api/v1/customers/{customer['id']}", headers=manager.headers
        ).json()["address"]
        == second["address"]
    )
    url = f"{addresses_url(customer)}/{second['id']}"
    archived = client.patch(url, headers=manager.headers, json={"active": False})
    assert archived.status_code == 200 and not archived.json()["is_primary"]
    assert (
        client.get(addresses_url(customer), headers=manager.headers).json()["items"][0][
            "id"
        ]
        == original["id"]
    )
    assert (
        client.get(
            addresses_url(customer),
            headers=manager.headers,
            params={"archive_status": "archived"},
        ).json()["items"][0]["id"]
        == second["id"]
    )
    assert (
        client.get(
            addresses_url(customer),
            headers=manager.headers,
            params={"archive_status": "all", "page_size": 1},
        ).json()["total"]
        == 2
    )
    assert (
        client.patch(url, headers=manager.headers, json={"active": True}).json()["id"]
        == second["id"]
    )


def test_archive_last_then_create_restores_primary(client, manager, customer):
    original = client.get(addresses_url(customer), headers=manager.headers).json()[
        "items"
    ][0]
    assert (
        client.patch(
            f"{addresses_url(customer)}/{original['id']}",
            headers=manager.headers,
            json={"active": False},
        ).status_code
        == 200
    )
    assert (
        client.get(addresses_url(customer), headers=manager.headers).json()["total"]
        == 0
    )
    assert (
        client.get(
            f"/api/v1/customers/{customer['id']}", headers=manager.headers
        ).json()["address"]
        == customer["address"]
    )
    assert create_address(client, manager, customer)["is_primary"]


@pytest.mark.parametrize(
    "role,expected",
    [("ADMIN", 201), ("LOGISTICS_MANAGER", 201), ("CHECKER", 403), ("DRIVER", 403)],
)
def test_rbac(client, session_factory, customer, role, expected):
    actor = create_authenticated_user(session_factory, role)
    result = client.post(
        addresses_url(customer), headers=actor.headers, json=address_payload()
    )
    assert result.status_code == expected
    original = client.get(addresses_url(customer), headers=actor.headers)
    assert original.status_code == (200 if expected == 201 else 403)
    with session_factory() as db:
        address = db.scalar(
            select(CustomerAddress).where(
                CustomerAddress.customer_id == uuid.UUID(customer["id"])
            )
        )
    assert client.patch(
        f"{addresses_url(customer)}/{address.id}",
        headers=actor.headers,
        json={"active": False},
    ).status_code == (200 if expected == 201 else 403)
    assert (
        client.post(addresses_url(customer), json=address_payload()).status_code == 401
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "XYZ"},
        {"postal_code": "invalid"},
        {"address": None},
        {"is_primary": None},
    ],
)
def test_invalid_address_payload(client, manager, customer, changes):
    payload = address_payload()
    payload.update(changes)
    assert (
        client.post(
            addresses_url(customer), headers=manager.headers, json=payload
        ).status_code
        == 422
    )


def test_missing_scoped_address_and_primary_validation(client, manager, customer):
    missing = f"{addresses_url(customer)}/{uuid.uuid4()}"
    assert (
        client.patch(
            missing, headers=manager.headers, json={"active": False}
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/customers/{uuid.uuid4()}/addresses", headers=manager.headers
        ).status_code
        == 404
    )
    assert (
        client.post(
            addresses_url(customer),
            headers=manager.headers,
            json=address_payload(active=False, is_primary=True),
        ).status_code
        == 409
    )
    original = client.get(addresses_url(customer), headers=manager.headers).json()[
        "items"
    ][0]
    assert (
        client.patch(
            f"{addresses_url(customer)}/{original['id']}",
            headers=manager.headers,
            json={"is_primary": False},
        ).status_code
        == 409
    )


def order_payload(session_factory, customer, address):
    return {
        "customer_id": customer["id"],
        "customer_address_id": address["id"],
        "priority": "NORMAL",
        "items": [
            {
                "product_id": create_product(session_factory),
                "quantity": 1,
                "delivery_sequence": 1,
            }
        ],
    }


def test_order_snapshot_survives_edit_archive_and_priority_patch(
    client, session_factory, manager, customer
):
    address = create_address(client, manager, customer)
    payload = order_payload(session_factory, customer, address)
    result = client.post("/api/v1/orders", headers=manager.headers, json=payload)
    assert result.status_code == 201, result.text
    order = result.json()
    snapshot = order["delivery_address_snapshot"]
    assert snapshot == {
        k: address[k] for k in ("label", "address", "city", "state", "postal_code")
    } | {"customer_address_id": address["id"]}
    assert (
        client.patch(
            f"{addresses_url(customer)}/{address['id']}",
            headers=manager.headers,
            json={"address": "Mudou", "city": "Sorocaba", "active": False},
        ).status_code
        == 200
    )
    url = f"/api/v1/orders/{order['id']}"
    edited = client.patch(url, headers=manager.headers, json={"priority": "HIGH"})
    assert (
        edited.status_code == 200
        and edited.json()["delivery_address_snapshot"] == snapshot
    )
    assert (
        client.get(url, headers=manager.headers).json()["delivery_address"]
        == address["address"]
    )
    assert (
        client.post("/api/v1/orders", headers=manager.headers, json=payload).status_code
        == 409
    )
    replacement = client.patch(
        url, headers=manager.headers, json={"delivery_address": "Destino manual"}
    ).json()
    assert replacement["customer_address_id"] is None and replacement[
        "delivery_address_snapshot"
    ] == {"address": "Destino manual"}


@pytest.mark.parametrize(
    "mode",
    [
        "other_customer",
        "missing",
        "ambiguous",
        "missing_selection",
        "archived_customer",
    ],
)
def test_invalid_order_selection(client, session_factory, manager, customer, mode):
    address = create_address(client, manager, customer)
    payload = order_payload(session_factory, customer, address)
    if mode == "other_customer":
        other = client.post(
            "/api/v1/customers",
            headers=manager.headers,
            json=make_customer_payload("00000000000272"),
        ).json()
        payload["customer_id"] = other["id"]
    elif mode == "missing":
        payload["customer_address_id"] = str(uuid.uuid4())
    elif mode == "ambiguous":
        payload["delivery_address"] = "Contraditório"
    elif mode == "missing_selection":
        payload.pop("customer_address_id")
    else:
        client.patch(
            f"/api/v1/customers/{customer['id']}",
            headers=manager.headers,
            json={"active": False},
        )
    result = client.post("/api/v1/orders", headers=manager.headers, json=payload)
    assert result.status_code == (409 if mode == "archived_customer" else 422)


def test_change_order_customer_requires_explicit_new_address(
    client, session_factory, manager, customer
):
    address = create_address(client, manager, customer)
    order = client.post(
        "/api/v1/orders",
        headers=manager.headers,
        json=order_payload(session_factory, customer, address),
    ).json()
    other = client.post(
        "/api/v1/customers",
        headers=manager.headers,
        json=make_customer_payload("00000000000272"),
    ).json()
    url = f"/api/v1/orders/{order['id']}"
    assert (
        client.patch(
            url, headers=manager.headers, json={"customer_id": other["id"]}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            url,
            headers=manager.headers,
            json={"customer_id": other["id"], "customer_address_id": address["id"]},
        ).status_code
        == 422
    )
    assert (
        client.get(url, headers=manager.headers).json()["customer_id"] == customer["id"]
    )
    updated = client.patch(
        url,
        headers=manager.headers,
        json={"customer_id": other["id"], "delivery_address": "Destino outro"},
    ).json()
    assert updated["customer_address_id"] is None and updated[
        "delivery_address_snapshot"
    ] == {"address": "Destino outro"}


def test_primary_unique_and_active_constraints(session_factory, customer):
    with session_factory() as db:
        for active in (True, False):
            row = CustomerAddress(
                customer_id=uuid.UUID(customer["id"]),
                label="Outro",
                address="Rua",
                city="Cidade",
                state="SP",
                active=active,
                is_primary=True,
            )
            db.add(row)
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
        assert (
            len(
                db.scalars(
                    select(CustomerAddress).where(
                        CustomerAddress.customer_id == uuid.UUID(customer["id"])
                    )
                ).all()
            )
            == 1
        )


def test_audit_failure_rolls_back_address_and_primary_projection(
    session_factory, manager, customer, monkeypatch
):
    def fail(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    with session_factory() as db:
        monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
        with pytest.raises(RuntimeError, match="audit unavailable"):
            CustomerAddressService(db).create_address(
                uuid.UUID(customer["id"]),
                CustomerAddressCreate.model_validate(address_payload(is_primary=True)),
                changed_by=manager.id,
            )
        rows = db.scalars(
            select(CustomerAddress).where(
                CustomerAddress.customer_id == uuid.UUID(customer["id"])
            )
        ).all()
        assert (
            len(rows) == 1
            and rows[0].is_primary
            and rows[0].address == customer["address"]
        )


def test_address_audit_and_downgrade_guard(client, session_factory, manager, customer):
    address = create_address(client, manager, customer)
    url = f"{addresses_url(customer)}/{address['id']}"
    for patch in (
        {"address": "Alterado"},
        {"active": False},
        {"active": False},
        {"active": True},
    ):
        assert client.patch(url, headers=manager.headers, json=patch).status_code == 200
    with session_factory() as db:
        events = db.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_id == uuid.UUID(address["id"]))
            .order_by(AuditEvent.created_at)
        ).all()
        assert [row.event_type for row in events] == [
            "CUSTOMER_ADDRESS_CREATED",
            "CUSTOMER_ADDRESS_UPDATED",
            "CUSTOMER_ADDRESS_ARCHIVED",
            "CUSTOMER_ADDRESS_REACTIVATED",
        ]
        assert all(row.actor_id == manager.id for row in events)
        migration = import_module(
            "migrations.versions.20261008_0017_customer_addresses"
        )
        with pytest.raises(RuntimeError, match="OC99 downgrade blocked"):
            migration.ensure_safe_downgrade(db.connection())


def test_openapi_address_and_order_contract(client):
    schema = client.get("/openapi.json").json()
    assert schema["paths"]["/api/v1/customers/{customer_id}/addresses"]["post"][
        "responses"
    ]["201"]
    fields = schema["components"]["schemas"]["OrderRead"]["properties"]
    assert "customer_address_id" in fields and "delivery_address_snapshot" in fields


def test_composite_foreign_key_rejects_address_from_other_customer(
    client, session_factory, manager, customer
):
    from app.modules.orders.models import Order

    address = create_address(client, manager, customer)
    other = client.post(
        "/api/v1/customers",
        headers=manager.headers,
        json=make_customer_payload("00000000000272"),
    ).json()
    with session_factory() as db:
        db.add(
            Order(
                customer_id=uuid.UUID(other["id"]),
                customer_address_id=uuid.UUID(address["id"]),
                priority="NORMAL",
                delivery_address="Destino",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_concurrent_primary_changes_are_serialized(postgres_engine, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete
    from sqlalchemy.orm import sessionmaker

    from app.modules.customers.models import Customer
    from app.modules.customers.schemas import CustomerCreate
    from app.modules.customers.service import CustomerService

    factory = sessionmaker(postgres_engine, autoflush=False)
    with factory() as db:
        customer = CustomerService(db).create_customer(
            CustomerCreate.model_validate(make_customer_payload())
        )
        identifier = customer.id
    # Audit rollback is tested separately; this test isolates committed locks.
    monkeypatch.setattr(CustomerAddressService, "_audit", lambda *args, **kwargs: None)
    barrier = Barrier(2)

    def propose(number):
        with factory() as db:
            barrier.wait(timeout=10)
            return (
                CustomerAddressService(db)
                .create_address(
                    identifier,
                    CustomerAddressCreate(
                        label=f"Filial {number}",
                        address=f"Rua {number}",
                        city="Campinas",
                        state="SP",
                        is_primary=True,
                    ),
                    changed_by=uuid.uuid4(),
                )
                .id
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(propose, number) for number in (1, 2)]
            ids = [future.result(timeout=15) for future in futures]
        with factory() as db:
            rows = db.scalars(
                select(CustomerAddress).where(CustomerAddress.customer_id == identifier)
            ).all()
            assert len(rows) == 3
            primaries = [row for row in rows if row.is_primary]
            assert len(primaries) == 1 and primaries[0].id in ids
            assert db.get(Customer, identifier).address == primaries[0].address
            cached = db.get(CustomerAddress, ids[0])
            with factory() as writer:
                source = writer.get(CustomerAddress, ids[0])
                source.active = False
                source.is_primary = False
                writer.commit()
            assert cached.active is True
            with pytest.raises(ApiError) as failure:
                CustomerAddressService(db).select_for_order(identifier, ids[0])
            assert failure.value.code == "RECORD_ARCHIVED"
            db.rollback()
    finally:
        with factory() as db:
            db.execute(
                delete(CustomerAddress).where(CustomerAddress.customer_id == identifier)
            )
            db.execute(delete(Customer).where(Customer.id == identifier))
            db.commit()
