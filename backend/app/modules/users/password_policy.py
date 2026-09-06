import unicodedata
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

PASSWORD_MIN_LENGTH = 15
PASSWORD_MAX_LENGTH = 128

_BLOCKED_PASSWORDS = frozenset(
    {
        "000000000000000",
        "111111111111111",
        "123456789012345",
        "123456789123456",
        "12345678987654321",
        "abcdefghijklmnop",
        "admin1234567890",
        "adminadminadmin",
        "administrator",
        "administrator123",
        "asdfghjklasdfgh",
        "changeme123456789",
        "changemechangeme",
        "dragon123456789",
        "footballfootball",
        "iloveyou123456",
        "iloveyouiloveyou",
        "letmein123456789",
        "letmeinletmein",
        "monkey123456789",
        "p@ssw0rdp@ssw0rd",
        "passw0rdpassw0rd",
        "password123456",
        "password123456789",
        "passwordpassword",
        "princessprincess",
        "qwertyuiopasdfgh",
        "qwertyqwertyqwerty",
        "senha123456789",
        "senha1234567890",
        "senhaforte123456",
        "senhasenhasenha",
        "sunshinesunshine",
        "trustno1trustno1",
        "welcome12345678",
        "welcome123456789",
    }
)
_BLOCKED_CONTEXT_PASSWORDS = frozenset(
    {
        "adminloadx123456",
        "loadx1234567890",
        "loadxadmin123456",
        "loadxloadxloadx",
        "sistemaloadx12345",
    }
)
BLOCKLIST_MAX_BYTES = 5 * 1024 * 1024
BLOCKLIST_MAX_ENTRIES = 100_000


class PasswordPolicyError(ValueError):
    pass


class PasswordBlocklistConfigurationError(RuntimeError):
    pass


def normalize_password(password: str) -> str:
    return unicodedata.normalize("NFC", password)


@lru_cache(maxsize=4)
def load_additional_password_blocklist(path: Path) -> frozenset[str]:
    try:
        if path.stat().st_size > BLOCKLIST_MAX_BYTES:
            raise PasswordBlocklistConfigurationError(
                "password blocklist exceeds the 5 MiB limit"
            )
        entries: set[str] = set()
        with path.open(encoding="utf-8") as blocklist_file:
            for raw_line in blocklist_file:
                value = raw_line.rstrip("\r\n")
                if not value or value.lstrip().startswith("#"):
                    continue
                entries.add(normalize_password(value).casefold())
                if len(entries) > BLOCKLIST_MAX_ENTRIES:
                    raise PasswordBlocklistConfigurationError(
                        "password blocklist exceeds the 100000 entry limit"
                    )
    except (OSError, UnicodeError) as error:
        raise PasswordBlocklistConfigurationError(
            "password blocklist could not be read as UTF-8"
        ) from error
    return frozenset(entries)


def validate_password_policy(
    password: str,
    *,
    additional_blocklist_path: Path | None = None,
) -> str:
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
    configured_path = additional_blocklist_path or settings.password_blocklist_path
    additional_blocklist = (
        load_additional_password_blocklist(configured_path)
        if configured_path is not None
        else frozenset()
    )
    if (
        comparable_password in _BLOCKED_PASSWORDS
        or comparable_password in _BLOCKED_CONTEXT_PASSWORDS
        or comparable_password in additional_blocklist
    ):
        raise PasswordPolicyError("password is present in the local blocklist")
    return normalized_password
