"""G03-A: PostgreSQL 16 negative tests for fleet ownership."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.drivers.models import Driver
from app.modules.drivers.repository import DriverRepository
from app.modules.organizations.models import (
    LEGACY_ORGANIZATION_ID,
    Organization,
    OrganizationMembership,
)
from app.modules.trucks.models import Truck
from app.modules.trucks.repository import TruckRepository
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService


def second_org(db):
    org = Organization(
        legal_name="Transportadora B fictícia",
        display_name="Empresa B",
        status="PENDING",
    )
    db.add(org)
    db.flush()
    return org


def driver(db, org_id):
    item = Driver(
        organization_id=org_id,
        name="Motorista fictício",
        document="00000000003",
        phone="11900000000",
        license_number="00000000003",
        license_category="D",
    )
    db.add(item)
    db.flush()
    return item


def truck(db, org_id):
    item = Truck(
        organization_id=org_id,
        plate="TES1T23",
        model="Caminhão teste",
        internal_width_cm=250,
        internal_height_cm=250,
        internal_length_cm=600,
        max_weight_kg=Decimal(4000),
        active=True,
    )
    db.add(item)
    db.flush()
    return item


def test_driver_ownership_rejects_known_uuid_from_other_org(session_factory):
    with session_factory() as db:
        org_b = second_org(db)
        a = driver(db, LEGACY_ORGANIZATION_ID)
        b = driver(db, org_b.id)
        assert a.document == b.document
        primary = DriverRepository(db)
        assert primary.get(a.id) is not None
        assert primary.get(b.id) is None
        assert primary.get_by_document(b.document).id == a.id
        assert DriverRepository(db, org_b.id).get(a.id) is None
        assert DriverRepository(db, org_b.id).get(b.id) is not None
        assert primary.names_for_ids([b.id]) == {}


def test_truck_ownership_rejects_known_uuid_from_other_org(session_factory):
    with session_factory() as db:
        org_b = second_org(db)
        a = truck(db, LEGACY_ORGANIZATION_ID)
        b = truck(db, org_b.id)
        assert a.plate == b.plate
        primary = TruckRepository(db)
        assert primary.get(b.id) is None
        assert primary.get_many([b.id]) == []
        assert primary.get_by_plate(a.plate).id == a.id
        assert [x.id for x in primary.list_all()] == [a.id]
        assert TruckRepository(db, org_b.id).get(a.id) is None
        assert TruckRepository(db, org_b.id).get(b.id) is not None


def test_membership_cannot_reference_driver_from_other_org(session_factory):
    with session_factory() as db:
        user = UserService(db).create_user(
            UserCreate(
                name="Operador fictício",
                email=f"g03-{uuid.uuid4().hex}@example.test",
                password="Senha local de teste forte 2026",
                role="CHECKER",
            )
        )
        org_b = second_org(db)
        b = driver(db, org_b.id)
        membership = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == LEGACY_ORGANIZATION_ID,
            )
        )
        assert membership is not None
        with pytest.raises(IntegrityError), db.begin_nested():
            membership.role = "DRIVER"
            membership.driver_id = b.id
            db.flush()
