import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database.session import get_db
from app.main import app
from app.modules.auth.models import AuthSession
from app.modules.customers.models import Customer
from app.modules.deliveries.models import Delivery, Trip
from app.modules.load_planning.distribution_models import (
    LoadDistribution,
    LoadDistributionOrder,
    LoadDistributionPart,
    LoadDistributionVolume,
)
from app.modules.load_planning.distribution_schemas import (
    DistributionCreate,
    DistributionRead,
)
from app.modules.load_planning.distribution_service import (
    DistributionError,
    LoadDistributionService,
)
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.load_planning.reference_service import LoadPlanReferenceService
from app.modules.loading.models import LoadingSession, LoadingSessionItem
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.status_history.models import StatusHistory
from app.modules.status_history.service import StatusHistoryService
from app.modules.trucks.models import Truck
from app.modules.users.models import User
from tests.integration.test_load_planning_api import (
    create_authenticated_user,
    seed_planning_scenario,
)


@dataclass
class DistributionScenario:
    factory: object
    user: object
    source: object
    truck_ids: list
    client: object = None

    def payload(self, parts=2):
        quantities = {1: [[1, 2, 3]], 2: [[1], [2, 3]], 3: [[1], [2], [3]]}[parts]
        return {
            "order_ids": [str(self.source.order_id)],
            "parts": [
                {
                    "truck_id": str(self.truck_ids[i]),
                    "volumes": [
                        {
                            "order_item_id": str(self.source.order_item_id),
                            "volume_index": index,
                        }
                        for index in indices
                    ],
                }
                for i, indices in enumerate(quantities)
            ],
        }

    def post(self, path="", data=None):
        return self.client.post(
            "/api/v1/load-distributions" + path,
            json={} if data is None else data,
            headers=self.user.headers,
        )

    def create(self, parts=2):
        response = self.post(data=self.payload(parts))
        assert response.status_code == 201, response.text
        return response.json()

    def order_status(self):
        with self.factory() as db:
            return db.get(Order, self.source.order_id).status


@pytest.fixture
def distribution_scenario(postgres_engine):
    factory = sessionmaker(bind=postgres_engine, expire_on_commit=False)
    user = create_authenticated_user(factory, "LOGISTICS_MANAGER")
    source = seed_planning_scenario(factory, quantity=3, truck_width_cm=30)
    ids = [source.truck_id]
    with factory() as db:
        first = db.get(Truck, source.truck_id)
        for _ in range(2):
            truck = Truck(
                id=uuid.uuid4(),
                plate=uuid.uuid4().hex[:7].upper(),
                model="Veiculo ficticio",
                internal_width_cm=30,
                internal_height_cm=10,
                internal_length_cm=10,
                max_weight_kg=first.max_weight_kg,
                active=True,
            )
            db.add(truck)
            ids.append(truck.id)
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    scenario = DistributionScenario(factory, user, source, ids)
    with TestClient(
        app, raise_server_exceptions=False, headers={"Origin": "http://localhost:5173"}
    ) as client:
        scenario.client = client
        try:
            yield scenario
        finally:
            app.dependency_overrides.clear()
            with factory() as db:
                order = db.get(Order, source.order_id)
                customer_id = order.customer_id
                distributions = select(LoadDistributionOrder.distribution_id).where(
                    LoadDistributionOrder.order_id == source.order_id
                )
                plan_ids = select(LoadPlanOrder.load_plan_id).where(
                    LoadPlanOrder.order_id == source.order_id
                )
                loading_ids = select(LoadingSession.id).where(
                    LoadingSession.load_plan_id.in_(plan_ids)
                )
                db.execute(
                    delete(LoadingSessionItem).where(
                        LoadingSessionItem.loading_session_id.in_(loading_ids)
                    )
                )
                db.execute(
                    delete(LoadingSession).where(
                        LoadingSession.load_plan_id.in_(plan_ids)
                    )
                )
                db.execute(delete(Delivery).where(Delivery.order_id == source.order_id))
                db.execute(delete(Trip).where(Trip.load_plan_id.in_(plan_ids)))
                db.execute(
                    delete(LoadDistributionVolume).where(
                        LoadDistributionVolume.distribution_id.in_(distributions)
                    )
                )
                db.execute(
                    delete(LoadDistributionPart).where(
                        LoadDistributionPart.distribution_id.in_(distributions)
                    )
                )
                identifiers = list(db.scalars(distributions))
                db.execute(
                    delete(LoadDistributionOrder).where(
                        LoadDistributionOrder.order_id == source.order_id
                    )
                )
                db.execute(
                    delete(LoadDistribution).where(LoadDistribution.id.in_(identifiers))
                )
                plans = list(db.scalars(plan_ids))
                db.execute(
                    delete(LoadPlanItem).where(LoadPlanItem.load_plan_id.in_(plans))
                )
                db.execute(
                    delete(LoadPlanOrder).where(LoadPlanOrder.load_plan_id.in_(plans))
                )
                db.execute(
                    update(LoadPlan)
                    .where(LoadPlan.id.in_(plans))
                    .values(recalculated_from_id=None)
                )
                db.execute(delete(LoadPlan).where(LoadPlan.id.in_(plans)))
                db.execute(
                    delete(OrderItem).where(OrderItem.order_id == source.order_id)
                )
                db.execute(delete(Order).where(Order.id == source.order_id))
                db.execute(delete(Customer).where(Customer.id == customer_id))
                db.execute(delete(Product).where(Product.id == source.product_id))
                db.execute(delete(Truck).where(Truck.id.in_(ids)))
                db.execute(
                    delete(StatusHistory).where(StatusHistory.changed_by == user.id)
                )
                db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
                db.execute(delete(User).where(User.id == user.id))
                db.commit()


