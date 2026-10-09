import os
import subprocess
import sys
from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
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
    _run_alembic(test_url, "upgrade", "head")

    with engine.connect() as connection:
        head_revision = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()
        assert head_revision == "20261009_0018"

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
