from unittest.mock import Mock

import pytest

from scripts import emit_inbound


@pytest.mark.parametrize(
    "arguments",
    [
        ["--url", "https://outside.invalid/api/v1/webhooks/controlled-events"],
        ["--port", "0"],
        ["--port", "65536"],
        ["--port", "not-a-port"],
        ["--port", "8000@outside.invalid"],
    ],
)
def test_emitter_rejects_url_or_invalid_port_before_network(
    arguments, tmp_path, monkeypatch
):
    opener = Mock(side_effect=AssertionError("no network permitted"))
    monkeypatch.setattr(emit_inbound, "build_opener", opener)
    monkeypatch.setattr(
        "sys.argv",
        ["emit_inbound", "--event-file", str(tmp_path / "event.json"), *arguments],
    )
    with pytest.raises(SystemExit) as error:
        emit_inbound.main()
    assert error.value.code == 2
    opener.assert_not_called()


def test_emitter_does_not_publish_unknown_response_content():
    with pytest.raises(ValueError, match="unknown error code"):
        emit_inbound.public_result(401, b'{"code":"sensitive-response"}')
    with pytest.raises(ValueError, match="invalid result"):
        emit_inbound.public_result(
            200, b'{"id":"00000000-0000-4000-8000-000000000001","duplicate":"secret"}'
        )
