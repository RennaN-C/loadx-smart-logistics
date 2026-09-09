from collections.abc import Generator, Sequence

import pytest
from sqlalchemy import Table, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def db_session(request: pytest.FixtureRequest) -> Generator[Session, None, None]:
    """Provide an isolated SQLite session for service-level unit tests."""

    tables: Sequence[Table] = request.module.SQLITE_TABLES
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    for table in tables:
        table.create(engine, checkfirst=True)

    testing_session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()
