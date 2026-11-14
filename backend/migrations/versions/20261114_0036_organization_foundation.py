"""Create the LoadX organization registry and session context foundation."""

import sqlalchemy as sa
from alembic import op

revision = "20261114_0036"
down_revision = "20261023_0035"
branch_labels = None
depends_on = None

LEGACY_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000301"
LEGACY_COMPANY_PROFILE_ID = "00000000-0000-0000-0000-000000000091"


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("legal_name", sa.String(160), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("cnpj", sa.String(14), nullable=True),
        sa.Column(
            "status", sa.String(16), server_default=sa.text("'ACTIVE'"), nullable=False
        ),
        sa.Column(
            "is_legacy", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'ACTIVE', 'SUSPENDED', 'CANCELED')",
            name="ck_organizations__status_allowed",
        ),
        sa.CheckConstraint(
            "length(trim(legal_name)) > 0 AND length(trim(display_name)) > 0",
            name="ck_organizations__names_not_empty",
        ),
        sa.CheckConstraint(
            "cnpj IS NULL OR length(cnpj) = 14",
            name="ck_organizations__cnpj_length",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
    )
    op.create_index(
        "uq_organizations__cnpj",
        "organizations",
        ["cnpj"],
        unique=True,
        postgresql_where=sa.text("cnpj IS NOT NULL"),
    )
    op.create_index(
        "uq_organizations__legacy",
        "organizations",
        ["is_legacy"],
        unique=True,
        postgresql_where=sa.text("is_legacy IS TRUE"),
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO organizations (
                id, legal_name, display_name, cnpj, status, is_legacy,
                created_at, updated_at
            )
            VALUES (
                CAST(:legacy_id AS uuid),
                COALESCE(
                    (SELECT NULLIF(BTRIM(legal_name), '')
                     FROM company_profiles
                     WHERE id = CAST(:profile_id AS uuid)),
                    'Empresa legada'
                ),
                COALESCE(
                    (SELECT NULLIF(BTRIM(display_name), '')
                     FROM company_profiles
                     WHERE id = CAST(:profile_id AS uuid)),
                    'Empresa legada'
                ),
                (SELECT cnpj
                 FROM company_profiles
                 WHERE id = CAST(:profile_id AS uuid)),
                'ACTIVE', TRUE, now(), now()
            )
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "legacy_id": LEGACY_ORGANIZATION_ID,
            "profile_id": LEGACY_COMPANY_PROFILE_ID,
        },
    )

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("custom_profile_id", sa.Uuid(), nullable=True),
        sa.Column("driver_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.String(16),
            server_default=sa.text("'ACTIVE'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "accepted_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('ADMIN', 'CHECKER', 'DRIVER', 'LOGISTICS_MANAGER', 'CUSTOM')",
            name="ck_organization_memberships__role_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'SUSPENDED', 'REMOVED')",
            name="ck_organization_memberships__status_allowed",
        ),
        sa.CheckConstraint(
            "(role = 'CUSTOM') = (custom_profile_id IS NOT NULL)",
            name="ck_organization_memberships__custom_profile_role",
        ),
        sa.CheckConstraint(
            "driver_id IS NULL OR role = 'DRIVER'",
            name="ck_organization_memberships__driver_role_required",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_organization_memberships__organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_organization_memberships__users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["custom_profile_id"], ["access_profiles.id"],
            name="fk_organization_memberships__access_profiles",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"], ["drivers.id"],
            name="fk_organization_memberships__drivers",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_memberships"),
        sa.UniqueConstraint(
            "organization_id", "user_id",
            name="uq_organization_memberships__organization_user",
        ),
        sa.UniqueConstraint(
            "id", "organization_id",
            name="uq_organization_memberships__id_organization",
        ),
    )
    op.create_index(
        "uq_organization_memberships__organization_driver",
        "organization_memberships",
        ["organization_id", "driver_id"],
        unique=True,
        postgresql_where=sa.text("driver_id IS NOT NULL"),
    )
    op.create_index(
        "ix_organization_memberships__user_status",
        "organization_memberships",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_organization_memberships__organization_status_role",
        "organization_memberships",
        ["organization_id", "status", "role"],
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO organization_memberships (
                id, organization_id, user_id, role, custom_profile_id, driver_id,
                status, created_at, accepted_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                CAST(:legacy_id AS uuid),
                u.id, u.role, u.custom_profile_id, u.driver_id,
                'ACTIVE', u.created_at, u.created_at, now()
            FROM users AS u
            ORDER BY u.id
            ON CONFLICT (organization_id, user_id) DO NOTHING
            """
        ),
        {"legacy_id": LEGACY_ORGANIZATION_ID},
    )

    op.create_table(
        "organization_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("email_normalized", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("custom_profile_id", sa.Uuid(), nullable=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("invited_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("revoked_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "role IN ('ADMIN', 'CHECKER', 'DRIVER', 'LOGISTICS_MANAGER', 'CUSTOM')",
            name="ck_organization_invitations__role_allowed",
        ),
        sa.CheckConstraint(
            "(role = 'CUSTOM') = (custom_profile_id IS NOT NULL)",
            name="ck_organization_invitations__custom_profile_role",
        ),
        sa.CheckConstraint(
            "length(email_normalized) > 0 AND "
            "email_normalized = lower(trim(email_normalized))",
            name="ck_organization_invitations__email_normalized",
        ),
        sa.CheckConstraint(
            "length(token_hash) = 64",
            name="ck_organization_invitations__token_hash_length",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_organization_invitations__expiration_after_creation",
        ),
        sa.CheckConstraint(
            "(accepted_at IS NULL) = (accepted_by_user_id IS NULL)",
            name="ck_organization_invitations__accepted_actor_consistent",
        ),
        sa.CheckConstraint(
            "(revoked_at IS NULL) = (revoked_by_user_id IS NULL)",
            name="ck_organization_invitations__revoked_actor_consistent",
        ),
        sa.CheckConstraint(
            "accepted_at IS NULL OR revoked_at IS NULL",
            name="ck_organization_invitations__terminal_state_exclusive",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_organization_invitations__organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["custom_profile_id"], ["access_profiles.id"],
            name="fk_organization_invitations__access_profiles",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"], ["users.id"],
            name="fk_organization_invitations__invited_by_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by_user_id"], ["users.id"],
            name="fk_organization_invitations__accepted_by_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_user_id"], ["users.id"],
            name="fk_organization_invitations__revoked_by_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_invitations"),
        sa.UniqueConstraint(
            "token_hash", name="uq_organization_invitations__token_hash"
        ),
    )
    op.create_index(
        "uq_organization_invitations__pending_email",
        "organization_invitations",
        ["organization_id", "email_normalized"],
        unique=True,
        postgresql_where=sa.text("accepted_at IS NULL AND revoked_at IS NULL"),
    )
    op.create_index(
        "ix_organization_invitations__organization_expiration",
        "organization_invitations",
        ["organization_id", "expires_at"],
    )

    op.create_table(
        "platform_owner_grants",
        sa.Column("id", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("granted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False
        ),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_platform_owner_grants__singleton"),
        sa.CheckConstraint(
            "length(trim(reason)) > 0",
            name="ck_platform_owner_grants__reason_not_empty",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_platform_owner_grants__user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"], ["users.id"],
            name="fk_platform_owner_grants__granted_by_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_platform_owner_grants"),
        sa.UniqueConstraint("user_id", name="uq_platform_owner_grants__user"),
    )

    op.add_column(
        "auth_sessions",
        sa.Column("active_organization_id", sa.Uuid(), nullable=True),
    )
    bind.execute(
        sa.text(
            """
            UPDATE auth_sessions AS s
            SET active_organization_id = m.organization_id
            FROM organization_memberships AS m
            WHERE m.user_id = s.user_id
              AND m.status = 'ACTIVE'
              AND m.organization_id = CAST(:legacy_id AS uuid)
            """
        ),
        {"legacy_id": LEGACY_ORGANIZATION_ID},
    )
    op.create_foreign_key(
        "fk_auth_sessions__active_organization_membership",
        "auth_sessions",
        "organization_memberships",
        ["active_organization_id", "user_id"],
        ["organization_id", "user_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_auth_sessions__active_organization_id",
        "auth_sessions",
        ["active_organization_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM organization_invitations)")
    ).scalar_one():
        raise RuntimeError(
            "Downgrade blocked: preserve organization invitation history."
        )
    if bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM platform_owner_grants)")
    ).scalar_one():
        raise RuntimeError(
            "Downgrade blocked: preserve the platform owner grant."
        )
    if bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM organizations
                WHERE id <> CAST(:legacy_id AS uuid) OR is_legacy IS NOT TRUE
            )
            """
        ),
        {"legacy_id": LEGACY_ORGANIZATION_ID},
    ).scalar_one():
        raise RuntimeError(
            "Downgrade blocked: preserve organizations beyond the legacy tenant."
        )
    if bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM organization_memberships AS m
                LEFT JOIN users AS u ON u.id = m.user_id
                WHERE m.organization_id <> CAST(:legacy_id AS uuid)
                   OR u.id IS NULL
                   OR m.status <> 'ACTIVE'
                   OR m.role IS DISTINCT FROM u.role
                   OR m.custom_profile_id IS DISTINCT FROM u.custom_profile_id
                   OR m.driver_id IS DISTINCT FROM u.driver_id
            )
            """
        ),
        {"legacy_id": LEGACY_ORGANIZATION_ID},
    ).scalar_one():
        raise RuntimeError(
            "Downgrade blocked: preserve organization membership changes."
        )

    op.drop_index(
        "ix_auth_sessions__active_organization_id", table_name="auth_sessions"
    )
    op.drop_constraint(
        "fk_auth_sessions__active_organization_membership",
        "auth_sessions",
        type_="foreignkey",
    )
    op.drop_column("auth_sessions", "active_organization_id")
    op.drop_table("platform_owner_grants")
    op.drop_table("organization_invitations")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
