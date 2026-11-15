import os
import subprocess
import sys
from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.database.readiness import DatabaseReadinessChecker
from app.database.session import get_db
from app.main import app, get_readiness_checker

SessionFactory = Callable[[], Session]
BACKEND_ROOT = Path(__file__).resolve().parents[2]
TEST_DATABASE_ENV = "TEST_DATABASE_URL"
EXPECTED_DATABASE_NAME = "loadx_test"
EXPECTED_POSTGRESQL_MAJOR = 16


def _required_test_database_url() -> URL:
    raw_url = os.getenv(TEST_DATABASE_ENV)
    if not raw_url:
        raise pytest.UsageError(
            f"{TEST_DATABASE_ENV} is required for integration tests. "
            "Use the dedicated loadx_test PostgreSQL database."
        )

    test_url = make_url(raw_url)
    if test_url.drivername != "postgresql+psycopg":
        raise pytest.UsageError(f"{TEST_DATABASE_ENV} must use postgresql+psycopg.")
    if test_url.database != EXPECTED_DATABASE_NAME:
        raise pytest.UsageError(
            f"{TEST_DATABASE_ENV} must target the exclusive "
            f"{EXPECTED_DATABASE_NAME!r} database."
        )

    configured_url = make_url(settings.database_url)
    if _database_identity(test_url) == _database_identity(configured_url):
        raise pytest.UsageError(
            f"{TEST_DATABASE_ENV} must not target the configured application database."
        )
    return test_url


def _database_identity(
    url: URL,
) -> tuple[str | None, int | None, str | None, str | None]:
    return (url.host, url.port, url.database, url.username)


