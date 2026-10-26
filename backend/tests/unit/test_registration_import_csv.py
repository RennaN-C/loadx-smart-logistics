import base64
import csv
from io import StringIO

import pytest

from app.modules.customers.schemas import CustomerCreate
from app.modules.drivers.schemas import DriverCreate
from app.modules.products.schemas import ProductCreate
from app.modules.registration_imports.csv_content import parse_csv
from app.modules.registration_imports.schemas import ImportFile
from app.modules.trucks.schemas import TruckCreate

SAMPLES = {
    "customers": (
        CustomerCreate,
        {
            "name": "Cliente fictício",
            "document": "00000000000191",
            "address": "Rua fictícia",
            "city": "Campinas",
            "state": "sp",
        },
    ),
    "products": (
        ProductCreate,
        {
            "code": "cx-a",
            "name": "Caixa fictícia",
            "width_cm": 20,
            "height_cm": 10,
            "length_cm": 30,
            "weight_kg": "1.125",
        },
    ),
    "trucks": (
        TruckCreate,
        {
            "plate": "abc1d23",
            "model": "Fictício",
            "internal_width_cm": 100,
            "internal_height_cm": 100,
            "internal_length_cm": 100,
            "max_weight_kg": "200.25",
            "odometer_km": 100,
        },
    ),
    "drivers": (
        DriverCreate,
        {
            "name": "Motorista fictício",
            "document": "12345678909",
            "phone": "11900000000",
            "license_number": "12345678900",
            "license_category": "d",
            "license_expires_at": "2099-01-01T00:00:00Z",
        },
    ),
}


def csv_file(
    rows: list[dict], *, delimiter=",", bom=False, file_name="fixture.csv"
) -> ImportFile:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter=delimiter)
    writer.writeheader()
    writer.writerows(rows)
    raw = output.getvalue().encode("utf-8-sig" if bom else "utf-8")
    return ImportFile(
        file_name=file_name, content_base64=base64.b64encode(raw).decode()
    )


@pytest.mark.parametrize("entity", SAMPLES)
@pytest.mark.parametrize("delimiter,bom", [(",", False), (";", True)])
def test_parses_the_same_manual_schemas(entity, delimiter, bom):
    schema, values = SAMPLES[entity]
    parsed = parse_csv(csv_file([values], delimiter=delimiter, bom=bom), schema)
    assert parsed.errors == []
    assert parsed.row_count == 1 and parsed.rows[0].line == 2
    normalized = parsed.rows[0].data.model_dump(mode="json")
    assert normalized["active"] is True
    if entity == "products":
        assert normalized["code"] == "CX-A" and normalized["weight_kg"] == 1.125
    if entity == "drivers":
        assert normalized["license_category"] == "D"
    if entity == "customers":
        assert normalized["state"] == "SP"


@pytest.mark.parametrize(
    "source,code",
    [
        ("name,unknown\nFake,x\n", "CSV_HEADER"),
        ("code,code,name\nA,A,Fake\n", "CSV_HEADER"),
        ("code,name\nA,Fake\n", "CSV_HEADER"),
        ("", "CSV_ENCODING"),
        ("code,name,width_cm,height_cm,length_cm,weight_kg\n", "CSV_EMPTY"),
        (
            "code,name,width_cm,height_cm,length_cm,weight_kg\nA,Fake,1,2\n",
            "CSV_COLUMN_COUNT",
        ),
        (
            'code,name,width_cm,height_cm,length_cm,weight_kg\nA,"unterminated',
            "CSV_INVALID",
        ),
        (
            "code,name,width_cm,height_cm,length_cm,weight_kg\nA,Fake\x00,1,2,3,4\n",
            "CSV_BINARY",
        ),
    ],
)
def test_rejects_bad_csv(source, code):
    data = ImportFile(
        file_name="fixture.csv",
        content_base64=base64.b64encode(source.encode()).decode() or "====",
    )
    parsed = parse_csv(data, ProductCreate)
    assert (
        code in {error.code for error in parsed.errors}
        or not source
        and parsed.errors[0].code == "CSV_ENCODING"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("width_cm", "-1"),
        ("weight_kg", "NaN"),
        ("weight_kg", "1,25"),
        ("name", "=WEBSERVICE(1)"),
        ("name", "@SUM(1)"),
        ("name", "x" * 4097),
        ("active", "yes"),
    ],
)
def test_errors_identify_line_and_field_without_original_value(field, value):
    schema, sample = SAMPLES["products"]
    parsed = parse_csv(csv_file([{**sample, field: value}]), schema)
    assert any(error.line == 2 and error.field == field for error in parsed.errors)
    assert all(value not in error.message for error in parsed.errors)


def test_optional_defaults_booleans_and_physical_multiline_positions():
    schema, sample = SAMPLES["products"]
    parsed = parse_csv(
        csv_file(
            [
                {
                    **sample,
                    "description": "linha1\nlinha2",
                    "active": "false",
                    "fragile": "1",
                },
                {
                    **sample,
                    "code": "cx-b",
                    "description": "",
                    "active": "",
                    "fragile": "0",
                },
            ]
        ),
        schema,
    )
    assert not parsed.errors
    assert [row.line for row in parsed.rows] == [2, 4]
    assert parsed.rows[0].data.active is False and parsed.rows[0].data.fragile is True
    assert (
        parsed.rows[1].data.active is True and parsed.rows[1].data.description is None
    )


def test_limit_allows_1000_but_rejects_1001():
    schema, sample = SAMPLES["products"]
    rows = [{**sample, "code": f"FIX-{i}"} for i in range(1001)]
    assert parse_csv(csv_file(rows[:1000]), schema).row_count == 1000
    parsed = parse_csv(csv_file(rows), schema)
    assert parsed.rows == [] and parsed.errors[0].code == "CSV_ROW_LIMIT"


@pytest.mark.parametrize(
    "file_name", ["fixture.xlsx", "../fixture.csv", "folder\\fixture.csv"]
)
def test_only_csv_without_paths(file_name):
    schema, sample = SAMPLES["products"]
    assert (
        parse_csv(csv_file([sample], file_name=file_name), schema).errors[0].code
        == "CSV_FILENAME"
    )


def test_invalid_utf8_and_decoded_size_limit():
    for source, code in [
        (b"\xff", "CSV_INVALID"),
        (b"x" * (1048576 + 1), "CSV_SIZE_LIMIT"),
    ]:
        parsed = parse_csv(
            ImportFile(
                file_name="fixture.csv",
                content_base64=base64.b64encode(source).decode(),
            ),
            ProductCreate,
        )
        assert parsed.errors[0].code == code


def test_odometer_requires_integer_and_dimensions_fit_postgresql():
    schema, sample = SAMPLES["trucks"]
    parsed = parse_csv(csv_file([{**sample, "odometer_km": "1.5"}]), schema)
    assert any(error.field == "odometer_km" for error in parsed.errors)
    schema, sample = SAMPLES["products"]
    parsed = parse_csv(csv_file([{**sample, "width_cm": 2147483648}]), schema)
    assert any(
        error.field == "width_cm" and error.code == "CSV_INTEGER_RANGE"
        for error in parsed.errors
    )