@pytest.mark.parametrize("parts", [1, 2, 3])
def test_complete_partition_preserves_original_identities_and_visualization(
    distribution_scenario, parts
):
    s = distribution_scenario
    result = s.create(parts)
    assert result["truck_count"] == parts and result["volume_count"] == 3
    assert s.order_status() == "READY"
    identities = [(v["order_item_id"], v["volume_index"]) for v in result["volumes"]]
    assert identities == [(str(s.source.order_item_id), i) for i in range(1, 4)]
    assert len(set(identities)) == 3
    actual = []
    for part in result["parts"]:
        plan = part["load_plan"]
        assert plan["unloaded_count"] == 0 and plan["status"] == "CALCULATED"
        actual.extend((v["order_item_id"], v["volume_index"]) for v in plan["items"])
        response = s.client.get(
            f"/api/v1/load-plans/{plan['id']}/visualization", headers=s.user.headers
        )
        assert response.status_code == 200
        assert len(response.json()["items"]) == plan["loaded_count"]
    assert sorted(actual) == identities
    approved = s.post(f"/{result['id']}/approve").json()
    assert approved["status"] == "APPROVED" and s.order_status() == "PLANNED"
    assert all(p["load_plan"]["status"] == "APPROVED" for p in approved["parts"])
    assert s.post(f"/{result['id']}/approve").json() == approved


