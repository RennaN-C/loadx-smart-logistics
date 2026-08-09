import unicodedata

PASSWORD_MIN_LENGTH = 15
PASSWORD_MAX_LENGTH = 128

_BLOCKED_PASSWORDS = frozenset(
    {
        "123456789012345",
        "adminadminadmin",
        "administrator",
        "changemechangeme",
        "letmeinletmein",
        "passwordpassword",
        "qwertyqwertyqwerty",
        "senha1234567890",
        "senhasenhasenha",
        "welcome123456789",
    }
)
_BLOCKED_CONTEXT_TERMS = ("loadx",)


class PasswordPolicyError(ValueError):
    pass


def normalize_password(password: str) -> str:
    return unicodedata.normalize("NFC", password)


def validate_password_policy(password: str) -> str:
    normalized_password = normalize_password(password)
    password_length = len(normalized_password)
    if password_length < PASSWORD_MIN_LENGTH:
        raise PasswordPolicyError(
            f"password must contain at least {PASSWORD_MIN_LENGTH} characters"
        )
    if password_length > PASSWORD_MAX_LENGTH:
        raise PasswordPolicyError(
            f"password must contain at most {PASSWORD_MAX_LENGTH} characters"
        )

    comparable_password = normalized_password.casefold()
    if comparable_password in _BLOCKED_PASSWORDS or any(
        term in comparable_password for term in _BLOCKED_CONTEXT_TERMS
    ):
        raise PasswordPolicyError("password is present in the local blocklist")
    return normalized_password
