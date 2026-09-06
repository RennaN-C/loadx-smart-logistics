import uuid
from collections.abc import Iterator
from typing import Any
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.integrations.ai import (
    MAX_EXPLANATION_LENGTH,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    FakeAIProvider,
)
from app.modules.load_planning.explanation_service import (
    LoadPlanExplanationForbiddenError,
    LoadPlanExplanationInvalidPlanError,
    LoadPlanExplanationNotFoundError,
    LoadPlanExplanationService,
)
from app.modules.load_planning.models import LoadPlan
from tests.unit.load_planning.test_explanation import make_item, make_plan


def make_partial_plan() -> LoadPlan:
    return make_plan(
        items=[
            make_item(suffix=1, loading_sequence=1),
            make_item(
                suffix=2,
                placed=False,
                rejection_reason="NO_VALID_POSITION",
            ),
        ]
    )


def make_service(
    load_plan: LoadPlan | None,
    provider: FakeAIProvider,
    *,
    timeout_seconds: float = 2.75,
) -> tuple[LoadPlanExplanationService, Mock]:
    db = Mock(spec=Session)
    db.scalar.return_value = load_plan
    return (
        LoadPlanExplanationService(
            db,
            provider,
            timeout_seconds=timeout_seconds,
        ),
        db,
    )


def assert_no_writes(db: Mock) -> None:
    db.add.assert_not_called()
    db.delete.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()
    db.refresh.assert_not_called()


