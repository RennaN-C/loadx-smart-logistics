"""Bounded per-process budget plus cross-worker PostgreSQL concurrency guard."""

import time
from collections import OrderedDict
from threading import Lock

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.modules.assistant.repository import AssistantConcurrencyRepository

_buckets: OrderedDict[str, tuple[int, int]] = OrderedDict()
_lock = Lock()


def ensure_budget(db: Session, actor: str, limit: int) -> None:
    # A rejected concurrent request must not consume the user's conversational quota.
    if not AssistantConcurrencyRepository(db).try_acquire(actor):
        raise ApiError(
            429,
            "ASSISTANT_BUSY",
            "Sua pergunta anterior ainda está sendo processada.",
            headers={"Retry-After": "2"},
        )
    minute = int(time.monotonic() // 60)
    with _lock:
        previous_minute, count = _buckets.pop(actor, (minute, 0))
        count = count if previous_minute == minute else 0
        if count >= limit:
            # Failed requests do not consume additional quota either.
            _buckets[actor] = (minute, count)
            raise ApiError(
                429,
                "ASSISTANT_RATE_LIMITED",
                "O limite temporário de perguntas foi atingido.",
                headers={"Retry-After": str(max(1, 60 - int(time.monotonic() % 60)))},
            )
        _buckets[actor] = (minute, count + 1)
        while len(_buckets) > 4096:
            _buckets.popitem(last=False)