def test_partial_approval_and_reprocess_keep_other_parts_stable(distribution_scenario):
    s = distribution_scenario
    initial = s.create()
    first, second = initial["parts"]
    prefix = f"/{initial['id']}/parts/{first['id']}"
    partial = s.post(prefix + "/approve").json()
    assert partial["status"] == "PARTIALLY_APPROVED" and s.order_status() == "READY"
    assert all(p["load_plan"]["status"] == "CALCULATED" for p in partial["parts"])
    assert s.post(prefix + "/cancel").json()["status"] == "INCOMPLETE"
    assert s.post(f"/{initial['id']}/approve").status_code == 409
    used = {p["load_plan"]["truck_id"] for p in initial["parts"]}
    replacement = next(str(t) for t in s.truck_ids if str(t) not in used)
    data = {"truck_id": replacement, "expected_load_plan_id": first["load_plan"]["id"]}
    reprocessed = s.post(prefix + "/reprocess", data).json()
    assert reprocessed["volumes"] == initial["volumes"]
    changed = next(p for p in reprocessed["parts"] if p["id"] == first["id"])
    assert changed["load_plan"]["recalculated_from_id"] == first["load_plan"]["id"]
    with s.factory() as db:
        references = LoadPlanReferenceService(db)
        original_ref = references.get_distribution_part_for_plan(
            uuid.UUID(first["load_plan"]["id"])
        )
        current_ref = references.get_distribution_part_for_plan(
            uuid.UUID(changed["load_plan"]["id"])
        )
        assert original_ref == current_ref
        assert current_ref.part_id == uuid.UUID(first["id"])
        assert current_ref.current_load_plan_id == uuid.UUID(changed["load_plan"]["id"])
        assert len(current_ref.volumes) == changed["load_plan"]["loaded_count"]

    assert next(p for p in reprocessed["parts"] if p["id"] == second["id"]) == second
    assert s.post(prefix + "/reprocess", data).status_code == 409
    assert s.post(f"/{initial['id']}/approve").status_code == 200
    assert s.post(prefix + "/cancel").status_code == 409


@pytest.mark.parametrize(
    "invalid",
    [
        "duplicate",
        "missing",
        "unknown_item",
        "index",
        "same_truck",
        "unknown_truck",
        "inactive",
        "capacity",
    ],
)
def test_invalid_distribution_never_persists_partial_plans(
    distribution_scenario, invalid
):
    s = distribution_scenario
    data = s.payload()
    if invalid == "duplicate":
        data["parts"][1]["volumes"].append(data["parts"][0]["volumes"][0])
    elif invalid == "missing":
        data["parts"][1]["volumes"].pop()
    elif invalid == "unknown_item":
        data["parts"][0]["volumes"][0]["order_item_id"] = str(uuid.uuid4())
    elif invalid == "index":
        data["parts"][0]["volumes"][0]["volume_index"] = 4
    elif invalid == "same_truck":
        data["parts"][1]["truck_id"] = data["parts"][0]["truck_id"]
    elif invalid == "unknown_truck":
        data["parts"][1]["truck_id"] = str(uuid.uuid4())
    else:
        with s.factory() as db:
            truck = db.get(Truck, s.truck_ids[1])
            if invalid == "inactive":
                truck.active = False
            else:
                truck.internal_width_cm = 10
            db.commit()
    response = s.post(data=data)
    assert response.status_code in {404, 409, 422}, response.text
    with s.factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(LoadPlanOrder)
                .where(LoadPlanOrder.order_id == s.source.order_id)
            )
            == 0
        )
        assert not LoadDistributionService(db).repository.has_active_orders(
            [s.source.order_id]
        )
    assert s.order_status() == "READY"


def test_cancel_releases_claims_but_preserves_history_and_blocks_legacy_bypass(
    distribution_scenario,
):
    s = distribution_scenario
    result = s.create()
    assert s.post(data=s.payload()).status_code == 409
    plan_id = result["parts"][0]["load_plan"]["id"]
    assert (
        s.client.post(
            f"/api/v1/load-plans/{plan_id}/approve", headers=s.user.headers
        ).status_code
        == 409
    )
    assert (
        s.client.post(
            f"/api/v1/load-plans/{plan_id}/recalculate", headers=s.user.headers
        ).status_code
        == 409
    )
    transition = s.client.patch(
        f"/api/v1/orders/{s.source.order_id}/status",
        json={"status": "DRAFT"},
        headers=s.user.headers,
    )
    assert transition.status_code == 409
    canceled = s.post(f"/{result['id']}/cancel")
    assert canceled.status_code == 200 and canceled.json()["status"] == "CANCELED"
    new = s.create()
    assert new["id"] != result["id"] and new["volumes"][0]["volume_index"] == 1
    with s.factory() as db:
        histories = db.scalars(
            select(StatusHistory)
            .where(StatusHistory.entity_id == uuid.UUID(result["id"]))
            .order_by(StatusHistory.created_at, StatusHistory.id)
        ).all()
        assert [(h.old_status, h.new_status) for h in histories] == [
            (None, "PROPOSED"),
            ("PROPOSED", "CANCELED"),
        ]


