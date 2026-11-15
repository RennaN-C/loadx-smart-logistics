"""G01 tenant ownership checks; two synthetic organizations, PostgreSQL 16 only."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.access_profiles.models import AccessProfile, ProfilePermission
from app.modules.access_profiles.repository import ProfileRepository
from app.modules.company_profile.schemas import CompanyProfileInput
from app.modules.company_profile.service import CompanyProfileService
from app.modules.organizations.models import (
    LEGACY_ORGANIZATION_ID,
    Organization,
    OrganizationMembership,
)
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService


def other_organization(db):
    other = Organization(
        legal_name="Organização B fictícia",
        display_name="Organização B",
        status="PENDING",
    )
    db.add(other)
    db.flush()
    return other


def profile(db, org_id, *, name="Consulta de frota"):
    row = AccessProfile(
        organization_id=org_id,
        name=name,
        name_key=name.lower(),
        description="Somente teste",
        active=True,
    )
    db.add(row)
    db.flush()
    return row


def test_profiles_are_scoped_by_organization_even_with_known_uuid(session_factory):
    with session_factory() as db:
        other = other_organization(db)
        legacy_profile = profile(db, LEGACY_ORGANIZATION_ID)
        other_profile = profile(db, other.id)  # Same name is valid in another org.

        legacy = ProfileRepository(db)
        secondary = ProfileRepository(db, organization_id=other.id)
        assert legacy.get(legacy_profile.id) is not None
        assert legacy.get(other_profile.id) is None
        assert legacy.count() == 1
        assert legacy.names([other_profile.id]) == {}
        assert secondary.get(other_profile.id) is not None
        assert secondary.get(legacy_profile.id) is None
        assert secondary.count() == 1


def test_profile_permissions_reject_cross_organization_reference(session_factory):
    with session_factory() as db:
        other = other_organization(db)
        b = profile(db, other.id)

        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(
                ProfilePermission(
                    organization_id=LEGACY_ORGANIZATION_ID,
                    profile_id=b.id,
                    permission_code="loadx.trucks.read",
                )
            )
            db.flush()


def test_membership_rejects_profile_from_another_organization(session_factory):
    with session_factory() as db:
        user = UserService(db).create_user(
            UserCreate(
                name="Responsável A",
                email=f"g01-{uuid.uuid4().hex}@example.test",
                password="Senha de teste forte 2026",
                role="CHECKER",
            )
        )
        other = other_organization(db)
        b = profile(db, other.id)
        membership = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == LEGACY_ORGANIZATION_ID,
                OrganizationMembership.user_id == user.id,
            )
        )
        assert membership is not None

        with pytest.raises(IntegrityError), db.begin_nested():
            membership.role = "CUSTOM"
            membership.custom_profile_id = b.id
            db.flush()


def test_company_profile_mirrors_six_fields_to_legacy_organization(session_factory):
    with session_factory() as db:
        user = UserService(db).create_user(
            UserCreate(
                name="Gestor A",
                email=f"g01-company-{uuid.uuid4().hex}@example.test",
                password="Senha de teste forte 2026",
                role="ADMIN",
            )
        )
        profile_input = CompanyProfileInput(
            legal_name="Empresa Legada LTDA",
            display_name="Logística Legada",
            cnpj=None,
            phone="(11) 90000-0000",
            email="ADMIN@EXAMPLE.TEST",
            logo_reference="https://example.test/logo.svg",
        )
        legacy_profile = CompanyProfileService(db).update(profile_input, user.id)
        company = db.get(Organization, LEGACY_ORGANIZATION_ID)
        assert company is not None
        for attr in (
            "legal_name",
            "display_name",
            "cnpj",
            "phone",
            "email",
            "logo_reference",
        ):
            assert getattr(company, attr) == getattr(legacy_profile, attr)


def test_organizations_reject_fourteen_non_numeric_cnpj(session_factory):
    with session_factory() as db:
        db.add(
            Organization(
                legal_name="CNPJ inválido",
                display_name="Empresa B",
                cnpj="abcdefghijklmn",
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
