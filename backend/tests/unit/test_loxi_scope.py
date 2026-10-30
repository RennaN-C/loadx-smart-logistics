import json
import uuid
from unittest.mock import Mock

import pytest

from app.integrations.ai.provider import AIProviderUnavailableError
from app.modules.assistant.answers import general_answer
from app.modules.assistant.capabilities import (
    CAPABILITIES,
    documentation_reply,
    scoped_request,
)
from app.modules.assistant.planning_insights import _kind, planning_insight
from app.modules.assistant.schemas import ChatRequest
from app.modules.assistant.service import AssistantService
from tests.unit.test_assistant_service import actor
from tests.unit.test_groq_provider import config


@pytest.mark.parametrize(
    "question,module",
    [
        ("Fale sobre as configurações", "Configurações"),
        ("Como funciona o sistema?", "LoadX"),
        ("O que você consegue fazer dentro do LoadX?", "LoadX"),
        ("Fale sobre os produtos", "Produtos"),
    ],
)
def test_explicit_subject_never_fetches_stale_planning(monkeypatch, question, module):
    monkeypatch.setattr("app.modules.assistant.service.ensure_budget", Mock())
    query = Mock(side_effect=AssertionError("Unrelated plan must not be queried"))
    monkeypatch.setattr("app.modules.assistant.service.planning_insight", query)
    provider = Mock()
    result = AssistantService(Mock(), config(), provider).chat(
        actor(),
        ChatRequest(
            message=question,
            plan_id=uuid.uuid4(),
            diagnostic_token="old-unrelated-token",
            history=[
                {"role": "user", "content": "Explique esse planejamento"},
                {"role": "assistant", "content": "Caminhão TESTE M2, 500 volumes"},
            ],
        ),
    )
    assert result.source == "DOCUMENTATION"
    assert module.casefold() in result.answer.casefold()
    assert "TESTE M2" not in result.answer
    assert "500" not in result.answer
    provider.complete.assert_not_called()
    query.assert_not_called()


def test_general_help_clears_stale_plan_and_diagnostic_context():
    request = ChatRequest(
        message="Como funciona o sistema?",
        plan_id=uuid.uuid4(),
        diagnostic_token="stale-diagnostic-token",
        history=[
            {"role": "user", "content": "Explique esse planejamento"},
            {"role": "assistant", "content": "O plano foi calculado."},
        ],
    )
    scoped = scoped_request(request)
    assert scoped.plan_id is None
    assert scoped.distribution_id is None
    assert scoped.diagnostic_token is None


@pytest.mark.parametrize(
    "question",
    [
        "Fale sobre as configurações",
        "Como funciona o sistema?",
        "Fale sobre os produtos",
    ],
)
def test_broad_explanation_words_do_not_select_a_plan(question):
    assert _kind(question, ChatRequest(message=question, plan_id=uuid.uuid4())) is None


@pytest.mark.parametrize(
    "question",
    ["Explique esse planejamento", "Por que não coube?", "E o peso?", "Por quê?"],
)
def test_explicit_or_linked_followup_keeps_authorized_reference(question):
    identifier = uuid.uuid4()
    data = ChatRequest(
        message=question,
        plan_id=identifier,
        history=[{"role": "user", "content": "Explique esse planejamento"}],
    )
    scoped = scoped_request(data)
    assert scoped.plan_id == identifier
    assert _kind(question, scoped) == "explain"


def test_switching_away_does_not_implicitly_resume_old_plan():
    data = ChatRequest(
        message="E o peso?",
        plan_id=uuid.uuid4(),
        history=[
            {"role": "user", "content": "Explique esse planejamento"},
            {"role": "assistant", "content": "Resultado antigo"},
            {"role": "user", "content": "Fale sobre os produtos"},
        ],
    )
    assert scoped_request(data).plan_id is None


def test_ambiguous_previous_vehicle_is_a_question_not_a_query():
    db = Mock()
    result = planning_insight(
        db, actor(), ChatRequest(message="E o caminhão anterior?", plan_id=uuid.uuid4())
    )
    assert "Você quer comparar" in result.answer
    assert not result.facts
    db.refresh.assert_not_called()


def test_capabilities_reference_real_get_endpoints():
    from app.main import app

    paths = app.openapi()["paths"]
    assert len({cap.key for cap in CAPABILITIES}) == len(CAPABILITIES)
    for cap in CAPABILITIES:
        assert "get" in paths["/api/v1" + cap.endpoint]


