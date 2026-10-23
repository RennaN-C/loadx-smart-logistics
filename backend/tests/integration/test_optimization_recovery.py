"""Real PostgreSQL transactions; fault injection models an unread committed response."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from threading import Event

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.modules.access_profiles.models import AccessProfile, ProfilePermission
from app.modules.auth.models import AuthSession
from app.modules.load_planning.distribution_models import (
    LoadDistribution,
    OptimizationRequest,
)
from app.modules.load_planning.distribution_schemas import DistributionNeedRequest
from app.modules.load_planning.distribution_service import (
    LoadDistributionService,
)
from app.modules.users.models import User
from tests.integration.auth_helpers import issue_session_headers
from tests.integration.test_load_distributions import distribution_scenario
from tests.integration.test_load_planning_api import (
    AuthenticatedUser,
    create_authenticated_user,
)

__all__ = ("distribution_scenario",)
BASE = "/api/v1/load-distributions"


def send(s, key, orders=None):
    return s.client.post(
        BASE + "/optimize",
        headers={**s.user.headers, "Idempotency-Key": str(key)},
        json={"order_ids": orders or [str(s.source.order_id)]},
    )


def recover(s, key, user=None):
    return s.client.get(
        BASE + f"/optimization-requests/{key}", headers=(user or s.user).headers
    )


def assert_one(s, identifier):
    with s.factory() as db:
        assert db.scalar(select(func.count()).select_from(OptimizationRequest)) == 1
        assert db.scalar(select(func.count()).select_from(LoadDistribution)) == 1
        request = db.scalar(select(OptimizationRequest))
        assert str(request.distribution_id) == identifier


def test_replay_and_recovery_do_not_run_optimizer_or_duplicate_after_commit(
    distribution_scenario, monkeypatch
):
    s = distribution_scenario
    key = uuid.uuid4()
    first = send(s, key)
    assert first.status_code == 201, first.text

    def forbidden(*args, **kwargs):
        raise AssertionError("Replay must never calculate")

    monkeypatch.setattr(LoadDistributionService, "_optimize", forbidden)
    replay = send(s, key)
    recovered = recover(s, key)
    assert replay.status_code == 201 and recovered.status_code == 200
    assert replay.json() == recovered.json() == first.json()
    assert_one(s, first.json()["id"])


def test_response_lost_after_actual_commit_recovers_with_same_key(
    distribution_scenario, monkeypatch
):
    s = distribution_scenario
    key = uuid.uuid4()
    original = LoadDistributionService._commit

    def lose_response(service, identifier):
        original(service, identifier)
        raise TimeoutError("Injected response loss AFTER commit")

    monkeypatch.setattr(LoadDistributionService, "_commit", lose_response)
    assert send(s, key).status_code == 500
    recovered = recover(s, key)
    assert recovered.status_code == 200
    assert send(s, key).json()["id"] == recovered.json()["id"]
    assert_one(s, recovered.json()["id"])


def test_different_payload_cannot_reuse_successful_key(distribution_scenario):
    s = distribution_scenario
    key = uuid.uuid4()
    first = send(s, key)
    conflict = send(s, key, [str(uuid.uuid4())])
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"
    assert_one(s, first.json()["id"])


def test_rollback_and_timeout_before_commit_allow_safe_retry(
    distribution_scenario, monkeypatch
):
    s = distribution_scenario
    key = uuid.uuid4()
    original = LoadDistributionService._history

    def fail(*args, **kwargs):
        raise TimeoutError("Injected failure before commit")

    monkeypatch.setattr(LoadDistributionService, "_history", fail)
    assert send(s, key).status_code == 500
    assert recover(s, key).status_code == 404
    with s.factory() as db:
        assert db.scalar(select(func.count()).select_from(OptimizationRequest)) == 0
        assert db.scalar(select(func.count()).select_from(LoadDistribution)) == 0
    monkeypatch.setattr(LoadDistributionService, "_history", original)
    result = send(s, key)
    assert result.status_code == 201
    assert_one(s, result.json()["id"])


def test_concurrent_same_request_is_nonblocking_and_recovers_after_worker_commit(
    distribution_scenario, monkeypatch
):
    s = distribution_scenario
    entered, release = Event(), Event()
    original = LoadDistributionService._optimize
    key = uuid.uuid4()
    data = DistributionNeedRequest(order_ids=[s.source.order_id])

    def paused(service, *args, **kwargs):
        entered.set()
        assert release.wait(10)
        return original(service, *args, **kwargs)

    monkeypatch.setattr(LoadDistributionService, "_optimize", paused)

    def first():
        with s.factory() as db:
            return LoadDistributionService(db).optimize(
                data, changed_by=s.user.id, idempotency_key=key
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(first)
        try:
            assert entered.wait(10)
            conflict = send(s, key)
            assert conflict.status_code == 409
            assert conflict.json()["code"] == "OPTIMIZATION_IN_PROGRESS"
            assert recover(s, key).json()["code"] == "OPTIMIZATION_IN_PROGRESS"
        finally:
            release.set()
        result = future.result(timeout=15)
    assert recover(s, key).json()["id"] == str(result.id)
    assert send(s, key).json()["id"] == str(result.id)
    assert_one(s, str(result.id))


@pytest.mark.parametrize(
    "role,status",
    [
        ("ADMIN", 404),
        ("LOGISTICS_MANAGER", 404),
        ("CHECKER", 403),
        ("DRIVER", 403),
        ("CUSTOM", 403),
        ("CUSTOM_CREATE", 404),
    ],
)
def test_recovery_is_actor_scoped_and_rbac_protected(
    distribution_scenario, role, status
):
    s = distribution_scenario
    key = uuid.uuid4()
    assert send(s, key).status_code == 201
    profile_id = None
    if role.startswith("CUSTOM"):
        profile_id, user_id = uuid.uuid4(), uuid.uuid4()
        with s.factory() as db:
            db.add(
                AccessProfile(
                    id=profile_id,
                    name=str(profile_id),
                    name_key=str(profile_id),
                    active=True,
                )
            )
            db.flush()
            if role == "CUSTOM_CREATE":
                db.add(
                    ProfilePermission(
                        profile_id=profile_id,
                        permission_code="loadx.planning.create",
                        delegable=True,
                    )
                )
            db.add(
                User(
                    id=user_id,
                    name="Perfil fictício",
                    email=f"{user_id}@example.test",
                    password_hash="fixture-only",
                    role="CUSTOM",
                    custom_profile_id=profile_id,
                    active=True,
                )
            )
            db.commit()
        other = AuthenticatedUser(user_id, issue_session_headers(s.factory, user_id))
    else:
        other = create_authenticated_user(s.factory, role)
    try:
        assert recover(s, key, other).status_code == status
    finally:
        with s.factory() as db:
            db.execute(delete(AuthSession).where(AuthSession.user_id == other.id))
            db.execute(delete(User).where(User.id == other.id))
            if profile_id:
                db.execute(
                    delete(ProfilePermission).where(
                        ProfilePermission.profile_id == profile_id
                    )
                )
                db.execute(delete(AccessProfile).where(AccessProfile.id == profile_id))
            db.commit()


def test_unknown_anonymous_and_invalid_key_contract(distribution_scenario):
    s = distribution_scenario
    assert recover(s, uuid.uuid4()).status_code == 404
    assert (
        s.client.get(BASE + f"/optimization-requests/{uuid.uuid4()}").status_code == 401
    )
    assert send(s, "invalid").status_code == 422
    assert (
        s.post("/optimize", {"order_ids": [str(s.source.order_id)]}).status_code == 201
    )


def test_record_constraints_and_populated_downgrade_protect_recovery(
    distribution_scenario,
):
    s = distribution_scenario
    key = uuid.uuid4()
    identifier = uuid.UUID(send(s, key).json()["id"])
    with s.factory() as db, pytest.raises(IntegrityError):
        db.add(
            OptimizationRequest(
                user_id=s.user.id,
                request_key=uuid.uuid4(),
                payload_hash="x" * 64,
                distribution_id=identifier,
            )
        )
        db.commit()
    migration = import_module("migrations.versions.20261023_0035_optimization_requests")
    with (
        s.factory() as db,
        Operations.context(MigrationContext.configure(db.connection())),
        pytest.raises(RuntimeError, match="Downgrade blocked"),
    ):
        migration.downgrade()
