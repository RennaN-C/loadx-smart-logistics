from datetime import UTC, datetime

import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_store_plain_text() -> None:
    password_hash = hash_password("senha-local")

    assert password_hash != "senha-local"
    assert verify_password("senha-local", password_hash) is True
    assert verify_password("senha-errada", password_hash) is False


def test_create_access_token_can_be_decoded() -> None:
    token = create_access_token("user-id", {"role": "ADMIN"})

    payload = decode_access_token(token)

    assert payload["sub"] == "user-id"
    assert payload["role"] == "ADMIN"
    assert datetime.fromtimestamp(payload["exp"], UTC) > datetime.now(UTC)


def test_decode_access_token_rejects_invalid_token() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("invalid-token")
