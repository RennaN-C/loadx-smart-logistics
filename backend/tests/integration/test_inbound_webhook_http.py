import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.config import Settings
from app.integrations.external_commands import (
    BoundExternalActorResolver,
    HmacExternalAuthenticator,
    TrustedIntegration,
)
from app.integrations.inbound_webhook import InboundWebhookRuntime
from app.main import create_app
from app.modules.external_commands.models import ExternalCommand
from app.modules.external_commands.repository import ExternalCommandRepository
from app.modules.external_commands.schemas import CommandName
from app.modules.users.models import User
from tests.integration.test_external_commands import Scenario, scenario
from tests.unit.test_external_command_validation import KEY, NOW, sign

__all__ = ("scenario",)
PATH = "/api/v1/webhooks/controlled-events"


def http_client(scenario: Scenario, actor="manager", **kwargs):
    app = create_app()
    app.state.inbound_webhook = InboundWebhookRuntime(scenario.service(actor, **kwargs))
    return TestClient(app)


def post(client, body, signature=None):
    return client.post(
        PATH,
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-LoadX-Signature": signature if signature is not None else sign(body),
        },
    )


def test_http_receipt_restart_and_current_expiry(scenario):
    body = scenario.body()
    before = scenario.counts()
    with http_client(scenario) as client:
        response = post(client, body)
        assert response.status_code == 200
        assert response.json()["duplicate"] is False
    # A fresh application/runtime and pool observe the persisted PostgreSQL identity.
    with http_client(scenario) as restarted:
        duplicate = post(restarted, body)
        assert duplicate.json() == {**response.json(), "duplicate": True}
    with http_client(scenario, clock=lambda: NOW + timedelta(minutes=5)) as client:
        assert post(client, body).status_code == 410
    assert scenario.counts() == ("DELIVERED", before[1] + 1, 1)


@pytest.mark.parametrize("actor", ["inactive", "checker", "unlinked", "other_driver"])
def test_http_actor_cannot_bypass_authorization(scenario, actor):
    before = scenario.counts()
    with http_client(scenario, actor) as client:
        response = post(client, scenario.body())
        assert response.status_code == 403
        assert response.json()["code"] == "EXTERNAL_COMMAND_FORBIDDEN"
    assert scenario.counts() == before


@pytest.mark.parametrize("restriction", ["binding", "capability"])
def test_http_requires_binding_and_capability(scenario, restriction):
    before = scenario.counts()
    with http_client(scenario) as client:
        commands = client.app.state.inbound_webhook.commands
        if restriction == "binding":
            commands.actor_resolver = BoundExternalActorResolver({})
        else:
            from pydantic import SecretBytes

            commands.authenticator = HmacExternalAuthenticator(
                TrustedIntegration("fixture", frozenset({CommandName.START_TRIP})),
                SecretBytes(KEY),
            )
        assert post(client, scenario.body()).status_code == 403
    assert scenario.counts() == before


def test_http_collision_and_revalidation(scenario):
    body = scenario.body()
    with http_client(scenario) as client:
        assert post(client, body).status_code == 200
        before = scenario.counts()
        assert post(client, body + b" ").status_code == 409
    with http_client(scenario, "driver") as client:
        assert post(client, body).status_code == 409
    with scenario.factory() as db:
        db.get(User, scenario.actors["manager"]).active = False
        db.commit()
    with http_client(scenario) as client:
        assert post(client, body).status_code == 403
    assert scenario.counts() == before


def test_http_failure_after_domain_commit_rolls_back_then_retries(
    scenario, monkeypatch
):
    body = scenario.body()
    before = scenario.counts()

    def fail(*args, **kwargs):
        raise RuntimeError("sensitive-provider-payload")

    with http_client(scenario) as client:
        with monkeypatch.context() as patcher:
            patcher.setattr(ExternalCommandRepository, "complete", fail)
            failed = post(client, body)
        assert failed.status_code == 500
        assert failed.json()["code"] == "EXTERNAL_PROCESSING_FAILED"
        assert scenario.counts() == before
        assert post(client, body).json()["duplicate"] is False
        # A different valid identity cannot bypass invalid current domain state.
        assert (
            post(
                client, scenario.body(event_id="out-of-order", command="START_DELIVERY")
            ).status_code
            == 409
        )
    assert scenario.counts() == ("DELIVERED", before[1] + 1, 1)


def test_two_http_requests_execute_once(scenario, monkeypatch):
    body = scenario.body()
    before = scenario.counts()
    barrier = Barrier(2)
    original = ExternalCommandRepository.claim

    def together(repository, **kwargs):
        barrier.wait(timeout=10)
        return original(repository, **kwargs)

    monkeypatch.setattr(ExternalCommandRepository, "claim", together)
    with http_client(scenario) as client, ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: post(client, body), range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    receipts = [response.json() for response in responses]
    assert receipts[0]["id"] == receipts[1]["id"]
    assert sorted(receipt["duplicate"] for receipt in receipts) == [False, True]
    assert scenario.counts() == ("DELIVERED", before[1] + 1, 1)


def test_http_signature_and_privacy_no_domain_access(scenario, caplog):
    body = scenario.body()
    before = scenario.counts()
    with (
        http_client(scenario) as client,
        caplog.at_level(logging.INFO, logger="loadx.security"),
    ):
        assert post(client, body, "0" * 64).status_code == 401
        response = post(client, body)
        assert response.status_code == 200
    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "loadx.security"
    ]
    completed = next(
        event for event in events if event["event"] == "EXTERNAL_COMMAND_COMPLETED"
    )
    assert completed["correlation_id"] == response.headers["x-request-id"]
    assert set(response.json()) == {"id", "duplicate"}
    for sensitive in ("fixture-event", "fixture-subject", body.decode(), sign(body)):
        assert sensitive not in caplog.text + response.text
    assert scenario.counts() == ("DELIVERED", before[1] + 1, 1)


def test_production_composition_preserves_namespace_and_bound_actor(scenario):
    settings = Settings(
        app_env="local",
        _env_file=None,
        database_url=scenario.factory.kw["bind"].url.render_as_string(
            hide_password=False
        ),
        inbound_webhook_enabled=True,
        inbound_webhook_signing_key=KEY,
        inbound_webhook_bindings=json.dumps(
            {"fixture-subject": str(scenario.actors["manager"])}
        ),
        inbound_webhook_capabilities='["FINISH_DELIVERY"]',
    )
    app = create_app(settings)
    app.state.inbound_webhook.commands.clock = lambda: NOW
    with app.state.inbound_webhook.commands.session_factory() as db:
        assert db.scalar(text("SHOW statement_timeout")) == "5s"
        assert db.scalar(text("SHOW lock_timeout")) == "2s"
    with TestClient(app) as client:
        response = post(client, scenario.body())
        assert response.status_code == 200
    with scenario.factory() as db:
        row = db.scalar(
            select(ExternalCommand).where(
                ExternalCommand.user_id == scenario.actors["manager"]
            )
        )
        assert row.integration_id == "loadx-controlled-webhook"
