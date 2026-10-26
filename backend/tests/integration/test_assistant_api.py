"""Real PostgreSQL, session/CSRF and persisted metrics; external Groq is not called."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.modules.assistant.limits import ensure_budget
from app.modules.assistant.schemas import ToolArguments
from app.modules.reports.assistant_service import AssistantMetricsService
from app.modules.users.models import User
from tests.integration.test_deliveries_api import create_trip, seed_operational_scenario
from tests.integration.test_messages_api import finish_loading


def test_chat_auth_csrf_context_and_honest_fallback(client, session_factory):
    scenario = seed_operational_scenario(session_factory)
    path = "/api/v1/assistant/messages"
    payload = {"message": "Por que não coube?", "plan_id": str(scenario.load_plan_id)}
    assert client.post(path, json=payload).status_code == 401
    assert (
        client.post(path, json=payload, headers=scenario.driver_headers).status_code
        == 403
    )
    headers = {
        k: v for k, v in scenario.manager_headers.items() if k.lower() != "x-csrf-token"
    }
    assert client.post(path, json=payload, headers=headers).status_code == 403
    response = client.post(path, json=payload, headers=scenario.checker_headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["source"] == "FALLBACK"
    assert result["facts"][0]["name"] == "Plano autorizado"
    assert result["links"][0]["href"] == f"/planning/{scenario.load_plan_id}"
    assert str(scenario.driver_id) not in str(result["facts"])
    assert (
        client.post(
            path,
            json={"message": "Consulte", "plan_id": str(uuid.uuid4())},
            headers=scenario.manager_headers,
        ).status_code
        == 404
    )


def test_checker_denied_unapproved_plan(client, session_factory):
    from app.modules.load_planning.models import LoadPlan

    scenario = seed_operational_scenario(session_factory)
    with session_factory() as db:
        plan = db.get(LoadPlan, scenario.load_plan_id)
        plan.status = "CALCULATED"
        plan.approved_at = None
        db.commit()
    result = client.post(
        "/api/v1/assistant/messages",
        json={"message": "Explique", "plan_id": str(scenario.load_plan_id)},
        headers=scenario.checker_headers,
    )
    assert result.status_code == 403


def test_metrics_read_real_orders_and_expedition_without_using_creation_date(
    client, session_factory
):
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    now = datetime.now(UTC)
    args = ToolArguments(
        start=now - timedelta(days=1),
        end=now + timedelta(days=1),
        customer="Cliente Operacional",
    )
    with session_factory() as db:
        user = db.query(User).filter(User.role == "LOGISTICS_MANAGER").first()
        service = AssistantMetricsService(db)
        orders = service.query(user, "get_customer_order_metrics", args)
        assert sum(orders.values.values()) == len(scenario.order_ids)
        assert (
            service.query(user, "get_delivery_metrics", args).values[
                "dispatched_orders"
            ]
            == 0
        )
    finish_loading(client, scenario)
    started = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        headers=scenario.manager_headers,
        json={"status": "IN_ROUTE"},
    )
    assert started.status_code == 200, started.text
    with session_factory() as db:
        user = db.query(User).filter(User.role == "LOGISTICS_MANAGER").first()
        service = AssistantMetricsService(db)
        facts = service.query(user, "get_delivery_metrics", args)
        assert facts.values["dispatched_orders"] == len(scenario.order_ids)
        assert facts.values["fully_delivered_orders"] == 0
        fleet = service.query(user, "get_fleet_utilization", args)
        assert fleet.values["distinct_trucks_used"] == 1
        assert fleet.values["trips_started"] == 1
        checker = db.query(User).filter(User.role == "CHECKER").first()
        with pytest.raises(ApiError):
            service.query(checker, "get_delivery_metrics", args)


def test_cross_worker_lock_and_per_process_budget(postgres_engine):
    actor = str(uuid.uuid4())
    with Session(postgres_engine) as first, Session(postgres_engine) as second:
        ensure_budget(first, actor, 30)
        with pytest.raises(ApiError) as caught:
            ensure_budget(second, actor, 30)
        assert caught.value.code == "ASSISTANT_BUSY"
        first.rollback()
        ensure_budget(second, actor, 30)
    with Session(postgres_engine) as db:
        actor = str(uuid.uuid4())
        ensure_budget(db, actor, 1)
        with pytest.raises(ApiError) as caught:
            ensure_budget(db, actor, 1)
        assert caught.value.status_code == 429


def test_multi_truck_partial_delivery_never_counts_as_complete_or_duplicates_orders(
    client, session_factory
):
    from tests.integration.oc90_helpers import seed_multi_flow

    flow = seed_multi_flow(client, session_factory)
    flow.approve()
    flow.prepare_loadings()
    for index in range(2):
        flow.finish_loading(index)
    flow.trips = [flow.create_trip(index) for index in range(2)]
    for index in range(2):
        flow.trip_status(index, "IN_ROUTE")
    now = datetime.now(UTC)
    args = ToolArguments(start=now - timedelta(days=1), end=now + timedelta(days=1))

    def query(name):
        with session_factory() as db:
            return (
                AssistantMetricsService(db)
                .query(db.get(User, flow.manager_id), name, args)
                .values
            )

    assert query("get_delivery_metrics")["dispatched_orders"] == 1
    assert query("get_fleet_utilization")["distinct_trucks_used"] == 2
    flow.complete_delivery(0)
    partial = query("get_delivery_metrics")
    assert partial["fully_delivered_orders"] == 0
    assert partial["completed_delivery_legs"] == 1
    flow.complete_delivery(1)
    completed = query("get_delivery_metrics")
    assert completed["fully_delivered_orders"] == 1
    assert completed["dispatched_orders"] == 1
    assert completed["completed_delivery_legs"] == 2


def test_chat_tool_loop_queries_postgresql_without_exposing_personal_data(
    client, session_factory, monkeypatch
):
    from app.modules.assistant.service import GroqProvider

    scenario = seed_operational_scenario(session_factory)
    complete = Mock(
        side_effect=[
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_read",
                        "type": "function",
                        "function": {
                            "name": "get_customer_order_metrics",
                            "arguments": '{"customer":"cliente operacional"}',
                        },
                    }
                ],
            },
            {
                "role": "assistant",
                "content": "Consulte os pedidos por situação nos fatos do sistema.",
            },
        ]
    )
    monkeypatch.setattr(GroqProvider, "complete", complete)
    response = client.post(
        "/api/v1/assistant/messages",
        headers=scenario.manager_headers,
        json={"message": "Quantos pedidos o cliente operacional fez?"},
    )
    assert response.status_code == 200, response.text
    values = response.json()["facts"][0]["values"]
    assert sum(values.values()) == len(scenario.order_ids)
    assert response.json()["source"] == "GROQ"
    assert complete.call_count == 2
    assert scenario.driver_id.hex not in str(complete.call_args)
    assert "document" not in str(complete.call_args).lower()


def test_customer_normalization_exact_match_and_no_wildcard_expansion(session_factory):
    from app.modules.customers.models import Customer
    from app.modules.reports.assistant_repository import AssistantMetricsRepository

    seed_operational_scenario(session_factory)
    with session_factory() as db:
        customer = db.query(Customer).first()
        customer.name = "  Cliente Ópera  "
        db.flush()
        repository = AssistantMetricsRepository(db)
        assert repository.customers("cliente opera")[0].id == customer.id
        assert repository.customers("%_") == []
