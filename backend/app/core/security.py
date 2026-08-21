from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from passlib.context import CryptContext

from app.modules.users.password_policy import normalize_password

password_hasher = PasswordHasher(
    memory_cost=19_456,
    time_cost=2,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)
legacy_password_context = CryptContext(schemes=["pbkdf2_sha256"])


def hash_password(password: str) -> str:
    return password_hasher.hash(normalize_password(password))


def verify_password(password: str, password_hash: str) -> bool:
    verified, _ = verify_and_update_password(password, password_hash)
    return verified


def verify_and_update_password(
    password: str,
    password_hash: str,
) -> tuple[bool, str | None]:
    normalized_password = normalize_password(password)
    candidates = (password, normalized_password)

    for candidate in dict.fromkeys(candidates):
        if password_hash.startswith("$argon2"):
            try:
                password_hasher.verify(password_hash, candidate)
            except (InvalidHashError, VerificationError, VerifyMismatchError):
                continue
            updated_hash = (
                hash_password(normalized_password)
                if candidate != normalized_password
                or password_hasher.check_needs_rehash(password_hash)
                else None
            )
            return True, updated_hash

        try:
            verified = legacy_password_context.verify(candidate, password_hash)
        except (TypeError, ValueError):
            return False, None
        if not verified:
            continue
        return True, hash_password(normalized_password)
    return False, None