def iter_mapping_keys(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            yield key
            yield from iter_mapping_keys(nested_value)
    elif isinstance(value, (list, tuple)):
        for nested_value in value:
            yield from iter_mapping_keys(nested_value)


def test_valid_ai_explanation_is_returned_without_persisting_or_mutating_plan() -> None:
    plan = make_partial_plan()
    original_status = plan.status
    original_item_state = tuple(
        (item.placed, item.loading_sequence, item.rejection_reason)
        for item in plan.items
    )
    provider = FakeAIProvider(
        response={"explanation": "  Explicacao tecnica controlada.  "}
    )
    service, db = make_service(plan, provider)

    result = service.explain(plan.id, requester_role="LOGISTICS_MANAGER")

    assert result.load_plan_id == plan.id
    assert result.source == "AI"
    assert result.explanation == "Explicacao tecnica controlada."
    assert result.algorithm_version == "heuristic-v1"
    assert len(provider.calls) == 1
    assert provider.calls[0].timeout_seconds == 2.75
    assert plan.status == original_status
    assert (
        tuple(
            (item.placed, item.loading_sequence, item.rejection_reason)
            for item in plan.items
        )
        == original_item_state
    )
    db.scalar.assert_called_once()
    assert_no_writes(db)


def test_provider_receives_only_the_explicit_technical_whitelist() -> None:
    plan = make_partial_plan()
    plan.truck_snapshot_plate = "CPF-123.456.789-00"
    plan.truck_snapshot_model = "Motorista Joao da Silva"
    plan.items[0].product_snapshot_code = "CNPJ-12.345.678/0001-90"
    plan.items[0].product_snapshot_name = "Cliente Maria, telefone e endereco"
    provider = FakeAIProvider(response={"explanation": "Contexto seguro."})
    service, _db = make_service(plan, provider, timeout_seconds=4.5)

    service.explain(plan.id, requester_role="ADMIN")

    call = provider.calls[0]
    serialized = call.context.model_dump(mode="json")
    assert call.timeout_seconds == 4.5
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
    assert set(serialized["placed_volumes"][0]) == {
        "original_width_cm",
        "original_height_cm",
        "original_length_cm",
        "weight_kg",
        "fragile",
        "stackable",
        "rotation_allowed",
        "delivery_sequence",
        "x_cm",
        "y_cm",
        "z_cm",
        "width_cm",
        "height_cm",
        "length_cm",
        "rotation_code",
        "loading_sequence",
    }
    assert set(serialized["rejected_volumes"][0]) == {
        "original_width_cm",
        "original_height_cm",
        "original_length_cm",
        "weight_kg",
        "fragile",
        "stackable",
        "rotation_allowed",
        "delivery_sequence",
        "rejection_reason",
    }
    keys = set(iter_mapping_keys(serialized))
    assert not any(key == "id" or key.endswith("_id") for key in keys)
    serialized_text = str(serialized).lower()
    for forbidden_value in (
        str(plan.id),
        str(plan.truck_id),
        str(plan.orders[0].order_id),
        plan.truck_snapshot_plate,
        plan.truck_snapshot_model,
        plan.items[0].product_snapshot_code,
        plan.items[0].product_snapshot_name,
        "customer",
        "driver",
        "cpf",
        "cnpj",
        "phone",
        "address",
    ):
        assert forbidden_value.lower() not in serialized_text


def test_timeout_unavailable_and_invalid_output_use_identical_fallback() -> None:
    plan = make_partial_plan()
    expected_explanation = (
        "Plano calculado por heuristic-v1: 1 de 2 volumes carregados; "
        "ocupacao 0.6% e peso total 12.500 kg. "
        "Rejeicoes: NO_VALID_POSITION=1."
    )
    providers = (
        FakeAIProvider(error=AIProviderTimeoutError("timeout")),
        FakeAIProvider(error=AIProviderUnavailableError("unavailable")),
        FakeAIProvider(response={"explanation": "   "}),
    )
    results = []

    for provider in providers:
        service, db = make_service(plan, provider)
        results.append(service.explain(plan.id, requester_role="LOGISTICS_MANAGER"))
        assert len(provider.calls) == 1
        assert_no_writes(db)

    assert {result.source for result in results} == {"FALLBACK"}
    assert {result.load_plan_id for result in results} == {plan.id}
    assert {result.algorithm_version for result in results} == {"heuristic-v1"}
    assert {result.explanation for result in results} == {expected_explanation}


def test_explanation_above_the_length_cap_falls_back_without_touching_the_plan() -> (
    None
):
    """Provider prolixo demais é saída INVÁLIDA, como texto vazio.

    Sem teto, um adapter defeituoso ou um modelo em laço devolveria megabytes e
    a aplicação aceitaria: o texto atravessa a API e chega ao navegador.
    """

    plan = make_partial_plan()
    oversized = "a" * (MAX_EXPLANATION_LENGTH + 1)
    provider = FakeAIProvider(response={"explanation": oversized})
    service, db = make_service(plan, provider)

    result = service.explain(plan.id, requester_role="LOGISTICS_MANAGER")

    assert result.source == "FALLBACK"
    assert oversized not in result.explanation
    assert result.algorithm_version == "heuristic-v1"
    assert len(provider.calls) == 1
    assert_no_writes(db)


def test_explanation_exactly_at_the_length_cap_is_accepted() -> None:
    """O limite é inclusivo: 8.000 passa, 8.001 não."""

    plan = make_partial_plan()
    at_the_cap = "a" * MAX_EXPLANATION_LENGTH
    provider = FakeAIProvider(response={"explanation": at_the_cap})
    service, db = make_service(plan, provider)

    result = service.explain(plan.id, requester_role="LOGISTICS_MANAGER")

    assert result.source == "AI"
    assert result.explanation == at_the_cap
    assert_no_writes(db)


def test_unexpected_provider_error_is_not_hidden_by_fallback() -> None:
    plan = make_partial_plan()
    error = RuntimeError("provider bug")
    provider = FakeAIProvider(error=error)
    service, db = make_service(plan, provider)

    with pytest.raises(RuntimeError) as exc_info:
        service.explain(plan.id, requester_role="LOGISTICS_MANAGER")

    assert exc_info.value is error
    assert len(provider.calls) == 1
    assert_no_writes(db)


def test_checker_can_explain_only_an_approved_plan() -> None:
    approved_plan = make_plan(items=[make_item(suffix=1)], status="APPROVED")
    provider = FakeAIProvider(response={"explanation": "Plano aprovado."})
    approved_service, approved_db = make_service(approved_plan, provider)

    result = approved_service.explain(
        approved_plan.id,
        requester_role="CHECKER",
    )

    assert result.source == "AI"
    assert result.explanation == "Plano aprovado."
    assert len(provider.calls) == 1
    assert_no_writes(approved_db)


@pytest.mark.parametrize(
    ("role", "status"),
    [
        ("CHECKER", "CALCULATED"),
        ("DRIVER", "APPROVED"),
    ],
)
def test_rbac_denies_checker_non_approved_plan_and_driver(
    role: str,
    status: str,
) -> None:
    plan = make_plan(items=[make_item(suffix=1)], status=status)
    provider = FakeAIProvider()
    service, db = make_service(plan, provider)

    with pytest.raises(LoadPlanExplanationForbiddenError):
        service.explain(plan.id, requester_role=role)

    assert provider.calls == []
    assert_no_writes(db)


def test_missing_plan_returns_not_found_without_calling_provider() -> None:
    provider = FakeAIProvider()
    service, db = make_service(None, provider)

    with pytest.raises(LoadPlanExplanationNotFoundError):
        service.explain(uuid.uuid4(), requester_role="LOGISTICS_MANAGER")

    assert provider.calls == []
    db.scalar.assert_called_once()
    assert_no_writes(db)


def test_invalid_persisted_plan_does_not_call_provider_or_use_fallback() -> None:
    plan = make_partial_plan()
    plan.loaded_count = 0
    provider = FakeAIProvider(error=AIProviderTimeoutError("must not be called"))
    service, db = make_service(plan, provider)

    with pytest.raises(
        LoadPlanExplanationInvalidPlanError,
        match="counts must match",
    ):
        service.explain(plan.id, requester_role="LOGISTICS_MANAGER")

    assert provider.calls == []
    assert_no_writes(db)
