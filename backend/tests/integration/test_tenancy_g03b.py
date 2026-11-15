"""G03-B1 tenant boundaries for driver/truck documents and maintenance."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.pagination import PaginationParams
from app.modules.drivers.document_repository import DocumentRepository as DriverDocs
from app.modules.drivers.models import (
    CNH_TYPE_ID,
    Driver,
    DriverDocument,
    DriverDocumentPolicy,
)
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID, Organization
from app.modules.trucks.document_repository import DocumentRepository as TruckDocs
from app.modules.trucks.maintenance_repository import MaintenanceRepository
from app.modules.trucks.models import (
    Truck,
    TruckDocument,
    TruckDocumentPolicy,
    TruckMaintenance,
)


def _other_organization(db):
    org = Organization(
        legal_name="Empresa B de homologação",
        display_name="Empresa B",
        status="PENDING",
    )
    db.add(org)
    db.flush()
    return org


def _other_truck(db, organization_id):
    row = Truck(
        organization_id=organization_id,
        plate=f"T{uuid.uuid4().hex[:6].upper()}",
        model="Caminhão fictício",
        internal_width_cm=230,
        internal_height_cm=250,
        internal_length_cm=600,
        max_weight_kg=Decimal(4000),
    )
    db.add(row)
    db.flush()
    return row


def _other_driver(db, organization_id):
    row = Driver(
        organization_id=organization_id,
        name="Motorista B",
        document=f"{uuid.uuid4().int % 10**11:011d}",
        phone="11988887777",
        license_number=f"{uuid.uuid4().int % 10**11:011d}",
        license_category="D",
    )
    db.add(row)
    db.flush()
    return row


def _page():
    return PaginationParams(page=1, page_size=10, sort_order="desc")


def test_cross_org_truck_maintenance_and_document_uuid_is_hidden(session_factory):
    with session_factory() as db:
        org_b = _other_organization(db)
        truck = _other_truck(db, org_b.id)
        now = datetime.now(UTC)
        maintenance = TruckMaintenance(
            organization_id=org_b.id,
            truck_id=truck.id,
            kind="PREVENTIVE",
            starts_at=now,
            description="Revisão fictícia",
        )
        document = TruckDocument(
            organization_id=org_b.id,
            truck_id=truck.id,
            kind="CRLV",
            reference="CRLV de homologação",
        )
        policy = TruckDocumentPolicy(
            organization_id=org_b.id,
            truck_id=truck.id,
            kind="CRLV",
            required=True,
        )
        db.add_all([maintenance, document, policy])
        db.flush()

        assert TruckDocs(db).get(truck.id, document.id) is None
        assert TruckDocs(db).list(truck.id, _page()).total == 0
        assert TruckDocs(db).policy(truck.id, "CRLV") is None
        maintenance_read = MaintenanceRepository(db).get_for_update(
            truck.id, maintenance.id
        )
        assert maintenance_read is None
        assert MaintenanceRepository(db).list(truck.id, _page()).total == 0

        assert TruckDocs(db, org_b.id).get(truck.id, document.id) is not None
        other_maintenance = MaintenanceRepository(db, org_b.id).get_for_update(
            truck.id, maintenance.id
        )
        assert other_maintenance is not None
        assert TruckDocs(db).blocked_truck_ids(None, now) == frozenset()
        assert TruckDocs(db, org_b.id).blocked_truck_ids(None, now) == frozenset()


def test_cross_org_driver_document_and_policy_uuid_is_hidden(session_factory):
    with session_factory() as db:
        org_b = _other_organization(db)
        driver = _other_driver(db, org_b.id)
        document = DriverDocument(
            organization_id=org_b.id,
            driver_id=driver.id,
            document_type_id=CNH_TYPE_ID,
            reference="12345678900",
            category="D",
            expires_at=datetime.now(UTC) + timedelta(days=365),
        )
        policy = DriverDocumentPolicy(
            organization_id=org_b.id,
            driver_id=driver.id,
            document_type_id=CNH_TYPE_ID,
            required=True,
            allowed_categories=["D"],
        )
        db.add_all([document, policy])
        db.flush()

        assert DriverDocs(db).get(driver.id, document.id) is None
        assert DriverDocs(db).list_documents(driver.id, _page()).total == 0
        assert DriverDocs(db).policies(driver.id) == []
        assert DriverDocs(db, org_b.id).get(driver.id, document.id) is not None
        assert len(DriverDocs(db, org_b.id).policies(driver.id)) == 1


@pytest.mark.parametrize(
    "kind",
    [
        "truck_maintenance",
        "truck_document",
        "truck_policy",
        "driver_document",
        "driver_policy",
    ],
)
def test_composite_fk_blocks_cross_org_record_creation(session_factory, kind):
    with session_factory() as db:
        org_b = _other_organization(db)
        driver = _other_driver(db, org_b.id)
        truck = _other_truck(db, org_b.id)
        data = {
            "truck_maintenance": TruckMaintenance(
                organization_id=LEGACY_ORGANIZATION_ID,
                truck_id=truck.id,
                kind="CORRECTIVE",
                starts_at=datetime.now(UTC),
                description="Tentativa cruzada",
            ),
            "truck_document": TruckDocument(
                organization_id=LEGACY_ORGANIZATION_ID,
                truck_id=truck.id,
                kind="CRLV",
                reference="Teste",
            ),
            "truck_policy": TruckDocumentPolicy(
                organization_id=LEGACY_ORGANIZATION_ID,
                truck_id=truck.id,
                kind="CRLV",
            ),
            "driver_document": DriverDocument(
                organization_id=LEGACY_ORGANIZATION_ID,
                driver_id=driver.id,
                document_type_id=CNH_TYPE_ID,
                reference="12345678900",
            ),
            "driver_policy": DriverDocumentPolicy(
                organization_id=LEGACY_ORGANIZATION_ID,
                driver_id=driver.id,
                document_type_id=CNH_TYPE_ID,
                allowed_categories=[],
            ),
        }
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(data[kind])
            db.flush()
