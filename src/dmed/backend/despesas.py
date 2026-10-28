"""Planilhas de despesas (coparticipação): padronização, validação e titular."""

from __future__ import annotations

import csv
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from dmed.backend import config, fontes, mensalidades
from dmed.backend.formatacao import formatar_cpf, ler_valor_monetario
from dmed.backend.ocorrencias import Ocorrencia, alerta, aviso, critico, erro

logger = logging.getLogger(__name__)

CACHE = "despesas"
COLUNAS = ["Nome", "CPF", "Valor a Pagar"]
NOMES_COLUNA_NOME = {"NOME", "BENEFICIARIO"}
NOMES_COLUNA_CPF = {"CPF", "CPF DO RESPONSAVEL", "CPF_DO_RESPONSAVEL"}
NOMES_COLUNA_VALOR = {"VALOR A PAGAR", "VALOR_DO_SERVICO", "VALOR DO SERVICO", "VALOR"}
# Ordem em que um CSV avulso é tentado; None deixa o pandas detectar o separador.
LEITURAS_CSV: list[tuple[str, str | None]] = [
    (codificacao, separador)
    for codificacao in ("latin1", "utf-8")
    for separador in (";", ",", None)
]


def processar_despesas() -> tuple[Path | None, list[Ocorrencia]]:
    """Junta as planilhas de despesas, liga cada uma ao titular e grava o cache."""
    with fontes.TRAVA:
        logger.info("Processando despesas...")
        ocorrencias: list[Ocorrencia] = []
        try:
            pasta = config.pasta_despesas()
            if not pasta.is_dir():
                return None, [critico("[DESPESAS] Pasta 'data/despesas' não encontrada.")]

            partes = list(_ler_pasta(pasta, ocorrencias))
            if not partes:
                ocorrencias.append(
                    alerta("[DESPESAS] Nenhum arquivo de despesas válido encontrado.")
                )
                return None, ocorrencias

            despesas = _consolidar(pd.concat(partes, ignore_index=True))
            if despesas is None:
                ocorrencias.append(
                    alerta("[DESPESAS] Nenhum registro de despesas restou após a limpeza.")
                )
                return None, ocorrencias

            despesas["CPF_DO_RESPONSAVEL"] = _cpf_do_responsavel(despesas, ocorrencias)
            despesas["BENEFICIARIO"] = despesas["Nome"]
            despesas["VALOR_DO_SERVICO"] = despesas["Valor a Pagar"]
            caminho = fontes.gravar_cache(despesas, CACHE)
            logger.info("Arquivo de despesas atualizado com sucesso!")
            return caminho, ocorrencias

        except Exception as falha:
            # Qualquer falha numa planilha vira ocorrência crítica no relatório.
            logger.exception("Falha ao processar despesas")
            return None, [critico(f"[DESPESAS] Erro crítico ao processar despesas: {falha}")]


def _ler_pasta(pasta: Path, ocorrencias: list[Ocorrencia]) -> Any:
    for arquivo in fontes.arquivos_da_pasta(pasta):
        nome = arquivo.name.lower()
        if nome.endswith(fontes.EXTENSOES_EXCEL):
            for aba, df in fontes.abas_da_planilha(arquivo):
                yield padronizar(df, f"{arquivo.name} -> Aba: {aba}", ocorrencias)
        elif nome.endswith(".csv"):
            df_csv = _ler_csv_avulso(arquivo)
            if df_csv is not None:
                yield padronizar(df_csv, f"Arquivo CSV: {arquivo.name}", ocorrencias)


def _ler_csv_avulso(arquivo: Path) -> pd.DataFrame | None:
    for codificacao, separador in LEITURAS_CSV:
        opcoes: dict[str, Any] = {"encoding": codificacao, "sep": separador}
        if separador is None:
            opcoes["engine"] = "python"
        try:
            return pd.read_csv(arquivo, **opcoes)
        except (ValueError, csv.Error):
            continue
    return None


def _normalizar_coluna(coluna: object) -> str:
    base = unicodedata.normalize("NFKD", str(coluna))
    base = "".join(c for c in base if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", base).strip().upper()


def _primeira_coluna(df: pd.DataFrame, aceitas: set[str]) -> Any:
    return next((col for col in df.columns if _normalizar_coluna(col) in aceitas), None)


def padronizar(
    df: pd.DataFrame, origem: str, ocorrencias: list[Ocorrencia]
) -> pd.DataFrame:
    """Reduz a aba às colunas Nome, CPF e Valor a Pagar, apontando problemas."""
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUNAS)

    col_nome = _primeira_coluna(df, NOMES_COLUNA_NOME)
    col_cpf = _primeira_coluna(df, NOMES_COLUNA_CPF)
    col_valor = _primeira_coluna(df, NOMES_COLUNA_VALOR)
    if not col_nome or not col_valor:
        ocorrencias.append(
            alerta(f"[DESPESAS | Origem: {origem}] Colunas obrigatórias ausentes (Nome ou Valor).")
        )
        return pd.DataFrame(columns=COLUNAS)

    if not col_cpf:
        df["CPF_AUSENTE"] = ""
        col_cpf = "CPF_AUSENTE"

    ocorrencias.extend(_validar(df, origem, col_nome, col_cpf, col_valor))
    resultado = df[[col_nome, col_cpf, col_valor]].copy()
    resultado.columns = pd.Index(COLUNAS)
    return resultado


