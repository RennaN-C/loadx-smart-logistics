from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.integrations.ai import (
    AIExplanationContext,
    AIPlacedVolumeContext,
    AIProviderOutput,
    AIProviderTimeoutError,
    AIRejectedVolumeContext,
    AITruckContext,
    FakeAIProvider,
    get_ai_provider,
    validate_ai_provider_output,
)


def make_context() -> AIExplanationContext:
    return AIExplanationContext(
        truck=AITruckContext(
            internal_width_cm=100,
            internal_height_cm=100,
            internal_length_cm=100,
            max_weight_kg=Decimal("8000.00"),
        ),
        internal_volume_cm3=1_000_000,
        used_volume_cm3=6_000,
        occupancy_percent=Decimal("0.60"),
        total_weight_kg=Decimal("12.500"),
        loaded_count=1,
        unloaded_count=1,
        algorithm_version="heuristic-v1",
        placed_volumes=(
            AIPlacedVolumeContext(
                original_width_cm=10,
                original_height_cm=20,
                original_length_cm=30,
                weight_kg=Decimal("12.500"),
                fragile=False,
                stackable=True,
                rotation_allowed=True,
                delivery_sequence=2,
                x_cm=1,
                y_cm=0,
                z_cm=2,
                width_cm=10,
                height_cm=20,
                length_cm=30,
                rotation_code="XYZ",
                loading_sequence=1,
            ),
        ),
        rejected_volumes=(
            AIRejectedVolumeContext(
                original_width_cm=50,
                original_height_cm=60,
                original_length_cm=70,
                weight_kg=Decimal("20.000"),
                fragile=True,
                stackable=False,
                rotation_allowed=False,
                delivery_sequence=1,
                rejection_reason="NO_VALID_POSITION",
            ),
        ),
    )


def test_context_serializes_only_whitelisted_technical_fields() -> None:
    serialized = make_context().model_dump(mode="json")

    assert set(serialized) == {
        "truck",
        "internal_volume_cm3",
        "used_volume_cm3",
        "occupancy_percent",
        "total_weight_kg",
        "loaded_count",
        "unloaded_count",
        "algorithm_version",
        "placed_volumes",
        "rejected_volumes",
    }
    assert set(serialized["truck"]) == {
        "internal_width_cm",
        "internal_height_cm",
        "internal_length_cm",
        "max_weight_kg",
    }
    assert isinstance(serialized["occupancy_percent"], float)
    assert isinstance(serialized["total_weight_kg"], float)
    serialized_text = str(serialized).lower()
    for forbidden_field in (
        "customer",
        "cpf",
        "cnpj",
        "phone",
        "address",
        "driver",
        "plate",
        "product_name",
        "order_id",
    ):
        assert forbidden_field not in serialized_text


def test_context_rejects_inconsistent_aggregate_counts() -> None:
    data = make_context().model_dump()
    data["loaded_count"] = 0

    with pytest.raises(ValidationError, match="loaded_count"):
        AIExplanationContext.model_validate(data)


def test_validates_and_normalizes_provider_output() -> None:
    output = validate_ai_provider_output({"explanation": "  Explicação válida.  "})

    assert output == AIProviderOutput(explanation="Explicação válida.")


@pytest.mark.parametrize(
    "invalid_output",
    [
        None,
        {},
        {"explanation": ""},
        {"explanation": "   "},
        {"explanation": 123},
        {"explanation": "Válida", "source": "AI"},
    ],
)
def test_rejects_invalid_provider_output(invalid_output: object) -> None:
    with pytest.raises(ValidationError):
        validate_ai_provider_output(invalid_output)


def test_fake_provider_returns_configured_response_and_captures_call() -> None:
    context = make_context()
    response = {"explanation": "Resposta controlada."}
    provider = FakeAIProvider(response=response)

    returned = provider.explain_load_plan(context, timeout_seconds=2.5)

    assert returned is response
    assert len(provider.calls) == 1
    assert provider.calls[0].context is context
    assert provider.calls[0].timeout_seconds == 2.5


def test_fake_provider_raises_configured_error_after_capturing_call() -> None:
    context = make_context()
    error = AIProviderTimeoutError("timeout controlado")
    provider = FakeAIProvider(error=error)

    with pytest.raises(AIProviderTimeoutError) as error_info:
        provider.explain_load_plan(context, timeout_seconds=5.0)

    assert error_info.value is error
    assert provider.calls[0].context is context
    assert provider.calls[0].timeout_seconds == 5.0


@pytest.mark.parametrize("timeout_seconds", [0.0, -1.0, float("inf"), True])
def test_fake_provider_rejects_invalid_timeout(timeout_seconds: float) -> None:
    provider = FakeAIProvider()

    with pytest.raises(ValueError, match="positive finite"):
        provider.explain_load_plan(
            make_context(),
            timeout_seconds=timeout_seconds,
        )

    assert provider.calls == []


def test_provider_dependency_returns_independent_fakes() -> None:
    first = get_ai_provider()
    second = get_ai_provider()

    assert isinstance(first, FakeAIProvider)
    assert isinstance(second, FakeAIProvider)
    assert first is not second
