"""create core catalog tables

Revision ID: 20260729_0001
Revises:
Create Date: 2026-07-29 23:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260729_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('ADMIN', 'CHECKER', 'DRIVER', 'LOGISTICS_MANAGER')",
            name=op.f("ck_users__role_allowed"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users__email"),
    )
    op.create_index("ix_users__role", "users", ["role"], unique=False)

    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("document", sa.String(length=32), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
        sa.UniqueConstraint("document", name="uq_customers__document"),
    )
    op.create_index("ix_customers__name", "customers", ["name"], unique=False)

    op.create_table(
        "drivers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("document", sa.String(length=32), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("license_number", sa.String(length=32), nullable=False),
        sa.Column("license_category", sa.String(length=8), nullable=True),
        sa.Column(
            "active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_drivers"),
        sa.UniqueConstraint("document", name="uq_drivers__document"),
        sa.UniqueConstraint("license_number", name="uq_drivers__license_number"),
    )
    op.create_index("ix_drivers__phone", "drivers", ["phone"], unique=False)

    op.create_table(
        "trucks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plate", sa.String(length=16), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("internal_width_cm", sa.Integer(), nullable=False),
        sa.Column("internal_height_cm", sa.Integer(), nullable=False),
        sa.Column("internal_length_cm", sa.Integer(), nullable=False),
        sa.Column("max_weight_kg", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "internal_width_cm > 0 AND internal_height_cm > 0 AND internal_length_cm > 0",
            name=op.f("ck_trucks__dimensions_positive"),
        ),
        sa.CheckConstraint(
            "max_weight_kg > 0", name=op.f("ck_trucks__max_weight_positive")
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trucks"),
        sa.UniqueConstraint("plate", name="uq_trucks__plate"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("width_cm", sa.Integer(), nullable=False),
        sa.Column("height_cm", sa.Integer(), nullable=False),
        sa.Column("length_cm", sa.Integer(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column(
            "fragile", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "stackable", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "rotation_allowed",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "width_cm > 0 AND height_cm > 0 AND length_cm > 0",
            name=op.f("ck_products__dimensions_positive"),
        ),
        sa.CheckConstraint("weight_kg > 0", name=op.f("ck_products__weight_positive")),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("code", name="uq_products__code"),
    )
    op.create_index("ix_products__name", "products", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_products__name", table_name="products")
    op.drop_table("products")

    op.drop_table("trucks")

    op.drop_index("ix_drivers__phone", table_name="drivers")
    op.drop_table("drivers")

    op.drop_index("ix_customers__name", table_name="customers")
    op.drop_table("customers")

    op.drop_index("ix_users__role", table_name="users")
    op.drop_table("users")
