import re
from collections.abc import Sequence
from typing import Annotated

from pydantic import BeforeValidator

_CPF_PATTERN = r"(?:[0-9]{11}|[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2})"
_CNPJ_PATTERN = r"(?:[0-9]{14}|[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2})"
_PHONE_PATTERN = r"(?:[0-9]{2}|\([0-9]{2}\)) ?[0-9]{4,5}-?[0-9]{4}"


def _normalize_document(value: object, pattern: str, message: str) -> str:
    if not isinstance(value, str) or re.fullmatch(pattern, value.strip()) is None:
        raise ValueError(message)
    digits = re.sub(r"[^0-9]", "", value.strip())
    if len(set(digits)) == 1:
        raise ValueError(message)
    return digits


def _mod11_digit(digits: str, weights: Sequence[int]) -> str:
    remainder = sum(int(digit) * weight for digit, weight in zip(digits, weights)) % 11
    return str(0 if remainder < 2 else 11 - remainder)


def normalize_cpf(value: object) -> str:
    """Valida formato e verificadores; não consulta situação cadastral."""
    message = "Informe um CPF válido."
    digits = _normalize_document(value, _CPF_PATTERN, message)
    first = _mod11_digit(digits[:9], range(10, 1, -1))
    second = _mod11_digit(digits[:9] + first, range(11, 1, -1))
    if digits[-2:] != first + second:
        raise ValueError(message)
    return digits


def normalize_cnpj(value: object) -> str:
    """Valida somente o CNPJ numérico previsto no contrato da OC63."""
    message = "Informe um CNPJ válido."
    digits = _normalize_document(value, _CNPJ_PATTERN, message)
    first = _mod11_digit(digits[:12], (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    second = _mod11_digit(digits[:12] + first, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    if digits[-2:] != first + second:
        raise ValueError(message)
    return digits


def normalize_customer_document(value: object) -> str:
    if isinstance(value, str):
        if re.fullmatch(_CPF_PATTERN, value.strip()):
            return normalize_cpf(value)
        if re.fullmatch(_CNPJ_PATTERN, value.strip()):
            return normalize_cnpj(value)
    raise ValueError("Informe um CPF ou CNPJ válido.")


def normalize_cnh(value: object) -> str:
    message = "Informe uma CNH válida com 11 dígitos."
    digits = _normalize_document(value, r"[0-9]{11}", message)
    base = [int(digit) for digit in digits[:9]]
    first = sum(digit * weight for digit, weight in zip(base, range(9, 0, -1))) % 11
    discount = 2 if first == 10 else 0
    first = 0 if first == 10 else first
    second_sum = sum(digit * weight for digit, weight in zip(base, range(1, 10)))
    # O desconto é aplicado antes de converter o resto 10 em zero.
    second = (second_sum - discount) % 11
    second = 0 if second == 10 else second
    if digits[-2:] != f"{first}{second}":
        raise ValueError(message)
    return digits


def normalize_phone(value: object) -> str:
    message = "Informe um telefone com DDD e 10 ou 11 dígitos."
    if (
        not isinstance(value, str)
        or re.fullmatch(_PHONE_PATTERN, value.strip()) is None
    ):
        raise ValueError(message)
    digits = re.sub(r"[^0-9]", "", value.strip())
    if digits[0] == "0":
        raise ValueError("O DDD não pode começar com zero.")
    if len(digits) == 11 and digits[2] != "9":
        raise ValueError("O celular deve começar com 9 após o DDD.")
    return digits


CPF = Annotated[str, BeforeValidator(normalize_cpf)]
CNH = Annotated[str, BeforeValidator(normalize_cnh)]
CustomerDocument = Annotated[str, BeforeValidator(normalize_customer_document)]
PhoneNumber = Annotated[str, BeforeValidator(normalize_phone)]
