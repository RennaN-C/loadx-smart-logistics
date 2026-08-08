from __future__ import annotations

from configparser import Error as ConfigParserError
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path
from time import monotonic
from typing import Any

import psycopg
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from psycopg import sql
from psycopg.cursor import Cursor
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

DEFAULT_READINESS_TIMEOUT_SECONDS = 2.0
DEFAULT_ALEMBIC_CONFIG_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"


class ReadinessFailureReason(StrEnum):
    CONFIGURATION_INVALID = "CONFIGURATION_INVALID"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    DATABASE_RESPONSE_INVALID = "DATABASE_RESPONSE_INVALID"
    MIGRATION_MISMATCH = "MIGRATION_MISMATCH"
    TIMEOUT = "TIMEOUT"


class ReadinessCheckError(RuntimeError):
    def __init__(self, reason: ReadinessFailureReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


@cache
def _load_expected_heads(config_path: Path) -> frozenset[str]:
    alembic_config = Config(str(config_path))
    heads = frozenset(ScriptDirectory.from_config(alembic_config).get_heads())
    if not heads:
        raise ValueError("Alembic has no configured head revision.")
    return heads


def _render_psycopg_url(database_url: str) -> str:
    parsed_url = make_url(database_url)
    if parsed_url.get_backend_name() != "postgresql":
        raise ValueError("Readiness requires PostgreSQL.")
    return parsed_url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )


def _remaining_milliseconds(deadline: float) -> int:
    remaining_ms = int((deadline - monotonic()) * 1000)
    if remaining_ms <= 0:
        raise ReadinessCheckError(ReadinessFailureReason.TIMEOUT)
    return remaining_ms


def _set_statement_timeout(cursor: Cursor[Any], deadline: float) -> None:
    remaining_ms = _remaining_milliseconds(deadline)
    cursor.execute(
        sql.SQL("SET statement_timeout = {}").format(sql.Literal(remaining_ms))
    )


@dataclass(frozen=True, slots=True)
class DatabaseReadinessChecker:
    database_url: str
    timeout_seconds: float = DEFAULT_READINESS_TIMEOUT_SECONDS
    alembic_config_path: Path = DEFAULT_ALEMBIC_CONFIG_PATH
    expected_heads: frozenset[str] | None = None

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("Readiness timeout must be positive.")

    def check(self) -> None:
        deadline = monotonic() + self.timeout_seconds
        expected_heads = self._expected_heads()
        conninfo = self._connection_url()

        try:
            current_heads = self._read_current_heads(conninfo, deadline)
        except ReadinessCheckError:
            raise
        except psycopg.errors.QueryCanceled:
            raise ReadinessCheckError(ReadinessFailureReason.TIMEOUT) from None
        except psycopg.Error:
            raise ReadinessCheckError(
                ReadinessFailureReason.DATABASE_UNAVAILABLE
            ) from None

        _remaining_milliseconds(deadline)
        if current_heads != expected_heads:
            raise ReadinessCheckError(ReadinessFailureReason.MIGRATION_MISMATCH)

    def _expected_heads(self) -> frozenset[str]:
        if self.expected_heads is not None:
            return self.expected_heads
        try:
            return _load_expected_heads(self.alembic_config_path)
        except (CommandError, ConfigParserError, KeyError, OSError, ValueError):
            raise ReadinessCheckError(
                ReadinessFailureReason.CONFIGURATION_INVALID
            ) from None

    def _connection_url(self) -> str:
        try:
            return _render_psycopg_url(self.database_url)
        except (ArgumentError, ValueError):
            raise ReadinessCheckError(
                ReadinessFailureReason.CONFIGURATION_INVALID
            ) from None

    def _read_current_heads(
        self,
        conninfo: str,
        deadline: float,
    ) -> frozenset[str]:
        remaining_ms = _remaining_milliseconds(deadline)
        connect_timeout = max(1, remaining_ms // 1000)
        options = (
            f"-c statement_timeout={remaining_ms} "
            "-c default_transaction_read_only=on"
        )

        with psycopg.connect(
            conninfo,
            connect_timeout=connect_timeout,
            options=options,
            autocommit=True,
        ) as connection, connection.cursor() as cursor:
            _set_statement_timeout(cursor, deadline)
            cursor.execute("SELECT 1")
            if cursor.fetchone() != (1,):
                raise ReadinessCheckError(
                    ReadinessFailureReason.DATABASE_RESPONSE_INVALID
                )

            _set_statement_timeout(cursor, deadline)
            cursor.execute("SELECT version_num FROM alembic_version")
            rows = cursor.fetchall()

        return frozenset(str(row[0]) for row in rows)
