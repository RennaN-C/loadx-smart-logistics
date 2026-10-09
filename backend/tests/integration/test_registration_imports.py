import uuid
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from threading import Barrier

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.modules.auth.models import AuthSession
from app.modules.customers.models import Customer, CustomerAddress
from app.modules.customers.service import (
    CustomerDocumentAlreadyExistsError,
    CustomerService,
)
from app.modules.drivers.models import Driver, DriverDocument
from app.modules.drivers.service import DriverDocumentAlreadyExistsError, DriverService
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate
from app.modules.products.service import ProductCodeAlreadyExistsError, ProductService
from app.modules.registration_imports.models import RegistrationImport
from app.modules.registration_imports.schemas import ImportConfirm
from app.modules.registration_imports.service import ImportService
from app.modules.status_history.models import AuditEvent
from app.modules.status_history.service import AuditService
from app.modules.trucks.models import Truck
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService
from tests.integration.auth_helpers import issue_session_headers
from tests.unit.test_registration_import_csv import SAMPLES, csv_file

MODELS = {
    "customers": Customer,
    "products": Product,
    "trucks": Truck,
    "drivers": Driver,
}
PATH = "/api/v1/registration-imports"


def user_in_db(factory, role="LOGISTICS_MANAGER", active=True):
    with factory() as db:
        return (
            UserService(db)
            .create_user(
                UserCreate(
                    name="Importador fictício",
                    email=f"{uuid.uuid4().hex}@example.test",
                    password="Senha-Fixture-OC104-Longa!",
                    role=role,
                    active=active,
                )
            )
            .id
        )


@pytest.fixture
def importer(session_factory):
    return issue_session_headers(session_factory, user_in_db(session_factory))


def preview(client, headers, entity, rows=None):
    data = csv_file(rows or [SAMPLES[entity][1]]).model_dump()
    response = client.post(f"{PATH}/{entity}/preview", json=data, headers=headers)
    assert response.status_code == 200, response.text
    return data, response.json()


def confirm(client, headers, entity, data, view, event_id=None):
    return client.post(
        f"{PATH}/{entity}/confirm",
        json={
            **data,
            "preview_sha256": view["sha256"],
            "event_id": str(event_id or uuid.uuid4()),
        },
        headers=headers,
    )


@pytest.mark.parametrize("entity", MODELS)
def test_preview_confirm_replay_and_owned_history(
    client, session_factory, importer, entity
):
    data, view = preview(client, importer, entity)
    assert view["can_confirm"] is True and view["valid_count"] == 1
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(RegistrationImport)) == 0
        assert db.scalar(select(func.count()).select_from(MODELS[entity])) == 0
    event = uuid.uuid4()
    response = confirm(client, importer, entity, data, view, event)
    assert response.status_code == 200, response.text
    result = response.json()
    assert (
        result["status"] == "COMPLETED"
        and result["created_count"] == result["row_count"] == 1
    )
    assert result["rejected_count"] == 0 and result["errors"] == []
    assert result["records"][0]["line"] == 2
    assert confirm(client, importer, entity, data, view, event).json() == result
    assert client.get(f"{PATH}/{result['id']}", headers=importer).json() == result
    listing = client.get(PATH, params={"entity_type": entity}, headers=importer).json()
    assert listing["total"] == 1 and listing["items"][0]["id"] == result["id"]
    assert "records" not in listing["items"][0]
    with session_factory() as db:
        record = db.get(MODELS[entity], uuid.UUID(result["records"][0]["id"]))
        assert record.active is True
        assert db.scalar(select(func.count()).select_from(RegistrationImport)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.entity_id == uuid.UUID(result["id"]))
            )
            == 1
        )
        if entity == "customers":
            address = db.scalar(
                select(CustomerAddress).where(CustomerAddress.customer_id == record.id)
            )
            assert address.is_primary and address.address == record.address
        if entity == "drivers":
            cnh = db.scalar(
                select(DriverDocument).where(DriverDocument.driver_id == record.id)
            )
            assert (
                cnh.reference == record.license_number
                and cnh.expires_at == record.license_expires_at
            )
        if entity == "trucks":
            assert record.odometer_km == 100
        persisted = db.get(RegistrationImport, uuid.UUID(result["id"]))
        assert "content_base64" not in persisted.__table__.columns
        assert not {"file_name", "fingerprint", "event_id"} & result.keys()


