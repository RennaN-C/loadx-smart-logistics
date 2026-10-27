"""Catalog answers are authorized read-only snapshots, not AI guesses."""

from types import SimpleNamespace
from unittest.mock import Mock

from app.modules.assistant.schemas import ToolArguments
from app.modules.products.service import ProductService
from app.modules.reports.assistant_service import AssistantMetricsService
from app.modules.trucks.service import TruckService
from tests.unit.test_assistant_service import actor


def test_registered_products_are_paged_and_keep_archived_visible(monkeypatch):
    list_products = Mock(
        return_value=SimpleNamespace(
            page=1,
            total_pages=2,
            total=11,
            items=[
                SimpleNamespace(name="Caixa de papelão", code="CX-10", active=True),
                SimpleNamespace(name="Produto antigo", code="OLD-1", active=False),
            ],
        )
    )
    monkeypatch.setattr(ProductService, "list_products", list_products)
    result = AssistantMetricsService(Mock()).query(
        actor(), "get_registered_products", ToolArguments(page=1)
    )
    assert result.values["total_records"] == 11
    assert result.values["total_pages"] == 2
    assert "Caixa de papelão" in result.values["item_1"]
    assert "Arquivado" in result.values["item_2"]
    assert list_products.call_args.args[0].page_size == 10


def test_registered_trucks_list_registration_not_operational_availability(monkeypatch):
    list_trucks = Mock(
        return_value=SimpleNamespace(
            page=1,
            total_pages=1,
            total=2,
            items=[
                SimpleNamespace(model="Volvo FH", plate="ABC1234", active=True),
                SimpleNamespace(model="Mercedes Atego", plate="DEF5678", active=False),
            ],
        )
    )
    monkeypatch.setattr(TruckService, "list_trucks", list_trucks)
    result = AssistantMetricsService(Mock()).query(
        actor(), "get_registered_trucks", ToolArguments(page=1)
    )
    assert result.name == "Caminhões cadastrados"
    assert result.values["total_records"] == 2
    assert "Volvo FH" in result.values["item_1"]
    assert "ABC1234" in result.values["item_1"]
    assert "Arquivado" in result.values["item_2"]
    assert list_trucks.call_args.args[0].page_size == 10
