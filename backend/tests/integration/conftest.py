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
        assert head_revision == "20260804_0004"

    _run_alembic(test_url, "downgrade", "-1")
    with engine.connect() as connection:
        downgraded_revision = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()
        load_plans_exists = connection.exec_driver_sql(
            "SELECT to_regclass('public.load_plans')"
        ).scalar_one()
        assert downgraded_revision == "20260730_0003"
        assert load_plans_exists is None

    _run_alembic(test_url, "upgrade", "head")


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
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
