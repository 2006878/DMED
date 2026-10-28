"""Caracterização ponta a ponta com planilhas fictícias: caches gerados,
arquivo DMED, consulta por CPF e PDF. As saídas de referência ficam em
tests/fixtures/esperado/ e são regravadas com --atualizar-esperado."""

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest

from dmed import funcoes
from conftest import csv_texto, normaliza_pdf

Esperado = Callable[[str, str], None]

# A ordem de os.listdir muda entre sistemas, então as listas de erros são
# comparadas ordenadas.
CACHES = {
    "processa_mensalidades": Path("data/cache/mensalidades.csv"),
    "processa_despesas": Path("data/cache/despesas.csv"),
    "processa_descontos": Path("data/cache/descontos.csv"),
}
CPFS = [
    "10000000001",
    "10000000004",
    "10000000007",
    "10000000012",
    "10000000015",
    "99999999999",
]


def linhas(erros: list[str] | None) -> str:
    return "\n".join(sorted(erros or [])) + "\n"


@pytest.mark.usefixtures("ambiente")
@pytest.mark.parametrize("etapa", list(CACHES))
def test_processamento_das_planilhas(etapa: str, esperado: Esperado) -> None:
    arquivo, erros = getattr(funcoes, etapa)()

    assert arquivo is not None
    esperado(f"{etapa}.csv", Path(arquivo).read_text(encoding="utf-8"))
    esperado(f"{etapa}_erros.txt", linhas(erros))


@pytest.mark.usefixtures("ambiente")
def test_arquivo_dmed(esperado: Esperado) -> None:
    conteudo, erros = funcoes.create_dmed_content(
        "00000000191", "RESPONSAVEL TESTE", "31", "999999999"
    )

    esperado("dmed.DEC", conteudo + "\n")
    esperado("dmed_erros.txt", linhas(erros))


@pytest.mark.usefixtures("ambiente")
@pytest.mark.parametrize("cpf", CPFS)
def test_consulta_por_cpf(cpf: str, esperado: Esperado) -> None:
    # Mesmo fluxo da tela inicial (main.py).
    df_mensalidades = funcoes.busca_dados_mensalidades(cpf)
    nome = df_mensalidades["Nome"].iloc[0] if not df_mensalidades.empty else ""
    descontos = funcoes.busca_dados_descontos(cpf)
    df_despesas = funcoes.busca_dados_despesas(cpf, nome)
    descontos = funcoes.parse_valor_monetario(descontos)
    descontos = (
        f"R$ {descontos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    partes = [
        f"descontos: {descontos}",
        "mensalidades:",
        csv_texto(df_mensalidades),
        "despesas:",
        csv_texto(df_despesas),
    ]
    if not df_mensalidades.empty or not df_despesas.empty:
        pdf = funcoes.generate_pdf(df_mensalidades, df_despesas, descontos, cpf)
        esperado(f"consulta_{cpf}.pdf.txt", normaliza_pdf(pdf))
        # generate_pdf altera o DataFrame recebido, e a tela usa o resultado.
        partes += ["mensalidades depois do PDF:", csv_texto(df_mensalidades)]
    esperado(f"consulta_{cpf}.txt", "\n".join(partes))


def test_cache_existente_nao_e_reprocessado(ambiente: Path) -> None:
    cache = ambiente / CACHES["processa_mensalidades"]
    cache.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "Titular_CPF": ["10000000001"],
            "Relação": ["Titular"],
            "Nome": ["CACHE"],
            "Total": ["1"],
        }
    ).to_csv(cache, index=False)

    assert funcoes.busca_dados_mensalidades("10000000001")["Nome"].tolist() == ["CACHE"]
