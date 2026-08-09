from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Self

import psycopg
import pytest

from app.database import readiness as readiness_module
from app.database.readiness import (
    DEFAULT_ALEMBIC_CONFIG_PATH,
    DatabaseReadinessChecker,
    ReadinessCheckError,
    ReadinessFailureReason,
    _load_expected_heads,
)


class FakeCursor:
    def __init__(self, heads: tuple[str, ...], ping: tuple[int] = (1,)) -> None:
        self.heads = heads
        self.ping = ping
        self.last_query = ""
        self.queries: list[object] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, query: object) -> None:
        self.queries.append(query)
        if isinstance(query, str) and query.startswith("SELECT"):
            self.last_query = query

    def fetchone(self) -> tuple[int]:
        return self.ping

    def fetchall(self) -> list[tuple[str]]:
        assert self.last_query == "SELECT version_num FROM alembic_version"
        return [(head,) for head in self.heads]


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self._cursor


def _install_fake_connection(
    monkeypatch: pytest.MonkeyPatch,
    cursor: FakeCursor,
) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def fake_connect(conninfo: str, **kwargs: Any) -> FakeConnection:
        captured["conninfo"] = conninfo
        captured.update(kwargs)
        return FakeConnection(cursor)

    monkeypatch.setattr(readiness_module.psycopg, "connect", fake_connect)
    return captured


def test_loads_the_versioned_alembic_head() -> None:
    assert _load_expected_heads(DEFAULT_ALEMBIC_CONFIG_PATH) == frozenset(
        {"20260808_0005"}
    )


def test_accepts_database_with_exact_head_and_read_only_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = FakeCursor(("20260804_0004",))
    captured = _install_fake_connection(monkeypatch, cursor)
    checker = DatabaseReadinessChecker(
        "postgresql+psycopg://loadx:secret@db:5432/loadx",
        expected_heads=frozenset({"20260804_0004"}),
    )

    checker.check()

    assert captured["autocommit"] is True
    assert captured["connect_timeout"] <= 2
    assert "default_transaction_read_only=on" in captured["options"]
    assert "statement_timeout=" in captured["options"]
    assert "SELECT 1" in cursor.queries
    assert "SELECT version_num FROM alembic_version" in cursor.queries


def test_rejects_migration_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = FakeCursor(("20260730_0003",))
    _install_fake_connection(monkeypatch, cursor)
    checker = DatabaseReadinessChecker(
        "postgresql+psycopg://loadx:secret@db:5432/loadx",
        expected_heads=frozenset({"20260804_0004"}),
    )

    with pytest.raises(ReadinessCheckError) as captured:
        checker.check()

    assert captured.value.reason is ReadinessFailureReason.MIGRATION_MISMATCH


def test_hides_driver_error_and_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_connect(*_args: object, **_kwargs: object) -> None:
        raise psycopg.OperationalError("could not connect with password secret-value")

    monkeypatch.setattr(readiness_module.psycopg, "connect", fail_connect)
    checker = DatabaseReadinessChecker(
        "postgresql+psycopg://loadx:secret-value@db:5432/loadx",
        expected_heads=frozenset({"20260804_0004"}),
    )

    with pytest.raises(ReadinessCheckError) as captured:
        checker.check()

    assert captured.value.reason is ReadinessFailureReason.DATABASE_UNAVAILABLE
    assert str(captured.value) == "DATABASE_UNAVAILABLE"
    assert "secret-value" not in str(captured.value)


def test_rejects_non_postgresql_configuration() -> None:
    checker = DatabaseReadinessChecker(
        "sqlite:///local.db",
        expected_heads=frozenset({"20260804_0004"}),
    )

    with pytest.raises(ReadinessCheckError) as captured:
        checker.check()

    assert captured.value.reason is ReadinessFailureReason.CONFIGURATION_INVALID


def test_stops_when_total_timeout_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    times: Iterator[float] = iter((0.0, 3.0))
    monkeypatch.setattr(readiness_module, "monotonic", lambda: next(times))
    checker = DatabaseReadinessChecker(
        "postgresql+psycopg://loadx:secret@db:5432/loadx",
        timeout_seconds=2,
        expected_heads=frozenset({"20260804_0004"}),
    )

    with pytest.raises(ReadinessCheckError) as captured:
        checker.check()

    assert captured.value.reason is ReadinessFailureReason.TIMEOUT
