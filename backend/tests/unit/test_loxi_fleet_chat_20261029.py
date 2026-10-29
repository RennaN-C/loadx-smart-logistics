"""Loxi fleet replies use authorized operational facts, not generated names."""

import uuid
from types import SimpleNamespace
from unittest.mock import Mock

from app.modules.assistant.schemas import ChatRequest, Source
from app.modules.assistant.service import (
    AssistantService,
    _fleet_availability_answer,
    _fleet_availability_intent,
)
from app.modules.reports.assistant_service import AssistantMetricsService
from tests.unit.test_groq_provider import config


def _user(role="ADMIN"):
    return SimpleNamespace(id=uuid.uuid4(), role=role, active=True)


def _fleet_result():
    def item(plate, model, active, available, **reasons):
        return SimpleNamespace(
            plate=plate,
            model=model,
            active=active,
            available=available,
            has_operation_conflict=reasons.get("operation", False),
            has_maintenance_conflict=reasons.get("maintenance", False),
            has_document_conflict=reasons.get("document", False),
        )

    return SimpleNamespace(
        page=1,
        total_pages=1,
        items=[
            item("ABC123", "Pequeno", True, True),
            item("ABD5543", "Baú Médio", False, False),
            item("TESTE M2", "Baú Pequeno", True, False, maintenance=True),
        ],
    )


def test_service_exposes_authorized_plates_and_explicit_reasons(monkeypatch):
    monkeypatch.setattr(
        "app.modules.reports.assistant_service.TruckOperationalStatusService.list_statuses",
        lambda self, pagination: _fleet_result(),
    )
    fact = AssistantMetricsService(Mock())._availability(page=1)
    assert fact.values["page_vehicle_count"] == 3
    assert fact.values["page_active_count"] == 2
    assert fact.values["page_unavailable_count"] == 2
    assert "ABD5543" in fact.values["item_1"]
    assert "cadastro arquivado" in fact.values["item_1"]
    assert "TESTE M2" in fact.values["item_2"]
    assert "manutenção" in fact.values["item_2"]
    assert "ABC123" not in str(fact.values["item_1"]) + str(fact.values["item_2"])


def test_availability_response_explains_page_and_distinct_statuses():
    fact = Source(
        name="Disponibilidade atual da frota",
        criteria="Consulta autorizada",
        values={
            "page": 1,
            "total_pages": 3,
            "page_unavailable_count": 1,
            "item_1": "Baú Pequeno · placa TESTE M2 · documentação",
        },
    )
    answer = _fleet_availability_answer(fact)
    assert "TESTE M2" in answer
    assert "documentação" in answer
    assert "Página 1 de 3" in answer
    assert "cadastro ativo" in answer
    assert "frota inteira" not in answer


def test_explicit_current_fleet_query_is_deterministic(monkeypatch):
    monkeypatch.setattr("app.modules.assistant.service.ensure_budget", Mock())
    monkeypatch.setattr(
        "app.modules.reports.assistant_service.TruckOperationalStatusService.list_statuses",
        lambda self, pagination: _fleet_result(),
    )
    provider = Mock()
    response = AssistantService(Mock(), config(), provider).chat(
        _user(), ChatRequest(message="Quais caminhões estão indisponíveis?")
    )
    assert response.source == "BACKEND"
    assert "TESTE M2" in response.answer
    assert "ABD5543" in response.answer
    assert "manutenção" in response.answer
    assert "cadastro ativo" in response.answer
    provider.complete.assert_not_called()


def test_fleet_query_rechecks_permission_without_provider(monkeypatch):
    monkeypatch.setattr("app.modules.assistant.service.ensure_budget", Mock())
    monkeypatch.setattr("app.modules.assistant.service.allowed_tool", lambda *_: False)
    provider = Mock()
    db = Mock()
    response = AssistantService(db, config(), provider).chat(
        _user(), ChatRequest(message="Quais caminhões estão indisponíveis?")
    )
    assert response.source == "GUARDRAIL"
    assert not response.facts
    provider.complete.assert_not_called()
    db.refresh.assert_not_called()


def test_historical_or_ambiguous_questions_do_not_claim_current_snapshot():
    assert _fleet_availability_intent("Quais veículos estão indisponíveis?")
    assert _fleet_availability_intent("Quantos caminhões estão bloqueados?")
    assert not _fleet_availability_intent(
        "Quais caminhões estavam indisponíveis ontem?"
    )
    assert not _fleet_availability_intent("Como faço para liberar caminhões?")
    assert not _fleet_availability_intent("Quais caminhões temos cadastrados?")


def test_catalog_distinguishes_total_from_current_page():
    from app.modules.assistant.service import _catalog_answer

    fact = Source(
        name="Caminhões cadastrados",
        criteria="Listagem paginada",
        values={
            "total_records": 30,
            "page": 2,
            "total_pages": 3,
            "item_1": "Baú Pequeno · placa ABC123 · Ativo",
            "item_2": "Baú Médio · placa DEF456 · Arquivado",
        },
    )
    answer = _catalog_answer(fact)
    assert "Encontrei 30 caminhões cadastrados" in answer
    assert "Mostrando 2 registro(s) nesta página" in answer
    assert "Página 2 de 3" in answer
