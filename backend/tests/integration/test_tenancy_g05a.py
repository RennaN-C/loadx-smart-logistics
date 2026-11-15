"""G05-A: reject cross-organization load-plan reads and truck lineage."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.pagination import PaginationParams
from app.modules.load_planning.models import LoadPlan
from app.modules.load_planning.repository import LoadPlanRepository
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID, Organization
from app.modules.trucks.models import Truck


def _organization(db):
    row = Organization(
        legal_name="Transportadora B fictícia",
        display_name="Transportadora B",
        status="PENDING",
    )
    db.add(row)
    db.flush()
    return row


def _truck(db, organization_id, plate):
    row = Truck(
        organization_id=organization_id,
        plate=plate,
        model="Caminhão fictício",
        internal_width_cm=100,
        internal_height_cm=100,
        internal_length_cm=100,
        max_weight_kg=Decimal(100),
    )
    db.add(row)
    db.flush()
    return row


def _plan(organization_id, truck_id, recalculated_from_id=None):
    return LoadPlan(
        organization_id=organization_id,
        truck_id=truck_id,
        recalculated_from_id=recalculated_from_id,
        status="REJECTED",
        truck_snapshot_plate="TEST123",
        truck_snapshot_model="Caminhão fictício",
        truck_snapshot_internal_width_cm=100,
        truck_snapshot_internal_height_cm=100,
        truck_snapshot_internal_length_cm=100,
        truck_snapshot_max_weight_kg=Decimal(100),
        internal_volume_cm3=1_000_000,
        used_volume_cm3=0,
        occupancy_percent=Decimal(0),
        total_weight_kg=Decimal(0),
        loaded_count=0,
        unloaded_count=1,
        algorithm_version="heuristic-v1",
    )


def test_known_uuid_from_other_organization_does_not_reveal_plan(session_factory):
    with session_factory() as db:
        other = _organization(db)
        a_truck = _truck(db, LEGACY_ORGANIZATION_ID, "TEN1A23")
        b_truck = _truck(db, other.id, "TEN1B23")
        a = _plan(LEGACY_ORGANIZATION_ID, a_truck.id)
        b = _plan(other.id, b_truck.id)
        db.add_all([a, b])
        db.flush()

        legacy_repo = LoadPlanRepository(db)
        b_repo = LoadPlanRepository(db, other.id)
        page = PaginationParams(page=1, page_size=10, sort_order="desc")
        assert legacy_repo.get(a.id) is not None
        assert legacy_repo.get(b.id) is None
        assert legacy_repo.get_for_update(b.id) is None
        assert legacy_repo.get_operation_summary(b.id) is None
        assert [item.id for item in legacy_repo.list(page).items] == [a.id]
        assert b_repo.get(a.id) is None
        assert b_repo.get(b.id) is not None
        assert [item.id for item in b_repo.list(page).items] == [b.id]


def test_fk_rejects_cross_org_truck_for_known_uuid(session_factory):
    with session_factory() as db:
        other = _organization(db)
        truck_b = _truck(db, other.id, "TEN2B23")
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(_plan(LEGACY_ORGANIZATION_ID, truck_b.id))
            db.flush()


def test_fk_rejects_cross_org_recalculation(session_factory):
    with session_factory() as db:
        other = _organization(db)
        truck_a = _truck(db, LEGACY_ORGANIZATION_ID, "TEN3A23")
        truck_b = _truck(db, other.id, "TEN3B23")
        source = _plan(other.id, truck_b.id)
        db.add(source)
        db.flush()
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(_plan(LEGACY_ORGANIZATION_ID, truck_a.id, source.id))
            db.flush()


def test_repository_rejects_cross_org_write(session_factory):
    with session_factory() as db:
        other = _organization(db)
        truck_b = _truck(db, other.id, "TEN4B23")
        plan_b = _plan(other.id, truck_b.id)
        with pytest.raises(ValueError, match="different organization"):
            LoadPlanRepository(db).add(plan_b)
