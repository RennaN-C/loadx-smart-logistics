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
    minute = int(time.monotonic() // 60)
    with _lock:
        previous_minute, count = _buckets.pop(actor, (minute, 0))
        count = count if previous_minute == minute else 0
        _buckets[actor] = (minute, count + 1)
        while len(_buckets) > 4096:
            _buckets.popitem(last=False)
        if count >= limit:
            raise ApiError(
                429,
                "ASSISTANT_RATE_LIMITED",
                "Aguarde um minuto antes de perguntar novamente.",
                headers={"Retry-After": "60"},
            )
    if not AssistantConcurrencyRepository(db).try_acquire(actor):
        raise ApiError(
            429,
            "ASSISTANT_BUSY",
            "Sua pergunta anterior ainda está sendo processada.",
            headers={"Retry-After": "2"},
        )