@pytest.mark.parametrize("entity", MODELS)
def test_archived_duplicates_never_reactivate_or_overwrite(
    client, session_factory, importer, entity
):
    data, view = preview(
        client, importer, entity, [{**SAMPLES[entity][1], "active": False}]
    )
    original = confirm(client, importer, entity, data, view).json()
    again_data, again = preview(client, importer, entity)
    assert again["can_confirm"] is False
    assert any(error["code"] == "DUPLICATE_EXISTING" for error in again["errors"])
    rejected = confirm(client, importer, entity, again_data, again).json()
    assert rejected["status"] == "REJECTED" and rejected["created_count"] == 0
    with session_factory() as db:
        assert (
            db.get(MODELS[entity], uuid.UUID(original["records"][0]["id"])).active
            is False
        )
        assert db.scalar(select(func.count()).select_from(MODELS[entity])) == 1


def test_normalized_duplicate_file_errors_and_rejected_result(
    client, session_factory, importer
):
    sample = SAMPLES["products"][1]
    data, view = preview(
        client, importer, "products", [sample, {**sample, "code": "CX-A"}]
    )
    assert view["can_confirm"] is False and view["valid_count"] == 0
    assert {error["line"] for error in view["errors"]} == {2, 3}
    response = confirm(client, importer, "products", data, view)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "REJECTED" and result["rejected_count"] == 2
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Product)) == 0
        assert (
            db.scalar(
                select(AuditEvent.event_type).where(
                    AuditEvent.entity_id == uuid.UUID(result["id"])
                )
            )
            == "IMPORT_REJECTED"
        )


def test_invalid_line_has_field_error_and_no_partial_import(
    client, session_factory, importer
):
    sample = SAMPLES["products"][1]
    data, view = preview(
        client,
        importer,
        "products",
        [sample, {**sample, "code": "CX-B", "weight_kg": "0"}],
    )
    assert view["can_confirm"] is False and view["valid_count"] == 1
    assert any(
        error["line"] == 3 and error["field"] == "weight_kg" for error in view["errors"]
    )
    assert (
        confirm(client, importer, "products", data, view).json()["created_count"] == 0
    )
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Product)) == 0


def test_file_hash_change_event_conflict_and_fresh_duplicate_check(
    client, session_factory, importer
):
    data, view = preview(client, importer, "products")
    mismatch = confirm(
        client,
        importer,
        "products",
        {
            **data,
            "content_base64": csv_file(
                [{**SAMPLES["products"][1], "code": "OTHER"}]
            ).content_base64,
        },
        view,
    )
    assert (
        mismatch.status_code == 409
        and mismatch.json()["code"] == "IMPORT_PREVIEW_MISMATCH"
    )
    event = uuid.uuid4()
    original = confirm(client, importer, "products", data, view, event).json()
    changed_data, changed_view = preview(client, importer, "trucks")
    assert (
        confirm(
            client, importer, "trucks", changed_data, changed_view, event
        ).status_code
        == 409
    )
    fresh = confirm(client, importer, "products", data, view).json()
    assert (
        fresh["status"] == "REJECTED"
        and fresh["errors"][0]["code"] == "DUPLICATE_EXISTING"
    )
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Product)) == 1
        assert db.get(RegistrationImport, uuid.UUID(original["id"])).created_count == 1


@pytest.mark.parametrize("role", ["CHECKER", "DRIVER"])
def test_every_operation_enforces_rbac(client, session_factory, role):
    headers = issue_session_headers(session_factory, user_in_db(session_factory, role))
    for method, path, data in [
        ("get", PATH, None),
        ("get", f"{PATH}/{uuid.uuid4()}", None),
        ("get", f"{PATH}/products/template", None),
        (
            "post",
            f"{PATH}/products/preview",
            csv_file([SAMPLES["products"][1]]).model_dump(),
        ),
        (
            "post",
            f"{PATH}/products/confirm",
            {
                **csv_file([SAMPLES["products"][1]]).model_dump(),
                "preview_sha256": "a" * 64,
                "event_id": str(uuid.uuid4()),
            },
        ),
    ]:
        kwargs = {"headers": headers}
        if data is not None:
            kwargs["json"] = data
        assert client.request(method, path, **kwargs).status_code == 403