def test_history_failure_rolls_back_distribution_and_approval(
    distribution_scenario, monkeypatch
):
    s = distribution_scenario
    result = s.create()
    original = StatusHistoryService.stage_status_change

    def failing(self, data):
        if data.entity_type == "ORDER":
            raise RuntimeError("simulated history failure")
        return original(self, data)

    monkeypatch.setattr(StatusHistoryService, "stage_status_change", failing)
    assert s.post(f"/{result['id']}/approve").status_code == 500
    assert s.order_status() == "READY"
    after = s.client.get(
        f"/api/v1/load-distributions/{result['id']}", headers=s.user.headers
    ).json()
    assert after == result


@pytest.mark.parametrize(
    "mutation", ["delete_volume", "wrong_snapshot", "premature_status", "alter_source"]
)
def test_deferred_database_constraints_reject_writes_outside_service(
    distribution_scenario, mutation
):
    s = distribution_scenario
    result = s.create()
    with s.factory() as db:
        with pytest.raises(IntegrityError):
            if mutation == "delete_volume":
                db.execute(
                    delete(LoadDistributionVolume).where(
                        LoadDistributionVolume.distribution_id
                        == uuid.UUID(result["id"]),
                        LoadDistributionVolume.volume_index == 1,
                    )
                )
            elif mutation == "wrong_snapshot":
                db.execute(
                    update(LoadDistributionVolume)
                    .where(
                        LoadDistributionVolume.distribution_id
                        == uuid.UUID(result["id"])
                    )
                    .values(snapshot_quantity=4)
                )
            elif mutation == "premature_status":
                db.execute(
                    update(LoadDistribution)
                    .where(LoadDistribution.id == uuid.UUID(result["id"]))
                    .values(status="APPROVED")
                )
            else:
                db.execute(
                    update(OrderItem)
                    .where(OrderItem.id == s.source.order_item_id)
                    .values(quantity=4)
                )
            db.commit()
        db.rollback()
    assert s.order_status() == "READY"


def test_concurrent_claims_have_one_winner_and_no_partial_plan(distribution_scenario):
    s = distribution_scenario
    barrier = Barrier(2)
    data = DistributionCreate.model_validate(s.payload(1))

    def claim(index):
        with s.factory() as db:
            barrier.wait(timeout=10)
            try:
                proposal = data.model_copy(deep=True)
                proposal.parts[0].truck_id = s.truck_ids[index]
                return (
                    LoadDistributionService(db)
                    .create(proposal, changed_by=s.user.id)
                    .id
                )
            except DistributionError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, range(2)))
    assert sum(isinstance(result, uuid.UUID) for result in results) == 1
    assert "DISTRIBUTION_ORDER_CLAIMED" in results
    with s.factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(LoadDistributionVolume)
                .where(LoadDistributionVolume.order_id == s.source.order_id)
            )
            == 3
        )


def test_preflight_and_authentication_contract(distribution_scenario):
    s = distribution_scenario
    response = s.post("/preflight", {"order_ids": [str(s.source.order_id)]})
    assert response.status_code == 200 and len(response.json()["volumes"]) == 3
    assert set(map(str, s.truck_ids)) <= {
        t["id"] for t in response.json()["eligible_trucks"]
    }
    assert (
        s.client.post("/api/v1/load-distributions", json=s.payload()).status_code == 401
    )
    without_csrf = {
        k: v for k, v in s.user.headers.items() if k.lower() != "x-csrf-token"
    }
    assert (
        s.client.post(
            "/api/v1/load-distributions", json=s.payload(), headers=without_csrf
        ).status_code
        == 403
    )
    assert (
        s.post(data={**s.payload(), "created_by": str(uuid.uuid4())}).status_code == 422
    )


