"""Caracterização das funções puras: fixam o comportamento atual, inclusive
as peculiaridades, para que a refatoração não o altere sem querer."""

import math

import pandas as pd
import pytest

from dmed.backend import processamento

T = pd.Timestamp


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (None, ""),
        (math.nan, ""),
        ("", ""),
        ("  ", ""),
        ("0", ""),
        (12345678909, "12345678909"),
        (1234567890.0, "01234567890"),
        ("1234567890.0", "01234567890"),
        ("123.456.789-09", "12345678909"),
        (" 123456789 ", "00123456789"),
        ("abc", ""),
        (1.5, "00000000015"),  # float não inteiro vira dígitos soltos
    ],
)
def test_format_cpf(entrada: object, esperado: str) -> None:
    assert processamento.format_cpf(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("10,50", "000001050"),
        ("R$ 1.234,56", "000123456"),
        (1234.5, "000123450"),
        (0, "000000001"),  # zero vira R$ 0,01
        (math.nan, "000000001"),
        (0.29, "000000028"),  # trunca em vez de arredondar
        ("abc", ""),
        (None, ""),
    ],
)
def test_format_valor(entrada: object, esperado: str) -> None:
    assert processamento.format_valor(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("R$ 1.234,56", 1234.56),
        ("12.5", 12.5),
        ("-5,00", -5.0),
        ("1,234.56", 1.23),  # vírgula sempre é lida como decimal
        ("R$ 300", 300.0),
        (math.nan, 0.0),
        ("", 0.0),
        ("abc", 0.0),
        (7, 7.0),
    ],
)
def test_parse_valor_monetario(entrada: object, esperado: float) -> None:
    assert processamento.parse_valor_monetario(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("José da Conceição", "JOSE DA CONCEICAO"),
        ("D'Ávila-Souza", "DAVILASOUZA"),
        ("  maria  ", "  MARIA  "),
        (math.nan, "NAN"),
    ],
)
def test_normalize_name(entrada: object, esperado: str) -> None:
    assert processamento.normalize_name(entrada) == esperado


@pytest.mark.parametrize(
    ("relacao", "codigo"),
    [
        ("Cônjuge", "03"),
        ("Filho(a)", "04"),
        ("Enteado(a)", "06"),
        ("Pais", "08"),
        ("Agregado(a)/outros", "10"),
        ("Outros", "10"),
        ("Titular", "10"),
    ],
)
def test_get_dependent_code(relacao: str, codigo: str) -> None:
    assert processamento.get_dependent_code(relacao) == codigo


TODOS = list(range(1, 13))


@pytest.mark.parametrize(
    ("admissao", "desligamento", "meses"),
    [
        (pd.NaT, pd.NaT, []),
        (T("2026-01-10"), pd.NaT, []),
        (T("2020-01-01"), pd.NaT, TODOS),
        (T("2025-04-15"), pd.NaT, list(range(4, 13))),
        (T("2025-02-01"), T("2025-06-30"), list(range(2, 7))),
        (T("2020-01-01"), T("2025-06-30"), list(range(1, 7))),
        (T("2025-03-01"), T("2026-02-01"), list(range(3, 13))),
        (T("2020-01-01"), T("2026-02-01"), TODOS),
        (T("2020-01-01"), T("2024-12-31"), []),
    ],
)
def test_calculate_active_months(
    admissao: pd.Timestamp, desligamento: pd.Timestamp, meses: list[int]
) -> None:
    assert processamento.ano_anterior == 2025
    assert processamento.calculate_active_months(admissao, desligamento) == meses


def test_process_group() -> None:
    grupo = pd.DataFrame(
        {
            "Titular_CPF": ["10000000001"] * 4,
            "Nome": ["ANA SOUZA", "Caio Souza", "Bia Souza", "Zeca"],
            "Total": [1200.0, 300.0, 0.0, -5.0],
            "Relação": ["Titular", "Filho(a)", "Cônjuge", "Outros"],
            "CPF": ["10000000001", "10000000003", 10000000002, None],
        }
    )
    despesas = {"10000000001": {"ANA SOUZA": 150.0, "CAIO SOUZA": 80.5}}
    assert processamento.process_group(grupo, "10000000001", despesas) == [
        "TOP|10000000001|ANA SOUZA|000135000|",
        "DTOP|||ZECA|10|000000001|",
        "DTOP|10000000002||BIA SOUZA|03|000000001|",
        "DTOP|10000000003||CAIO SOUZA|04|000038050|",
    ]
