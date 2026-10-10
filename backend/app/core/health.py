"""Sinal de liveness compartilhado, sem consulta externa."""


def liveness_status() -> dict[str, str]:
    return {"status": "ok", "service": "loadx-api"}
