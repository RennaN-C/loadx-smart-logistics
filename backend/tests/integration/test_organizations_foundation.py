import uuid
from datetime import UTC, datetime, timedelta
from importlib import import_module

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.auth.models import AuthSession
from app.modules.auth.sessions import AuthSessionInvalidError, AuthSessionService
from app.modules.company_profile.models import PROFILE_ID, CompanyProfile
from app.modules.organizations.models import (
    LEGACY_ORGANIZATION_ID,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    PlatformOwnerGrant,
)
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService


def create_foundation_user(db: Session) -> User:
    return UserService(db).create_user(
        UserCreate(
            name="Usuário fictício",
            email=f"{uuid.uuid4().hex}@example.test",
            password="Senha-local-segura-2026",
            role="CHECKER",
        )
    )


def test_session_requires_legacy_membership_even_when_another_is_active(
    session_factory,
) -> None:
    with session_factory() as db:
        user = create_foundation_user(db)
        organization = Organization(legal_name="Outra empresa", display_name="Outra")
        db.add(organization)
        db.flush()
        legacy = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id
            )
        )
        legacy.status = "SUSPENDED"
        db.add(
            OrganizationMembership(
                organization_id=organization.id, user_id=user.id, role="ADMIN"
            )
        )
        db.commit()

        with pytest.raises(AuthSessionInvalidError):
            AuthSessionService(db).create_session(user.id)


@pytest.mark.parametrize("path", ["/api/v1/auth/me", "/api/v1/products"])
def test_session_rejects_nonlegacy_organization_context(client, session_factory, path):
    with session_factory() as db:
        user = create_foundation_user(db)
        issued = AuthSessionService(db).create_session(user.id)
        organization = Organization(legal_name="Outra empresa", display_name="Outra")
        db.add(organization)
        db.flush()
        db.add(
            OrganizationMembership(
                organization_id=organization.id, user_id=user.id, role="ADMIN"
            )
        )
        db.flush()
        issued.auth_session.active_organization_id = organization.id
        db.commit()

        response = client.get(
            path,
            headers={
                "Cookie": f"{settings.session_cookie_name}={issued.token}",
            },
        )
        assert response.status_code == 401
        db.refresh(issued.auth_session)
        assert issued.auth_session.revoked_at is not None


def test_session_organization_context_is_required_by_database(session_factory):
    with session_factory() as db:
        user = create_foundation_user(db)
        issued = AuthSessionService(db).create_session(user.id)

        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(
                text(
                    "UPDATE auth_sessions "
                    "SET active_organization_id = NULL WHERE id = :session_id"
                ),
                {"session_id": issued.auth_session.id},
            )

        db.refresh(issued.auth_session)
        assert issued.auth_session.active_organization_id == LEGACY_ORGANIZATION_ID


