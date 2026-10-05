import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.deliveries.models import Delivery, Trip
from app.modules.occurrences.models import Occurrence
from app.modules.trucks.models import Truck
from app.modules.users.models import User
from tests.integration.auth_helpers import issue_session_headers
from tests.integration.test_deliveries_api import (
    create_trip,
    seed_operational_scenario,
)

SessionFactory = Callable[[], Session]


def create_role_headers(
    session_factory: SessionFactory,
    role: str,
) -> dict[str, str]:
    with session_factory() as db:
        user = User(
            name=f"Indicadores {role}",
            email=f"indicators-{role.lower()}-{uuid.uuid4().hex}@example.test",
            password_hash="hash-ficticio",
            role=role,
            active=True,
        )
        db.add(user)
        db.commit()
        user_id = user.id

    return issue_session_headers(session_factory, user_id)


def test_operational_indicators_returns_zeroes_for_empty_operational_base(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    headers = create_role_headers(session_factory, "LOGISTICS_MANAGER")

    response = client.get(
        "/api/v1/operational-indicators",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "fleet": {
            "period": "CURRENT_SNAPSHOT",
            "total": 0,
            "active": 0,
            "inactive": 0,
            "available": 0,
            "unavailable": 0,
            "with_operation_conflict": 0,
        },
        "trips": {
            "period": "ALL_TIME",
            "total": 0,
            "scheduled": 0,
            "in_route": 0,
            "finished": 0,
        },
        "deliveries": {
            "period": "ALL_TIME",
            "total": 0,
            "pending": 0,
            "in_delivery": 0,
            "delivered": 0,
        },
        "occurrences": {
            "period": "ALL_TIME",
            "total": 0,
        },
    }


def test_operational_indicators_aggregates_real_domain_states(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    scenarios = [seed_operational_scenario(session_factory) for _ in range(3)]
    trips = [create_trip(client, scenario) for scenario in scenarios]

    now = datetime.now(UTC)

    with session_factory() as db:
        in_route_trip = db.get(Trip, uuid.UUID(trips[1]["id"]))
        assert in_route_trip is not None
        in_route_trip.status = "IN_ROUTE"
        in_route_trip.started_at = now - timedelta(minutes=30)

        in_route_deliveries = list(
            db.scalars(
                select(Delivery)
                .where(Delivery.trip_id == in_route_trip.id)
                .order_by(Delivery.sequence.asc())
            )
        )
        in_route_deliveries[0].status = "IN_DELIVERY"

        finished_trip = db.get(Trip, uuid.UUID(trips[2]["id"]))
        assert finished_trip is not None
        finished_trip.status = "FINISHED"
        finished_trip.started_at = now - timedelta(hours=2)
        finished_trip.finished_at = now - timedelta(hours=1)

        finished_deliveries = list(
            db.scalars(
                select(Delivery)
                .where(Delivery.trip_id == finished_trip.id)
                .order_by(Delivery.sequence.asc())
            )
        )
        for delivery in finished_deliveries:
            delivery.status = "DELIVERED"
            delivery.delivered_at = now - timedelta(hours=1)

        db.add(
            Truck(
                plate=f"I{uuid.uuid4().hex[:6]}",
                model="Caminhao inativo indicadores",
                internal_width_cm=100,
                internal_height_cm=100,
                internal_length_cm=100,
                max_weight_kg=Decimal("1000.00"),
                active=False,
            )
        )

        db.add_all(
            (
                Occurrence(
                    trip_id=uuid.UUID(trips[0]["id"]),
                    type="DELAY",
                    description="Atraso para teste de indicadores.",
                ),
                Occurrence(
                    trip_id=uuid.UUID(trips[1]["id"]),
                    type="VEHICLE_PROBLEM",
                    description="Problema para teste de indicadores.",
                ),
            )
        )

        db.commit()

    response = client.get(
        "/api/v1/operational-indicators",
        headers=scenarios[0].manager_headers,
    )

    assert response.status_code == 200
    body = response.json()

    assert body["fleet"] == {
        "period": "CURRENT_SNAPSHOT",
        "total": 4,
        "active": 3,
        "inactive": 1,
        "available": 1,
        "unavailable": 3,
        "with_operation_conflict": 2,
    }

    assert body["trips"] == {
        "period": "ALL_TIME",
        "total": 3,
        "scheduled": 1,
        "in_route": 1,
        "finished": 1,
    }

    assert body["deliveries"] == {
        "period": "ALL_TIME",
        "total": 6,
        "pending": 3,
        "in_delivery": 1,
        "delivered": 2,
    }

    assert body["occurrences"] == {
        "period": "ALL_TIME",
        "total": 2,
    }


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        ("ADMIN", 200),
        ("LOGISTICS_MANAGER", 200),
        ("CHECKER", 403),
        ("DRIVER", 403),
    ],
)
def test_operational_indicators_enforces_rbac(
    client: TestClient,
    session_factory: SessionFactory,
    role: str,
    expected_status: int,
) -> None:
    headers = create_role_headers(session_factory, role)

    response = client.get(
        "/api/v1/operational-indicators",
        headers=headers,
    )

    assert response.status_code == expected_status

    if expected_status == 403:
        assert response.json()["code"] == "AUTH_FORBIDDEN"


def test_operational_indicators_requires_authentication(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/operational-indicators")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_TOKEN"
