"""OC81 consumes existing durable channel facts without personal inbox access."""

import uuid

import pytest
from sqlalchemy import func, select

from app.modules.access_profiles.models import AccessProfile, ProfilePermission
from app.modules.notifications.models import (
    NotificationRecipient,
    OperationalNotification,
)
from app.modules.notifications.outbox_models import OutboxEvent
from app.modules.users.models import User
from tests.integration.auth_helpers import issue_session_headers
from tests.integration.test_deliveries_api import create_trip, seed_operational_scenario


@pytest.fixture
def operation(client, session_factory):
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    deliveries = trip["deliveries"]
    origins = []
    for delivery_id in (
        deliveries[0]["id"],
        deliveries[0]["id"],
        deliveries[1]["id"],
        None,
    ):
        response = client.post(
            "/api/v1/occurrences",
            headers=scenario.manager_headers,
            json={
                "trip_id": trip["id"],
                "delivery_id": delivery_id,
                "type": "DELAY",
                "description": "Descrição fictícia que não deve sair na projeção.",
            },
        )
        assert response.status_code == 201, response.text
        origins.append(response.json()["id"])
    return scenario, trip, origins


def path(operation):
    return f"/api/v1/deliveries/{operation[1]['deliveries'][0]['id']}/communications"


@pytest.mark.parametrize(
    "actor,expected",
    [
        ("admin", 200),
        ("manager", 200),
        ("driver", 200),
        ("other_driver", 403),
        ("checker", 403),
    ],
)
def test_read_requires_delivery_and_occurrence_access(
    client, operation, actor, expected
):
    response = client.get(
        path(operation), headers=getattr(operation[0], f"{actor}_headers")
    )
    assert response.status_code == expected, response.text
    if expected == 200:
        data = response.json()
        assert data["total"] == 2
        assert {row["occurrence_id"] for row in data["items"]} == set(operation[2][:2])
        for row in data["items"]:
            assert set(row) == {
                "id",
                "occurrence_id",
                "event_type",
                "created_at",
                "channel",
                "simulation_status",
                "processing_status",
            }
            assert row["channel"] == "WHATSAPP_MOCK"
            assert row["event_type"] == "OCCURRENCE_REGISTERED"
            assert row["simulation_status"] == "NOT_ATTEMPTED"
            assert row["processing_status"] == "PENDING"
        assert "Descrição fictícia" not in response.text
        assert "recipient_driver_id" not in response.text


def test_anonymous_cannot_consult_delivery_communications(client, operation):
    assert client.get(path(operation)).status_code == 401


def test_pagination_is_deterministic_and_read_only(client, operation, session_factory):
    headers = operation[0].manager_headers
    with session_factory() as db:
        before = list(
            db.execute(
                select(
                    NotificationRecipient.notification_id,
                    NotificationRecipient.user_id,
                    NotificationRecipient.read_at,
                )
            )
        )
        queue = list(
            db.execute(
                select(OutboxEvent.id, OutboxEvent.status, OutboxEvent.attempt_count)
            )
        )
        count = db.scalar(select(func.count()).select_from(OperationalNotification))

    def page(n, order="asc"):
        response = client.get(
            path(operation),
            headers=headers,
            params={"page": n, "page_size": 1, "sort_order": order},
        )
        assert response.status_code == 200, response.text
        return response.json()

    first, second = page(1), page(2)
    assert first["total"] == second["total"] == 2
    assert first["total_pages"] == second["total_pages"] == 2
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert page(1) == first
    assert page(1, "desc")["items"] == second["items"]
    assert page(3)["items"] == []
    with session_factory() as db:
        assert (
            list(
                db.execute(
                    select(
                        NotificationRecipient.notification_id,
                        NotificationRecipient.user_id,
                        NotificationRecipient.read_at,
                    )
                )
            )
            == before
        )
        assert (
            list(
                db.execute(
                    select(
                        OutboxEvent.id, OutboxEvent.status, OutboxEvent.attempt_count
                    )
                )
            )
            == queue
        )
        assert (
            db.scalar(select(func.count()).select_from(OperationalNotification))
            == count
        )


@pytest.mark.parametrize(
    "params", [{"page": 0}, {"page_size": 101}, {"sort_order": "invalid"}]
)
def test_invalid_pagination_is_rejected(client, operation, params):
    assert (
        client.get(
            path(operation), headers=operation[0].manager_headers, params=params
        ).status_code
        == 422
    )


def test_missing_delivery_returns_stable_404(client, operation):
    response = client.get(
        f"/api/v1/deliveries/{uuid.uuid4()}/communications",
        headers=operation[0].manager_headers,
    )
    assert response.status_code == 404
    assert response.json()["code"] == "DELIVERY_NOT_FOUND"


def test_inactive_driver_cannot_consult_own_communication(
    client, operation, session_factory
):
    from app.modules.drivers.models import Driver

    with session_factory() as db:
        db.get(Driver, operation[0].driver_id).active = False
        db.commit()
    assert (
        client.get(path(operation), headers=operation[0].driver_headers).status_code
        == 403
    )


@pytest.mark.parametrize(
    "grants,expected",
    [
        (("loadx.deliveries.read",), 403),
        (("loadx.occurrences.read",), 403),
        (("loadx.deliveries.read", "loadx.occurrences.read"), 200),
    ],
)
def test_custom_profile_requires_both_effective_permissions(
    client, operation, session_factory, grants, expected
):
    with session_factory() as db:
        name = "Consulta fictícia " + uuid.uuid4().hex
        profile = AccessProfile(name=name, name_key=name.lower(), active=True)
        db.add(profile)
        db.flush()
        for permission in grants:
            db.add(ProfilePermission(profile_id=profile.id, permission_code=permission))
        user = User(
            name="Consulta fictícia",
            email=uuid.uuid4().hex + "@example.test",
            password_hash="hash-fictício",
            role="CUSTOM",
            active=True,
            custom_profile_id=profile.id,
        )
        db.add(user)
        db.commit()
        identifier = user.id
    headers = issue_session_headers(session_factory, identifier)
    assert client.get(path(operation), headers=headers).status_code == expected


def test_trip_wide_started_fact_is_not_attributed_to_delivery(client, operation):
    from tests.integration.test_messages_api import finish_loading

    finish_loading(client, operation[0])
    started = client.patch(
        f"/api/v1/trips/{operation[1]['id']}/status",
        json={"status": "IN_ROUTE"},
        headers=operation[0].manager_headers,
    )
    assert started.status_code == 200, started.text
    response = client.get(path(operation), headers=operation[0].manager_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert {row["occurrence_id"] for row in response.json()["items"]} == set(
        operation[2][:2]
    )


def test_multi_truck_query_never_combines_same_order_across_parts(
    client, session_factory
):
    from tests.integration.oc90_helpers import seed_multi_flow

    flow = seed_multi_flow(client, session_factory)
    flow.approve()
    trips = [flow.create_trip(index) for index in range(2)]
    origins = []
    for trip in trips:
        origins.append(
            flow.request(
                "POST",
                "/occurrences",
                {
                    "trip_id": trip["id"],
                    "delivery_id": trip["deliveries"][0]["id"],
                    "type": "DELAY",
                    "description": "Atraso fictício da parte.",
                },
                expected=201,
            )
        )
    for index, trip in enumerate(trips):
        result = flow.request(
            "GET", f"/deliveries/{trip['deliveries'][0]['id']}/communications"
        )
        assert result["total"] == 1
        assert result["items"][0]["occurrence_id"] == origins[index]["id"]
