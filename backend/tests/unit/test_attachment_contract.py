import uuid

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.core.exceptions import ApiError
from app.main import app
from app.modules.attachments.router import get_attachment_storage
from app.modules.attachments.schemas import AttachmentCreate


@pytest.mark.parametrize("environment", ["local", "production"])
def test_attachment_storage_requires_opt_in_and_denies_production(
    monkeypatch, environment
):
    monkeypatch.setattr(settings, "app_env", environment)
    monkeypatch.setattr(settings, "evidence_storage_dir", None)
    with pytest.raises(ApiError) as caught:
        get_attachment_storage()
    assert caught.value.code == "ATTACHMENT_STORAGE_UNAVAILABLE"
    assert caught.value.status_code == 503


def test_configured_local_adapter_is_shared_but_production_stays_disabled(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "evidence_storage_dir", tmp_path / "private")
    assert get_attachment_storage().root == tmp_path / "private"
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(ApiError):
        get_attachment_storage()


def test_openapi_is_additive_and_preserves_document_evidence_contracts():
    contract = app.openapi()
    schemas = contract["components"]["schemas"]
    assert {
        "DocumentCreate",
        "DocumentRead",
        "DriverDocumentCreate",
        "DeliveryEvidenceCreate",
        "AttachmentCreate",
        "AttachmentRead",
    } <= schemas.keys()
    assert schemas["AttachmentCreate"]["additionalProperties"] is False
    assert set(schemas["AttachmentCreate"]["properties"]) == {
        "event_id",
        "content_base64",
    }
    route = contract["paths"]["/api/v1/attachments/{resource_type}/{resource_id}"]
    assert route["get"]["security"] and route["post"]["security"]
    assert {"401", "403", "404", "409", "422", "503"} <= route["post"][
        "responses"
    ].keys()
    assert "/api/v1/deliveries/{delivery_id}/evidences" in contract["paths"]


def test_schema_does_not_accept_actor_or_storage_reference():
    with pytest.raises(ValidationError):
        AttachmentCreate(
            event_id=uuid.uuid4(), content_base64="a", url="https://example.invalid"
        )
