import uuid
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from tests.integration.test_deliveries_api import (
    OperationalScenario,
    seed_operational_scenario,
)

ALL_ROLES = ("ADMIN", "LOGISTICS_MANAGER", "CHECKER", "DRIVER")


@dataclass(frozen=True)
class LoadingAuthorizationCase:
    name: str
    allowed_roles: frozenset[str]


LOADING_AUTHORIZATION_CASES = (
    LoadingAuthorizationCase(
        "read", frozenset({"ADMIN", "LOGISTICS_MANAGER", "CHECKER"})
    ),
    LoadingAuthorizationCase("create", frozenset({"LOGISTICS_MANAGER"})),
    LoadingAuthorizationCase("start", frozenset({"CHECKER"})),
    LoadingAuthorizationCase("check_item", frozenset({"CHECKER"})),
    LoadingAuthorizationCase("finish", frozenset({"CHECKER"})),
)


def _headers_for_role(scenario: OperationalScenario, role: str) -> dict[str, str]:
    return {
        "ADMIN": scenario.admin_headers,
        "LOGISTICS_MANAGER": scenario.manager_headers,
        "CHECKER": scenario.checker_headers,
        "DRIVER": scenario.driver_headers,
    }[role]


def _create_loading(
    client: TestClient, scenario: OperationalScenario
) -> dict[str, object]:
    response = client.post(
        "/api/v1/loading-sessions",
        json={"load_plan_id": str(scenario.load_plan_id)},
        headers=scenario.manager_headers,
    )
    assert response.status_code == 201
    return response.json()


def _start_loading(
    client: TestClient,
    scenario: OperationalScenario,
    loading: dict[str, object],
) -> None:
    response = client.patch(
        f"/api/v1/loading-sessions/{loading['id']}/status",
        json={"status": "IN_PROGRESS"},
        headers=scenario.checker_headers,
    )
    assert response.status_code == 200


def _check_all_items(
    client: TestClient,
    scenario: OperationalScenario,
    loading: dict[str, object],
) -> None:
    for item in loading["items"]:
        response = client.patch(
            f"/api/v1/loading-sessions/{loading['id']}/items/{item['id']}",
            json={"status": "CHECKED"},
            headers=scenario.checker_headers,
        )
        assert response.status_code == 200


def _request_operation(
    client: TestClient,
    scenario: OperationalScenario,
    case: LoadingAuthorizationCase,
    role: str,
):
    headers = _headers_for_role(scenario, role)
    if case.name == "create":
        return client.post(
            "/api/v1/loading-sessions",
            json={"load_plan_id": str(scenario.load_plan_id)},
            headers=headers,
        )

    loading = _create_loading(client, scenario)
    if case.name == "read":
        return client.get(f"/api/v1/loading-sessions/{loading['id']}", headers=headers)
    if case.name == "start":
        return client.patch(
            f"/api/v1/loading-sessions/{loading['id']}/status",
            json={"status": "IN_PROGRESS"},
            headers=headers,
        )

    _start_loading(client, scenario, loading)
    if case.name == "check_item":
        item = loading["items"][0]
        return client.patch(
            f"/api/v1/loading-sessions/{loading['id']}/items/{item['id']}",
            json={"status": "CHECKED"},
            headers=headers,
        )

    _check_all_items(client, scenario, loading)
    return client.patch(
        f"/api/v1/loading-sessions/{loading['id']}/status",
        json={"status": "FINISHED"},
        headers=headers,
    )


@pytest.mark.parametrize("role", ALL_ROLES)
@pytest.mark.parametrize(
    "case", LOADING_AUTHORIZATION_CASES, ids=lambda case: case.name
)
def test_loading_authorization_matrix(
    client: TestClient,
    session_factory,
    case: LoadingAuthorizationCase,
    role: str,
) -> None:
    scenario = seed_operational_scenario(session_factory)

    response = _request_operation(client, scenario, case, role)

    if role in case.allowed_roles:
        assert response.status_code in {200, 201}
    else:
        assert response.status_code == 403
        assert response.json() == {
            "code": "AUTH_FORBIDDEN",
            "message": "Usuário sem permissão para esta ação.",
            "details": [],
        }


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    (
        ("POST", "/api/v1/loading-sessions", {"load_plan_id": str(uuid.uuid4())}),
        ("GET", f"/api/v1/loading-sessions/{uuid.uuid4()}", None),
        (
            "PATCH",
            f"/api/v1/loading-sessions/{uuid.uuid4()}/status",
            {"status": "IN_PROGRESS"},
        ),
        (
            "PATCH",
            f"/api/v1/loading-sessions/{uuid.uuid4()}/items/{uuid.uuid4()}",
            {"status": "CHECKED"},
        ),
    ),
    ids=("create", "read", "status", "item"),
)
def test_loading_anonymous_access_returns_401(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, str] | None,
) -> None:
    response = client.request(method, path, json=payload)

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.parametrize(
    ("role", "method", "path_suffix", "payload"),
    (
        (
            "CHECKER",
            "POST",
            "",
            {"load_plan_id": str(uuid.uuid4())},
        ),
        ("DRIVER", "GET", f"/{uuid.uuid4()}", None),
        (
            "LOGISTICS_MANAGER",
            "PATCH",
            f"/{uuid.uuid4()}/status",
            {"status": "IN_PROGRESS"},
        ),
        (
            "LOGISTICS_MANAGER",
            "PATCH",
            f"/{uuid.uuid4()}/items/{uuid.uuid4()}",
            {"status": "CHECKED"},
        ),
    ),
    ids=("create", "read", "status", "item"),
)
def test_loading_forbidden_access_does_not_reveal_object_existence(
    client: TestClient,
    session_factory,
    role: str,
    method: str,
    path_suffix: str,
    payload: dict[str, str] | None,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    response = client.request(
        method,
        f"/api/v1/loading-sessions{path_suffix}",
        json=payload,
        headers=_headers_for_role(scenario, role),
    )

    assert response.status_code == 403
    assert response.json() == {
        "code": "AUTH_FORBIDDEN",
        "message": "Usuário sem permissão para esta ação.",
        "details": [],
    }
