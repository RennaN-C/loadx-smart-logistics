"""Read-only planning assistant: last plan, history, algorithm facts and RBAC."""

import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exceptions import ApiError
from app.core.pagination import PageResult
from app.modules.assistant.conversation import conversation_reply
from app.modules.assistant.planning_insights import _kind, planning_insight
from app.modules.assistant.schemas import ChatRequest


def person(role="ADMIN"):
    return SimpleNamespace(id=uuid.uuid4(), role=role, active=True)


def summary(index=1, status="CALCULATED"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        truck_plate=f"ABC{index}123",
        status=status,
        loaded_count=50,
        unloaded_count=2,
    )


def persisted(plan_id):
    return SimpleNamespace(
        id=plan_id,
        status="CALCULATED",
        algorithm_version="loadx-engine-v1",
        truck_snapshot_plate="ABC1234",
        truck_snapshot_max_weight_kg=Decimal(4000),
        truck_snapshot_internal_width_cm=240,
        truck_snapshot_internal_height_cm=270,
        truck_snapshot_internal_length_cm=680,
        loaded_count=50,
        unloaded_count=2,
        total_weight_kg=Decimal(2500),
        occupancy_percent=Decimal("62.5"),
        items=[
            SimpleNamespace(rejection_reason="TRUCK_WEIGHT_EXCEEDED"),
            SimpleNamespace(rejection_reason="NO_VALID_POSITION"),
        ],
    )


def stub_service(monkeypatch, items):
    service = Mock()
    service.list_load_plans.side_effect = lambda page, **kwargs: PageResult.create(
        items[page.offset : page.offset + page.page_size], page, len(items)
    )
    service.get_load_plan.side_effect = lambda key: persisted(key)
    service.get_distribution_state_for_plan.return_value = (None, None, None, True)
    monkeypatch.setattr(
        "app.modules.assistant.planning_insights.LoadPlanningService",
        lambda _: service,
    )
    return service


def test_latest_plan_explains_persisted_algorithm_without_groq(monkeypatch):
    latest = summary()
    service = stub_service(monkeypatch, [latest])
    result = planning_insight(
        Mock(),
        person(),
        ChatRequest(message="Explique o último planejamento calculado"),
    )
    assert result.source == "BACKEND"
    assert "loadx-engine-v1" in result.answer
    assert "50 volumes" in result.answer
    assert "2" in result.answer
    assert "limite de peso" in result.answer
    assert "nenhuma posição válida" in result.answer
    assert "melhor arranjo possível" in result.answer
    assert result.facts[0].values["occupancy_percent"] == 62.5
    assert result.facts[0].links[0]["href"] == f"/planning/{latest.id}"
    assert service.get_load_plan.call_args.args[0] == latest.id


def test_list_history_is_bounded_paginated_and_linked(monkeypatch):
    entries = [summary(index) for index in range(12)]
    service = stub_service(monkeypatch, entries)
    result = planning_insight(
        Mock(),
        person(),
        ChatRequest(message="Liste todos os planejamentos página 2"),
    )
    assert result.source == "BACKEND"
    fact = result.facts[0]
    assert fact.values["total_records"] == 12
    assert fact.values["page"] == 2
    assert len(fact.links) == 4
    assert len([key for key in fact.values if key.startswith("item_")]) == 4
    assert service.list_load_plans.call_args.kwargs["requester_role"] == "ADMIN"


def test_checker_uses_original_role_filtered_service(monkeypatch):
    service = stub_service(monkeypatch, [summary(status="APPROVED")])
    result = planning_insight(
        Mock(),
        person("CHECKER"),
        ChatRequest(message="Quais os planejamentos salvos?"),
    )
    assert result.source == "BACKEND"
    assert service.list_load_plans.call_args.kwargs["requester_role"] == "CHECKER"


def test_checker_cannot_read_unapproved_plan_by_guessed_id(monkeypatch):
    service = stub_service(monkeypatch, [])
    with pytest.raises(ApiError) as error:
        planning_insight(
            Mock(),
            person("CHECKER"),
            ChatRequest(message="Explique o planejamento " + str(uuid.uuid4())),
        )
    assert error.value.status_code == 403
    assert service.get_distribution_state_for_plan.call_count == 0


def test_plan_missing_returns_truthful_answer(monkeypatch):
    stub_service(monkeypatch, [])
    result = planning_insight(
        Mock(),
        person(),
        ChatRequest(message="Explique o último planejamento"),
    )
    assert result.source == "BACKEND"
    assert "não encontrei" in result.answer.lower()


def test_latest_plan_takes_current_page_context_when_requested(monkeypatch):
    service = stub_service(monkeypatch, [])
    target = uuid.uuid4()
    result = planning_insight(
        Mock(),
        person(),
        ChatRequest(message="Explique por que o algoritmo fez isso", plan_id=target),
    )
    assert result.source == "BACKEND"
    service.get_load_plan.assert_called_once_with(target)
    service.list_load_plans.assert_not_called()


@pytest.mark.parametrize(
    "question",
    [
        "Qual o último planejamento?",
        "Por que o último cálculo rejeitou volumes?",
        "Quais os planejamentos anteriores?",
        "Explique o plano " + str(uuid.uuid4()),
    ],
)
def test_detects_explicit_planning_queries(question):
    assert _kind(question, ChatRequest(message=question)) is not None


@pytest.mark.parametrize(
    "question",
    [
        "Oi",
        "Qual produto temos cadastrado?",
        "Quantas entregas tivemos?",
        "Como funcionam as permissões?",
    ],
)
def test_other_chats_never_consult_plans(question):
    assert _kind(question, ChatRequest(message=question)) is None


def test_suggestions_only_when_asked_respect_checker_permissions():
    answer = conversation_reply(person("CHECKER"), "Me dê sugestões")
    assert answer.source == "BACKEND"
    assert "planejamento" in answer.answer.lower()
    assert "entregues nos últimos 30 dias" not in answer.answer


def test_action_is_handoff_not_write():
    result = conversation_reply(person(), "aprovar plano")
    assert result.source == "BACKEND"
    assert result.links == [{"label": "Abrir tela da operação", "href": "/planning"}]
    assert "Nenhum registro foi alterado" in result.answer
