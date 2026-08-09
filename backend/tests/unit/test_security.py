from datetime import UTC, datetime

import pytest
from passlib.context import CryptContext

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_and_update_password,
    verify_password,
)


def test_hash_password_does_not_store_plain_text() -> None:
    password_hash = hash_password("senha-local-segura")

    assert password_hash != "senha-local-segura"
    assert password_hash.startswith("$argon2id$")
    assert "m=19456,t=2,p=1" in password_hash
    assert verify_password("senha-local-segura", password_hash) is True
    assert verify_password("senha-errada", password_hash) is False


def test_verify_and_update_password_migrates_legacy_pbkdf2() -> None:
    legacy_context = CryptContext(schemes=["pbkdf2_sha256"])
    legacy_hash = legacy_context.hash("senha-local-segura")

    verified, updated_hash = verify_and_update_password(
        "senha-local-segura",
        legacy_hash,
    )

    assert verified is True
    assert updated_hash is not None
    assert updated_hash.startswith("$argon2id$")


def test_verify_password_rejects_malformed_hash() -> None:
    assert verify_password("senha-local-segura", "invalid-hash") is False


def test_create_access_token_can_be_decoded() -> None:
    token = create_access_token("user-id", {"role": "ADMIN"})

    payload = decode_access_token(token)

    assert payload["sub"] == "user-id"
    assert payload["role"] == "ADMIN"
    assert datetime.fromtimestamp(payload["exp"], UTC) > datetime.now(UTC)


def test_decode_access_token_rejects_invalid_token() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("invalid-token")
