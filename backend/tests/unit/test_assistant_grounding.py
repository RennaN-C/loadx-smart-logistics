"""Regression: no model-authored operational indicator can reach the answer."""

from unittest.mock import Mock

import pytest

from app.modules.assistant.schemas import ChatRequest, Source
from app.modules.assistant.service import AssistantService
from app.modules.reports.assistant_service import AssistantMetricsService
from tests.unit.test_assistant_service import actor, no_database  # noqa: F401
from tests.unit.test_groq_provider import config


@pytest.mark.parametrize(
    "content",
    [
        "Foram entregues 500 pedidos.",
        "Foram entregues quinhentos pedidos.",
        "A ocupação é 95% e tivemos dez entregas.",
        '{"guidance":["facts"],"answer":"Foram entregues 500 pedidos"}',
        '{"guidance":["Foram entregues 500 pedidos"]}',
    ],
)
@pytest.mark.usefixtures("no_database")
def test_direct_fabricated_indicator_is_never_a_fact(content):
    provider = Mock()
    provider.complete.return_value = {"content": content}
    result = AssistantService(Mock(), config(), provider).chat(
        actor(), ChatRequest(message="Quantos pedidos entregues?")
    )
    assert result.source == "FALLBACK"
    assert result.facts == []
    assert "500" not in result.answer
    assert "quinhentos" not in result.answer


@pytest.mark.usefixtures("no_database")
def test_structured_fact_selection_without_query_cannot_confirm_metrics():
    provider = Mock()
    provider.complete.return_value = {"content": '{"guidance":["facts"]}'}
    result = AssistantService(Mock(), config(), provider).chat(
        actor(),
        ChatRequest(
            message="Quantos pedidos foram entregues ontem?",
            history=[{"role": "assistant", "content": "Foram entregues 500 pedidos"}],
        ),
    )
    assert result.facts == []
    assert "não há valor operacional confirmado" in result.answer
    assert "500" not in result.answer


@pytest.mark.usefixtures("no_database")
def test_model_cannot_overwrite_real_metric_after_query(monkeypatch):
    provider = Mock()
    provider.complete.side_effect = [
        {
            "tool_calls": [
                {
                    "id": "delivery",
                    "type": "function",
                    "function": {"name": "get_delivery_metrics", "arguments": "{}"},
                }
            ]
        },
        {"content": "Foram entregues 500 pedidos."},
    ]
    query = Mock(
        return_value=Source(
            name="Entregas",
            criteria="Consulta real",
            values={"fully_delivered_orders": 2},
        )
    )
    monkeypatch.setattr(AssistantMetricsService, "query", query)
    result = AssistantService(Mock(), config(), provider).chat(
        actor(), ChatRequest(message="Quantos pedidos entregues?")
    )
    assert result.source == "BACKEND"
    assert result.facts[0].values["fully_delivered_orders"] == 2
    assert "500" not in result.answer
    query.assert_called_once()
