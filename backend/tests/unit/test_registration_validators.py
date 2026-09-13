from collections.abc import Callable

import pytest

from app.shared.validators import (
    normalize_cnh,
    normalize_cnpj,
    normalize_cpf,
    normalize_customer_document,
    normalize_phone,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12345678909", "12345678909"),
        (" 123.456.789-09 ", "12345678909"),
        ("987.654.321-00", "98765432100"),
    ],
)
def test_cpf_accepts_valid_check_digits_and_normalizes(
    value: str, expected: str
) -> None:
    assert normalize_cpf(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "12345678919",
        "12345678908",
        "00000000000",
        "111.111.111-11",
        "1234567890",
        "123.456.78909",
        "12345678909a",
        "１２３４５６７８９０９",
    ],
)
def test_cpf_rejects_invalid_digits_format_and_repeated_sequences(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_cpf(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("00000000000191", "00000000000191"),
        (" 00.000.000/0001-91 ", "00000000000191"),
        ("00.000.000/0002-72", "00000000000272"),
    ],
)
def test_cnpj_accepts_valid_check_digits_and_preserves_leading_zeroes(
    value: str, expected: str
) -> None:
    assert normalize_cnpj(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "00000000000181",
        "00000000000190",
        "00000000000000",
        "11.111.111/1111-11",
        "0000000000191",
        "00.000.000-0001-91",
        "00.000.00A/0001-91",
    ],
)
def test_cnpj_rejects_invalid_digits_format_and_repeated_sequences(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_cnpj(value)


@pytest.mark.parametrize(
    "value",
    [
        "12345678900",
        "98765432109",
        "12340004909",
        "12340005700",
        "12340003008",
    ],
)
def test_cnh_accepts_valid_check_digits_including_remainder_boundaries(
    value: str,
) -> None:
    assert normalize_cnh(f" {value} ") == value


@pytest.mark.parametrize(
    "value",
    [
        "12345678910",
        "12345678901",
        "12340004900",
        "00000000000",
        "11111111111",
        "1234567890",
        "123.456.789-00",
        "CNH12345678900",
    ],
)
def test_cnh_rejects_invalid_digits_format_and_repeated_sequences(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_cnh(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1130000000", "1130000000"),
        ("11900000000", "11900000000"),
        (" (11) 3000-0000 ", "1130000000"),
        ("(11)90000-0000", "11900000000"),
        ("11 90000-0000", "11900000000"),
        ("113000-0000", "1130000000"),
    ],
)
def test_phone_accepts_landline_and_mobile_with_ddd_and_normalizes(
    value: str, expected: str
) -> None:
    assert normalize_phone(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "0130000000",
        "01900000000",
        "11800000000",
        "119000000",
        "119000000000",
        "+55 (11) 90000-0000",
        "(11 90000-0000",
        "11) 90000-0000",
        "11.90000.0000",
        "11 90000-0000 ramal 1",
        "１１９００００００００",
    ],
)
def test_phone_rejects_invalid_ddd_mobile_prefix_length_and_format(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_phone(value)


@pytest.mark.parametrize(
    "normalizer",
    [
        normalize_cpf,
        normalize_cnpj,
        normalize_cnh,
        normalize_phone,
        normalize_customer_document,
    ],
)
def test_normalizers_reject_non_strings_and_empty_values(
    normalizer: Callable[[object], str],
) -> None:
    for value in (None, 12345678909, True, "", "   "):
        with pytest.raises(ValueError):
            normalizer(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("123.456.789-09", "12345678909"),
        ("00.000.000/0001-91", "00000000000191"),
    ],
)
def test_customer_document_accepts_cpf_and_cnpj(value: str, expected: str) -> None:
    assert normalize_customer_document(value) == expected


@pytest.mark.parametrize("value", ["12345678908", "00000000000190", "123456789012"])
def test_customer_document_rejects_invalid_cpf_cnpj_and_other_lengths(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        normalize_customer_document(value)