def test_client_headers_cannot_choose_organization(client, session_factory):
    with session_factory() as db:
        user = create_foundation_user(db)
        service = AuthSessionService(db)
        issued = service.create_session(user.id)
        response = client.get(
            "/api/v1/auth/me",
            headers={
                "Cookie": f"{settings.session_cookie_name}={issued.token}",
                "X-Company-ID": str(uuid.uuid4()),
                "X-Organization-ID": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 200
        db.refresh(issued.auth_session)
        assert issued.auth_session.active_organization_id == LEGACY_ORGANIZATION_ID


@pytest.mark.parametrize("status", ["PENDING", "SUSPENDED", "CANCELED"])
def test_session_rejects_inactive_organization(session_factory, status):
    with session_factory() as db:
        user = create_foundation_user(db)
        service = AuthSessionService(db)
        issued = service.create_session(user.id)
        db.get(Organization, LEGACY_ORGANIZATION_ID).status = status
        db.commit()
        with pytest.raises(AuthSessionInvalidError):
            service.resolve_session(issued.token)
        with pytest.raises(AuthSessionInvalidError):
            service.create_session(user.id)


def test_session_requires_membership_and_composite_fk_rejects_other_user(
    session_factory,
):
    with session_factory() as db:
        user = User(
            name="Sem vínculo",
            email=f"{uuid.uuid4().hex}@example.test",
            password_hash="hash-ficticio",
            role="CHECKER",
            active=True,
        )
        db.add(user)
        db.commit()
        with pytest.raises(AuthSessionInvalidError):
            AuthSessionService(db).create_session(user.id)
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(
                AuthSession(
                    user_id=user.id,
                    active_organization_id=LEGACY_ORGANIZATION_ID,
                    token_hash="b" * 64,
                    created_at=datetime.now(UTC),
                    last_seen_at=datetime.now(UTC),
                    idle_expires_at=datetime.now(UTC) + timedelta(minutes=30),
                    absolute_expires_at=datetime.now(UTC) + timedelta(hours=8),
                )
            )
            db.flush()


@pytest.mark.parametrize(
    "invalid",
    [
        "expired",
        "both_terminal",
        "missing_actor",
        "not_normalized",
        "duplicate_hash",
        "late_acceptance",
        "early_acceptance",
        "early_revocation",
    ],
)
def test_invitation_constraints_reject_inconsistent_states(session_factory, invalid):
    with session_factory() as db:
        user = create_foundation_user(db)
        now = datetime.now(UTC)
        values = {
            "organization_id": LEGACY_ORGANIZATION_ID,
            "email_normalized": "invite@example.test",
            "role": "CHECKER",
            "token_hash": "c" * 64,
            "invited_by_user_id": user.id,
            "created_at": now,
            "expires_at": now + timedelta(hours=1),
        }
        if invalid == "expired":
            values["expires_at"] = now
        elif invalid == "both_terminal":
            values.update(
                accepted_at=now,
                accepted_by_user_id=user.id,
                revoked_at=now,
                revoked_by_user_id=user.id,
            )
        elif invalid == "missing_actor":
            values["accepted_at"] = now
        elif invalid == "not_normalized":
            values["email_normalized"] = " INVITE@example.test "
        elif invalid == "late_acceptance":
            values.update(accepted_at=values["expires_at"], accepted_by_user_id=user.id)
        elif invalid == "early_acceptance":
            values.update(
                accepted_at=now - timedelta(seconds=1), accepted_by_user_id=user.id
            )
        elif invalid == "early_revocation":
            values.update(
                revoked_at=now - timedelta(seconds=1), revoked_by_user_id=user.id
            )
        else:
            db.add(OrganizationInvitation(**values))
            db.flush()
            values["email_normalized"] = "other@example.test"
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(OrganizationInvitation(**values))
            db.flush()


def test_platform_owner_is_not_seeded_and_second_grant_is_rejected(session_factory):
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(PlatformOwnerGrant)) == 0
        user = create_foundation_user(db)
        other = create_foundation_user(db)
        db.add(PlatformOwnerGrant(user_id=user.id, reason="Concessão de teste"))
        db.flush()
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(PlatformOwnerGrant(id=2, user_id=other.id, reason="Segundo grant"))
            db.flush()


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


@pytest.mark.parametrize("status", ["SUSPENDED", "REMOVED"])
def test_user_service_creates_membership_and_session_revalidates_it(
    session_factory,
    status,
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

        membership.status = status
        db.add(membership)
        db.commit()

        with pytest.raises(AuthSessionInvalidError):
            sessions.resolve_session(issued.token)

        db.refresh(issued.auth_session)
        assert issued.auth_session.revoked_at is not None

        with pytest.raises(AuthSessionInvalidError):
            sessions.create_session(user.id)


@pytest.mark.parametrize(
    "role", ["ADMIN", "CHECKER", "LOGISTICS_MANAGER", "CUSTOM", "DRIVER"]
)
def test_organization_migration_backfills_legacy_profile_users_and_sessions(
    session_factory,
    role,
) -> None:
    migration = import_module(
        "migrations.versions.20261114_0036_organization_foundation"
    )
    newer_migrations = [
        import_module(
            "migrations.versions.20261115_0037_scope_legacy_profiles_company"
        ),
        import_module("migrations.versions.20261115_0038_scope_customers_products"),
        import_module("migrations.versions.20261115_0039_scope_fleet_registry"),
    ]
    now = datetime.now(UTC)
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    profile_id = uuid.uuid4() if role == "CUSTOM" else None
    driver_id = uuid.uuid4() if role == "DRIVER" else None

    with session_factory() as db:
        connection = db.connection()
        with Operations.context(MigrationContext.configure(connection)):
            for newer_migration in reversed(newer_migrations):
                newer_migration.downgrade()
            migration.downgrade()

        if profile_id is not None:
            # Match the historical 0035 table; the ORM already has G01 columns.
            db.execute(
                text(
                    "INSERT INTO access_profiles(id, name, name_key, description) "
                    "VALUES (:id, 'Perfil legado', 'perfil legado', '')"
                ),
                {"id": profile_id},
            )
        if driver_id is not None:
            # The historical schema predates the G03 organization column.
            db.execute(
                text(
                    "INSERT INTO drivers("
                    "id, name, document, phone, license_number, license_category"
                    ") VALUES ("
                    ":id, 'Motorista fictício', '98765432100', "
                    "'11900000000', '98765432100', 'D'"
                    ")"
                ),
                {"id": driver_id},
            )
        db.flush()

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
                role=role,
                custom_profile_id=profile_id,
                driver_id=driver_id,
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
            for newer_migration in newer_migrations:
                newer_migration.upgrade()

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
        assert row.role == role
        assert row.custom_profile_id == profile_id
        assert row.driver_id == driver_id
        assert row.active_organization_id == LEGACY_ORGANIZATION_ID
        assert db.scalar(
            select(func.count()).select_from(OrganizationMembership)
        ) == db.scalar(select(func.count()).select_from(User))


@pytest.mark.parametrize("state", ["organization", "membership", "invitation", "owner"])
def test_downgrade_preserves_organization_history(session_factory, state):
    migration = import_module(
        "migrations.versions.20261114_0036_organization_foundation"
    )
    with session_factory() as db:
        user = create_foundation_user(db)
        if state == "organization":
            db.add(Organization(legal_name="Empresa fictícia", display_name="Empresa"))
        elif state == "membership":
            membership = db.scalar(
                select(OrganizationMembership).where(
                    OrganizationMembership.user_id == user.id
                )
            )
            membership.status = "REMOVED"
        elif state == "owner":
            db.add(PlatformOwnerGrant(user_id=user.id, reason="Teste de preservação"))
        else:
            db.add(
                OrganizationInvitation(
                    organization_id=LEGACY_ORGANIZATION_ID,
                    email_normalized="invite@example.test",
                    role="CHECKER",
                    token_hash="d" * 64,
                    invited_by_user_id=user.id,
                    expires_at=datetime.now(UTC) + timedelta(hours=1),
                )
            )
        db.flush()
        with (
            Operations.context(MigrationContext.configure(db.connection())),
            pytest.raises(RuntimeError, match="Downgrade blocked"),
        ):
            migration.downgrade()
        assert db.get(Organization, LEGACY_ORGANIZATION_ID) is not None
