from unittest.mock import Mock

from app.main import app
from app.modules.notifications import worker


def test_outbox_openapi_has_admin_actions_and_sanitized_contracts():
    schema = app.openapi()
    for suffix, method in [
        ("", "get"),
        ("/summary", "get"),
        ("/{event_id}", "get"),
        ("/{event_id}/attempts", "get"),
        ("/{event_id}/source", "get"),
        ("/{event_id}/retry", "post"),
    ]:
        operation = schema["paths"]["/api/v1/outbox-events" + suffix][method]
        assert {"401", "403", "404", "409", "422", "500"} <= operation[
            "responses"
        ].keys()
        assert operation["security"]
    event = schema["components"]["schemas"]["EventRead"]["properties"]
    assert {
        "id",
        "notification_id",
        "status",
        "generation",
        "last_error_code",
    } <= event.keys()
    assert (
        not {"payload", "phone", "content", "idempotency_key", "token"} & event.keys()
    )
    request = schema["components"]["schemas"]["RetryRequest"]
    assert request["additionalProperties"] is False
    assert request["required"] == ["command_id"]


def test_worker_lifecycle_waits_on_idle_errors_and_disposes_on_shutdown(monkeypatch):
    stop = Mock()
    stop.is_set.side_effect = [False, False, False, True]
    engine = Mock()
    signal = Mock()
    processor = Mock(side_effect=[False, True, RuntimeError("secret")])
    monkeypatch.setattr(worker.threading, "Event", lambda: stop)
    monkeypatch.setattr(worker.signal, "signal", signal)
    monkeypatch.setattr(worker, "create_engine", Mock(return_value=engine))
    monkeypatch.setattr(worker, "sessionmaker", Mock(return_value=Mock()))
    monkeypatch.setattr(worker, "process_one", processor)
    worker.main()
    assert processor.call_count == 3
    assert stop.wait.call_count == 2
    engine.dispose.assert_called_once()
    assert signal.call_count == 2
    signal.call_args_list[0].args[1](15, None)
    stop.set.assert_called_once()
