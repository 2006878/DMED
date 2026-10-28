"""Montagem do arquivo DMED (.DEC) entregue à Receita Federal."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import pandas as pd

from dmed.backend import config, fontes, mensalidades
from dmed.backend.consulta import ETAPAS, Consulta
from dmed.backend.formatacao import formatar_cpf, formatar_valor_dmed, normalizar_nome
from dmed.backend.ocorrencias import Ocorrencia, critico

logger = logging.getLogger(__name__)

# Código da relação de dependência no registro DTOP; o que não está aqui é 10.
CODIGOS_DEPENDENCIA = {
    "Cônjuge": "03",
    "Filho(a)": "04",
    "Enteado(a)": "06",
    "Pais": "08",
    "Agregado(a)/outros": "10",
}
CODIGO_OUTROS = "10"


@dataclass(frozen=True)
class Responsavel:
    """Responsável pelo preenchimento, informado na tela."""

    cpf: str
    nome: str
    ddd: str
    telefone: str


def codigo_dependencia(relacao: str) -> str:
    return CODIGOS_DEPENDENCIA.get(relacao, CODIGO_OUTROS)


def gerar_arquivo_dmed(
    responsavel: Responsavel, *, reprocessar: bool = True
) -> tuple[str | None, list[Ocorrencia]]:
    """Reprocessa as planilhas e monta o conteúdo do arquivo DMED.

    O arquivo é gerado mesmo com inconsistências: elas voltam na lista de
    ocorrências para o relatório de erros.
    """
    inicio = time.perf_counter()
    with fontes.TRAVA:
        ocorrencias: list[Ocorrencia] = []
        falhas: set[str] = set()
        for cache, processar in ETAPAS_DMED:
            if reprocessar or not fontes.cache_existe(cache):
                caminho, novas = processar()
                ocorrencias.extend(novas)
                if caminho is None:
                    falhas.add(cache)

        if ocorrencias:
            logger.info("%d ocorrência(s) nas planilhas; gerando o DMED mesmo assim.", len(ocorrencias))

        if mensalidades.CACHE in falhas:
            ocorrencias.append(
                critico("[SISTEMA] Erro ao ler o arquivo de mensalidades: o processamento falhou.")
            )
            return None, ocorrencias
        try:
            base = fontes.ler_cache(mensalidades.CACHE, como_texto=True)
        except fontes.CacheIndisponivel as falha:
            ocorrencias.append(critico(f"[SISTEMA] Erro ao ler o arquivo de mensalidades: {falha}"))
            return None, ocorrencias

        consulta = Consulta.carregar(ignorar=frozenset(falhas))
        conteudo = _montar(base, responsavel, consulta)

    logger.info("Arquivo DMED montado em %.1f s.", time.perf_counter() - inicio)
    return conteudo, ocorrencias


# Mesma ordem em que o arquivo sempre processou as planilhas.
ETAPAS_DMED = (ETAPAS[0], ETAPAS[2], ETAPAS[1])


def _montar(base: pd.DataFrame, responsavel: Responsavel, consulta: Consulta) -> str:
    base["Total"] = pd.to_numeric(base["Total"], errors="coerce").fillna(0).round(2)
    base["Titular_CPF"] = base["Titular_CPF"].map(formatar_cpf)

    linhas = [
        f"DMED|{config.ano_entrega()}|{config.ano_calendario()}|N|||",
        f"RESPO|{responsavel.cpf}|{responsavel.nome}|{responsavel.ddd}|{responsavel.telefone}||||",
        f"DECPJ|{config.CNPJ}|{config.RAZAO_SOCIAL_DMED}|2|{config.REGISTRO_ANS}||{responsavel.cpf}|N||S|",
        "OPPAS|",
    ]
    despesas = _despesas_por_titular(base, consulta)

    familias = (
        base.groupby(["Titular_CPF", "Nome"])
        .agg({"Total": "sum", "Relação": "first", "CPF": "first"})
        .reset_index()
    )
    for titular_cpf, grupo in familias.groupby("Titular_CPF"):
        if pd.notna(titular_cpf):
            linhas.extend(registros_do_grupo(grupo, str(titular_cpf), despesas))

    linhas.append("FIMDmed|")
    return "\n".join(linhas)


def _despesas_por_titular(base: pd.DataFrame, consulta: Consulta) -> dict[str, dict[str, float]]:
    """Despesa de cada beneficiário (pelo nome normalizado), por CPF do titular."""
    despesas: dict[str, dict[str, float]] = {}
    primeiras_linhas = base.drop_duplicates("Titular_CPF")
    for cpf, nome_bruto in zip(primeiras_linhas["Titular_CPF"], primeiras_linhas["Nome"], strict=True):
        if pd.isna(cpf) or str(cpf).strip() == "":
            continue
        nome = (
            str(nome_bruto).strip()
            if pd.notna(nome_bruto) and str(nome_bruto).lower() != "nan"
            else ""
        )
        tabela = consulta.despesas(cpf, nome)
        despesas[cpf] = {}
        if not tabela.empty:
            for beneficiario, valor in zip(tabela["Nome"], tabela["Valor"], strict=True):
                texto = str(valor).replace("R$", "").replace(".", "").replace(",", ".").strip()
                despesas[cpf][normalizar_nome(beneficiario)] = float(texto or 0)
    return despesas


def registros_do_grupo(
    grupo: pd.DataFrame, titular_cpf: str, despesas: dict[str, dict[str, float]]
) -> list[str]:
    """Registros TOP (titular) e DTOP (dependentes, por CPF) de uma família."""
    registros = []

    titular = grupo[grupo["Relação"] == "Titular"]
    if not titular.empty:
        linha = titular.iloc[0]
        nome_titular = normalizar_nome(linha["Nome"])
        valor_despesas = despesas.get(titular_cpf, {}).get(nome_titular, 0)
        valor_titular = pd.to_numeric(linha["Total"]).round(2) + valor_despesas
        if valor_titular <= 0:
            valor_titular = 0.01
        registros.append(
            f"TOP|{formatar_cpf(titular_cpf)}|{nome_titular}|{formatar_valor_dmed(valor_titular)}|"
        )

    dependentes = grupo[grupo["Relação"] != "Titular"].copy()
    if not dependentes.empty:
        dependentes["CPF"] = dependentes["CPF"].map(formatar_cpf)
        for _, dependente in dependentes.sort_values(["CPF"]).iterrows():
            nome_dependente = normalizar_nome(dependente["Nome"])
            valor_mensalidade = pd.to_numeric(dependente["Total"])
            valor_despesas = despesas.get(titular_cpf, {}).get(nome_dependente, 0)
            valor_total = valor_mensalidade + valor_despesas
            if valor_total <= 0:
                valor_total = 0.01
            registros.append(
                f"DTOP|{formatar_cpf(dependente['CPF'])}||{nome_dependente}|"
                f"{codigo_dependencia(dependente['Relação'])}|"
                f"{formatar_valor_dmed(str(valor_total))}|"
            )

    return registros
