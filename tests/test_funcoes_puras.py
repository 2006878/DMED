"""Caracterização das funções puras: fixam o comportamento atual, inclusive
as peculiaridades, para que a refatoração não o altere sem querer."""

import math

import pandas as pd
import pytest

from dmed.backend import arquivo_dmed, config, formatacao, mensalidades
from dmed.backend.informe_pdf import valor_para_exibicao, valor_para_soma
from dmed.backend.ocorrencias import Ocorrencia, Severidade

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
def test_formatar_cpf(entrada: object, esperado: str) -> None:
    assert formatacao.formatar_cpf(entrada) == esperado


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
def test_formatar_valor_dmed(entrada: object, esperado: str) -> None:
    assert formatacao.formatar_valor_dmed(entrada) == esperado


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
def test_ler_valor_monetario(entrada: object, esperado: float) -> None:
    assert formatacao.ler_valor_monetario(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("José da Conceição", "JOSE DA CONCEICAO"),
        ("D'Ávila-Souza", "DAVILASOUZA"),
        ("  maria  ", "  MARIA  "),
        (math.nan, "NAN"),
    ],
)
def test_normalizar_nome(entrada: object, esperado: str) -> None:
    assert formatacao.normalizar_nome(entrada) == esperado


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
def test_codigo_dependencia(relacao: str, codigo: str) -> None:
    assert arquivo_dmed.codigo_dependencia(relacao) == codigo


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
def test_meses_ativos(
    admissao: pd.Timestamp, desligamento: pd.Timestamp, meses: list[int]
) -> None:
    assert config.ano_calendario() == 2025
    assert mensalidades.meses_ativos(admissao, desligamento, 2025) == meses


def test_registros_do_grupo() -> None:
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
    assert arquivo_dmed.registros_do_grupo(grupo, "10000000001", despesas) == [
        "TOP|10000000001|ANA SOUZA|000135000|",
        "DTOP|||ZECA|10|000000001|",
        "DTOP|10000000002||BIA SOUZA|03|000000001|",
        "DTOP|10000000003||CAIO SOUZA|04|000038050|",
    ]


# Fórmulas copiadas do código anterior, para provar que as novas dão o mesmo resultado.
def _moeda_antiga(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _exibicao_antiga(valor_moeda: str) -> str:
    # generate_pdf alterava a coluna Valor assim, e a tela convertia o resultado.
    valor = pd.Series([valor_moeda]).astype(str).str.strip()
    valor = valor.str.replace(r"[^\d,]", "", regex=True).str.replace(",", ".", regex=True)
    texto = valor.iloc[0]
    texto = str(texto).replace("R$", "").replace(".", "", texto.count(".") - 1)
    texto = texto.replace(",", ".").strip()
    try:
        return f"{float(texto):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except ValueError:
        return "Valor inválido"


VALORES = [0.0, 0.01, 0.29, 1.5, 999.999, 1000.0, 1234.56, 1234567.891, -5.0, -1234.5]


@pytest.mark.parametrize("valor", VALORES)
def test_formatar_moeda_igual_a_formula_antiga(valor: float) -> None:
    assert formatacao.formatar_moeda(valor) == _moeda_antiga(valor)


@pytest.mark.parametrize(
    "valor_moeda",
    [_moeda_antiga(v) for v in VALORES] + ["", "abc", "nan", "R$ 1.234.567,89", "12,3,4"],
)
def test_valor_para_exibicao_igual_a_tela_antiga(valor_moeda: str) -> None:
    assert valor_para_exibicao(valor_moeda) == _exibicao_antiga(valor_moeda)


def test_valor_para_soma_descarta_o_sinal() -> None:
    assert valor_para_soma("R$ -1.234,56") == "1234.56"


def test_ocorrencia_mantem_o_texto_do_relatorio() -> None:
    ocorrencia = Ocorrencia(Severidade.ERRO, "[DESPESAS] Linha 2")

    assert str(ocorrencia) == "🛑 [DESPESAS] Linha 2"
    assert [s.bloqueante for s in Severidade] == [False, False, True, True]
