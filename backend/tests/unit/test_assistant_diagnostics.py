import base64
import uuid
from types import SimpleNamespace

import pytest

from app.core.exceptions import ApiError
from app.modules.assistant.context import planning_context
from app.modules.assistant.schemas import ChatRequest
from app.modules.load_planning.assistant_diagnostics import (
    TTL_SECONDS,
    issue_capacity_diagnostic,
    read_capacity_diagnostic,
)


def user(role="ADMIN"):
    return SimpleNamespace(id=uuid.uuid4(), role=role, active=True)


def receipt(actor):
    return issue_capacity_diagnostic(
        actor.id,
        [
            {
                "remaining_volumes": [
                    {
                        "order_item_id": str(uuid.uuid4()),
                        "volume_index": 0,
                        "reasons": ["COLLISION", "COLLISION", "private-injected-text"],
                    }
                ],
                "ineligible_trucks": [
                    {"truck_id": str(uuid.uuid4()), "reason": "private"}
                ],
            }
        ],
    )


def test_signed_attempt_preserves_exact_reason_without_private_identifiers():
    actor = user()
    token = receipt(actor)
    value = read_capacity_diagnostic(token, actor)
    assert value.remaining_volumes == 1
    assert value.unavailable_trucks == 1
    assert value.reasons == {"COLLISION": 1}
    assert receipt(actor) != token
    encoded = base64.urlsafe_b64decode(token.split(".")[0] + "==").decode()
    assert "private" not in encoded
    assert "order_item_id" not in encoded
    assert "truck_id" not in encoded
    facts, links = planning_context(
        None, actor, ChatRequest(message="Por que falhou?", diagnostic_token=token)
    )
    assert facts[0].values["COLLISION"] == 1
    assert "sem sobrepor volumes" in facts[0].criteria
    assert "Nenhum plano parcial foi salvo" in facts[0].criteria
    assert not links


@pytest.mark.parametrize(
    "case", ["tamper", "other_actor", "expired", "malformed", "unicode"]
)
def test_untrusted_or_expired_diagnostic_fails_closed(case, monkeypatch):
    actor = user()
    token = receipt(actor)
    if case == "tamper":
        token = token[:-1] + ("0" if token[-1] != "0" else "1")
    if case == "other_actor":
        actor = user()
    if case == "expired":
        import time

        now = time.time()
        monkeypatch.setattr(
            "app.modules.load_planning.assistant_diagnostics.time.time",
            lambda: now + TTL_SECONDS,
        )
    if case == "malformed":
        token = "client-asserted-COLLISION"
    if case == "unicode":
        token = "abc.💥"
    with pytest.raises(ApiError) as caught:
        read_capacity_diagnostic(token, actor)
    assert caught.value.code == "ASSISTANT_DIAGNOSTIC_INVALID"


def test_checker_cannot_read_manager_attempt():
    actor = user()
    token = receipt(actor)
    actor.role = "CHECKER"
    with pytest.raises(ApiError) as caught:
        read_capacity_diagnostic(token, actor)
    assert caught.value.status_code == 403