def _validar(
    df: pd.DataFrame, origem: str, col_nome: Any, col_cpf: Any, col_valor: Any
) -> list[Ocorrencia]:
    posicoes = [df.columns.get_loc(col) for col in (col_nome, col_cpf, col_valor)]
    ocorrencias = []
    for indice, *valores in df.itertuples(index=True, name=None):
        nome_bruto, cpf_bruto, valor_bruto = (valores[p] for p in posicoes)  # type: ignore[index]
        nome = str(nome_bruto).strip()
        cpf = str(cpf_bruto).strip()
        valor = str(valor_bruto).strip()

        # Linhas de divisão ou separadores ("-----") não são despesas.
        texto_da_linha = " ".join(str(v).upper() for v in valores if pd.notna(v))
        if "DIVISÃO" in texto_da_linha or "DIVISAO" in texto_da_linha:
            continue
        if nome and nome.replace("-", "").replace("_", "").strip() == "":
            continue

        falta_nome = pd.isna(nome_bruto) or nome == "" or nome.lower() == "nan"
        falta_cpf = pd.isna(cpf_bruto) or cpf == "" or cpf.lower() == "nan"
        valor_numerico = 0.0 if pd.isna(valor_bruto) else ler_valor_monetario(valor)
        falta_valor = (
            pd.isna(valor_bruto) or valor == "" or valor.lower() == "nan" or valor_numerico <= 0
        )

        if falta_nome or falta_valor:
            campos = " e ".join(
                campo
                for campo, falta in (("NOME", falta_nome), ("VALOR (Ausente ou Zero)", falta_valor))
                if falta
            )
            ocorrencias.append(
                erro(
                    f"[DESPESAS | Origem: {origem}] Linha {indice + 2} | "
                    f"ERRO: Faltando {campos}. | Dados Lidos: Nome: '{nome}', "
                    f"CPF: '{cpf}', Valor: '{valor}'"
                )
            )
        elif falta_cpf:
            ocorrencias.append(
                aviso(
                    f"[DESPESAS | Origem: {origem}] Linha {indice + 2} | "
                    f"AVISO: CPF Ausente. O sistema tentará mapear pelo nome '{nome}'."
                )
            )
    return ocorrencias


def _consolidar(despesas: pd.DataFrame) -> pd.DataFrame | None:
    """Limpa e soma as despesas por CPF (ou pelo nome, quando falta o CPF)."""
    despesas["Nome"] = despesas["Nome"].fillna("").astype(str).str.strip().str.upper()
    despesas["CPF"] = despesas["CPF"].map(formatar_cpf)
    despesas["Valor a Pagar"] = despesas["Valor a Pagar"].map(ler_valor_monetario)

    # Linhas como "--------" não têm letras nem dígitos e saem aqui.
    nome_valido = despesas["Nome"].str.contains(r"[A-Z0-9]", regex=True, na=False)
    despesas = despesas[(despesas["CPF"] != "") | ((despesas["Nome"] != "") & nome_valido)]
    despesas = despesas[~((despesas["CPF"] == "") & (despesas["Valor a Pagar"] <= 0))]
    if despesas.empty:
        return None

    despesas = despesas.assign(
        Chave_Agrupamento=despesas["CPF"].where(despesas["CPF"] != "", despesas["Nome"])
    )
    despesas = despesas.groupby("Chave_Agrupamento", as_index=False).agg(
        {"Nome": "first", "CPF": "first", "Valor a Pagar": "sum"}
    )
    despesas["Valor a Pagar"] = despesas["Valor a Pagar"].round(2)
    despesas = despesas.drop(columns=["Chave_Agrupamento"])
    despesas["CPF"] = despesas["CPF"].fillna("").astype(str)
    return despesas


def _cpf_do_responsavel(
    despesas: pd.DataFrame, ocorrencias: list[Ocorrencia]
) -> pd.Series[str]:
    """CPF do titular de cada despesa, procurado pelo CPF e depois pelo nome."""
    if not fontes.cache_existe(mensalidades.CACHE):
        _, ocorrencias_mensalidades = mensalidades.processar_mensalidades()
        ocorrencias.extend(ocorrencias_mensalidades)

    por_cpf: dict[str, str] = {}
    por_nome: dict[str, str] = {}
    try:
        base = fontes.ler_cache(mensalidades.CACHE, como_texto=True)
        if not base.empty and "Titular_CPF" in base.columns:
            base["Titular_CPF"] = base["Titular_CPF"].map(formatar_cpf)
            base["CPF"] = base["CPF"].map(formatar_cpf) if "CPF" in base.columns else ""
            base["Nome"] = (
                base["Nome"].fillna("").astype(str).str.strip().str.upper()
                if "Nome" in base.columns
                else ""
            )
            com_titular = base[base["Titular_CPF"] != ""]
            por_cpf = _primeiro_titular(com_titular, "CPF")
            por_nome = _primeiro_titular(com_titular, "Nome")
    except (fontes.CacheIndisponivel, KeyError) as falha:
        ocorrencias.append(
            critico(f"[DESPESAS] Erro ao mapear Titular_CPF das mensalidades: {falha}")
        )

    responsavel = [
        por_cpf.get(cpf) or por_nome.get(nome) or cpf
        for cpf, nome in zip(despesas["CPF"], despesas["Nome"], strict=True)
    ]
    return pd.Series(responsavel, index=despesas.index, dtype=object).map(formatar_cpf)


def _primeiro_titular(base: pd.DataFrame, coluna: str) -> dict[str, str]:
    """Para cada CPF (ou nome) de beneficiário, o titular da primeira linha em que aparece."""
    validos = base[base[coluna] != ""].drop_duplicates(coluna)
    return dict(zip(validos[coluna], validos["Titular_CPF"], strict=True))
