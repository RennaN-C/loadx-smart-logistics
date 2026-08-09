import pytest

from app.modules.users.password_policy import (
    PasswordBlocklistConfigurationError,
    PasswordPolicyError,
    load_additional_password_blocklist,
    validate_password_policy,
)


def test_password_policy_accepts_spaces_unicode_and_no_composition() -> None:
    password = " frase longa com café "

    assert validate_password_policy(password) == password
    assert validate_password_policy("apenasletrasminusculas") == (
        "apenasletrasminusculas"
    )


@pytest.mark.parametrize(
    "password",
    [
        "curta",
        "passwordpassword",
        "loadxloadxloadx",
        "a" * 129,
    ],
)
def test_password_policy_rejects_length_and_blocklist(password: str) -> None:
    with pytest.raises(PasswordPolicyError):
        validate_password_policy(password)


def test_password_policy_normalizes_unicode_to_nfc() -> None:
    decomposed_password = "cafe\u0301 com uma frase longa"

    assert validate_password_policy(decomposed_password) == ("café com uma frase longa")


def test_password_policy_compares_the_whole_password_to_context_values() -> None:
    password = "frase longa exclusiva para o loadx"

    assert validate_password_policy(password) == password


def test_password_policy_uses_configured_utf8_blocklist(tmp_path) -> None:
    blocklist_path = tmp_path / "compromised-passwords.txt"
    blocklist_path.write_text(
        "# fonte aprovada pela operação\nFrase comprometida muito comum\n",
        encoding="utf-8",
    )

    with pytest.raises(PasswordPolicyError):
        validate_password_policy(
            "frase comprometida muito comum",
            additional_blocklist_path=blocklist_path,
        )


def test_password_blocklist_rejects_invalid_utf8(tmp_path) -> None:
    blocklist_path = tmp_path / "invalid.txt"
    blocklist_path.write_bytes(b"\xff\xfe")

    with pytest.raises(PasswordBlocklistConfigurationError):
        load_additional_password_blocklist(blocklist_path)
