"""OC107: PostgreSQL filtering, safe DTOs and authorization before querying."""

import uuid

import pytest
from sqlalchemy import event

from app.main import app
from app.modules.customers.service import CustomerService
from app.modules.deliveries.service import TripService
from app.modules.drivers.models import Driver
from app.modules.drivers.service import DriverService
from app.modules.global_search.service import GlobalSearchService
from app.modules.users.models import User
from tests.integration import test_server_side_filters as oc95
from tests.integration.auth_helpers import issue_session_headers
from tests.integration.test_deliveries_api import create_trip, seed_operational_scenario


@pytest.fixture
def collection(session_factory):
    return oc95.collection.__wrapped__(session_factory)


@pytest.fixture
def manager_headers(session_factory):
    return headers_for(session_factory, "LOGISTICS_MANAGER")


def headers_for(session_factory, role):
    with session_factory() as db:
        user = User(
            name="Pessoa fictícia",
            email=f"{uuid.uuid4()}@example.test",
            role=role,
            active=True,
            password_hash="unused-test-hash",
        )
        db.add(user)
        db.commit()
        identity = user.id
    return issue_session_headers(session_factory, identity)


def search(client, headers, term, **params):
    return client.get(
        "/api/v1/search", headers=headers, params={"search": term, **params}
    )


@pytest.mark.parametrize("role", ["ADMIN", "LOGISTICS_MANAGER"])
def test_categories_limits_order_and_safe_summary(
    client, session_factory, collection, role
):
    headers = headers_for(session_factory, role)
    response = search(client, headers, "  ALVO SÃO LUÍS  ", limit_per_category=2)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    results = response.json()["results"]
    assert {row["category"] for row in results} == {
        "order",
        "customer",
        "truck",
        "driver",
    }
    for category in {row["category"] for row in results}:
        rows = [row for row in results if row["category"] == category]
        expected = collection[-1:-3:-1] if category == "order" else collection[-2:-4:-1]
        assert [row["id"] for row in rows] == expected
        assert all(set(row) == {"id", "category", "title", "href"} for row in rows)
        assert all(row["href"].startswith("/") for row in rows)
    assert "SEGREDO" not in response.text
    assert "license_number" not in response.text
    assert (
        search(client, headers, "ALVO SÃO LUÍS", limit_per_category=2).json()
        == response.json()
    )


@pytest.mark.parametrize(
    "term,found",
    [
        ("%_\\", True),
        ("'; OR TRUE--", False),
        ("Inexistente", False),
        ("Alvo Sao Luis", False),
    ],
)
def test_literal_search_and_accents(client, manager_headers, collection, term, found):
    response = search(client, manager_headers, term)
    assert response.status_code == 200
    assert bool(response.json()["results"]) is found


def test_checker_does_not_query_or_disclose_restricted_categories(
    client, session_factory, collection, monkeypatch
):
    def forbidden_query(*_args, **_kwargs):
        raise AssertionError("Categoria restrita não pode ser consultada")

    for service, method in (
        (CustomerService, "list_customers"),
        (CustomerService, "matching_name_ids"),
        (DriverService, "list_drivers"),
        (TripService, "list_trips"),
    ):
        monkeypatch.setattr(service, method, forbidden_query)
    headers = headers_for(session_factory, "CHECKER")
    assert search(client, headers, "ALVO SÃO LUÍS").json()["results"]
    results = search(client, headers, "ALVO SÃO LUÍS").json()["results"]
    assert {row["category"] for row in results} == {"truck"}
    assert "Cliente" not in str(results)
    results = search(client, headers, collection[22]).json()["results"]
    assert [row["category"] for row in results] == ["order"]
    assert results[0]["title"] == f"Pedido {collection[22]}"
    # Name-only terms cannot reveal even the existence of an order to CHECKER.
    with session_factory() as db:
        from app.modules.customers.models import Customer

        customer = db.get(Customer, uuid.UUID(collection[22]))
        customer.name = "Nome confidencial exclusivo"
        db.commit()
    assert search(client, headers, "confidencial exclusivo").json() == {"results": []}


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"search": ""},
        {"search": "   "},
        {"search": "a"},
        {"search": "a" * 121},
        {"search": "xx", "limit_per_category": 0},
        {"search": "xx", "limit_per_category": 11},
        {"search": "xx", "limit_per_category": "bad"},
    ],
)
def test_invalid_queries(client, manager_headers, params):
    assert (
        client.get("/api/v1/search", headers=manager_headers, params=params).status_code
        == 422
    )


def test_authentication_and_unlinked_driver(client, session_factory):
    assert search(client, {}, "termo").status_code == 401
    assert (
        search(client, headers_for(session_factory, "DRIVER"), "termo").status_code
        == 403
    )


def test_driver_only_own_trip_and_inactive_binding_fails_closed(
    client, session_factory
):
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    identity = trip["id"]
    own = search(client, scenario.driver_headers, identity)
    assert own.status_code == 200
    assert own.json()["results"] == [
        {
            "category": "trip",
            "id": identity,
            "title": f"Viagem {identity}",
            "href": f"/trips/{identity}",
        }
    ]
    assert search(client, scenario.other_driver_headers, identity).json() == {
        "results": []
    }
    assert search(client, scenario.checker_headers, identity).json() == {"results": []}
    assert search(client, scenario.manager_headers, identity).json() == own.json()
    with session_factory() as db:
        db.get(Driver, scenario.driver_id).active = False
        db.commit()
    assert search(client, scenario.driver_headers, identity).status_code == 403


def test_bounded_queries_do_not_grow_per_result(session_factory, collection):
    with session_factory() as db:
        actor = User(role="ADMIN")
        statements = []

        def capture(_connection, _cursor, statement, _parameters, _context, _many):
            statements.append(statement)

        connection = db.connection()
        event.listen(connection, "before_cursor_execute", capture)
        try:
            counts = []
            for limit in (1, 4):
                statements.clear()
                GlobalSearchService(db).search(
                    "ALVO SÃO LUÍS", limit, current_user=actor
                )
                counts.append(len(statements))
            assert counts[0] == counts[1]
            assert counts[0] <= 12
        finally:
            event.remove(connection, "before_cursor_execute", capture)


def test_openapi_search_contract():
    operation = app.openapi()["paths"]["/api/v1/search"]["get"]
    assert {"401", "403", "422"} <= operation["responses"].keys()
    parameters = {item["name"]: item for item in operation["parameters"]}
    assert parameters["search"]["schema"]["minLength"] == 2
    assert parameters["search"]["schema"]["maxLength"] == 120
    assert parameters["limit_per_category"]["schema"]["maximum"] == 10