def test_busy_truck_preserves_operational_conflict_rule(distribution_scenario):
    from app.modules.load_planning.schemas import LoadPlanCreate
    from app.modules.load_planning.service import LoadPlanningService
    from app.modules.loading.service import LoadingService

    s = distribution_scenario
    with s.factory() as db:
        planning = LoadPlanningService(db)
        plan = planning.create_load_plan(
            LoadPlanCreate(truck_id=s.source.truck_id, order_ids=[s.source.order_id]),
            changed_by=s.user.id,
        )
        planning.approve_load_plan(plan.id, changed_by=s.user.id)
        LoadingService(db).create_session(plan.id)
    response = s.post(data=s.payload())
    assert (
        response.status_code == 409
        and response.json()["code"] == "TRUCK_OPERATION_CONFLICT"
    )


@pytest.mark.parametrize("parts", [1, 2])
def test_operational_port_preserves_single_truck_and_gates_split_orders(
    distribution_scenario, parts
):
    s = distribution_scenario
    result = s.create(parts)
    part = result["parts"][0]
    path = "/api/v1/loading-sessions"
    body = {"load_plan_id": part["load_plan"]["id"]}
    assert s.client.post(path, json=body, headers=s.user.headers).status_code == 409
    s.post(f"/{result['id']}/approve")
    response = s.client.post(path, json=body, headers=s.user.headers)
    assert response.status_code == (201 if parts == 1 else 409), response.text


@pytest.mark.parametrize("role", ["CHECKER", "DRIVER"])
def test_roles_cannot_create_or_approve_distribution(distribution_scenario, role):
    s = distribution_scenario
    user = create_authenticated_user(s.factory, role)
    try:
        result = s.create()
        response = s.client.post(
            "/api/v1/load-distributions", json=s.payload(), headers=user.headers
        )
        assert response.status_code == 403
        response = s.client.post(
            f"/api/v1/load-distributions/{result['id']}/approve",
            json={},
            headers=user.headers,
        )
        assert response.status_code == 403
        read = s.client.get(
            f"/api/v1/load-distributions/{result['id']}", headers=user.headers
        )
        assert read.status_code == 403
    finally:
        with s.factory() as db:
            db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
            db.execute(delete(User).where(User.id == user.id))
            db.commit()


def test_admin_can_create_and_approve_distribution(distribution_scenario):
    s = distribution_scenario
    with s.factory() as db:
        db.get(User, s.user.id).role = "ADMIN"
        db.commit()
    try:
        response = s.post(data=s.payload())
        assert response.status_code == 201, response.text
        approved = s.post(f"/{response.json()['id']}/approve")
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "APPROVED"
    finally:
        with s.factory() as db:
            db.get(User, s.user.id).role = "LOGISTICS_MANAGER"
            db.commit()


def test_availability_is_revalidated_on_approval(distribution_scenario):
    s = distribution_scenario
    result = s.create()
    with s.factory() as db:
        db.get(Truck, s.truck_ids[0]).active = False
        db.commit()
    assert s.post(f"/{result['id']}/approve").status_code == 409
    assert s.order_status() == "READY"
    with s.factory() as db:
        assert LoadDistributionService(db).get(
            uuid.UUID(result["id"])
        ) == DistributionRead.model_validate(result)


def test_concurrent_part_approvals_have_single_total_transition(distribution_scenario):
    s = distribution_scenario
    result = s.create()
    barrier = Barrier(2)

    def approve(part):
        with s.factory() as db:
            barrier.wait(timeout=10)
            return LoadDistributionService(db).approve(
                uuid.UUID(result["id"]),
                part_id=uuid.UUID(part["id"]),
                changed_by=s.user.id,
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(approve, result["parts"]))
    assert all(r.status in {"PARTIALLY_APPROVED", "APPROVED"} for r in replies)
    assert any(r.status == "APPROVED" for r in replies)
    assert s.order_status() == "PLANNED"
    with s.factory() as db:
        changes = db.scalars(
            select(StatusHistory).where(
                StatusHistory.entity_id == s.source.order_id,
                StatusHistory.new_status == "PLANNED",
            )
        ).all()
        assert len(changes) == 1


