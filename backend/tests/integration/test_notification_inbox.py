"""Personal inbox contracts, real PostgreSQL transactions and independent actors."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from app.integrations.whatsapp import mock_whatsapp_provider
from app.modules.access_profiles.models import AccessProfile, ProfilePermission
from app.modules.auth.models import AuthSession
from app.modules.notifications.inbox_repository import InboxRepository
from app.modules.notifications.inbox_service import InboxService
from app.modules.notifications.models import (
    NotificationPreference,
    NotificationRecipient,
    OperationalNotification,
)
from app.modules.notifications.schemas import PreferencesWrite
from app.modules.notifications.service import OperationalNotificationService
from app.modules.occurrences.models import Occurrence
from app.modules.status_history.models import AuditEvent
from app.modules.users.models import User
from tests.integration.auth_helpers import issue_session_headers
from tests.integration.conftest import _required_test_database_url, _run_alembic
from tests.integration.test_deliveries_api import create_trip, seed_operational_scenario
from tests.integration.test_messages_api import finish_loading

BASE = "/api/v1/notifications"


@pytest.fixture(autouse=True)
def isolate_mock():
    mock_whatsapp_provider.sent_messages.clear()
    yield
    mock_whatsapp_provider.sent_messages.clear()


@pytest.fixture
def session_factory(committed_session_factory):
    return committed_session_factory


@pytest.fixture
def operation(client, session_factory):
    scenario = seed_operational_scenario(session_factory)
    return scenario, create_trip(client, scenario)


def register(client, operation):
    scenario, trip = operation
    response = client.post(
        "/api/v1/occurrences",
        headers=scenario.manager_headers,
        json={
            "trip_id": trip["id"],
            "type": "DELAY",
            "description": "Fato fictício da central.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def inbox(client, headers, **params):
    response = client.get(BASE, headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(
    "actor,expected",
    [("admin", 1), ("manager", 1), ("driver", 1), ("other_driver", 0), ("checker", 0)],
)
def test_only_actual_personal_recipients_see_event(client, operation, actor, expected):
    register(client, operation)
    scenario, _ = operation
    result = inbox(client, getattr(scenario, f"{actor}_headers"))
    assert result["total"] == expected
    assert result["unread_count"] == expected
    if expected:
        item = result["items"][0]
        assert item["read_at"] is None
        assert item["event_type"] == "OCCURRENCE_REGISTERED"
        assert set(item) == {
            "id",
            "event_type",
            "category",
            "title",
            "summary",
            "created_at",
            "received_at",
            "read_at",
        }


def test_read_is_personal_and_idempotent_without_changing_channel(
    client, operation, session_factory
):
    register(client, operation)
    scenario, _ = operation
    item = inbox(client, scenario.driver_headers)["items"][0]
    with session_factory() as db:
        initial_mock = db.get(
            OperationalNotification, uuid.UUID(item["id"])
        ).mock_status
    first = client.post(f"{BASE}/{item['id']}/read", headers=scenario.driver_headers)
    second = client.post(f"{BASE}/{item['id']}/read", headers=scenario.driver_headers)
    assert first.status_code == 200
    assert second.json()["read_at"] == first.json()["read_at"]
    assert first.json()["read_at"] is not None
    assert inbox(client, scenario.driver_headers)["unread_count"] == 0
    assert inbox(client, scenario.admin_headers)["unread_count"] == 1
    with session_factory() as db:
        assert (
            db.get(OperationalNotification, uuid.UUID(item["id"])).mock_status
            == initial_mock
        )


def test_admin_cannot_read_another_accounts_suppressed_notification(client, operation):
    scenario, _ = operation
    response = client.put(
        f"{BASE}/preferences",
        headers=scenario.admin_headers,
        json={"items": [{"category": "OCCURRENCES", "enabled": False}]},
    )
    assert response.status_code == 200
    register(client, operation)
    item = inbox(client, scenario.driver_headers)["items"][0]
    assert inbox(client, scenario.admin_headers)["total"] == 0
    for suffix, method in (("read", client.post), ("source", client.get)):
        denied = method(f"{BASE}/{item['id']}/{suffix}", headers=scenario.admin_headers)
        assert denied.status_code == 404


def test_pagination_filters_and_counter_share_consistent_scope(
    client, operation, session_factory
):
    scenario, _ = operation
    for _ in range(3):
        register(client, operation)
    pages = [
        inbox(client, scenario.manager_headers, page=page, page_size=1)
        for page in (1, 2, 3)
    ]
    ids = [result["items"][0]["id"] for result in pages]
    assert len(set(ids)) == 3
    assert (
        inbox(client, scenario.manager_headers, page=1, page_size=1)["items"][0]["id"]
        == ids[0]
    )
    oldest = inbox(client, scenario.manager_headers, page_size=100, sort_order="asc")
    assert [item["id"] for item in oldest["items"]] == list(reversed(ids))
    client.post(f"{BASE}/{ids[0]}/read", headers=scenario.manager_headers)
    filtered = inbox(
        client, scenario.manager_headers, read=True, category="OCCURRENCES"
    )
    assert filtered["total"] == 1
    assert filtered["unread_count"] == 2
    assert inbox(client, scenario.manager_headers, read=False)["total"] == 2
    assert inbox(client, scenario.manager_headers, category="TRIPS")["total"] == 0
    assert (
        inbox(client, scenario.manager_headers, category="SECURITY")["unread_count"]
        == 2
    )
    assert inbox(client, scenario.manager_headers, page=99)["items"] == []
    assert client.get(
        f"{BASE}/unread-count", headers=scenario.manager_headers
    ).json() == {"unread_count": 2}


def test_read_all_is_idempotent_and_does_not_read_future_events_or_other_boxes(
    client, operation
):
    scenario, _ = operation
    register(client, operation)
    register(client, operation)
    assert client.post(f"{BASE}/read-all", headers=scenario.manager_headers).json() == {
        "updated": 2
    }
    assert client.post(f"{BASE}/read-all", headers=scenario.manager_headers).json() == {
        "updated": 0
    }
    register(client, operation)
    assert inbox(client, scenario.manager_headers)["unread_count"] == 1
    assert inbox(client, scenario.driver_headers)["unread_count"] == 3


def test_preferences_suppress_only_future_receipts_and_audit_changes(
    client, operation, session_factory
):
    scenario, _ = operation
    register(client, operation)
    payload = {"items": [{"category": "OCCURRENCES", "enabled": False}]}
    assert (
        client.put(
            f"{BASE}/preferences", json=payload, headers=scenario.driver_headers
        ).status_code
        == 200
    )
    register(client, operation)
    assert inbox(client, scenario.driver_headers)["total"] == 1
    assert inbox(client, scenario.manager_headers)["total"] == 2
    assert (
        client.get(f"{BASE}/preferences", headers=scenario.driver_headers).json()[
            "items"
        ][1]["enabled"]
        is False
    )
    payload["items"][0]["enabled"] = True
    client.put(f"{BASE}/preferences", json=payload, headers=scenario.driver_headers)
    assert inbox(client, scenario.driver_headers)["total"] == 1
    register(client, operation)
    assert inbox(client, scenario.driver_headers)["total"] == 2
    with session_factory() as db:
        events = db.scalars(
            select(AuditEvent).where(
                AuditEvent.changed_fields == "notification_preferences.OCCURRENCES"
            )
        ).all()
        assert len(events) == 2
        assert all(row.actor_id == row.entity_id for row in events)


@pytest.mark.parametrize(
    "items",
    [
        [{"category": "SECURITY", "enabled": False}],
        [{"category": "DOCUMENTS", "enabled": True}],
        [{"category": "TRIPS", "enabled": True}] * 2,
        [{"category": "TRIPS", "enabled": "false"}],
        [],
    ],
)
def test_invalid_preferences_never_silence_security(client, operation, items):
    scenario, _ = operation
    response = client.put(
        f"{BASE}/preferences", headers=scenario.manager_headers, json={"items": items}
    )
    assert response.status_code == 422
    security = client.get(
        f"{BASE}/preferences", headers=scenario.manager_headers
    ).json()["items"][2]
    assert security == {"category": "SECURITY", "enabled": True, "mandatory": True}


@pytest.mark.parametrize("protection", ["anonymous", "csrf", "origin"])
def test_authentication_csrf_and_origin_are_preserved(client, operation, protection):
    scenario, _ = operation
    headers = dict(scenario.manager_headers)
    if protection == "anonymous":
        headers = {}
    elif protection == "csrf":
        headers.pop("X-CSRF-Token")
    else:
        headers["Origin"] = "https://untrusted.example.test"
    response = client.post(f"{BASE}/read-all", headers=headers)
    assert response.status_code == (401 if protection == "anonymous" else 403)


def test_origin_is_real_and_reauthorization_hides_revoked_access(
    client, operation, session_factory
):
    scenario, trip = operation
    register(client, operation)
    item = inbox(client, scenario.driver_headers)["items"][0]
    source = client.get(f"{BASE}/{item['id']}/source", headers=scenario.driver_headers)
    assert source.json() == {"href": f"/trips/{trip['id']}"}
    assert (
        client.get(
            f"/api/v1/trips/{trip['id']}", headers=scenario.driver_headers
        ).status_code
        == 200
    )
    with session_factory() as db:
        driver_user = db.scalar(
            select(User).where(User.driver_id == scenario.driver_id)
        )
        driver_user.driver_id = None
        db.commit()
    assert inbox(client, scenario.driver_headers)["total"] == 0
    assert (
        client.get(
            f"{BASE}/{item['id']}/source", headers=scenario.driver_headers
        ).status_code
        == 404
    )
    assert inbox(client, scenario.manager_headers)["total"] == 1


def test_multiple_drivers_never_share_boxes(client, operation, session_factory):
    first = operation
    second_scenario = seed_operational_scenario(session_factory)
    second = second_scenario, create_trip(client, second_scenario)
    register(client, first)
    register(client, second)
    own = inbox(client, first[0].driver_headers)
    other = inbox(client, second[0].driver_headers)
    assert own["total"] == 1
    assert other["total"] == 1
    assert own["items"][0]["id"] != other["items"][0]["id"]
    assert (
        client.post(
            f"{BASE}/{other['items'][0]['id']}/read", headers=first[0].driver_headers
        ).status_code
        == 404
    )


def test_concurrent_read_keeps_first_timestamp(client, operation, session_factory):
    scenario, _ = operation
    register(client, operation)
    identifier = uuid.UUID(inbox(client, scenario.driver_headers)["items"][0]["id"])
    barrier = Barrier(2)

    def read():
        with session_factory() as db:
            user = db.scalar(select(User).where(User.driver_id == scenario.driver_id))
            barrier.wait(timeout=10)
            return InboxService(db).mark_read(user, identifier).read_at

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: read(), range(2)))
    assert results[0] == results[1]
    assert inbox(client, scenario.driver_headers)["unread_count"] == 0


def test_snapshot_replay_does_not_add_new_account_and_no_get_writes(
    client, operation, session_factory
):
    scenario, trip = operation
    occurrence = register(client, operation)
    with session_factory() as db:
        notification = db.scalar(
            select(OperationalNotification).where(
                OperationalNotification.occurrence_id == uuid.UUID(occurrence["id"])
            )
        )
        before = db.scalar(select(func.count()).select_from(NotificationRecipient))
        user = User(
            name="Nova conta",
            email="later@example.test",
            password_hash="fixture",
            role="ADMIN",
            active=True,
        )
        db.add(user)
        db.commit()
        identity = user.id
        OperationalNotificationService().stage(
            db,
            event_type="OCCURRENCE_REGISTERED",
            trip_id=uuid.UUID(trip["id"]),
            recipient_driver_id=scenario.driver_id,
            occurrence_id=uuid.UUID(occurrence["id"]),
        )
        db.commit()
        assert (
            db.scalar(select(func.count()).select_from(NotificationRecipient)) == before
        )
        notification_id = notification.id
    headers = issue_session_headers(session_factory, identity)
    assert inbox(client, headers)["total"] == 0
    assert (
        client.get(f"{BASE}/{notification_id}/source", headers=headers).status_code
        == 404
    )


def test_recipient_failure_rolls_back_domain_fact(
    client, operation, session_factory, monkeypatch
):
    scenario, trip = operation

    def fail(*args, **kwargs):
        raise RuntimeError("fixture recipient failure")

    monkeypatch.setattr(InboxRepository, "stage_recipients", fail)
    result = client.post(
        "/api/v1/occurrences",
        headers=scenario.manager_headers,
        json={"trip_id": trip["id"], "type": "DELAY", "description": "Fato fictício"},
    )
    assert result.status_code == 500
    assert (
        client.get(
            f"/api/v1/trips/{trip['id']}/occurrences", headers=scenario.manager_headers
        ).json()
        == []
    )
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(OperationalNotification)) == 0


def test_native_constraints_protect_recipient_and_required_preference(
    client, operation, session_factory
):
    register(client, operation)
    with session_factory() as db:
        row = db.scalar(select(NotificationRecipient))
        statement = (
            update(NotificationRecipient)
            .where(NotificationRecipient.user_id == row.user_id)
            .values(user_id=uuid.uuid4())
        )
        with pytest.raises(IntegrityError):
            db.execute(statement)
        db.rollback()
        preference = NotificationPreference(
            user_id=row.user_id, category="SECURITY", enabled=False
        )
        db.add(preference)
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_migration_backfills_real_facts_and_refuses_loss(
    client, operation, session_factory
):
    from importlib import import_module

    scenario, _ = operation
    register(client, operation)
    with session_factory() as db:
        original = list(db.scalars(select(OperationalNotification.id)))
        db.execute(delete(NotificationRecipient))
        db.commit()
    from tests.integration.notification_helpers import clear_outbox_fixture

    with session_factory() as db:
        clear_outbox_fixture(db)
        db.commit()
    # Target OC103's parent even when newer revisions (such as OC90) exist.
    _run_alembic(_required_test_database_url(), "downgrade", "20261020_0025")
    _run_alembic(_required_test_database_url(), "upgrade", "head")
    assert inbox(client, scenario.driver_headers)["total"] == 1
    with session_factory() as db:
        assert list(db.scalars(select(OperationalNotification.id))) == original
        migration = import_module(
            "migrations.versions.20261020_0026_notification_inbox"
        )
        connection = db.connection()
        with pytest.raises(RuntimeError, match="OC103 downgrade blocked"):
            migration.ensure_safe_downgrade(connection)


@pytest.mark.parametrize(
    "permissions,expected_trip,expected_occurrence",
    [
        (["loadx.trips.read"], 1, 0),
        (["loadx.occurrences.read"], 0, 0),
        (["loadx.trips.read", "loadx.occurrences.read"], 1, 1),
    ],
)
def test_custom_profiles_follow_effective_permissions_and_revocation(
    client,
    operation,
    session_factory,
    permissions,
    request,
    expected_trip,
    expected_occurrence,
):
    scenario, trip = operation
    with session_factory() as db:
        profile_name = f"Operador da central {uuid.uuid4().hex}"
        profile = AccessProfile(
            name=profile_name,
            name_key=profile_name.lower(),
            description="Perfil fictício",
            active=True,
        )
        db.add(profile)
        db.flush()
        profile_id = profile.id
        db.add_all(
            ProfilePermission(profile_id=profile.id, permission_code=code)
            for code in permissions
        )
        user = User(
            name="Operador personalizado",
            email="custom-inbox@example.test",
            password_hash="fixture",
            role="CUSTOM",
            custom_profile_id=profile.id,
            active=True,
        )
        db.add(user)
        db.commit()
        user_id = user.id

    def cleanup_custom_identity():
        with session_factory() as db:
            db.execute(
                delete(NotificationRecipient).where(
                    NotificationRecipient.user_id == user_id
                )
            )
            db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
            db.execute(delete(User).where(User.id == user_id))
            db.execute(
                delete(ProfilePermission).where(
                    ProfilePermission.profile_id == profile_id
                )
            )
            db.execute(delete(AccessProfile).where(AccessProfile.id == profile_id))
            db.commit()

    request.addfinalizer(cleanup_custom_identity)
    headers = issue_session_headers(session_factory, user_id)
    register(client, operation)
    finish_loading(client, scenario)
    started = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        headers=scenario.manager_headers,
        json={"status": "IN_ROUTE"},
    )
    assert started.status_code == 200
    assert inbox(client, headers, category="TRIPS")["total"] == expected_trip
    assert (
        inbox(client, headers, category="OCCURRENCES")["total"] == expected_occurrence
    )
    with session_factory() as db:
        db.execute(
            delete(ProfilePermission).where(ProfilePermission.profile_id == profile_id)
        )
        db.commit()
    assert inbox(client, headers)["total"] == 0


def test_tied_timestamps_have_stable_id_order(client, operation, session_factory):
    scenario, trip = operation
    with session_factory() as db:
        identifiers = []
        for _ in range(3):
            event = Occurrence(
                trip_id=uuid.UUID(trip["id"]),
                type="DELAY",
                description="Fato fictício simultâneo",
            )
            db.add(event)
            db.flush()
            identifiers.append(
                OperationalNotificationService().stage(
                    db,
                    event_type="OCCURRENCE_REGISTERED",
                    trip_id=event.trip_id,
                    recipient_driver_id=scenario.driver_id,
                    occurrence_id=event.id,
                )
            )
        db.commit()
    result = inbox(client, scenario.driver_headers, sort_order="asc")
    assert len({row["created_at"] for row in result["items"]}) == 1
    assert [row["id"] for row in result["items"]] == sorted(map(str, identifiers))


def test_concurrent_preferences_are_idempotent_and_audited_once(
    client, operation, session_factory
):
    scenario, _ = operation
    barrier = Barrier(2)
    data = PreferencesWrite(items=[{"category": "OCCURRENCES", "enabled": False}])

    def save():
        with session_factory() as db:
            user = db.scalar(select(User).where(User.driver_id == scenario.driver_id))
            barrier.wait(timeout=10)
            return InboxService(db).save_preferences(user, data)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: save(), range(2)))
    assert results[0] == results[1]
    with session_factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.changed_fields == "notification_preferences.OCCURRENCES"
                )
            )
            == 1
        )


def test_concurrent_event_replay_keeps_exact_recipient_snapshot(
    client, operation, session_factory
):
    scenario, trip = operation
    occurrence = register(client, operation)
    barrier = Barrier(2)

    def replay():
        with session_factory() as db:
            barrier.wait(timeout=10)
            identifier = OperationalNotificationService().stage(
                db,
                event_type="OCCURRENCE_REGISTERED",
                trip_id=uuid.UUID(trip["id"]),
                recipient_driver_id=scenario.driver_id,
                occurrence_id=uuid.UUID(occurrence["id"]),
            )
            db.commit()
            return identifier

    with ThreadPoolExecutor(max_workers=2) as pool:
        identifiers = list(pool.map(lambda _: replay(), range(2)))
    assert identifiers[0] == identifiers[1]
    with session_factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(NotificationRecipient)
                .where(NotificationRecipient.notification_id == identifiers[0])
            )
            == 3
        )


def test_preference_audit_failure_rolls_back_preference(client, operation, monkeypatch):
    from app.modules.status_history.service import AuditService

    scenario, _ = operation

    def fail(*args, **kwargs):
        raise RuntimeError("fixture audit failure")

    monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
    result = client.put(
        f"{BASE}/preferences",
        headers=scenario.driver_headers,
        json={"items": [{"category": "TRIPS", "enabled": False}]},
    )
    assert result.status_code == 500
    preferences = client.get(
        f"{BASE}/preferences", headers=scenario.driver_headers
    ).json()
    assert preferences["items"][0]["enabled"] is True


@pytest.mark.parametrize(
    "path",
    [
        BASE,
        f"{BASE}/unread-count",
        f"{BASE}/preferences",
        f"{BASE}/{uuid.uuid4()}/source",
    ],
)
def test_unauthenticated_queries_never_expose_inbox(client, path):
    result = client.get(path)
    assert result.status_code == 401
