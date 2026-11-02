"""Conversational budget must not charge busy or rejected requests."""

import uuid
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exceptions import ApiError
from app.modules.assistant import limits


def test_busy_request_does_not_charge_chat_quota(monkeypatch):
    actor = str(uuid.uuid4())
    monkeypatch.setattr(limits.time, "monotonic", lambda: 125.5)
    monkeypatch.setattr(
        limits,
        "AssistantConcurrencyRepository",
        lambda db: SimpleNamespace(try_acquire=lambda identity: False),
    )
    db = Mock()
    with pytest.raises(ApiError) as busy:
        limits.ensure_budget(db, actor, 1)
    assert busy.value.status_code == 429

    monkeypatch.setattr(
        limits,
        "AssistantConcurrencyRepository",
        lambda db: SimpleNamespace(try_acquire=lambda identity: True),
    )
    limits.ensure_budget(db, actor, 1)
    with pytest.raises(ApiError) as limited:
        limits.ensure_budget(db, actor, 1)
    assert limited.value.status_code == 429
