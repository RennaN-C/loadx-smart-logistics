import base64
import binascii
import csv
import hashlib
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from io import StringIO

from pydantic import BaseModel, ValidationError

from app.modules.registration_imports.schemas import (
    MAX_IMPORT_BYTES,
    MAX_IMPORT_CELL,
    MAX_IMPORT_ROWS,
    ImportFile,
    ImportRowError,
)


@dataclass(frozen=True, slots=True)
class ParsedRow:
    line: int
    data: BaseModel


@dataclass(slots=True)
class ParsedImport:
    sha256: str
    row_count: int = 0
    rows: list[ParsedRow] = field(default_factory=list)
    errors: list[ImportRowError] = field(default_factory=list)


def row_error(line: int, field: str, code: str, message: str) -> ImportRowError:
    return ImportRowError(line=line, field=field, code=code, message=message)


def _file_error(parsed: ParsedImport, code: str, message: str) -> ParsedImport:
    parsed.rows.clear()
    parsed.row_count = 0
    parsed.errors = [row_error(0, "file", code, message)]
    return parsed


def _unsafe_cell(value: str, field: str) -> bool:
    text = value.lstrip()
    if not text or text[0] not in "=+-@":
        return False
    return not (field == "phone" and re.fullmatch(r"\+[0-9 ()-]+", text))


def _parse_row(
    values: list[str],
    header: list[str],
    line: int,
    schema: type[BaseModel],
    parsed: ParsedImport,
) -> None:
    if len(values) != len(header):
        parsed.errors.append(
            row_error(
                line,
                "row",
                "CSV_COLUMN_COUNT",
                "Quantidade de colunas diferente do cabeçalho.",
            )
        )
        return
    payload: dict[str, object] = {}
    for name, value in zip(header, values, strict=True):
        if len(value) > MAX_IMPORT_CELL:
            parsed.errors.append(
                row_error(
                    line, name, "CSV_CELL_LIMIT", "Célula excede 4096 caracteres."
                )
            )
        elif _unsafe_cell(value, name):
            parsed.errors.append(
                row_error(
                    line, name, "CSV_FORMULA", "Prefixos de fórmula não são permitidos."
                )
            )
        if not value.strip() and not schema.model_fields[name].is_required():
            continue
        if name in {"weight_kg", "max_weight_kg"}:
            try:
                payload[name] = Decimal(value)
            except InvalidOperation:
                payload[name] = value
        elif name == "odometer_km":
            payload[name] = (
                int(value) if re.fullmatch(r"[0-9]+", value.strip()) else value
            )
        elif name in {"active", "fragile", "stackable", "rotation_allowed"}:
            text = value.strip().lower()
            payload[name] = {"true": True, "false": False, "1": True, "0": False}.get(
                text, value
            )
            if text not in {"true", "false", "1", "0"}:
                parsed.errors.append(
                    row_error(line, name, "CSV_BOOLEAN", "Use true/false ou 1/0.")
                )
        else:
            payload[name] = value
    try:
        model = schema.model_validate(payload)
    except ValidationError as error:
        parsed.errors.extend(
            row_error(
                line,
                str(item["loc"][0]),
                item["type"],
                "Valor inválido para este campo do cadastro.",
            )
            for item in error.errors(
                include_input=False, include_context=False, include_url=False
            )
        )
        return
    for name in schema.model_fields:
        if name.endswith("_cm") and getattr(model, name) > 2_147_483_647:
            parsed.errors.append(
                row_error(
                    line,
                    name,
                    "CSV_INTEGER_RANGE",
                    "Dimensão excede a capacidade inteira do banco.",
                )
            )
    parsed.rows.append(ParsedRow(line, model))


def parse_csv(data: ImportFile, schema: type[BaseModel]) -> ParsedImport:
    """Bounded decoding and csv parsing; no persistence, eval or spreadsheet engine."""
    parsed = ParsedImport(hashlib.sha256(data.content_base64.encode()).hexdigest())
    try:
        raw = base64.b64decode(data.content_base64, validate=True)
    except (ValueError, binascii.Error):
        return _file_error(parsed, "CSV_ENCODING", "Arquivo base64 inválido.")
    parsed.sha256 = hashlib.sha256(raw).hexdigest()
    if (
        not data.file_name.lower().endswith(".csv")
        or "/" in data.file_name
        or "\\" in data.file_name
    ):
        return _file_error(
            parsed, "CSV_FILENAME", "Selecione um arquivo .csv sem caminho."
        )
    if not 0 < len(raw) <= MAX_IMPORT_BYTES:
        return _file_error(
            parsed,
            "CSV_SIZE_LIMIT",
            "Arquivo deve conter até 1 MiB e não pode ser vazio.",
        )
    if any(byte < 32 and byte not in {9, 10, 13} for byte in raw):
        return _file_error(
            parsed, "CSV_BINARY", "Arquivo contém controles ou conteúdo binário."
        )
    try:
        source = raw.decode("utf-8-sig")
        first_line = source.splitlines()[0]
        delimiter = ";" if ";" in first_line and "," not in first_line else ","
        reader = csv.reader(
            StringIO(source, newline=""), delimiter=delimiter, strict=True
        )
        header = [name.strip() for name in next(reader)]
        allowed = schema.model_fields
        required = {name for name, spec in allowed.items() if spec.is_required()}
        if (
            len(header) != len(set(header))
            or not set(header) <= set(allowed)
            or not required <= set(header)
        ):
            return _file_error(
                parsed,
                "CSV_HEADER",
                "Cabeçalho deve usar os campos aprovados, sem repetição, com todos os obrigatórios.",
            )
        while True:
            line = reader.line_num + 1
            try:
                values = next(reader)
            except StopIteration:
                break
            if not values:
                continue
            parsed.row_count += 1
            if parsed.row_count > MAX_IMPORT_ROWS:
                return _file_error(
                    parsed, "CSV_ROW_LIMIT", "Limite de 1000 registros excedido."
                )
            _parse_row(values, header, line, schema, parsed)
    except (UnicodeDecodeError, csv.Error, IndexError, StopIteration):
        return _file_error(
            parsed, "CSV_INVALID", "CSV UTF-8 inválido ou aspas incompletas."
        )
    if not parsed.row_count:
        return _file_error(
            parsed, "CSV_EMPTY", "O arquivo precisa conter ao menos um registro."
        )
    return parsed