def _run_alembic(test_url: URL, *arguments: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise pytest.UsageError(
            "Alembic failed against the exclusive test database.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def _assert_postgresql_16(engine: Engine) -> None:
    with engine.connect() as connection:
        server_version_num = int(
            connection.exec_driver_sql("SHOW server_version_num").scalar_one()
        )
    if server_version_num // 10_000 != EXPECTED_POSTGRESQL_MAJOR:
        raise pytest.UsageError(
            "Integration tests require PostgreSQL 16; "
            f"the configured server reports {server_version_num}."
        )


def _reset_public_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
        connection.exec_driver_sql("CREATE SCHEMA public")


def _prepare_migrated_database(engine: Engine, test_url: URL) -> None:
    _reset_public_schema(engine)
    _run_alembic(test_url, "upgrade", "20261009_0019")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO drivers(id,name,document,phone,license_number,license_category,active) VALUES ('00000000-0000-4000-8000-000000000202','Legado fictício','12345678909','11900000000','12345678900','D',false)"
        )
    # Exercise the 0037 backfill with actual legacy profile + company rows.
    _run_alembic(test_url, "upgrade", "20261114_0036")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO company_profiles (
                id, legal_name, display_name, cnpj, phone, email, logo_reference
            ) VALUES (
                '00000000-0000-0000-0000-000000000091',
                'Empresa migrada LTDA', 'Empresa migrada',
                '11222333000181', '11900000000',
                'contato@example.test', 'https://example.test/logo.svg'
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO access_profiles(id, name, name_key, description)
            VALUES (
                '00000000-0000-4000-8000-000000000777',
                'Perfil legado', 'perfil legado', ''
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO access_profile_permissions(profile_id, permission_code)
            VALUES ('00000000-0000-4000-8000-000000000777', 'loadx.trucks.read')
            """
        )
    _run_alembic(test_url, "upgrade", "20261115_0037")
    # Verify G02's backfill against rows written by the PREVIOUS schema.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO customers(id,name,document,address,city,state)
            VALUES (
                '00000000-0000-4000-8000-000000000787',
                'Cliente legado', '00000000000199', 'Rua antiga',
                'Curitiba', 'PR'
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO products(
                id,code,name,width_cm,height_cm,length_cm,weight_kg
            ) VALUES (
                '00000000-0000-4000-8000-000000000788',
                'G02-LEGACY-SKU', 'Produto legado', 10, 20, 30, 3.250
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO customer_addresses(
                id,customer_id,label,address,city,state
            ) VALUES (
                '00000000-0000-4000-8000-000000000789',
                '00000000-0000-4000-8000-000000000787',
                'Principal', 'Rua antiga', 'Curitiba', 'PR'
            )
            """
        )
    _run_alembic(test_url, "upgrade", "20261115_0038")
    # Exercise G03 over the existing legacy fleet, not a fresh 0039 schema.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO trucks(
                id, plate, model, internal_width_cm, internal_height_cm,
                internal_length_cm, max_weight_kg
            ) VALUES (
                '00000000-0000-4000-8000-000000000790',
                'G03T123', 'Frota legada', 200, 220, 600, 4000
            )
            """
        )
    _run_alembic(test_url, "upgrade", "20261115_0039")
    # G03-B1 must backfill rows created by the historical fleet schema.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO truck_maintenances(
                id, truck_id, kind, starts_at, description
            ) VALUES (
                '00000000-0000-4000-8000-000000000791',
                '00000000-0000-4000-8000-000000000790',
                'PREVENTIVE', NOW(), 'Manutenção legada'
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO truck_documents(id, truck_id, kind, reference)
            VALUES (
                '00000000-0000-4000-8000-000000000792',
                '00000000-0000-4000-8000-000000000790',
                'CRLV', 'Documento legado'
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO truck_document_policies(id, truck_id, kind, required)
            VALUES (
                '00000000-0000-4000-8000-000000000793',
                '00000000-0000-4000-8000-000000000790',
                'CRLV', TRUE
            )
            """
        )
    _run_alembic(test_url, "upgrade", "20261115_0040")
    # Backfill legacy custom document types and their dependent policy.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO driver_document_types(id, code, name)
            VALUES (
                '00000000-0000-4000-8000-000000000794',
                'G03B2_LEGACY', 'Tipo documental legado'
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO driver_document_policies(
                id, driver_id, document_type_id, required, allowed_categories
            ) VALUES (
                '00000000-0000-4000-8000-000000000795',
                '00000000-0000-4000-8000-000000000202',
                '00000000-0000-4000-8000-000000000794',
                TRUE, '[]'
            )
            """
        )
    _run_alembic(test_url, "upgrade", "20261115_0041")
    # G04 must migrate already existing order/customer/product references.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO orders(
                id, customer_id, priority, delivery_address
            ) VALUES (
                '00000000-0000-4000-8000-000000000796',
                '00000000-0000-4000-8000-000000000787',
                'NORMAL', 'Endereço legado'
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO order_items(
                id, order_id, product_id, quantity, delivery_sequence
            ) VALUES (
                '00000000-0000-4000-8000-000000000797',
                '00000000-0000-4000-8000-000000000796',
                '00000000-0000-4000-8000-000000000788',
                3, 1
            )
            """
        )
    _run_alembic(test_url, "upgrade", "20261115_0042")
    # Exercise G05-A against a plan created before its organization column exists.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO load_plans(
                id, truck_id, status, truck_snapshot_plate,
                truck_snapshot_model, truck_snapshot_internal_width_cm,
                truck_snapshot_internal_height_cm,
                truck_snapshot_internal_length_cm,
                truck_snapshot_max_weight_kg, internal_volume_cm3,
                used_volume_cm3, occupancy_percent, total_weight_kg,
                loaded_count, unloaded_count, algorithm_version
            ) VALUES (
                '00000000-0000-4000-8000-000000000798',
                '00000000-0000-4000-8000-000000000790',
                'REJECTED', 'G03T123', 'Frota legada',
                100, 100, 100, 100, 1000000, 0, 0, 0,
                0, 1, 'heuristic-v1'
            )
            """
        )
    _run_alembic(test_url, "upgrade", "20261115_0043")
    # Exercise G05-B against links and rejected volumes created by the old schema.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO load_plan_orders(load_plan_id, order_id)
            VALUES (
                '00000000-0000-4000-8000-000000000798',
                '00000000-0000-4000-8000-000000000796'
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO load_plan_items(
                id, load_plan_id, order_id, order_item_id, product_id,
                volume_index, order_item_snapshot_quantity,
                order_item_snapshot_delivery_sequence, product_snapshot_code,
                product_snapshot_name, product_snapshot_width_cm,
                product_snapshot_height_cm, product_snapshot_length_cm,
                product_snapshot_weight_kg, product_snapshot_fragile,
                product_snapshot_stackable, product_snapshot_rotation_allowed,
                placed, rejection_reason
            ) VALUES (
                '00000000-0000-4000-8000-000000000799',
                '00000000-0000-4000-8000-000000000798',
                '00000000-0000-4000-8000-000000000796',
                '00000000-0000-4000-8000-000000000797',
                '00000000-0000-4000-8000-000000000788',
                1, 3, 1, 'G02-LEGACY-SKU', 'Produto legado',
                10, 20, 30, 3.250, false, true, true,
                false, 'NO_VALID_POSITION'
            )
            """
        )
    _run_alembic(test_url, "upgrade", "head")
    with engine.connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT organization_id::text FROM load_plan_orders "
            "WHERE load_plan_id='00000000-0000-4000-8000-000000000798'"
        ).scalar_one() == "00000000-0000-4000-8000-000000000301"
        assert connection.exec_driver_sql(
            "SELECT organization_id::text FROM load_plan_items "
            "WHERE id='00000000-0000-4000-8000-000000000799'"
        ).scalar_one() == "00000000-0000-4000-8000-000000000301"
        plan_owner = connection.exec_driver_sql(
            "SELECT organization_id::text FROM load_plans "
            "WHERE id='00000000-0000-4000-8000-000000000798'"
        ).scalar_one()
        assert plan_owner == "00000000-0000-4000-8000-000000000301"
        for table, row_id in (
            ("orders", "00000000-0000-4000-8000-000000000796"),
            ("order_items", "00000000-0000-4000-8000-000000000797"),
        ):
            owner = connection.exec_driver_sql(
                f"SELECT organization_id::text FROM {table} WHERE id='{row_id}'"
            ).scalar_one()
            assert owner == "00000000-0000-4000-8000-000000000301"
        custom_type_owner = connection.exec_driver_sql(
            "SELECT organization_id::text FROM driver_document_types "
            "WHERE id='00000000-0000-4000-8000-000000000794'"
        ).scalar_one()
        custom_policy_owner = connection.exec_driver_sql(
            "SELECT document_type_organization_id::text "
            "FROM driver_document_policies "
            "WHERE id='00000000-0000-4000-8000-000000000795'"
        ).scalar_one()
        cnh_owner = connection.exec_driver_sql(
            "SELECT organization_id FROM driver_document_types "
            "WHERE id='00000000-0000-4000-8000-000000000102'"
        ).scalar_one()
        assert custom_type_owner == "00000000-0000-4000-8000-000000000301"
        assert custom_policy_owner == "00000000-0000-4000-8000-000000000301"
        assert cnh_owner is None
        for table, row_id in (
            ("truck_maintenances", "00000000-0000-4000-8000-000000000791"),
            ("truck_documents", "00000000-0000-4000-8000-000000000792"),
            ("truck_document_policies", "00000000-0000-4000-8000-000000000793"),
            ("drivers", "00000000-0000-4000-8000-000000000202"),
            ("trucks", "00000000-0000-4000-8000-000000000790"),
            ("customers", "00000000-0000-4000-8000-000000000787"),
            ("products", "00000000-0000-4000-8000-000000000788"),
            ("customer_addresses", "00000000-0000-4000-8000-000000000789"),
        ):
            owner = connection.exec_driver_sql(
                f"SELECT organization_id::text FROM {table} WHERE id='{row_id}'"
            ).scalar_one()
            assert owner == "00000000-0000-4000-8000-000000000301"
        assert tuple(
            connection.exec_driver_sql(
                "SELECT reference,category,expires_at,legacy_backfill FROM driver_documents WHERE driver_id='00000000-0000-4000-8000-000000000202'"
            ).one()
        ) == ("12345678900", "D", None, True)
        driver_doc_owner = connection.exec_driver_sql(
            "SELECT organization_id::text FROM driver_documents "
            "WHERE driver_id='00000000-0000-4000-8000-000000000202'"
        ).scalar_one()
        assert driver_doc_owner == "00000000-0000-4000-8000-000000000301"
        profile_org = connection.exec_driver_sql(
            "SELECT organization_id::text FROM access_profiles "
            "WHERE id='00000000-0000-4000-8000-000000000777'"
        ).scalar_one()
        permission_org = connection.exec_driver_sql(
            "SELECT organization_id::text FROM access_profile_permissions "
            "WHERE profile_id='00000000-0000-4000-8000-000000000777'"
        ).scalar_one()
        assert profile_org == "00000000-0000-4000-8000-000000000301"
        assert permission_org == "00000000-0000-4000-8000-000000000301"
        assert tuple(
            connection.exec_driver_sql(
                "SELECT legal_name, display_name, cnpj, phone, email, logo_reference "
                "FROM organizations "
                "WHERE id='00000000-0000-4000-8000-000000000301'"
            ).one()
        ) == (
            "Empresa migrada LTDA",
            "Empresa migrada",
            "11222333000181",
            "11900000000",
            "contato@example.test",
            "https://example.test/logo.svg",
        )
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "DELETE FROM driver_document_policies "
            "WHERE id='00000000-0000-4000-8000-000000000795'"
        )
        connection.exec_driver_sql(
            "DELETE FROM driver_document_types "
            "WHERE id='00000000-0000-4000-8000-000000000794'"
        )
        connection.exec_driver_sql(
            "DELETE FROM truck_document_policies "
            "WHERE id='00000000-0000-4000-8000-000000000793'"
        )
        connection.exec_driver_sql(
            "DELETE FROM truck_documents WHERE id='00000000-0000-4000-8000-000000000792'"
        )
        connection.exec_driver_sql(
            "DELETE FROM truck_maintenances "
            "WHERE id='00000000-0000-4000-8000-000000000791'"
        )
        connection.exec_driver_sql(
            "DELETE FROM load_plan_items WHERE id='00000000-0000-4000-8000-000000000799'"
        )
        connection.exec_driver_sql(
            "DELETE FROM load_plan_orders "
            "WHERE load_plan_id='00000000-0000-4000-8000-000000000798'"
        )
        connection.exec_driver_sql(
            "DELETE FROM load_plans WHERE id='00000000-0000-4000-8000-000000000798'"
        )
        connection.exec_driver_sql(
            "DELETE FROM trucks WHERE id='00000000-0000-4000-8000-000000000790'"
        )
        connection.exec_driver_sql(
            "DELETE FROM order_items WHERE id='00000000-0000-4000-8000-000000000797'"
        )
        connection.exec_driver_sql(
            "DELETE FROM orders WHERE id='00000000-0000-4000-8000-000000000796'"
        )
        connection.exec_driver_sql(
            "DELETE FROM customer_addresses WHERE id='00000000-0000-4000-8000-000000000789'"
        )
        connection.exec_driver_sql(
            "DELETE FROM products WHERE id='00000000-0000-4000-8000-000000000788'"
        )
        connection.exec_driver_sql(
            "DELETE FROM customers WHERE id='00000000-0000-4000-8000-000000000787'"
        )
        connection.exec_driver_sql(
            "DELETE FROM access_profile_permissions "
            "WHERE profile_id='00000000-0000-4000-8000-000000000777'"
        )
        connection.exec_driver_sql(
            "DELETE FROM access_profiles WHERE id='00000000-0000-4000-8000-000000000777'"
        )
        connection.exec_driver_sql(
            "DELETE FROM company_profiles WHERE id='00000000-0000-0000-0000-000000000091'"
        )
        connection.exec_driver_sql(
            "UPDATE organizations SET legal_name='Empresa legada', "
            "display_name='Empresa legada', cnpj=NULL, phone=NULL, "
            "email=NULL, logo_reference=NULL "
            "WHERE id='00000000-0000-4000-8000-000000000301'"
        )

    with engine.connect() as connection:
        head_revision = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()
        assert head_revision == "20261115_0044"

    # Descend through OC94 and trusted-device revisions explicitly; -1 would
    # only reach 0030 now and would not exercise the trusted-device rollback.
    _run_alembic(test_url, "downgrade", "20261021_0029")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            == "20261021_0029"
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.auth_trusted_devices')"
            ).scalar_one()
            is None
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.auth_factors')"
            ).scalar_one()
            is not None
        )
    _run_alembic(test_url, "upgrade", "head")
    _run_alembic(test_url, "downgrade", "20261021_0029")

    # OC98 rollback preserves all integrated operational and authorization tables.
    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            == "20261020_0028"
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.auth_factors')"
            ).scalar_one()
            is None
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.access_profiles')"
            ).scalar_one()
            is not None
        )
        for table in (
            "operational_notifications",
            "notification_recipients",
            "outbox_events",
        ):
            assert (
                connection.exec_driver_sql(
                    f"SELECT to_regclass('public.{table}')"
                ).scalar_one()
                == table
            )
        assert connection.exec_driver_sql(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='deliveries' AND column_name='distribution_part_id')"
        ).scalar_one()
    _run_alembic(test_url, "upgrade", "head")
    _run_alembic(test_url, "downgrade", "20261020_0028")

    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        assert not connection.exec_driver_sql(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='deliveries' AND column_name='distribution_part_id')"
        ).scalar_one()
    _run_alembic(test_url, "upgrade", "head")
    _run_alembic(test_url, "downgrade", "20261020_0027")

    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.outbox_events')"
            ).scalar_one()
            is None
        )
        assert (
            connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            == "20261020_0026"
        )

    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            == "20261020_0025"
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.notification_recipients')"
            ).scalar_one()
            is None
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.operational_notifications')"
            ).scalar_one()
            == "operational_notifications"
        )

    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            == "20261016_0024"
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.operational_notifications')"
            ).scalar_one()
            is None
        )
    _run_alembic(test_url, "upgrade", "head")
    _run_alembic(test_url, "downgrade", "20261020_0026")
    _run_alembic(test_url, "downgrade", "-1")
    _run_alembic(test_url, "downgrade", "-1")
    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.access_profiles')"
            ).scalar_one()
            is None
        )
    _run_alembic(test_url, "upgrade", "head")
    _run_alembic(test_url, "downgrade", "20261009_0023")

    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            == "20261009_0022"
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.company_profiles')"
            ).scalar_one()
            is None
        )

    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            == "20261009_0021"
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.registration_imports')"
            ).scalar_one()
            is None
        )

    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            == "20261009_0020"
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.operational_attachments')"
            ).scalar_one()
            is None
        )

    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            == "20261009_0019"
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.driver_documents')"
            ).scalar_one()
            is None
        )
    with engine.begin() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT license_number FROM drivers WHERE id='00000000-0000-4000-8000-000000000202'"
            ).scalar_one()
            == "12345678900"
        )
        connection.exec_driver_sql(
            "DELETE FROM drivers WHERE id='00000000-0000-4000-8000-000000000202'"
        )
    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            == "20261009_0018"
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.truck_documents')"
            ).scalar_one()
            is None
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.truck_document_policies')"
            ).scalar_one()
            is None
        )
    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        downgraded_revision = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()
        loading_sessions_exists = connection.exec_driver_sql(
            "SELECT to_regclass('public.loading_sessions')"
        ).scalar_one()
        loading_items_exists = connection.exec_driver_sql(
            "SELECT to_regclass('public.loading_session_items')"
        ).scalar_one()
        trip_created_at_exists = connection.exec_driver_sql(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'trips'
                  AND column_name = 'created_at'
            )
            """
        ).scalar_one()
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' "
                "AND table_name='trucks' AND column_name='odometer_km'"
            ).scalar_one()
            == 0
        )
        assert downgraded_revision == "20261008_0017"
        assert loading_sessions_exists == "loading_sessions"
        assert loading_items_exists == "loading_session_items"
        assert trip_created_at_exists is True
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.external_commands')"
            ).scalar_one()
            == "external_commands"
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.audit_events')"
            ).scalar_one()
            == "audit_events"
        )
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.load_distributions')"
            ).scalar_one()
            == "load_distributions"
        )

        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.delivery_evidences')"
            ).scalar_one()
            == "delivery_evidences"
        )

    _run_alembic(test_url, "downgrade", "20261008_0016")
    # Exercise real OC99 backfill against legacy data, including an archived
    # customer and a contracted destination different from the registry.
    with engine.begin() as connection:
        connection.exec_driver_sql("""
            INSERT INTO customers (id, name, document, address, city, state, active)
            VALUES ('00000000-0000-4000-8000-000000000099', 'Legado fictício', '00000000000191', 'Cadastro antigo', 'Campinas', 'SP', false);
            INSERT INTO orders (id, customer_id, priority, delivery_address)
            VALUES ('00000000-0000-4000-8000-000000000098', '00000000-0000-4000-8000-000000000099', 'NORMAL', 'Destino contratado antigo')
        """)
    # OC99 updates existing orders. Commit its RI trigger events before
    # subsequent migrations (G04 adds columns to the same table).
    # This still exercises the historical 0017 backfill and full upgrade.
    _run_alembic(test_url, "upgrade", "20261008_0017")
    _run_alembic(test_url, "upgrade", "head")
    with engine.connect() as connection:
        legacy = connection.exec_driver_sql(
            "SELECT a.address, a.city, a.state, a.is_primary, a.active, c.active FROM customer_addresses a JOIN customers c ON c.id=a.customer_id"
        ).one()
        assert tuple(legacy) == ("Cadastro antigo", "Campinas", "SP", True, True, False)
        order = connection.exec_driver_sql(
            "SELECT customer_address_id, delivery_address, delivery_address_snapshot FROM orders"
        ).one()
        assert tuple(order) == (
            None,
            "Destino contratado antigo",
            {"address": "Destino contratado antigo"},
        )
    _run_alembic(test_url, "downgrade", "20261008_0016")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT delivery_address FROM orders"
            ).scalar_one()
            == "Destino contratado antigo"
        )
    # OC99 updates existing orders. Commit its RI trigger events before
    # subsequent migrations (G04 adds columns to the same table).
    # This still exercises the historical 0017 backfill and full upgrade.
    _run_alembic(test_url, "upgrade", "20261008_0017")
    _run_alembic(test_url, "upgrade", "head")
    _run_alembic(test_url, "check")
    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM orders")
        connection.exec_driver_sql("DELETE FROM customer_addresses")
        connection.exec_driver_sql("DELETE FROM customers")


@pytest.fixture(scope="session")
def postgres_engine() -> Generator[Engine, None, None]:
    test_url = _required_test_database_url()
    engine = create_engine(test_url, poolclass=NullPool)
    _assert_postgresql_16(engine)
    _prepare_migrated_database(engine, test_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session_factory(
    postgres_engine: Engine,
) -> Generator[SessionFactory, None, None]:
    """Isolate each integration test in an outer PostgreSQL transaction."""

    connection = postgres_engine.connect()
    transaction = connection.begin()
    testing_session_local = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield testing_session_local
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def committed_session_factory(
    postgres_engine: Engine,
) -> Generator[SessionFactory, None, None]:
    """Exercise real commit boundaries; exclusively on the validated test database."""
    factory = sessionmaker(bind=postgres_engine, autoflush=False)
    try:
        yield factory
    finally:
        with postgres_engine.begin() as connection:
            connection.execute(
                text("TRUNCATE customers, products, trucks, drivers, users CASCADE")
            )


@pytest.fixture
def client(session_factory: SessionFactory) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    test_database_url = _required_test_database_url().render_as_string(
        hide_password=False
    )
    readiness_checker = DatabaseReadinessChecker(test_database_url)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_readiness_checker] = lambda: readiness_checker
    try:
        with TestClient(
            app,
            raise_server_exceptions=False,
            headers={"Origin": "http://localhost:5173"},
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
