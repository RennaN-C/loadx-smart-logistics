"""Scope custom access profiles and migrate legacy company fields into organizations.

G01 is deliberately a single-organization compatibility step. Further tenant
creation and organization switching remain disabled until repository isolation
is implemented across every operational domain.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261115_0037"
down_revision = "20261114_0036"
branch_labels = None
depends_on = None

LEGACY_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000301"
LEGACY_COMPANY_PROFILE_ID = "00000000-0000-0000-0000-000000000091"
LEGACY_DEFAULT = sa.text("'00000000-0000-4000-8000-000000000301'")


def upgrade() -> None:
    # Do not silently turn invalid legacy CNPJ data into a SaaS identity.
    op.drop_constraint(
        op.f("ck_organizations__cnpj_length"), "organizations", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_organizations__cnpj_format"),
        "organizations",
        "cnpj IS NULL OR cnpj ~ '^[0-9]{14}$'",
    )

    op.add_column("organizations", sa.Column("phone", sa.String(11), nullable=True))
    op.add_column("organizations", sa.Column("email", sa.String(255), nullable=True))
    op.add_column(
        "organizations", sa.Column("logo_reference", sa.String(2048), nullable=True)
    )
    # A live single-tenant installation might have updated company_profiles
    # after 0036 first copied name/CNPJ. Reconcile all six fields atomically.
    op.execute(
        f"""
        UPDATE organizations AS o
        SET legal_name = cp.legal_name,
            display_name = cp.display_name,
            cnpj = cp.cnpj,
            phone = cp.phone,
            email = cp.email,
            logo_reference = cp.logo_reference,
            updated_at = NOW()
        FROM company_profiles AS cp
        WHERE o.id = '{LEGACY_ORGANIZATION_ID}'::uuid
          AND cp.id = '{LEGACY_COMPANY_PROFILE_ID}'::uuid
        """
    )

    # Compatibility defaults exist ONLY until the organization-aware login
    # and all operational resource scopes are deployed. They must be removed
    # before enabling the creation of a second operational organization.
    op.add_column(
        "access_profiles",
        sa.Column(
            "organization_id",
            sa.Uuid(),
            nullable=False,
            server_default=LEGACY_DEFAULT,
        ),
    )
    op.create_foreign_key(
        op.f("fk_access_profiles__organizations"),
        "access_profiles",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        op.f("uq_access_profiles__name_key"),
        "access_profiles",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_access_profiles__organization_id"),
        "access_profiles",
        ["organization_id", "id"],
    )
    op.create_unique_constraint(
        op.f("uq_access_profiles__organization_name_key"),
        "access_profiles",
        ["organization_id", "name_key"],
    )

    op.add_column(
        "access_profile_permissions",
        sa.Column(
            "organization_id",
            sa.Uuid(),
            nullable=False,
            server_default=LEGACY_DEFAULT,
        ),
    )
    op.drop_constraint(
        op.f("fk_access_profile_permissions__access_profiles"),
        "access_profile_permissions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_access_profile_permissions__organization_profile",
        "access_profile_permissions",
        "access_profiles",
        ["organization_id", "profile_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )

    # Membership and invitation custom profiles must be from their OWN
    # organization, not just from any existing profile UUID.
    for table in ("organization_memberships", "organization_invitations"):
        op.drop_constraint(
            f"fk_{table}__access_profiles",
            table,
            type_="foreignkey",
        )
        op.create_foreign_key(
            f"fk_{table}__organization_profile",
            table,
            "access_profiles",
            ["organization_id", "custom_profile_id"],
            ["organization_id", "id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM access_profiles
                WHERE organization_id <> CAST(:legacy_id AS uuid)
            ) OR EXISTS (
                SELECT 1 FROM access_profile_permissions
                WHERE organization_id <> CAST(:legacy_id AS uuid)
            ) OR EXISTS (
                SELECT 1 FROM organizations
                WHERE id <> CAST(:legacy_id AS uuid)
                  AND (phone IS NOT NULL OR email IS NOT NULL
                       OR logo_reference IS NOT NULL)
            )
            """
        ),
        {"legacy_id": LEGACY_ORGANIZATION_ID},
    ).scalar():
        raise RuntimeError(
            "G01 downgrade refused: cross-organization profiles or institutional "
            "data cannot be collapsed into the legacy singleton."
        )

    for table in ("organization_invitations", "organization_memberships"):
        op.drop_constraint(
            f"fk_{table}__organization_profile",
            table,
            type_="foreignkey",
        )
        op.create_foreign_key(
            f"fk_{table}__access_profiles",
            table,
            "access_profiles",
            ["custom_profile_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.drop_constraint(
        "fk_access_profile_permissions__organization_profile",
        "access_profile_permissions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_access_profile_permissions__access_profiles"),
        "access_profile_permissions",
        "access_profiles",
        ["profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_column("access_profile_permissions", "organization_id")

    op.drop_constraint(
        op.f("uq_access_profiles__organization_name_key"),
        "access_profiles",
        type_="unique",
    )
    op.drop_constraint(
        op.f("uq_access_profiles__organization_id"),
        "access_profiles",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_access_profiles__name_key"), "access_profiles", ["name_key"]
    )
    op.drop_constraint(
        op.f("fk_access_profiles__organizations"),
        "access_profiles",
        type_="foreignkey",
    )
    op.drop_column("access_profiles", "organization_id")

    # Preserve the legacy singleton as the compatibility read source.
    op.drop_column("organizations", "logo_reference")
    op.drop_column("organizations", "email")
    op.drop_column("organizations", "phone")
    op.drop_constraint(
        op.f("ck_organizations__cnpj_format"), "organizations", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_organizations__cnpj_length"),
        "organizations",
        "cnpj IS NULL OR length(cnpj) = 14",
    )
