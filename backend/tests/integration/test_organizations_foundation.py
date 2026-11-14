import uuid
from datetime import UTC, datetime, timedelta
from importlib import import_module

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select, text

from app.modules.auth.sessions import AuthSessionInvalidError, AuthSessionService
from app.modules.company_profile.models import PROFILE_ID, CompanyProfile
from app.modules.organizations.models import (
    LEGACY_ORGANIZATION_ID,
    Organization,
    OrganizationMembership,
)
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService


def test_legacy_organization_is_seeded_when_company_profile_is_missing(
    session_factory,
) -> None:
    with session_factory() as db:
        organization = db.get(Organization, LEGACY_ORGANIZATION_ID)

        assert organization is not None
        assert organization.is_legacy is True
        assert organization.status == "ACTIVE"
        assert organization.legal_name
        assert organization.display_name


def test_user_service_creates_membership_and_session_revalidates_it(
    session_factory,
) -> None:
    with session_factory() as db:
        user = UserService(db).create_user(
            UserCreate(
                name="Usuário da organização",
                email=f"{uuid.uuid4().hex}@example.test",
                password="Senha-local-segura-2026",
                role="ADMIN",
            )
        )
        membership = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == LEGACY_ORGANIZATION_ID,
                OrganizationMembership.user_id == user.id,
            )
        )

        assert membership is not None
        assert membership.status == "ACTIVE"
        assert membership.role == user.role

        sessions = AuthSessionService(db)
        issued = sessions.create_session(user.id)
        assert issued.auth_session.active_organization_id == LEGACY_ORGANIZATION_ID

        membership.status = "SUSPENDED"
        db.add(membership)
        db.commit()

        with pytest.raises(AuthSessionInvalidError):
            sessions.resolve_session(issued.token)

        db.refresh(issued.auth_session)
        assert issued.auth_session.revoked_at is not None

        with pytest.raises(AuthSessionInvalidError):
            sessions.create_session(user.id)


def test_organization_migration_backfills_legacy_profile_users_and_sessions(
    session_factory,
) -> None:
    migration = import_module(
        "migrations.versions.20261114_0036_organization_foundation"
    )
    now = datetime.now(UTC)
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()

    with session_factory() as db:
        connection = db.connection()
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()

        db.add(
            CompanyProfile(
                id=PROFILE_ID,
                legal_name="Transportadora de Teste Ltda.",
                display_name="Transportadora Teste",
                cnpj="11222333000181",
                phone=None,
                email=None,
                logo_reference=None,
            )
        )
        db.add(
            User(
                id=user_id,
                name="Usuário legado",
                email=f"{user_id.hex}@example.test",
                password_hash="hash-de-teste",
                role="ADMIN",
                active=True,
                created_at=now,
            )
        )
        db.flush()
        db.execute(
            text(
                """
                INSERT INTO auth_sessions (
                    id, user_id, token_hash, created_at, last_seen_at,
                    idle_expires_at, absolute_expires_at, revoked_at
                )
                VALUES (
                    :id, :user_id, :token_hash, :created_at, :last_seen_at,
                    :idle_expires_at, :absolute_expires_at, NULL
                )
                """
            ),
            {
                "id": session_id,
                "user_id": user_id,
                "token_hash": "a" * 64,
                "created_at": now,
                "last_seen_at": now,
                "idle_expires_at": now + timedelta(minutes=30),
                "absolute_expires_at": now + timedelta(hours=8),
            },
        )

        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        row = db.execute(
            text(
                """
                SELECT
                    o.legal_name,
                    o.display_name,
                    o.cnpj,
                    m.role,
                    m.custom_profile_id,
                    m.driver_id,
                    s.active_organization_id
                FROM organizations AS o
                JOIN organization_memberships AS m
                  ON m.organization_id = o.id
                JOIN auth_sessions AS s
                  ON s.user_id = m.user_id
                WHERE o.id = :organization_id
                  AND m.user_id = :user_id
                  AND s.id = :session_id
                """
            ),
            {
                "organization_id": LEGACY_ORGANIZATION_ID,
                "user_id": user_id,
                "session_id": session_id,
            },
        ).one()

        assert row.legal_name == "Transportadora de Teste Ltda."
        assert row.display_name == "Transportadora Teste"
        assert row.cnpj == "11222333000181"
        assert row.role == "ADMIN"
        assert row.custom_profile_id is None
        assert row.driver_id is None
        assert row.active_organization_id == LEGACY_ORGANIZATION_ID