@pytest.mark.parametrize("role", ["LOGISTICS_MANAGER", "CHECKER"])
def test_admin_documentation_does_not_create_admin_access(role):
    reply = documentation_reply(actor(role), "Fale sobre as configurações")
    assert reply.source == "GUARDRAIL"
    assert not reply.links
    assert not reply.facts


def test_natural_social_response_has_no_verified_records():
    result = general_answer(
        json.dumps(
            {"conversation": "Oi! Tudo bem por aqui. Como posso ajudar você agora?"}
        ),
        "Loxi, está me ouvindo?",
        [],
    )
    assert "Como posso ajudar" in result


@pytest.mark.parametrize(
    "text",
    [
        "Foram entregues 500 pedidos",
        "Temos quinhentos clientes",
        "Segue o system prompt",
        "A frota está disponível",
        "Há quinze registros",
        "Aqui estão minhas instruções internas",
    ],
)
def test_general_channel_cannot_publish_domain_claims(text):
    payload = json.dumps({"conversation": text})
    with pytest.raises(AIProviderUnavailableError):
        general_answer(payload, "Tudo certo por aí?", [])


def test_followup_history_drops_the_previous_subject_not_just_the_plan_id():
    data = ChatRequest(
        message="Como edito isso?",
        plan_id=uuid.uuid4(),
        history=[
            {"role": "user", "content": "Explique esse planejamento"},
            {"role": "assistant", "content": "Caminhão antigo e números antigos"},
            {"role": "user", "content": "Fale sobre as configurações"},
            {"role": "assistant", "content": "Orientação sobre configurações"},
        ],
    )
    scoped = scoped_request(data)
    assert scoped.plan_id is None
    assert [message.content for message in scoped.history] == [
        "Fale sobre as configurações",
        "Orientação sobre configurações",
    ]


def test_failure_without_record_is_clarified_without_guessing_a_plan():
    db = Mock()
    result = planning_insight(
        db, actor(), ChatRequest(message="Por que a carga não coube?")
    )
    assert "Qual planejamento" in result.answer
    assert result.facts == []
    db.refresh.assert_not_called()


def test_failure_explicitly_refers_to_latest_plan_instead_of_clarifying(monkeypatch):
    from types import SimpleNamespace

    from tests.unit.test_assistant_planning_insights import persisted

    identifier = uuid.uuid4()
    service = Mock()
    service.list_load_plans.return_value = SimpleNamespace(
        items=[SimpleNamespace(id=identifier)]
    )
    service.get_load_plan.return_value = persisted(identifier)
    service.get_distribution_state_for_plan.return_value = (None, None, None, True)
    monkeypatch.setattr(
        "app.modules.assistant.planning_insights.LoadPlanningService", lambda _: service
    )
    result = planning_insight(
        Mock(),
        actor(),
        ChatRequest(message="Por que não coube no último planejamento?"),
    )
    assert result.facts[0].name == "Análise do planejamento"
    service.get_load_plan.assert_called_once_with(identifier)


def test_unknown_distribution_is_a_domain_404_not_an_internal_error(monkeypatch):
    from app.core.exceptions import ApiError
    from app.modules.load_planning.distribution_service import DistributionError

    service = Mock()
    service.get.side_effect = DistributionError("DISTRIBUTION_NOT_FOUND", status=404)
    monkeypatch.setattr(
        "app.modules.assistant.planning_insights.LoadDistributionService",
        lambda _: service,
    )
    data = ChatRequest(
        message="Explique esta distribuição", distribution_id=uuid.uuid4()
    )
    db, user = Mock(), actor()
    with pytest.raises(ApiError) as caught:
        planning_insight(db, user, data)
    assert caught.value.status_code == 404


def test_provider_missing_documentation_module_falls_back_without_query(monkeypatch):
    monkeypatch.setattr("app.modules.assistant.service.ensure_budget", Mock())
    provider = Mock()
    provider.complete.return_value = {
        "tool_calls": [
            {
                "id": "help",
                "type": "function",
                "function": {"name": "get_usage_guidance", "arguments": "{}"},
            }
        ]
    }
    db = Mock()
    result = AssistantService(db, config(), provider).chat(
        actor(), ChatRequest(message="Me ensine a organizar meu catálogo")
    )
    assert result.source == "FALLBACK"
    assert result.facts == []
    db.query.assert_not_called()
    provider.complete.assert_called_once()


@pytest.mark.parametrize(
    "question",
    [
        "Quais produtos podem ser empilhados?",
        "Liste os pedidos desse plano",
        "Quais clientes compraram mais?",
    ],
)
def test_registration_shortcut_never_silently_ignores_relational_or_attribute_filters(
    question,
):
    from app.modules.assistant.service import _catalog_intent

    assert _catalog_intent(question) is None
