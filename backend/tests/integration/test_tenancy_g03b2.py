"""G03-B2 PostgreSQL 16 guarantees for the global CNH / custom type split."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.drivers.document_repository import DocumentRepository
from app.modules.drivers.models import (
    CNH_TYPE_ID,
    Driver,
    DriverDocument,
    DriverDocumentPolicy,
    DriverDocumentType,
)
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID, Organization


def _organization_b(db):
    org = Organization(
        legal_name="Transportadora B fictícia",
        display_name="Transportadora B",
        status="PENDING",
    )
    db.add(org)
    db.flush()
    return org


def _driver_b(db, organization_id):
    suffix = str(uuid.uuid4().int % 10**11).zfill(11)
    driver = Driver(
        organization_id=organization_id,
        name="Motorista fictício B",
        document=suffix,
        license_number=suffix,
        phone="11999999999",
        license_category="D",
    )
    db.add(driver)
    db.flush()
    return driver


def test_cnh_is_global_but_custom_types_are_tenant_scoped(session_factory):
    with session_factory() as db:
        org_b = _organization_b(db)
        a_type = DriverDocumentType(
            organization_id=LEGACY_ORGANIZATION_ID,
            code="TENANT_DOCUMENT",
            name="Documento A",
        )
        b_type = DriverDocumentType(
            organization_id=org_b.id,
            code="TENANT_DOCUMENT",
            name="Documento B",
        )
        db.add_all([a_type, b_type])
        db.flush()

        legacy = DocumentRepository(db)
        other = DocumentRepository(db, org_b.id)
        assert legacy.get_type(CNH_TYPE_ID).organization_id is None
        assert other.get_type(CNH_TYPE_ID).organization_id is None
        assert legacy.get_type(a_type.id) is not None
        assert legacy.get_type(b_type.id) is None
        assert other.get_type(a_type.id) is None
        assert other.get_type(b_type.id) is not None
        assert [x.code for x in legacy.types()] == ["CNH", "TENANT_DOCUMENT"]
        assert [x.code for x in other.types()] == ["CNH", "TENANT_DOCUMENT"]


def test_duplicate_custom_code_within_same_organization_is_rejected(session_factory):
    with session_factory() as db:
        db.add(
            DriverDocumentType(
                organization_id=LEGACY_ORGANIZATION_ID,
                code="TENANT_DUPLICATE",
                name="Original",
            )
        )
        db.flush()
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(
                DriverDocumentType(
                    organization_id=LEGACY_ORGANIZATION_ID,
                    code="TENANT_DUPLICATE",
                    name="Duplicado",
                )
            )
            db.flush()


def test_only_seeded_cnh_may_be_global_or_use_reserved_code(session_factory):
    with session_factory() as db:
        org_b = _organization_b(db)
        for org_id, code in (
            (None, "UNSCOPED_CUSTOM"),
            (org_b.id, "CNH"),
        ):
            with pytest.raises(IntegrityError), db.begin_nested():
                db.add(
                    DriverDocumentType(
                        organization_id=org_id,
                        code=code,
                        name="Tipo proibido",
                    )
                )
                db.flush()


@pytest.mark.parametrize("record_kind", ["document", "policy"])
def test_known_uuid_cannot_reference_other_organization_custom_type(
    session_factory, record_kind
):
    with session_factory() as db:
        org_b = _organization_b(db)
        driver_b = _driver_b(db, org_b.id)
        type_a = DriverDocumentType(
            organization_id=LEGACY_ORGANIZATION_ID,
            code="CUSTOM_A",
            name="Documento privativo A",
        )
        db.add(type_a)
        db.flush()

        if record_kind == "document":
            record = DriverDocument(
                organization_id=org_b.id,
                driver_id=driver_b.id,
                document_type_id=type_a.id,
                # Attempt to disguise an A type as B in the composite FK.
                document_type_organization_id=org_b.id,
                reference="REF-TESTE",
            )
        else:
            record = DriverDocumentPolicy(
                organization_id=org_b.id,
                driver_id=driver_b.id,
                document_type_id=type_a.id,
                document_type_organization_id=org_b.id,
                required=True,
                allowed_categories=[],
            )
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(record)
            db.flush()


def test_b_driver_can_use_global_cnh_and_its_own_custom_type(session_factory):
    with session_factory() as db:
        org_b = _organization_b(db)
        driver_b = _driver_b(db, org_b.id)
        custom_type = DriverDocumentType(
            organization_id=org_b.id,
            code="CUSTOM_B",
            name="Documento B",
        )
        db.add(custom_type)
        db.flush()

        cnh = DriverDocument(
            organization_id=org_b.id,
            driver_id=driver_b.id,
            document_type_id=CNH_TYPE_ID,
            document_type_organization_id=None,
            reference="12345678900",
            category="D",
        )
        own = DriverDocument(
            organization_id=org_b.id,
            driver_id=driver_b.id,
            document_type_id=custom_type.id,
            document_type_organization_id=org_b.id,
            reference="REF-B",
        )
        db.add_all([cnh, own])
        db.flush()
        assert DocumentRepository(db).get(driver_b.id, cnh.id) is None
        assert DocumentRepository(db, org_b.id).get(driver_b.id, cnh.id) is not None
        assert DocumentRepository(db, org_b.id).get(driver_b.id, own.id) is not None
