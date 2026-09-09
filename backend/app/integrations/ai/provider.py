"""Porta e fake controlado para explicações de planos por IA."""

from dataclasses import dataclass
from math import isfinite
from typing import Annotated, Literal, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    StringConstraints,
    model_validator,
)

from app.core.json_decimal import JsonDecimal

RotationCode = Literal["XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"]
RejectionReason = Literal[
    "TRUCK_DIMENSIONS_EXCEEDED",
    "TRUCK_WEIGHT_EXCEEDED",
    "NON_STACKABLE_SUPPORT",
    "FRAGILE_SUPPORT_WEIGHT_EXCEEDED",
    "INSUFFICIENT_SUPPORT",
    "COLLISION",
    "NO_VALID_POSITION",
]
NonEmptyText = Annotated[
    StrictStr,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class _FrozenProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class AITruckContext(_FrozenProviderModel):
    """Somente a capacidade física do caminhão, sem identificadores."""

    internal_width_cm: int = Field(gt=0)
    internal_height_cm: int = Field(gt=0)
    internal_length_cm: int = Field(gt=0)
    max_weight_kg: JsonDecimal = Field(gt=0, max_digits=10, decimal_places=2)


class AIPlacedVolumeContext(_FrozenProviderModel):
    """Dados físicos necessários para descrever um volume posicionado."""

    original_width_cm: int = Field(gt=0)
    original_height_cm: int = Field(gt=0)
    original_length_cm: int = Field(gt=0)
    weight_kg: JsonDecimal = Field(gt=0, max_digits=10, decimal_places=3)
    fragile: bool
    stackable: bool
    rotation_allowed: bool
    delivery_sequence: int = Field(gt=0)
    x_cm: int = Field(ge=0)
    y_cm: int = Field(ge=0)
    z_cm: int = Field(ge=0)
    width_cm: int = Field(gt=0)
    height_cm: int = Field(gt=0)
    length_cm: int = Field(gt=0)
    rotation_code: RotationCode
    loading_sequence: int = Field(gt=0)


class AIRejectedVolumeContext(_FrozenProviderModel):
    """Dados físicos e motivo de um volume não posicionado."""

    original_width_cm: int = Field(gt=0)
    original_height_cm: int = Field(gt=0)
    original_length_cm: int = Field(gt=0)
    weight_kg: JsonDecimal = Field(gt=0, max_digits=10, decimal_places=3)
    fragile: bool
    stackable: bool
    rotation_allowed: bool
    delivery_sequence: int = Field(gt=0)
    rejection_reason: RejectionReason


class AIExplanationContext(_FrozenProviderModel):
    """Payload técnico e minimizado entregue ao provider de IA."""

    truck: AITruckContext
    internal_volume_cm3: int = Field(gt=0)
    used_volume_cm3: int = Field(ge=0)
    occupancy_percent: JsonDecimal = Field(ge=0, le=100, decimal_places=2)
    total_weight_kg: JsonDecimal = Field(
        ge=0,
        max_digits=11,
        decimal_places=3,
    )
    loaded_count: int = Field(ge=0)
    unloaded_count: int = Field(ge=0)
    algorithm_version: NonEmptyText = Field(max_length=64)
    placed_volumes: tuple[AIPlacedVolumeContext, ...]
    rejected_volumes: tuple[AIRejectedVolumeContext, ...]

    @model_validator(mode="after")
    def validate_aggregate_shape(self) -> "AIExplanationContext":
        expected_internal_volume = (
            self.truck.internal_width_cm
            * self.truck.internal_height_cm
            * self.truck.internal_length_cm
        )
        if self.internal_volume_cm3 != expected_internal_volume:
            raise ValueError("internal volume must match truck dimensions")
        if self.used_volume_cm3 > self.internal_volume_cm3:
            raise ValueError("used volume must not exceed internal volume")
        if self.total_weight_kg > self.truck.max_weight_kg:
            raise ValueError("total weight must not exceed truck capacity")
        if self.loaded_count != len(self.placed_volumes):
            raise ValueError("loaded_count must match placed_volumes")
        if self.unloaded_count != len(self.rejected_volumes):
            raise ValueError("unloaded_count must match rejected_volumes")
        if self.loaded_count + self.unloaded_count <= 0:
            raise ValueError("at least one volume is required")
        return self


MAX_EXPLANATION_LENGTH = 8_000
"""Teto do texto devolvido pelo provider.

Vazio já era recusado, mas não havia limite superior: um adapter defeituoso ou
um modelo em laço podia devolver megabytes, e a aplicação aceitaria. O texto
atravessa a API e chega ao navegador, então o teto protege memória, banda e
renderização. Passar do limite é saída inválida como qualquer outra, e cai no
FALLBACK — o plano não é tocado e nada é persistido.
"""


class AIProviderOutput(_FrozenProviderModel):
    """Saída mínima validada antes de ser aceita pela aplicação."""

    explanation: NonEmptyText = Field(max_length=MAX_EXPLANATION_LENGTH)


def validate_ai_provider_output(value: object) -> AIProviderOutput:
    """Valida dados não confiáveis devolvidos por qualquer adapter."""

    return AIProviderOutput.model_validate(value)


class AIProviderError(Exception):
    """Falha operacional normalizada por um adapter de IA."""


class AIProviderTimeoutError(AIProviderError):
    """O provider excedeu o timeout configurado."""


class AIProviderUnavailableError(AIProviderError):
    """O provider não estava disponível para responder."""


class AIProvider(Protocol):
    """Porta síncrona para explicar dados técnicos de um plano validado."""

    def explain_load_plan(
        self,
        context: AIExplanationContext,
        *,
        timeout_seconds: float,
    ) -> object:
        """Retorna dados não confiáveis que o service deve validar."""


@dataclass(frozen=True, slots=True)
class AIProviderCall:
    context: AIExplanationContext
    timeout_seconds: float


_DEFAULT_FAKE_RESPONSE = object()


class FakeAIProvider:
    """Fake configurável e observável, sem SDK ou acesso externo."""

    def __init__(
        self,
        *,
        response: object = _DEFAULT_FAKE_RESPONSE,
        error: Exception | None = None,
    ) -> None:
        self.response = (
            AIProviderOutput(explanation="Explicação simulada do plano de carga.")
            if response is _DEFAULT_FAKE_RESPONSE
            else response
        )
        self.error = error
        self.calls: list[AIProviderCall] = []

    def explain_load_plan(
        self,
        context: AIExplanationContext,
        *,
        timeout_seconds: float,
    ) -> object:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a positive finite number")

        self.calls.append(
            AIProviderCall(
                context=context,
                timeout_seconds=float(timeout_seconds),
            )
        )
        if self.error is not None:
            raise self.error
        return self.response


def get_ai_provider() -> AIProvider:
    """Fornece o fake local até o Dev4 integrar um adapter concreto."""

    return FakeAIProvider()
