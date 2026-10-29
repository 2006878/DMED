"""Regras dos formulários e do resultado da DMED, sem abrir o app."""

import datetime as dt

import pytest

from dmed.backend.arquivo_dmed import Responsavel
from dmed.backend.ocorrencias import alerta, erro
from dmed.frontend.resultado_dmed import ResultadoDmed
from dmed.frontend.validacao import (
    CpfConsultado,
    cpf_com_mascara,
    ler_cpf_da_consulta,
    validar_responsavel,
)


@pytest.mark.parametrize(
    ("digitado", "esperado"),
    [
        ("100.000.000-01", CpfConsultado(cpf="10000000001")),
        (" 10000000001 ", CpfConsultado(cpf="10000000001")),
        ("", CpfConsultado(erro="Digite os números do CPF do titular.")),
        ("abc", CpfConsultado(erro="Digite os números do CPF do titular.")),
        (
            "123456789012",
            CpfConsultado(
                erro="O CPF tem 12 números, mas deve ter 11. Confira o número digitado."
            ),
        ),
    ],
)
def test_ler_cpf_da_consulta(digitado: str, esperado: CpfConsultado) -> None:
    assert ler_cpf_da_consulta(digitado) == esperado


def test_cpf_curto_completa_com_zeros_e_avisa() -> None:
    lido = ler_cpf_da_consulta("1234567890")

    assert lido.cpf == "01234567890"
    assert "Consultamos 012.345.678-90" in lido.aviso
    assert not lido.erro


def test_cpf_com_mascara() -> None:
    assert cpf_com_mascara("00000000191") == "000.000.001-91"


def test_validar_responsavel_tira_mascara_e_espacos() -> None:
    assert validar_responsavel("000.000.001-91", "  MARIA  ", "(31)", "99999-9999") == (
        Responsavel("00000000191", "MARIA", "31", "999999999"),
        [],
    )


def test_validar_responsavel_aceita_telefone_de_8_numeros() -> None:
    responsavel, problemas = validar_responsavel("00000000191", "M", "31", "3333-4444")

    assert responsavel is not None
    assert responsavel.telefone == "33334444"
    assert not problemas


def test_validar_responsavel_lista_todos_os_problemas() -> None:
    responsavel, problemas = validar_responsavel("", "", "", "")

    assert responsavel is None
    assert len(problemas) == 4


def test_resultado_conta_registros_e_pendencias() -> None:
    resultado = ResultadoDmed(
        "DMED|2026|\nTOP|1|\nDTOP|2|\nDTOP|3|\nFIMDmed|",
        [erro("linha 1"), alerta("linha 2")],
    )

    assert resultado.contar("TOP") == 1
    assert resultado.contar("DTOP") == 2
    assert [o.texto for o in resultado.bloqueantes] == ["linha 1"]


def test_relatorio_de_erros_mantem_o_formato() -> None:
    resultado = ResultadoDmed(
        None,
        [erro("linha 1")],
        gerado_em=dt.datetime(2026, 3, 15, 9, 5, 7, tzinfo=dt.UTC),
    )

    assert resultado.relatorio_de_erros() == (
        "========================================================\n"
        "RELATORIO DE INCONSISTENCIAS - COSEMI DMED\n"
        "Gerado em: 15/03/2026 as 09:05:07\n"
        "========================================================\n"
        "\n"
        "Por favor, corrija as linhas listadas abaixo nas planilhas originais:\n\n"
        "🛑 linha 1"
    )