def test_reprocess_requires_canceled_part(distribution_scenario):
    s = distribution_scenario
    result = s.create()
    part = result["parts"][0]
    prefix = f"/{result['id']}/parts/{part['id']}"
    data = {
        "truck_id": part["load_plan"]["truck_id"],
        "expected_load_plan_id": part["load_plan"]["id"],
    }

    pending = s.post(prefix + "/reprocess", data)
    assert pending.status_code == 409
    assert pending.json()["code"] == "DISTRIBUTION_PART_REPROCESS_REQUIRES_CANCELED"

    assert s.post(prefix + "/approve").status_code == 200
    approved = s.post(prefix + "/reprocess", data)
    assert approved.status_code == 409
    assert approved.json()["code"] == "DISTRIBUTION_PART_REPROCESS_REQUIRES_CANCELED"


def test_reprocess_failure_preserves_plan_chain_and_other_parts(
    distribution_scenario, monkeypatch
):
    s = distribution_scenario
    result = s.create()
    part = result["parts"][0]
    canceled = s.post(f"/{result['id']}/parts/{part['id']}/cancel").json()
    original = StatusHistoryService.stage_status_change

    def failing(self, data):
        if data.entity_type == "LOAD_DISTRIBUTION_PART":
            raise RuntimeError("simulated reprocess failure")
        return original(self, data)

    monkeypatch.setattr(StatusHistoryService, "stage_status_change", failing)
    data = {
        "truck_id": part["load_plan"]["truck_id"],
        "expected_load_plan_id": part["load_plan"]["id"],
    }
    assert (
        s.post(f"/{result['id']}/parts/{part['id']}/reprocess", data).status_code == 500
    )
    assert (
        s.client.get(
            f"/api/v1/load-distributions/{result['id']}", headers=s.user.headers
        ).json()
        == canceled
    )
    with s.factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(LoadPlanOrder)
                .where(LoadPlanOrder.order_id == s.source.order_id)
            )
            == 2
        )


@pytest.mark.parametrize(
    "mutation",
    ["duplicate_identity", "foreign_part", "invalid_index", "invalid_provenance"],
)
def test_native_constraints_preserve_identity_and_provenance(
    distribution_scenario, mutation
):
    s = distribution_scenario
    result = s.create()
    with s.factory() as db:
        volume = db.scalar(
            select(LoadDistributionVolume).where(
                LoadDistributionVolume.distribution_id == uuid.UUID(result["id"])
            )
        )
        with pytest.raises(IntegrityError):
            if mutation == "duplicate_identity":
                db.add(
                    LoadDistributionVolume(
                        distribution_id=volume.distribution_id,
                        order_item_id=volume.order_item_id,
                        volume_index=volume.volume_index,
                        order_id=volume.order_id,
                        product_id=volume.product_id,
                        snapshot_quantity=volume.snapshot_quantity,
                        part_id=volume.part_id,
                        active=True,
                    )
                )
            else:
                values = {
                    "foreign_part": {"part_id": uuid.uuid4()},
                    "invalid_index": {"volume_index": 0},
                    "invalid_provenance": {"product_id": uuid.uuid4()},
                }[mutation]
                db.execute(
                    update(LoadDistributionVolume)
                    .where(
                        LoadDistributionVolume.distribution_id == volume.distribution_id
                    )
                    .values(**values)
                )
            db.commit()
        db.rollback()


def test_nonexistent_sources_and_part_scope_are_rejected(distribution_scenario):
    s = distribution_scenario
    data = s.payload()
    data["order_ids"] = [str(uuid.uuid4())]
    assert s.post(data=data).status_code == 404
    result = s.create()
    assert (
        s.client.get(
            f"/api/v1/load-distributions/{uuid.uuid4()}", headers=s.user.headers
        ).status_code
        == 404
    )
    assert s.post(f"/{result['id']}/parts/{uuid.uuid4()}/approve").status_code == 404
    assert s.order_status() == "READY"
