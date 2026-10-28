"""Natural, grounded wording for planning follow-ups and read-only lists."""

import json
import uuid
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.integrations.ai.provider import AIProviderUnavailableError
from app.modules.assistant.briefs import brief_verified_plan
from app.modules.assistant.followups import resolve_followup
from app.modules.assistant.schemas import ChatRequest, ChatResponse, Source
from app.modules.assistant.service import AssistantService, _catalog_answer
from tests.unit.test_groq_provider import config


def _plan() -> ChatResponse:
    return ChatResponse(
        source="BACKEND",
        answer=(
            "Analisei o planejamento salvo. Situação calculado. O algoritmo "
            "posicionou 24 volumes e rejeitou 0. Ocupação 22,5%."
        ),
        facts=[
            Source(
                name="Análise do planejamento",
                criteria="Snapshot persistido e autorizado",
                values={
                    "status": "CALCULATED",
                    "loaded_volumes": 24,
                    "rejected_volumes": 0,
                    "occupancy_percent": 22.5,
                    "weight_kg": 3600,
                    "truck_capacity_weight_kg": 4000,
                    "truck_plate": "TESTE M2",
                },
            )
        ],
    )


def test_initial_explanation_is_brief_and_factual():
    response = brief_verified_plan("Me explique sobre o último planejamento", _plan())
    assert response.answer.startswith("O planejamento no caminhão TESTE M2")
    assert "24 volumes" in response.answer
    assert "22,5%" in response.answer
    assert response.facts == _plan().facts
    assert len(response.answer) < 470


def test_followup_answers_only_the_truck_question():
    response = brief_verified_plan(
        "Explique esse planejamento e responda: Trocar de caminhão ajudaria?",
        _plan(),
    )
    assert "não parece necessária" in response.answer
    assert "3600" in response.answer or "3.600" in response.answer
    assert "novo cálculo" in response.answer
    assert "22,5%" not in response.answer
    assert "O algoritmo posicionou" not in response.answer


def test_rejections_are_not_conflated_with_operational_safety():
    response = brief_verified_plan("Deu algum problema?", _plan())
    assert "nenhuma rejeição foi registrada" in response.answer
    assert "outros problemas operacionais" in response.answer


def test_unknown_fields_never_create_new_numbers():
    result = ChatResponse(
        source="BACKEND",
        answer="Sem dados adicionais.",
        facts=[Source(name="Análise do planejamento", criteria="Persistido", values={})],
    )
    assert brief_verified_plan("Explique o plano", result) == result


def test_registry_list_has_friendly_order_summary():
    records = Source(
        name="Pedidos cadastrados",
        criteria="Consulta autorizada",
        values={
            "total_records": 2,
            "page": 1,
            "total_pages": 1,
            "item_1": "Pedido d31816aa · Pronto",
            "item_2": "Pedido fa5a8944 · Entregue",
        },
    )
    answer = _catalog_answer(records)
    assert "Encontrei 2 pedidos cadastrados" in answer
    assert "Pedido d31816aa" in answer
    assert "prontos, planejados ou entregues" in answer


def test_latest_plan_truck_followup_without_client_plan_id():
    request = ChatRequest(
        message="Trocar de caminhão ajudaria?",
        history=[
            {"role": "user", "content": "Me explique sobre o último planejamento"},
            {"role": "assistant", "content": "Analisei o último planejamento."},
        ],
    )
    resolved, changed = resolve_followup(request)
    assert changed
    assert resolved.message.startswith("Explique o último planejamento")
    assert resolved.plan_id is None


@pytest.fixture
def isolated(monkeypatch):
    monkeypatch.setattr("app.modules.assistant.service.ensure_budget", Mock())
    monkeypatch.setattr(
        "app.modules.assistant.service.planning_context", lambda *_: ([], [])
    )
    monkeypatch.setattr(
        "app.modules.assistant.service.planning_insight",
        lambda *_: _plan(),
    )


def test_groq_unavailable_keeps_concise_relevant_fallback(isolated):
    provider = Mock()
    provider.complete.side_effect = AIProviderUnavailableError()
    user = SimpleNamespace(id=uuid.uuid4(), active=True, role="ADMIN")
    response = AssistantService(Mock(), config(), provider).chat(
        user,
        ChatRequest(message="Trocar de caminhão ajudaria?"),
    )
    assert response.source == "BACKEND"
    assert "não parece necessária" in response.answer
    assert "novo cálculo" in response.answer
    assert "O algoritmo posicionou" not in response.answer
    assert provider.complete.call_count == 1


def test_groq_can_answer_first_planning_question_naturally(isolated):
    provider = Mock()
    provider.complete.return_value = {
        "content": json.dumps(
            {
                "answer": "O plano posicionou 24 volumes sem rejeições. Quer verificar a carga?",
                "source_names": ["Análise do planejamento"],
            }
        )
    }
    user = SimpleNamespace(id=uuid.uuid4(), active=True, role="ADMIN")
    response = AssistantService(Mock(), config(), provider).chat(
        user, ChatRequest(message="Me explique sobre o último planejamento")
    )
    assert response.source == "GROQ"
    assert response.answer.startswith("O plano posicionou")
    assert response.facts[0].values["loaded_volumes"] == 24
    assert provider.complete.call_count == 1
