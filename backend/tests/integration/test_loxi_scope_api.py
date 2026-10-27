import uuid
from unittest.mock import Mock

from app.integrations.ai.groq import GroqProvider
from app.modules.customers.models import Customer
from app.modules.load_planning.schemas import LoadPlanCreate
from app.modules.load_planning.service import LoadPlanningService
from app.modules.products.service import ProductService
from tests.integration.test_deliveries_api import seed_operational_scenario
from tests.integration.test_load_planning_api import seed_planning_scenario


def test_documentation_ignores_unrelated_invalid_plan_and_provider(
    client, session_factory, monkeypatch
):
    scenario = seed_operational_scenario(session_factory)
    complete = Mock(side_effect=AssertionError("Documentation must not depend on Groq"))
    monkeypatch.setattr(GroqProvider, "complete", complete)
    response = client.post(
        "/api/v1/assistant/messages",
        headers=scenario.manager_headers,
        json={
            "message": "Fale sobre os produtos",
            "plan_id": str(uuid.uuid4()),
            "diagnostic_token": "stale-invalid-token",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["source"] == "DOCUMENTATION"
    assert "centímetros" in response.json()["answer"]
    assert all(
        fact["name"].startswith("Como usar:") for fact in response.json()["facts"]
    )
    complete.assert_not_called()


def test_registration_is_paginated_active_and_role_scoped(client, session_factory):
    scenario = seed_operational_scenario(session_factory)
    with session_factory() as db:
        for index in range(12):
            db.add(
                Customer(
                    name=f"Cliente QA {index}",
                    document=uuid.uuid4().hex,
                    address="Endereço privado",
                    city="Cidade QA",
                    state="SP",
                    active=True,
                )
            )
        db.add(
            Customer(
                name="Arquivado não selecionável",
                document=uuid.uuid4().hex,
                address="Privado",
                city="Cidade QA",
                state="SP",
                active=False,
            )
        )
        db.commit()
    response = client.post(
        "/api/v1/assistant/messages",
        headers=scenario.manager_headers,
        json={"message": "Liste os clientes cadastrados, página 2"},
    )
    assert response.status_code == 200, response.text
    values = response.json()["facts"][0]["values"]
    assert values["page"] == 2
    assert 0 < values["page_records"] <= 10
    assert "Endereço privado" not in str(response.json())
    assert "Arquivado não selecionável" not in str(response.json())
    denied = client.post(
        "/api/v1/assistant/messages",
        headers=scenario.checker_headers,
        json={"message": "Liste os clientes cadastrados"},
    )
    assert denied.json()["source"] == "GUARDRAIL"
    assert denied.json()["facts"] == []


def test_provider_selects_documentation_semantically_without_listing_products(
    client, session_factory, monkeypatch
):
    scenario = seed_operational_scenario(session_factory)
    complete = Mock(
        side_effect=[
            {
                "tool_calls": [
                    {
                        "id": "help",
                        "type": "function",
                        "function": {
                            "name": "get_usage_guidance",
                            "arguments": '{"module":"products"}',
                        },
                    }
                ]
            },
            {"content": '{"guidance":["facts"]}'},
        ]
    )
    monkeypatch.setattr(GroqProvider, "complete", complete)
    records = Mock(side_effect=AssertionError("How-to is not a product listing"))
    monkeypatch.setattr(ProductService, "list_products", records)
    response = client.post(
        "/api/v1/assistant/messages",
        headers=scenario.manager_headers,
        json={"message": "Me ensine a organizar meu catálogo"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["source"] == "DOCUMENTATION"
    assert "Produtos guarda dimensões" in response.json()["answer"]
    records.assert_not_called()


def test_comparison_uses_two_authorized_snapshots_and_denies_checker_partial_access(
    client, session_factory
):
    scenario = seed_operational_scenario(session_factory)
    second = seed_planning_scenario(session_factory, quantity=2)
    from app.modules.users.models import User

    with session_factory() as db:
        manager = db.query(User).filter(User.role == "LOGISTICS_MANAGER").first()
        plan = LoadPlanningService(db).create_load_plan(
            LoadPlanCreate(truck_id=second.truck_id, order_ids=[second.order_id]),
            changed_by=manager.id,
        )
        second_id = plan.id
    payload = {"message": f"Compare os planos {scenario.load_plan_id} e {second_id}"}
    response = client.post(
        "/api/v1/assistant/messages", headers=scenario.manager_headers, json=payload
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["facts"]) == 2
    assert "não prova ótimo global" in response.json()["answer"]
    denied = client.post(
        "/api/v1/assistant/messages", headers=scenario.checker_headers, json=payload
    )
    assert denied.status_code == 403
    assert "facts" not in denied.json()
