import base64

import pytest
from cryptography.fernet import Fernet

from app.modules.auth.totp import (
    IdentityUnavailableError,
    decrypt_secret,
    encrypt_secret,
    matching_step,
    totp_code,
)

SECRET = base64.b32encode(b"12345678901234567890").decode()


@pytest.mark.parametrize(
    "timestamp,expected",
    [
        (59, "94287082"),
        (1111111109, "07081804"),
        (1111111111, "14050471"),
        (1234567890, "89005924"),
        (2000000000, "69279037"),
        (20000000000, "65353130"),
    ],
)
def test_rfc6238_sha1_vectors(timestamp, expected):
    assert totp_code(SECRET, timestamp // 30, digits=8) == expected


def test_controlled_window_and_replay():
    code = totp_code(SECRET, 100)
    assert matching_step(SECRET, code, 3030, 99) == 100
    assert matching_step(SECRET, code, 3030, 100) is None
    assert matching_step(SECRET, code, 3090, 99) is None
    assert matching_step(SECRET, "wrong!", 3000, -1) is None


def test_authenticated_encryption_has_no_plaintext_fallback():
    key = Fernet.generate_key().decode()
    encrypted = encrypt_secret(SECRET, key)
    assert SECRET not in encrypted
    assert decrypt_secret(encrypted, key) == SECRET
    for bad_key in (None, "invalid", Fernet.generate_key().decode()):
        with pytest.raises(IdentityUnavailableError):
            decrypt_secret(encrypted, bad_key)
    with pytest.raises(IdentityUnavailableError):
        decrypt_secret(encrypted[:-2] + "aa", key)
