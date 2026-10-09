"""Suprime logs do transporte somente no contexto do envio sensível."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_sensitive_send: ContextVar[bool] = ContextVar("whatsapp_sensitive_send", default=False)


class _SensitiveSendFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not _sensitive_send.get()


@contextmanager
def sensitive_http_send() -> Iterator[None]:
    for name in (
        "httpx2",
        "httpcore2.connection",
        "httpcore2.http11",
        "httpcore2.http2",
        "httpcore2.proxy",
        "httpcore2.socks",
    ):
        target = logging.getLogger(name)
        if not any(isinstance(item, _SensitiveSendFilter) for item in target.filters):
            target.addFilter(_SensitiveSendFilter())
    token = _sensitive_send.set(True)
    try:
        yield
    finally:
        _sensitive_send.reset(token)
