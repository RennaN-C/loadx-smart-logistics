import re
from math import isfinite
from typing import Annotated, Literal, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    StrictStr,
    StringConstraints,
    ValidationError,
    field_validator,
)


class ViaCEPProviderError(Exception):
    """Falha normalizada, sem detalhes do serviço externo."""

    code = "VIACEP_ERROR"
    message = "Não foi possível consultar o CEP. Preencha o endereço manualmente."

    def __init__(self) -> None:
        super().__init__(self.message)


class ViaCEPInvalidCEPError(ViaCEPProviderError):
    code = "VIACEP_INVALID_CEP"
    message = "Informe um CEP com 8 dígitos."


class ViaCEPNotFoundError(ViaCEPProviderError):
    code = "VIACEP_NOT_FOUND"
    message = "CEP não encontrado. Preencha o endereço manualmente."


class ViaCEPTimeoutError(ViaCEPProviderError):
    code = "VIACEP_TIMEOUT"
    message = (
        "A consulta de CEP excedeu o tempo limite. Preencha o endereço manualmente."
    )


class ViaCEPUnavailableError(ViaCEPProviderError):
    code = "VIACEP_UNAVAILABLE"
    message = "A consulta de CEP está indisponível. Preencha o endereço manualmente."


class ViaCEPInvalidResponseError(ViaCEPProviderError):
    code = "VIACEP_INVALID_RESPONSE"
    message = "Não foi possível validar o endereço do CEP. Preencha-o manualmente."


def normalize_cep(value: object) -> str:
    """Aceita oito dígitos ASCII, com hífen opcional e espaços nas extremidades."""
    if not isinstance(value, str):
        raise ViaCEPInvalidCEPError()
    value = value.strip()
    if re.fullmatch(r"[0-9]{5}-?[0-9]{3}", value) is None:
        raise ViaCEPInvalidCEPError()
    return value.replace("-", "")


def validate_timeout_seconds(value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value <= 0
    ):
        raise ValueError("timeout_seconds must be a positive finite number")
    return float(value)


AddressText = Annotated[StrictStr, StringConstraints(strip_whitespace=True)]
CityText = Annotated[AddressText, StringConstraints(min_length=1)]
StateCode = Literal[
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
]


class ViaCEPAddress(BaseModel):
    """Dados transitórios para preenchimento, sem alterar o modelo de Customer."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    cep: StrictStr
    street: AddressText | None = None
    neighborhood: AddressText | None = None
    complement: AddressText | None = None
    city: CityText
    state: StateCode

    @field_validator("cep")
    @classmethod
    def normalize_address_cep(cls, value: str) -> str:
        return normalize_cep(value)

    @field_validator("street", "neighborhood", "complement")
    @classmethod
    def normalize_empty_address_field(cls, value: str | None) -> str | None:
        return value or None


def validate_viacep_output(value: object, *, requested_cep: str) -> ViaCEPAddress:
    """Valida o contrato interno e a correspondência com o CEP solicitado."""
    cep = normalize_cep(requested_cep)
    try:
        address = ViaCEPAddress.model_validate(value)
    except (ValidationError, ViaCEPInvalidCEPError):
        raise ViaCEPInvalidResponseError() from None
    if address.cep != cep:
        raise ViaCEPInvalidResponseError()
    return address


class ViaCEPProvider(Protocol):
    def lookup_address(self, cep: str, *, timeout_seconds: float) -> ViaCEPAddress:
        """Valida o CEP antes de consultar e retorna somente um endereço validado."""
        ...