def test_admin_and_template_unknown_import_and_no_orders(client, session_factory):
    headers = issue_session_headers(
        session_factory, user_in_db(session_factory, "ADMIN")
    )
    for entity, (schema, _) in SAMPLES.items():
        response = client.get(f"{PATH}/{entity}/template", headers=headers)
        assert response.status_code == 200
        assert response.content.decode("utf-8-sig").strip() == ",".join(
            schema.model_fields
        )
        assert response.headers["content-type"].startswith("text/csv")
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["cache-control"] == "no-store"
    assert client.get(f"{PATH}/{uuid.uuid4()}", headers=headers).status_code == 404
    assert (
        client.post(
            f"{PATH}/orders/preview",
            json=csv_file([SAMPLES["products"][1]]).model_dump(),
            headers=headers,
        ).status_code
        == 422
    )


def test_anonymous_csrf_inactive_and_request_limits(client, session_factory, importer):
    data = csv_file([SAMPLES["products"][1]]).model_dump()
    path = f"{PATH}/products/preview"
    assert client.post(path, json=data).status_code == 401
    headers = dict(importer)
    headers.pop("X-CSRF-Token")
    assert client.post(path, json=data, headers=headers).status_code == 403
    inactive = issue_session_headers(
        session_factory, user_in_db(session_factory, active=False)
    )
    assert client.post(path, json=data, headers=inactive).status_code == 403
    assert (
        client.post(
            path, json={**data, "content_base64": "x" * 1398105}, headers=importer
        ).status_code
        == 422
    )
    assert (
        client.post(
            path, json={**data, "actor_id": str(uuid.uuid4())}, headers=importer
        ).status_code
        == 422
    )
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(RegistrationImport)) == 0


@pytest.mark.parametrize(
    "entity,method,error_type",
    [
        ("products", "stage_create_product", ProductCodeAlreadyExistsError),
        ("customers", "stage_create_customer", CustomerDocumentAlreadyExistsError),
        ("drivers", "stage_create_driver", DriverDocumentAlreadyExistsError),
    ],
)
def test_savepoint_rolls_back_every_domain_side_effect(
    client, session_factory, importer, monkeypatch, entity, method, error_type
):
    sample = SAMPLES[entity][1]
    second = (
        {**sample, "code": "CX-B"}
        if entity == "products"
        else {
            **sample,
            "document": "11144477735",
            **({"license_number": "98765432109"} if entity == "drivers" else {}),
        }
    )
    data, view = preview(client, importer, entity, [sample, second])
    assert view["can_confirm"] is True, view["errors"]
    cls = {
        "products": ProductService,
        "customers": CustomerService,
        "drivers": DriverService,
    }[entity]
    original = getattr(cls, method)
    calls = 0

    def raced(service, payload, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise error_type
        return original(service, payload, **kwargs)

    monkeypatch.setattr(cls, method, raced)
    result = confirm(client, importer, entity, data, view).json()
    assert result["status"] == "REJECTED" and result["records"] == []
    assert result["errors"][0]["code"] == "DUPLICATE_CONCURRENT"
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(MODELS[entity])) == 0
        assert db.scalar(select(func.count()).select_from(CustomerAddress)) == 0
        assert db.scalar(select(func.count()).select_from(DriverDocument)) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.event_type.in_(
                        ("DRIVER_DOCUMENT_CREATED", "CUSTOMER_ADDRESS_CREATED")
                    )
                )
            )
            == 0
        )


@pytest.mark.parametrize("failure", ["domain", "audit"])
def test_unexpected_failure_rolls_back_attempt_and_all_rows(
    client, session_factory, importer, monkeypatch, failure
):
    data, view = preview(client, importer, "products")

    def fail(*args, **kwargs):
        raise RuntimeError("Fixture failure")

    monkeypatch.setattr(
        ProductService if failure == "domain" else AuditService,
        "stage_create_product" if failure == "domain" else "stage_administrative_event",
        fail,
    )
    assert confirm(client, importer, "products", data, view).status_code == 500
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(RegistrationImport)) == 0
        assert db.scalar(select(func.count()).select_from(Product)) == 0


def test_large_file_within_limit_is_atomic(client, session_factory, importer):
    sample = SAMPLES["products"][1]
    data, view = preview(
        client,
        importer,
        "products",
        [{**sample, "code": f"BULK-{i}"} for i in range(1000)],
    )
    assert view["can_confirm"] is True and view["valid_count"] == 1000
    result = confirm(client, importer, "products", data, view).json()
    assert result["created_count"] == len(result["records"]) == 1000
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Product)) == 1000


