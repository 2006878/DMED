"""Planilhas de descontos em folha: validação e total por CPF (ou por nome)."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from dmed.backend import config, fontes
from dmed.backend.config import Planilha
from dmed.backend.formatacao import formatar_cpf, ler_valor_monetario
from dmed.backend.ocorrencias import Ocorrencia, alerta, aviso, critico, erro

logger = logging.getLogger(__name__)

CACHE = "descontos"
COLUNAS = ["Nome", "CPF", "Total de Descontos"]


def processar_descontos() -> tuple[Path | None, list[Ocorrencia]]:
    """Lê todas as planilhas de descontos e grava o total por pessoa no cache.

    A DESCONTOS.xlsx vem do Google Drive e é baixada quando falta; as demais
    planilhas da pasta são lidas como estão no repositório.
    """
    with fontes.TRAVA:
        logger.info("Processando descontos...")
        ocorrencias: list[Ocorrencia] = []
        try:
            if not config.destino_planilha(Planilha.DESCONTOS).exists():
                fontes.baixar_planilha(Planilha.DESCONTOS)

            partes = [
                padronizar(df, f"{arquivo.name} -> Aba: {aba}", ocorrencias)
                for arquivo in fontes.arquivos_da_pasta(config.pasta_descontos())
                if arquivo.name.lower().endswith(".xlsx")
                for aba, df in fontes.abas_da_planilha(arquivo)
            ]
            if not partes:
                ocorrencias.append(
                    alerta("[DESCONTOS] Nenhum arquivo ou aba válida para processar.")
                )
                return None, ocorrencias

            descontos = pd.concat(partes, ignore_index=True)
            if descontos.empty:
                ocorrencias.append(
                    alerta("[DESCONTOS] Nenhum desconto encontrado para processar.")
                )
                return None, ocorrencias

            consolidados = _consolidar(descontos)
            if consolidados is None:
                ocorrencias.append(
                    alerta(
                        "[DESCONTOS] Nenhum registro restou após a limpeza "
                        "(todos zerados ou sem nome)."
                    )
                )
                return None, ocorrencias

            caminho = fontes.gravar_cache(consolidados, CACHE)
            logger.info("Arquivo de descontos atualizado com sucesso!")
            return caminho, ocorrencias

        except Exception as falha:
            # Qualquer falha numa planilha vira ocorrência crítica no relatório.
            logger.exception("Falha ao processar descontos")
            return None, [
                critico(
                    f"[DESCONTOS] Erro crítico ao processar o arquivo de descontos: {falha}"
                )
            ]


def padronizar(
    df: pd.DataFrame, origem: str, ocorrencias: list[Ocorrencia]
) -> pd.DataFrame:
    """Reduz a aba às colunas Nome, CPF e Total de Descontos, apontando problemas."""
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUNAS)

    df.columns = pd.Index([str(coluna).strip() for coluna in df.columns])
    if "Nome" not in df.columns or "Total de Descontos" not in df.columns:
        ocorrencias.append(
            alerta(f"[DESCONTOS | Origem: {origem}] Colunas obrigatórias ausentes.")
        )
        return pd.DataFrame(columns=COLUNAS)
    if "CPF" not in df.columns:
        df["CPF"] = ""

    for indice, nome_bruto, cpf_bruto, valor_bruto in zip(
        df.index, df["Nome"], df["CPF"], df["Total de Descontos"], strict=True
    ):
        nome = str(nome_bruto).strip()
        cpf = str(cpf_bruto).strip()
        valor = str(valor_bruto).strip()

        falta_nome = pd.isna(nome_bruto) or nome == "" or nome.lower() == "nan"
        falta_cpf = pd.isna(cpf_bruto) or cpf == "" or cpf.lower() == "nan"
        valor_numerico = 0.0 if pd.isna(valor_bruto) else ler_valor_monetario(valor)
        falta_valor = (
            pd.isna(valor_bruto)
            or valor == ""
            or valor.lower() == "nan"
            or valor_numerico <= 0
        )

        if falta_nome or falta_valor:
            campos = " e ".join(
                campo
                for campo, falta in (
                    ("NOME", falta_nome),
                    ("TOTAL DE DESCONTOS (Ausente ou Zero)", falta_valor),
                )
                if falta
            )
            ocorrencias.append(
                erro(
                    f"[DESCONTOS | Origem: {origem}] Linha {indice + 2} | "
                    f"ERRO: Faltando {campos}. | Dados Lidos: Nome: '{nome}', "
                    f"CPF: '{cpf}', Valor: '{valor}'"
                )
            )
        elif falta_cpf:
            ocorrencias.append(
                aviso(
                    f"[DESCONTOS | Origem: {origem}] Linha {indice + 2} | "
                    f"AVISO: CPF Ausente. Agrupamento será feito pelo nome '{nome}'."
                )
            )

    return df[COLUNAS].copy()


def _consolidar(descontos: pd.DataFrame) -> pd.DataFrame | None:
    """Tira linhas sem nome ou zeradas e soma por CPF (ou pelo nome, sem CPF)."""
    descontos["Nome"] = descontos["Nome"].fillna("").astype(str).str.strip().str.upper()
    descontos["CPF"] = descontos["CPF"].map(formatar_cpf)
    descontos["Total de Descontos"] = descontos["Total de Descontos"].map(
        ler_valor_monetario
    )

    descontos = descontos[
        (descontos["Nome"] != "") & (descontos["Total de Descontos"] > 0)
    ]
    if descontos.empty:
        return None

    descontos = descontos.assign(
        Chave_Agrupamento=descontos["CPF"].where(
            descontos["CPF"] != "", descontos["Nome"]
        )
    )
    descontos = descontos.groupby("Chave_Agrupamento", as_index=False).agg(
        {"Nome": "first", "CPF": "first", "Total de Descontos": "sum"}
    )
    descontos["Total de Descontos"] = descontos["Total de Descontos"].round(2)
    return descontos.drop(columns=["Chave_Agrupamento"])
