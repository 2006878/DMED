"""Caracterização ponta a ponta com planilhas fictícias: caches gerados,
arquivo DMED, consulta por CPF e PDF. As saídas de referência ficam em
tests/fixtures/esperado/ e são regravadas com --atualizar-esperado."""

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest

from conftest import csv_texto, normaliza_pdf
from dmed.backend import config, descontos, despesas, fontes, mensalidades
from dmed.backend.arquivo_dmed import Responsavel, gerar_arquivo_dmed
from dmed.backend.config import Planilha
from dmed.backend.consulta import Consulta
from dmed.backend.formatacao import formatar_moeda, ler_valor_monetario
from dmed.backend.informe_pdf import gerar_informe_pdf, valor_para_soma
from dmed.backend.ocorrencias import Ocorrencia, Severidade

Esperado = Callable[[str, str], None]

ETAPAS = {
    "mensalidades": mensalidades.processar_mensalidades,
    "despesas": despesas.processar_despesas,
    "descontos": descontos.processar_descontos,
}
CPFS = [
    "10000000001",
    "10000000004",
    "10000000007",
    "10000000012",
    "10000000015",
    "99999999999",
]
RESPONSAVEL = Responsavel("00000000191", "RESPONSAVEL TESTE", "31", "999999999")


def linhas(ocorrencias: list[Ocorrencia]) -> str:
    # A ordem dos arquivos na pasta já foi diferente entre sistemas; compara ordenado.
    return "\n".join(sorted(str(o) for o in ocorrencias)) + "\n"


@pytest.mark.usefixtures("ambiente")
@pytest.mark.parametrize("etapa", list(ETAPAS))
def test_processamento_das_planilhas(etapa: str, esperado: Esperado) -> None:
    arquivo, ocorrencias = ETAPAS[etapa]()

    assert arquivo is not None
    esperado(f"{etapa}.csv", arquivo.read_text(encoding="utf-8"))
    esperado(f"{etapa}_erros.txt", linhas(ocorrencias))


@pytest.mark.usefixtures("ambiente")
def test_arquivo_dmed(esperado: Esperado) -> None:
    conteudo, ocorrencias = gerar_arquivo_dmed(RESPONSAVEL)

    assert conteudo is not None
    esperado("dmed.DEC", conteudo + "\n")
    esperado("dmed_erros.txt", linhas(ocorrencias))


@pytest.mark.usefixtures("ambiente")
@pytest.mark.parametrize("cpf", CPFS)
def test_consulta_por_cpf(cpf: str, esperado: Esperado) -> None:
    # Mesmo fluxo da página inicial.
    consulta = Consulta.carregar()
    familia = consulta.mensalidades(cpf)
    nome = familia["Nome"].iloc[0] if not familia.empty else ""
    total_descontos = formatar_moeda(ler_valor_monetario(consulta.descontos(cpf)))
    tabela_despesas = consulta.despesas(cpf, nome)

    partes = [
        f"descontos: {total_descontos}",
        "mensalidades:",
        csv_texto(familia),
        "despesas:",
        csv_texto(tabela_despesas),
    ]
    if not familia.empty or not tabela_despesas.empty:
        pdf = gerar_informe_pdf(familia, tabela_despesas, total_descontos, cpf)
        esperado(f"consulta_{cpf}.pdf.txt", normaliza_pdf(pdf))
        # Antes, o PDF alterava a tabela e a tela lia os valores convertidos;
        # hoje a conversão é explícita e o resultado tem de ser o mesmo.
        convertida = familia.assign(Valor=familia["Valor"].map(valor_para_soma))
        partes += ["mensalidades depois do PDF:", csv_texto(convertida)]
    esperado(f"consulta_{cpf}.txt", "\n".join(partes))


def test_pdf_nao_altera_a_tabela(ambiente: Path) -> None:
    familia = Consulta.carregar().mensalidades("10000000001")
    antes = familia.copy()

    gerar_informe_pdf(familia, pd.DataFrame(columns=["Nome", "Valor"]), "R$ 0,00", "1")

    pd.testing.assert_frame_equal(familia, antes)


def test_cache_existente_nao_e_reprocessado(ambiente: Path) -> None:
    cache = ambiente / "data/cache/mensalidades.csv"
    cache.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "Titular_CPF": ["10000000001"],
            "Relação": ["Titular"],
            "Nome": ["CACHE"],
            "Total": ["1"],
        }
    ).to_csv(cache, index=False)

    familia = Consulta.carregar().mensalidades("10000000001")

    assert familia["Nome"].tolist() == ["CACHE"]


def test_descontos_baixa_a_planilha_do_drive_quando_falta(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DMED_DRIVE_DESCONTOS", "id-de-teste")
    config.destino_planilha(Planilha.DESCONTOS).unlink()

    arquivo, ocorrencias = descontos.processar_descontos()

    assert arquivo is None
    assert [o.severidade for o in ocorrencias] == [Severidade.CRITICO]
    assert "acesso à rede bloqueado" in ocorrencias[0].texto


def test_download_que_falha_preserva_a_planilha_local(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DMED_DRIVE_DESCONTOS", "id-de-teste")
    planilha = config.destino_planilha(Planilha.DESCONTOS)
    antes = planilha.read_bytes()

    sucesso, mensagem = fontes.baixar_planilhas_do_drive()

    assert not sucesso
    assert mensagem.startswith("❌ Erro ao atualizar os arquivos físicos:")
    assert planilha.read_bytes() == antes


def test_sem_id_do_drive_a_mensagem_explica_a_configuracao(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMED_DRIVE_DESCONTOS", raising=False)
    monkeypatch.setattr(
        config, "url_drive", _sem_configuracao, raising=True
    )

    sucesso, mensagem = fontes.baixar_planilhas_do_drive()

    assert not sucesso
    assert "secrets.toml" in mensagem


def _sem_configuracao(planilha: Planilha) -> str:
    raise config.ConfiguracaoAusente(f"ID do Google Drive para '{planilha.value}' (secrets.toml)")


def test_arquivos_da_pasta_em_ordem_alfabetica(tmp_path: Path) -> None:
    for nome in ("b.xlsx", "A.xlsx", "c.csv"):
        (tmp_path / nome).write_text("")
    (tmp_path / "pasta").mkdir()

    assert [a.name for a in fontes.arquivos_da_pasta(tmp_path)] == ["A.xlsx", "b.xlsx", "c.csv"]