@pytest.mark.parametrize(
    "mutation",
    [
        {"entity_type": "orders"},
        {"row_count": 1001},
        {"sha256": "not hash"},
        {"created_count": 1},
        {"status": "COMPLETED", "created_count": 1, "row_count": 1},
        {"status": "REJECTED", "rejected_count": 1, "row_count": 1},
    ],
)
def test_database_rejects_inconsistent_results(session_factory, mutation):
    actor = user_in_db(session_factory)
    with session_factory() as db:
        row = RegistrationImport(
            id=uuid.uuid4(),
            entity_type="products",
            recorded_by=actor,
            event_id=uuid.uuid4(),
            sha256="a" * 64,
            fingerprint="b" * 64,
            row_count=0,
        )
        for field, value in mutation.items():
            setattr(row, field, value)
        db.add(row)
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_downgrade_preserves_even_rejected_results(client, session_factory, importer):
    sample = SAMPLES["products"][1]
    data, view = preview(client, importer, "products", [{**sample, "weight_kg": 0}])
    assert (
        confirm(client, importer, "products", data, view).json()["status"] == "REJECTED"
    )
    migration = import_module("migrations.versions.20261009_0022_registration_imports")
    with (
        session_factory() as db,
        pytest.raises(RuntimeError, match="import results and audit"),
    ):
        migration.ensure_safe_downgrade(db.connection())


@pytest.mark.parametrize("same_event", [True, False])
def test_concurrent_confirmation_uses_real_commits(postgres_engine, same_event):
    factory = sessionmaker(bind=postgres_engine, autoflush=False)
    actor_id = user_in_db(factory)
    sample = {**SAMPLES["products"][1], "code": f"PAR-{uuid.uuid4().hex}"}
    file = csv_file([sample])
    from app.modules.registration_imports.csv_content import parse_csv

    sha = parse_csv(file, ProductCreate).sha256
    event = uuid.uuid4()
    barrier = Barrier(2)

    def worker(index):
        with factory() as db:
            actor = db.get(User, actor_id)
            data = ImportConfirm(
                **file.model_dump(),
                preview_sha256=sha,
                event_id=event if same_event else uuid.uuid4(),
            )
            barrier.wait(timeout=10)
            return ImportService(db).confirm("products", data, current_user=actor)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, range(2)))
        if same_event:
            assert results[0].id == results[1].id
        else:
            assert {result.status for result in results} == {"COMPLETED", "REJECTED"}
        with factory() as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(Product)
                    .where(Product.code == sample["code"].upper())
                )
                == 1
            )
            assert db.scalar(
                select(func.count())
                .select_from(RegistrationImport)
                .where(RegistrationImport.recorded_by == actor_id)
            ) == (1 if same_event else 2)
    finally:
        with factory() as db:
            db.execute(
                delete(RegistrationImport).where(
                    RegistrationImport.recorded_by == actor_id
                )
            )
            db.execute(delete(AuditEvent).where(AuditEvent.actor_id == actor_id))
            db.execute(delete(Product).where(Product.code == sample["code"].upper()))
            db.execute(delete(AuthSession).where(AuthSession.user_id == actor_id))
            db.execute(delete(User).where(User.id == actor_id))
            db.commit()


def test_bad_header_confirmation_only_records_rejected_audit(
    client, session_factory, importer
):
    import base64

    data = {
        "file_name": "fixture.csv",
        "content_base64": base64.b64encode(b"unapproved\nmalicious\n").decode(),
    }
    view = client.post(f"{PATH}/products/preview", json=data, headers=importer).json()
    assert view["errors"][0]["code"] == "CSV_HEADER"
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(RegistrationImport)) == 0
    rejected = confirm(client, importer, "products", data, view).json()
    assert rejected["status"] == "REJECTED"
    assert rejected["created_count"] == 0
    assert rejected["records"] == []
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Product)) == 0


def test_import_openapi_contract_is_additive_and_authorized():
    from app.main import app

    schema = app.openapi()
    assert "ImportConfirm" in schema["components"]["schemas"]
    assert (
        schema["components"]["schemas"]["ImportConfirm"]["additionalProperties"]
        is False
    )
    properties = schema["components"]["schemas"]["ImportConfirm"]["properties"]
    assert set(properties) == {
        "file_name",
        "content_base64",
        "preview_sha256",
        "event_id",
    }
    operation = schema["paths"][f"{PATH}/{{entity_type}}/confirm"]["post"]
    assert operation["security"]
    assert {"401", "403", "404", "409", "422", "500"} <= operation["responses"].keys()
    assert "/api/v1/deliveries/{delivery_id}/evidences" in schema["paths"]
