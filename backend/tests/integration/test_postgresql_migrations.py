import uuid
from collections.abc import Callable
from decimal import Decimal

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.integrity import get_integrity_constraint_name
from app.modules.orders.models import Order
from app.modules.trucks.models import Truck

SessionFactory = Callable[[], Session]


def test_postgresql_16_reaches_alembic_head(postgres_engine: Engine) -> None:
    with postgres_engine.connect() as connection:
        server_version_num = int(
            connection.exec_driver_sql("SHOW server_version_num").scalar_one()
        )
        revision = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()
        tables = set(
            connection.exec_driver_sql(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ).scalars()
        )

    assert server_version_num // 10_000 == 16
    assert revision == "20260825_0010"
    assert {
        "users",
        "customers",
        "drivers",
        "trucks",
        "products",
        "orders",
        "order_items",
        "status_history",
        "load_plans",
        "load_plan_orders",
        "load_plan_items",
        "auth_login_throttles",
        "auth_sessions",
        "trips",
        "deliveries",
        "occurrences",
        "loading_sessions",
        "loading_session_items",
    } <= tables


def test_postgresql_exposes_official_native_column_types(
    postgres_engine: Engine,
) -> None:
    with postgres_engine.connect() as connection:
        rows = connection.exec_driver_sql(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND (table_name, column_name) IN (
                  ('users', 'id'),
                  ('trucks', 'max_weight_kg'),
                  ('users', 'created_at')
              )
            """
        ).all()

    column_types = {
        (table_name, column_name): data_type
        for table_name, column_name, data_type in rows
    }
    assert column_types[("users", "id")] == "uuid"
    assert column_types[("trucks", "max_weight_kg")] == "numeric"
    assert column_types[("users", "created_at")] == "timestamp with time zone"


def test_postgresql_rejects_foreign_key_violation(
    session_factory: SessionFactory,
) -> None:
    with session_factory() as db:
        db.add(
            Order(
                customer_id=uuid.uuid4(),
                status="DRAFT",
                priority="NORMAL",
                delivery_address="Rua de Teste, 100",
            )
        )
        with pytest.raises(IntegrityError) as raised:
            db.flush()

        assert get_integrity_constraint_name(raised.value) == "fk_orders__customers"


def test_postgresql_rejects_dimension_check_violation(
    session_factory: SessionFactory,
) -> None:
    with session_factory() as db:
        db.add(
            Truck(
                plate="CHK1A23",
                model="Caminhao de constraint",
                internal_width_cm=0,
                internal_height_cm=200,
                internal_length_cm=500,
                max_weight_kg=Decimal("8000.00"),
                active=True,
            )
        )
        with pytest.raises(IntegrityError) as raised:
            db.flush()

        assert (
            get_integrity_constraint_name(raised.value)
            == "ck_trucks__dimensions_positive"
        )


def test_postgresql_preserves_uuid_numeric_and_timezone_values(
    session_factory: SessionFactory,
) -> None:
    with session_factory() as db:
        truck = Truck(
            plate="TYP1A23",
            model="Caminhao de tipos",
            internal_width_cm=240,
            internal_height_cm=260,
            internal_length_cm=600,
            max_weight_kg=Decimal("8000.10"),
            active=True,
        )
        db.add(truck)
        db.commit()
        db.refresh(truck)

        assert isinstance(truck.id, uuid.UUID)
        assert truck.max_weight_kg == Decimal("8000.10")
        assert truck.created_at.tzinfo is not None
        assert truck.created_at.utcoffset() is not None
