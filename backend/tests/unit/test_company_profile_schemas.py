import pytest
from pydantic import ValidationError

from app.modules.company_profile.schemas import CompanyProfileInput

BASE = {"legal_name": " Empresa Ltda ", "display_name": " Empresa "}


def test_names_are_trimmed_and_optional_fields_default_to_null():
    profile = CompanyProfileInput(**BASE)
    assert profile.legal_name == "Empresa Ltda"
    assert profile.display_name == "Empresa"
    assert all(
        getattr(profile, field) is None
        for field in ["cnpj", "phone", "email", "logo_reference"]
    )


@pytest.mark.parametrize("field", ["cnpj", "phone", "email", "logo_reference"])
def test_optional_whitespace_is_null(field):
    assert getattr(CompanyProfileInput(**BASE, **{field: "  "}), field) is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("cnpj", "00.000.000/0000-00"),
        ("phone", "00000000000"),
        ("email", "not-an-email"),
        ("logo_reference", "https://[broken/logo"),
        ("logo_reference", "https://example.test:invalid/logo"),
        ("logo_reference", "https://@example.test/logo"),
    ],
)
def test_invalid_values_are_rejected(field, value):
    with pytest.raises(ValidationError):
        CompanyProfileInput(**BASE, **{field: value})


def test_logotype_is_reference_without_upload_or_identity_contract():
    profile = CompanyProfileInput(
        **BASE, logo_reference="https://example.test/assets/logo.svg"
    )
    assert profile.logo_reference == "https://example.test/assets/logo.svg"
    assert "tenant_id" not in CompanyProfileInput.model_fields
    assert "file" not in CompanyProfileInput.model_fields
    with pytest.raises(ValidationError):
        CompanyProfileInput(**BASE, secret_key="secret")
