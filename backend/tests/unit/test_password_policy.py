import pytest

from app.modules.users.password_policy import (
    PasswordPolicyError,
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
        "minha-senha-loadx-segura",
        "a" * 129,
    ],
)
def test_password_policy_rejects_length_and_blocklist(password: str) -> None:
    with pytest.raises(PasswordPolicyError):
        validate_password_policy(password)


def test_password_policy_normalizes_unicode_to_nfc() -> None:
    decomposed_password = "cafe\u0301 com uma frase longa"

    assert validate_password_policy(decomposed_password) == ("café com uma frase longa")
