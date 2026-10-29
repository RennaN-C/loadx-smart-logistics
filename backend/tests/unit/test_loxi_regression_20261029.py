"""Regression scenarios from real Loxi conversations; no external Groq calls."""

import json
import uuid
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest

from app.integrations.ai.provider import AIProviderUnavailableError
from app.modules.assistant.answers import natural_answer
from app.modules.assistant.briefs import brief_verified_plan
from app.modules.assistant.capabilities import documentation_reply
from app.modules.assistant.followups import resolve_followup
from app.modules.assistant.schemas import ChatRequest, ChatResponse, Source
from app.modules.assistant.service import AssistantService
from tests.unit.test_groq_provider import config


def _user(role="ADMIN"):
    return SimpleNamespace(id=uuid.uuid4(), role=role, active=True)


def _plan():
    return ChatResponse(
        source="BACKEND",
        answer="Plano calculado com 24 volumes.",
        facts=[
            Source(
                name="Análise do planejamento",
                criteria="Snapshot persistido e autorizado",
                values={
                    "status": "CALCULATED",
                    "truck_plate": "TESTE M2",
                    "loaded_volumes": 24,
                    "rejected_volumes": 0,
                    "occupancy_percent": 22.5,
                    "weight_utilization_percent": 90,
                    "weight_kg": 3600,
                    "truck_capacity_weight_kg": 4000,
                },
            )
        ],
    )


def _narration(answer):
    return json.dumps({"answer": answer, "source_names": ["Análise do planejamento"]})


def test_occupation_question_distinguishes_weight_from_geometry():
    result = brief_verified_plan(
        "Qual foi a ocupação de peso e de espaço do último planejamento?", _plan()
    )
    assert "22,5%" in result.answer
    assert "90%" in result.answer
    assert "3600 de 4000 kg" in result.answer
    assert "indicadores diferentes" in result.answer


def test_percentage_difference_is_explained_without_a_new_simulation():
    result = brief_verified_plan(
        "Por que 22,5% de ocupação se o caminhão está com 3.600 kg?", _plan()
    )
    assert "90%" in result.answer
    assert "22,5%" in result.answer
    assert "sem nova simulação" in result.answer


def test_saved_status_and_truck_comparison_are_brief():
    state = brief_verified_plan(
        "Esse planejamento está calculado ou aprovado?", _plan()
    )
    assert "calculado, ainda não aprovado" in state.answer
    change = brief_verified_plan(
        "Trocar de caminhão ajudaria? Explique usando os dados reais.", _plan()
    )
    assert "troca não parece necessária" in change.answer
    assert "não simulei a troca" in change.answer


@pytest.mark.parametrize(
    "answer",
    [
        "O peso usa 22,5% da capacidade.",
        "A ocupação de peso é 22,5%.",
        "A ocupação geométrica é 90%.",
        "A ocupação de espaço não foi registrada no snapshot.",
        "O plano está PROPOSED e PENDING para aprovação.",
        "O planejamento já está aprovado.",
    ],
)
def test_provider_cannot_relabel_verified_metrics_or_status(answer):
    with pytest.raises(AIProviderUnavailableError):
        natural_answer(_narration(answer), _plan().facts)


def test_provider_can_use_both_percentages_with_correct_meaning():
    response = natural_answer(
        _narration("A ocupação de peso é 90% e a ocupação geométrica é 22,5%."),
        _plan().facts,
    )
    assert "90%" in response and "22,5%" in response


def test_savings_and_new_optimization_are_not_claimed_by_backend():
    result = brief_verified_plan("Trocar de caminhão ajudaria?", _plan())
    assert "novo cálculo" in result.answer
    assert "não simulei" in result.answer


def test_fleet_question_retains_recent_planning_through_weight_followup():
    history = [
        {"role": "user", "content": "Esse planejamento está calculado ou aprovado?"},
        {"role": "assistant", "content": "Calculado."},
        {
            "role": "user",
            "content": "Por que 22,5% de ocupação se o caminhão tem 3600 kg?",
        },
        {"role": "assistant", "content": "Peso e espaço são diferentes."},
    ]
    result, changed = resolve_followup(
        ChatRequest(
            message="Trocar de caminhão ajudaria? Explique usando os dados reais.",
            history=history,
        )
    )
    assert changed
    assert result.message.startswith("Explique o último planejamento")
    assert result.plan_id is None


def test_single_registered_product_uses_correct_portuguese():
    from app.modules.assistant.service import _catalog_answer

    response = _catalog_answer(
        Source(
            name="Produtos cadastrados",
            criteria="Persistido",
            values={"total_records": 1, "item_1": "Caixa média"},
        )
    )
    assert "Encontrei 1 produto cadastrado" in response


def test_general_capabilities_are_server_documented_without_groq():
    result = documentation_reply(_user(), "O que você consegue fazer dentro do LoadX?")
    assert result is not None
    assert result.source == "DOCUMENTATION"
    assert "Planejamento" in result.answer


def test_critical_plan_questions_skip_groq(monkeypatch):
    monkeypatch.setattr("app.modules.assistant.service.ensure_budget", Mock())
    monkeypatch.setattr(
        "app.modules.assistant.service.planning_insight",
        lambda *_: _plan(),
    )
    provider = Mock()
    result = AssistantService(Mock(), config(), provider).chat(
        _user(),
        ChatRequest(message="Qual a ocupação de peso e espaço do último planejamento?"),
    )
    assert result.source == "BACKEND"
    assert "90%" in result.answer
    provider.complete.assert_not_called()


def test_action_handoff_never_writes_and_links_only_authorized_record(monkeypatch):
    monkeypatch.setattr("app.modules.assistant.service.ensure_budget", Mock())
    plan_id = uuid.uuid4()
    permitted = Mock(
        return_value=(
            [
                Source(
                    name="Plano autorizado",
                    criteria="Persistido",
                    values={"status": "CALCULATED"},
                )
            ],
            [{"label": "Abrir plano", "href": f"/planning/{plan_id}"}],
        )
    )
    monkeypatch.setattr("app.modules.assistant.service.planning_context", permitted)
    provider, db = Mock(), Mock()
    result = AssistantService(db, config(), provider).chat(
        _user(), ChatRequest(message="Aprove esse planejamento", plan_id=plan_id)
    )
    assert result.source == "BACKEND"
    assert result.links[0]["href"] == f"/planning/{plan_id}"
    assert "Nenhum registro foi alterado" in result.answer
    provider.complete.assert_not_called()
    db.execute.assert_not_called()


def test_provider_429_opens_short_process_local_circuit(monkeypatch):
    from app.integrations.ai import groq

    monkeypatch.setattr(groq, "_rate_limited_until", 0.0)
    now = [100.0]
    monkeypatch.setattr(groq.time, "monotonic", lambda: now[0])
    opener = Mock()
    opener.open.side_effect = HTTPError(
        "https://example.invalid", 429, "limit", {}, None
    )
    monkeypatch.setattr(groq, "build_opener", lambda *_: opener)
    production = config().model_copy(update={"app_env": "production"})
    provider = groq.GroqProvider(production)
    with pytest.raises(AIProviderUnavailableError) as first:
        provider.complete([], timeout_seconds=1)
    assert first.value.reason == "http_429"
    with pytest.raises(AIProviderUnavailableError) as second:
        provider.complete([], timeout_seconds=1)
    assert second.value.reason == "http_429"
    assert opener.open.call_count == 1
