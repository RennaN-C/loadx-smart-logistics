import uuid

import pytest

from tests.integration.test_deliveries_api import seed_operational_scenario
from tests.integration.test_loading_authorization import (
    ALL_ROLES,
    _check_all_items,
    _create_loading,
    _headers_for_role,
    _start_loading,
)


def _scan(client, scenario, loading, code=None, headers=None):
    return client.post(
        f"/api/v1/loading-sessions/{loading['id']}/scan",
        json={"code": code or loading["items"][0]["code"]},
        headers=scenario.checker_headers if headers is None else headers,
    )


def test_scan_valid_duplicate_missing_and_invalid(client, session_factory):
    scenario = seed_operational_scenario(session_factory)
    loading = _create_loading(client, scenario)
    _start_loading(client, scenario, loading)
    response = _scan(client, scenario, loading)
    assert response.status_code == 200
    result = response.json()
    item_id = loading["items"][0]["id"]
    assert (
        next(item for item in result["items"] if item["id"] == item_id)["status"]
        == "CHECKED"
    )
    assert sum(item["status"] == "CHECKED" for item in result["items"]) == 1
    assert result["status"] == "IN_PROGRESS"
    duplicate = _scan(client, scenario, loading)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "LOADING_ITEM_ALREADY_CHECKED"
    missing = _scan(client, scenario, loading, f"loadx:loading-item:{uuid.uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "LOADING_ITEM_NOT_FOUND"
    invalid = _scan(client, scenario, loading, "invalid")
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "VALIDATION_ERROR"
    assert (
        client.get(
            f"/api/v1/loading-sessions/{loading['id']}",
            headers=scenario.checker_headers,
        ).json()
        == result
    )


@pytest.mark.parametrize("state", ["PENDING", "FINISHED"])
def test_scan_requires_in_progress(client, session_factory, state):
    scenario = seed_operational_scenario(session_factory)
    loading = _create_loading(client, scenario)
    if state == "FINISHED":
        _start_loading(client, scenario, loading)
        _check_all_items(client, scenario, loading)
        assert (
            client.patch(
                f"/api/v1/loading-sessions/{loading['id']}/status",
                json={"status": "FINISHED"},
                headers=scenario.checker_headers,
            ).status_code
            == 200
        )
    response = _scan(client, scenario, loading)
    assert response.status_code == 409
    assert response.json()["code"] == "LOADING_STATUS_TRANSITION_NOT_ALLOWED"


def test_scan_rejects_other_session_and_missing_session(client, session_factory):
    first = seed_operational_scenario(session_factory)
    second = seed_operational_scenario(session_factory)
    loading = _create_loading(client, first)
    other = _create_loading(client, second)
    _start_loading(client, first, loading)
    response = _scan(client, first, loading, other["items"][0]["code"])
    assert response.status_code == 409
    assert response.json()["code"] == "LOADING_ITEM_SESSION_MISMATCH"
    response = _scan(client, first, {**loading, "id": str(uuid.uuid4())})
    assert response.status_code == 404
    assert response.json()["code"] == "LOADING_SESSION_NOT_FOUND"
    result = client.get(
        f"/api/v1/loading-sessions/{loading['id']}", headers=first.checker_headers
    ).json()
    assert all(item["status"] == "PENDING" for item in result["items"])


@pytest.mark.parametrize("role", ALL_ROLES)
def test_scan_rbac_before_lookup(client, session_factory, role):
    scenario = seed_operational_scenario(session_factory)
    loading = _create_loading(client, scenario)
    _start_loading(client, scenario, loading)
    response = _scan(
        client, scenario, loading, headers=_headers_for_role(scenario, role)
    )
    assert response.status_code == (200 if role == "CHECKER" else 403)
    if role != "CHECKER":
        response = _scan(
            client,
            scenario,
            {**loading, "id": str(uuid.uuid4())},
            headers=_headers_for_role(scenario, role),
        )
        assert response.status_code == 403
        assert response.json()["code"] == "AUTH_FORBIDDEN"


def test_scan_authentication_and_csrf(client, session_factory):
    scenario = seed_operational_scenario(session_factory)
    loading = _create_loading(client, scenario)
    _start_loading(client, scenario, loading)
    assert _scan(client, scenario, loading, headers={}).status_code == 401
    headers = {
        key: value
        for key, value in scenario.checker_headers.items()
        if key.lower() != "x-csrf-token"
    }
    assert _scan(client, scenario, loading, headers=headers).status_code == 403
