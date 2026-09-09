import json

import pytest

from app.core.responses import error_response


@pytest.mark.parametrize(
    ("details", "expected_details"),
    [
        (None, []),
        ([], []),
        ([{"field": "email"}], [{"field": "email"}]),
    ],
)
def test_error_response_builds_standard_envelope(
    details: list[object] | None,
    expected_details: list[object],
) -> None:
    response = error_response(
        status_code=409,
        code="USER_EMAIL_ALREADY_EXISTS",
        message="Já existe um usuário cadastrado com este e-mail.",
        details=details,
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "code": "USER_EMAIL_ALREADY_EXISTS",
        "message": "Já existe um usuário cadastrado com este e-mail.",
        "details": expected_details,
    }
