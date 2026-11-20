"""G05-C PostgreSQL isolation of optimization identity, recovery and locks."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from app.modules.customers.models import Customer
from app.modules.load_planning.distribution_models import (
    LoadDistribution,
    LoadDistributionOrder,
    LoadDistributionPart,
    LoadDistributionVolume,
    OptimizationRequest,
)
from app.modules.load_planning.distribution_schemas import DistributionNeedRequest
from app.modules.load_planning.distribution_service import (
    DistributionError,
    LoadDistributionService,
)
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.load_planning.optimization_repository import OptimizationRepository
from app.modules.load_planning.repository import LoadPlanRepository
from app.modules.orders.models import Order, OrderItem
from app.modules.organizations.models import (
    LEGACY_ORGANIZATION_ID,
    Organization,
    OrganizationMembership,
)
from app.modules.products.models import Product
from app.modules.trucks.models import Truck
from app.modules.users.models import User
from tests.integration.test_load_distributions import distribution_scenario
from tests.integration.test_tenancy_g05b import (
    _order_and_item,
    _plan,
    _rejected_volume,
    _truck,
)

__all__ = ("distribution_scenario",)
BASE = "/api/v1/load-distributions"


def _organization(db):
    organization = Organization(
        legal_name="Transportadora fictícia G05-C",
        display_name="Teste G05-C",
        status="PENDING",
    )
    db.add(organization)
    db.flush()
    return organization


def _actor(db, organization_ids):
    actor = User(
        name="Identidade fictícia G05-C",
        email=f"g05c-{uuid.uuid4().hex}@example.test",
        password_hash="fixture-only",
        role="LOGISTICS_MANAGER",
        active=True,
    )
    db.add(actor)
    db.flush()
    for organization_id in organization_ids:
        db.add(
            OrganizationMembership(
                organization_id=organization_id,
                user_id=actor.id,
                role="LOGISTICS_MANAGER",
                status="ACTIVE",
            )
        )
    db.flush()
    return actor


def _request(db, organization_id, actor_id, key):
    result = LoadDistribution(created_by=actor_id, status="PROPOSED")
    db.add(result)
    db.flush()
    request = OptimizationRequest(
        organization_id=organization_id,
        user_id=actor_id,
        request_key=key,
        payload_hash="a" * 64,
        distribution_id=result.id,
    )
    return request


def test_same_actor_and_key_have_distinct_results_per_organization(session_factory):
    with session_factory() as db:
        other = _organization(db)
        actor = _actor(db, [LEGACY_ORGANIZATION_ID, other.id])
        key = uuid.uuid4()
        repository_a = OptimizationRepository(db, LEGACY_ORGANIZATION_ID)
        repository_b = OptimizationRepository(db, other.id)
        request_a = _request(db, LEGACY_ORGANIZATION_ID, actor.id, key)
        request_b = _request(db, other.id, actor.id, key)
        repository_a.add(request_a)
        repository_b.add(request_b)
        db.flush()

        assert repository_a.get(actor.id, key) is request_a
        assert repository_b.get(actor.id, key) is request_b
        assert request_a.distribution_id != request_b.distribution_id
        assert repository_a.get(uuid.uuid4(), key) is None


def test_cached_known_request_from_b_is_not_returned_in_a(session_factory):
    with session_factory() as db:
        other = _organization(db)
        actor = _actor(db, [LEGACY_ORGANIZATION_ID, other.id])
        key = uuid.uuid4()
        request_b = _request(db, other.id, actor.id, key)
        OptimizationRepository(db, other.id).add(request_b)
        db.flush()

        assert db.get(OptimizationRequest, (other.id, actor.id, key)) is request_b
        assert (
            OptimizationRepository(db, LEGACY_ORGANIZATION_ID).get(actor.id, key)
            is None
        )


def test_repository_rejects_forged_organization_before_persisting(session_factory):
    with session_factory() as db:
        other = _organization(db)
        actor = _actor(db, [other.id])
        request = _request(db, other.id, actor.id, uuid.uuid4())
        with pytest.raises(ValueError, match="different organization"):
            OptimizationRepository(db, LEGACY_ORGANIZATION_ID).add(request)
        assert request not in db


@pytest.mark.parametrize("missing_organization", [False, True])
def test_database_rejects_missing_organization_or_membership(
    session_factory,
    missing_organization,
):
    with session_factory() as db:
        other = _organization(db)
        actor = _actor(db, [LEGACY_ORGANIZATION_ID])
        request = _request(
            db,
            None if missing_organization else other.id,
            actor.id,
            uuid.uuid4(),
        )
        with pytest.raises(IntegrityError) as error, db.begin_nested():
            db.add(request)
            db.flush()
        assert error.value.orig.sqlstate == (
            "23502" if missing_organization else "23503"
        )


def test_advisory_locks_are_independent_between_organizations(session_factory):
    actor, key, other = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    def competing(organization_id):
        with (
            session_factory() as db,
            OptimizationRepository(db, organization_id).session_lock(
                actor, key
            ) as acquired,
        ):
            return acquired

    with (
        session_factory() as db,
        OptimizationRepository(db, LEGACY_ORGANIZATION_ID).session_lock(
            actor, key
        ) as acquired,
    ):
        assert acquired
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert (
                pool.submit(competing, LEGACY_ORGANIZATION_ID).result(timeout=5)
                is False
            )
            assert pool.submit(competing, other).result(timeout=5) is True
    assert competing(LEGACY_ORGANIZATION_ID) is True


def test_advisory_lock_is_released_after_worker_exception(session_factory):
    actor, key = uuid.uuid4(), uuid.uuid4()
    with session_factory() as db:
        repository = OptimizationRepository(db, LEGACY_ORGANIZATION_ID)
        with (
            pytest.raises(TimeoutError, match="interrupted"),
            repository.session_lock(actor, key) as acquired,
        ):
            assert acquired
            raise TimeoutError("interrupted optimization")
        with repository.session_lock(actor, key) as acquired:
            assert acquired


@pytest.fixture
def foreign_optimization(distribution_scenario):
    s = distribution_scenario
    with s.factory() as db:
        organization = _organization(db)
        organization_id = organization.id
        db.add(
            OrganizationMembership(
                organization_id=organization_id,
                user_id=s.user.id,
                role="CHECKER",
                status="ACTIVE",
            )
        )
        order, item, product = _order_and_item(db, organization_id)
        order.status = "READY"
        order_id, customer_id = order.id, order.customer_id
        item_id, product_id = item.id, product.id
        truck = _truck(db, organization_id, "G05C101")
        truck_id = truck.id
        plan = _plan(organization_id, truck_id)
        plan.status = "CALCULATED"
        plan.loaded_count, plan.unloaded_count = 1, 0
        plan.used_volume_cm3 = 6000
        plan.occupancy_percent = Decimal("0.60")
        plan.total_weight_kg = product.weight_kg
        plan.orders = [LoadPlanOrder(order_id=order.id)]
        volume = _rejected_volume(None, order, item, product)
        volume.placed, volume.rejection_reason = True, None
        volume.position_x_cm = volume.position_y_cm = volume.position_z_cm = 0
        volume.used_width_cm, volume.used_height_cm, volume.used_length_cm = 10, 20, 30
        volume.rotation_code, volume.loading_sequence = "XYZ", 1
        plan.items = [volume]
        LoadPlanRepository(db, organization_id).add(plan)
        db.flush()
        plan_id = plan.id
        key = uuid.uuid4()
        request = _request(db, organization_id, s.user.id, key)
        distribution_id = request.distribution_id
        db.add(
            LoadDistributionOrder(distribution_id=distribution_id, order_id=order_id)
        )
        part = LoadDistributionPart(
            distribution_id=distribution_id,
            load_plan_id=plan_id,
            status="PENDING",
        )
        db.add(part)
        db.flush()
        db.add(
            LoadDistributionVolume(
                distribution_id=distribution_id,
                part_id=part.id,
                order_id=order_id,
                order_item_id=item_id,
                product_id=product_id,
                snapshot_quantity=1,
                volume_index=1,
                active=True,
            )
        )
        OptimizationRepository(db, organization_id).add(request)
        db.flush()
        # Prove physical coverage, partition and lifecycle are valid. Recovery
        # must fail because of tenant ownership, not incomplete test data.
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        db.commit()
    try:
        yield s, organization_id, key, distribution_id
    finally:
        with s.factory() as db:
            db.execute(
                delete(OptimizationRequest).where(
                    OptimizationRequest.distribution_id == distribution_id
                )
            )
            db.execute(
                delete(LoadDistributionVolume).where(
                    LoadDistributionVolume.distribution_id == distribution_id
                )
            )
            db.execute(
                delete(LoadDistributionPart).where(
                    LoadDistributionPart.distribution_id == distribution_id
                )
            )
            db.execute(
                delete(LoadDistributionOrder).where(
                    LoadDistributionOrder.distribution_id == distribution_id
                )
            )
            db.execute(
                delete(LoadDistribution).where(LoadDistribution.id == distribution_id)
            )
            db.execute(delete(LoadPlanItem).where(LoadPlanItem.load_plan_id == plan_id))
            db.execute(
                delete(LoadPlanOrder).where(LoadPlanOrder.load_plan_id == plan_id)
            )
            db.execute(delete(LoadPlan).where(LoadPlan.id == plan_id))
            db.execute(delete(Truck).where(Truck.id == truck_id))
            db.execute(delete(OrderItem).where(OrderItem.id == item_id))
            db.execute(delete(Order).where(Order.id == order_id))
            db.execute(delete(Product).where(Product.id == product_id))
            db.execute(delete(Customer).where(Customer.id == customer_id))
            db.execute(
                delete(OrganizationMembership).where(
                    OrganizationMembership.organization_id == organization_id
                )
            )
            db.execute(delete(Organization).where(Organization.id == organization_id))
            db.commit()


def test_http_cannot_recover_b_or_select_tenant_with_query_or_header(
    foreign_optimization,
):
    s, organization_id, key, distribution_id = foreign_optimization
    response = s.client.get(
        BASE + f"/optimization-requests/{key}",
        headers={**s.user.headers, "X-Organization-ID": str(organization_id)},
        params={"organization_id": str(organization_id)},
    )
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "OPTIMIZATION_NOT_FOUND"
    assert str(distribution_id) not in response.text


def test_http_forged_tenant_does_not_change_optimization_identity(foreign_optimization):
    s, organization_id, key, distribution_id = foreign_optimization
    headers = {
        **s.user.headers,
        "X-Organization-ID": str(organization_id),
        "Idempotency-Key": str(key),
    }
    body = {"order_ids": [str(s.source.order_id)]}
    forbidden_body = s.client.post(
        BASE + "/optimize",
        headers=headers,
        json={**body, "organization_id": str(organization_id)},
    )
    assert forbidden_body.status_code == 422
    response = s.client.post(
        BASE + "/optimize",
        headers=headers,
        json=body,
        params={"organization_id": str(organization_id)},
    )
    assert response.status_code == 201, response.text
    assert response.json()["id"] != str(distribution_id)
    with s.factory() as db:
        request_a = OptimizationRepository(db, LEGACY_ORGANIZATION_ID).get(
            s.user.id, key
        )
        request_b = OptimizationRepository(db, organization_id).get(s.user.id, key)
        assert str(request_a.distribution_id) == response.json()["id"]
        assert request_b.distribution_id == distribution_id


def test_recovery_refuses_legacy_request_pointing_to_b_result(foreign_optimization):
    s, organization_id, key, distribution_id = foreign_optimization
    # G06 adds the final composite result FK. Until then service validation must
    # reject an inconsistent legacy row rather than returning foreign snapshots.
    with s.factory() as db:
        request_b = OptimizationRepository(db, organization_id).get(s.user.id, key)
        db.delete(request_b)
        db.flush()
        OptimizationRepository(db, LEGACY_ORGANIZATION_ID).add(
            OptimizationRequest(
                organization_id=LEGACY_ORGANIZATION_ID,
                user_id=s.user.id,
                request_key=key,
                payload_hash="a" * 64,
                distribution_id=distribution_id,
            )
        )
        db.commit()
    response = s.client.get(
        BASE + f"/optimization-requests/{key}",
        headers=s.user.headers,
    )
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "OPTIMIZATION_NOT_FOUND"
    assert str(distribution_id) not in response.text


def test_recovery_checks_foreign_order_even_when_every_plan_is_local(
    foreign_optimization,
):
    s, organization_id, _, foreign_distribution_id = foreign_optimization
    key = uuid.uuid4()
    result = s.client.post(
        BASE + "/optimize",
        headers={**s.user.headers, "Idempotency-Key": str(key)},
        json={"order_ids": [str(s.source.order_id)]},
    )
    assert result.status_code == 201, result.text
    distribution_id = uuid.UUID(result.json()["id"])
    with s.factory() as db:
        foreign_source = db.scalar(
            select(Order)
            .join(LoadDistributionOrder)
            .where(
                LoadDistributionOrder.distribution_id == foreign_distribution_id,
            )
        )
        # A draft order may have no items. Such an extra link satisfies physical
        # coverage, while its foreign ownership must still prevent disclosure.
        foreign_order = Order(
            organization_id=organization_id,
            customer_id=foreign_source.customer_id,
            status="READY",
            priority="NORMAL",
            delivery_address="Destino fictício",
        )
        db.add(foreign_order)
        db.flush()
        foreign_order_id = foreign_order.id
        db.add(
            LoadDistributionOrder(
                distribution_id=distribution_id,
                order_id=foreign_order_id,
            )
        )
        db.flush()
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        db.commit()
    try:
        response = s.client.get(
            BASE + f"/optimization-requests/{key}",
            headers=s.user.headers,
        )
        assert response.status_code == 404, response.text
        assert response.json()["code"] == "OPTIMIZATION_NOT_FOUND"
        assert str(foreign_order_id) not in response.text
    finally:
        with s.factory() as db:
            db.execute(
                delete(LoadDistributionOrder).where(
                    LoadDistributionOrder.distribution_id == distribution_id,
                    LoadDistributionOrder.order_id == foreign_order_id,
                )
            )
            db.execute(delete(Order).where(Order.id == foreign_order_id))
            db.commit()


@pytest.mark.parametrize("operation", ["optimize", "recover"])
def test_service_refuses_nonlegacy_organization_without_creating_work(
    session_factory,
    operation,
):
    with session_factory() as db:
        organization = _organization(db)
        actor = _actor(db, [organization.id])
        service = LoadDistributionService(db, organization.id)
        before = db.scalar(select(func.count()).select_from(LoadDistribution))
        with pytest.raises(DistributionError) as error:
            if operation == "optimize":
                service.optimize(
                    DistributionNeedRequest(order_ids=[uuid.uuid4()]),
                    changed_by=actor.id,
                    idempotency_key=uuid.uuid4(),
                )
            else:
                service.recover_optimization(uuid.uuid4(), changed_by=actor.id)
        assert error.value.code == "AUTH_FORBIDDEN"
        assert error.value.status == 403
        assert db.scalar(select(func.count()).select_from(LoadDistribution)) == before
