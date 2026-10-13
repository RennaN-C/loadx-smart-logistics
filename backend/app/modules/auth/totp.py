"""RFC 4226/6238 primitives; authenticated encryption uses cryptography."""

import base64
import hmac
import secrets
import struct
from urllib.parse import quote, urlencode

from cryptography.fernet import Fernet, InvalidToken


class IdentityUnavailableError(Exception):
    pass


def cipher(key: str | None) -> Fernet:
    try:
        if not key:
            raise ValueError
        return Fernet(key.encode("ascii"))
    except ValueError:
        raise IdentityUnavailableError from None


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def encrypt_secret(secret: str, key: str | None) -> str:
    return cipher(key).encrypt(secret.encode("ascii")).decode("ascii")


def decrypt_secret(encrypted: str, key: str | None) -> str:
    try:
        return cipher(key).decrypt(encrypted.encode("ascii")).decode("ascii")
    except (InvalidToken, UnicodeError):
        raise IdentityUnavailableError from None


def totp_code(secret: str, step: int, digits: int = 6) -> str:
    # RFC 4226/6238 requires HMAC, not a standalone SHA-1 hash. SHA-1
    # collision attacks do not permit forging this keyed authenticator.
    digest = hmac.digest(base64.b32decode(secret), struct.pack(">Q", step), "sha1")
    offset = digest[-1] & 15
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % (10**digits)).zfill(digits)


def matching_step(
    secret: str, code: str, timestamp: float, last_step: int
) -> int | None:
    if not code.isascii():
        return None
    step = int(timestamp) // 30
    for candidate in (step, step - 1, step + 1):
        if (
            candidate >= 0
            and candidate > last_step
            and hmac.compare_digest(totp_code(secret, candidate), code)
        ):
            return candidate
    return None


def provisioning_uri(secret: str, email: str) -> str:
    return (
        "otpauth://totp/"
        + quote("LoadX:" + email, safe="")
        + "?"
        + urlencode(
            {
                "secret": secret,
                "issuer": "LoadX",
                "algorithm": "SHA1",
                "digits": 6,
                "period": 30,
            }
        )
    )
