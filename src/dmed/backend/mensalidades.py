"""Planilha de mensalidades: validação, hierarquia familiar e rateio anual."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from dmed.backend import config, fontes
from dmed.backend.formatacao import formatar_cpf
from dmed.backend.ocorrencias import Ocorrencia, alerta, critico

logger = logging.getLogger(__name__)

CACHE = "mensalidades"
TITULAR = "T."
# Mapeia a coluna "Par." (já em maiúsculas) para a relação de dependência.
RELACOES = {
    "T.": "Titular",
    "T": "Titular",
    "esp.": "Cônjuge",
    "FIL.": "Filho(a)",
    "ENT.": "Enteado(a)",
    "MAE": "Pais",
    "PAI": "Pais",
}
MEMBROS_NO_RATEIO = 4  # planos comuns: só os 4 primeiros da família dividem o valor


def meses_ativos(
    admissao: pd.Timestamp, desligamento: pd.Timestamp, ano: int
) -> list[int]:
    """Meses do ano-calendário em que o beneficiário esteve no plano."""
    if pd.isna(admissao) or admissao.year > ano:
        return []
    if pd.isna(desligamento):
        return list(range(1, 13)) if admissao.year < ano else list(range(admissao.month, 13))
    if desligamento.year == ano and admissao.year == ano:
        return list(range(admissao.month, desligamento.month + 1))
    if desligamento.year == ano and admissao.year < ano:
        return list(range(1, desligamento.month + 1))
    if desligamento.year > ano and admissao.year == ano:
        return list(range(admissao.month, 13))
    if desligamento.year > ano and admissao.year < ano:
        return list(range(1, 13))
    return []


def processar_mensalidades() -> tuple[Path | None, list[Ocorrencia]]:
    """Lê a planilha de mensalidades (baixando-a se faltar) e grava o cache."""
    with fontes.TRAVA:
        ocorrencias: list[Ocorrencia] = []
        arquivo = config.destino_planilha(config.Planilha.MENSALIDADES)
        try:
            if not arquivo.exists():
                fontes.baixar_planilhas_do_drive()

            logger.info("Processando mensalidades...")
            resultado = pd.DataFrame()
            for aba, df in fontes.abas_da_planilha(arquivo):
                df["Planilha_Origem"] = aba
                ocorrencias.extend(validar_aba(df, aba))
                rateio = ratear_aba(df, aba, config.ano_calendario())
                if not rateio.empty:
                    resultado = pd.concat([resultado, rateio], ignore_index=True)

            return fontes.gravar_cache(resultado, CACHE), ocorrencias

        except Exception as erro:
            # Qualquer falha numa planilha vira ocorrência crítica no relatório.
            logger.exception("Falha ao processar mensalidades")
            return None, [critico(f"Erro crítico ao processar mensalidades: {erro}")]


def validar_aba(df: pd.DataFrame, aba: str) -> list[Ocorrencia]:
    """Aponta linhas sem nome, sem CPF ou titulares sem o valor anual."""
    ocorrencias = []
    tem_total = config.COLUNA_TOTAL_ANUAL in df.columns
    colunas = [
        df[nome] if nome in df.columns else [None] * len(df)
        for nome in ("Nome", "CPF", config.COLUNA_TOTAL_ANUAL, "Par.")
    ]
    padrao = {nome: nome in df.columns for nome in ("Nome", "CPF", "Par.")}
    for indice, nome_bruto, cpf_bruto, total_bruto, par_bruto in zip(
        df.index, *colunas, strict=True
    ):
        nome = str(nome_bruto if padrao["Nome"] else "").strip()
        cpf = str(cpf_bruto if padrao["CPF"] else "").strip()
        valor = str(total_bruto if tem_total else "").strip()
        parentesco = str(par_bruto if padrao["Par."] else "").strip().upper()

        falta_nome = pd.isna(nome_bruto) or nome == "" or nome.lower() == "nan"
        falta_cpf = pd.isna(cpf_bruto) or cpf == "" or cpf.lower() == "nan"
        falta_valor = (
            parentesco == TITULAR
            and tem_total
            and (pd.isna(total_bruto) or valor == "" or valor.lower() == "nan")
        )
        if not (falta_nome or falta_cpf or falta_valor):
            continue

        faltando = [
            campo
            for campo, falta in (
                ("NOME", falta_nome),
                ("CPF", falta_cpf),
                ("VALOR (Obrigatório p/ Titular)", falta_valor),
            )
            if falta
        ]
        ocorrencias.append(
            alerta(
                f"[MENSALIDADES | Aba: {aba}] Linha {indice + 2} | "
                f"Faltando: {' e '.join(faltando)} | Dados: Nome: '{nome}', "
                f"CPF: '{cpf}', Par: '{parentesco}'"
            )
        )
    return ocorrencias


def ratear_aba(df: pd.DataFrame, aba: str, ano: int) -> pd.DataFrame:
    """Distribui o valor anual do titular entre os membros da família.

    Câmara: só os dependentes recebem, e o primeiro membro fica fora da soma de
    meses. Complemento: todos recebem. Demais planos: só os 4 primeiros.
    """
    if "Tipo de Plano" not in df.columns:
        df["Tipo de Plano"] = (
            "Apartamento" if aba.lower().startswith("apartamento") else "Enfermaria"
        )
    df["Tipo de Plano"] = np.where(
        df["Tipo de Plano"].astype(str).str.strip().str.upper() == "APARTAMENTO",
        "Apartamento",
        "Enfermaria",
    )
    df["Deslig."] = pd.to_datetime(df["Deslig."], errors="coerce")
    df["Adm."] = pd.to_datetime(df["Adm."], errors="coerce")

    ativos = df[(df["Deslig."].dt.year >= ano) | pd.isna(df["Deslig."])].copy()
    ativos["CPF"] = ativos["CPF"].map(formatar_cpf)
    _atribuir_titulares(ativos)
    ativos["Total"] = 0.0
    ativos["Meses Ativos"] = pd.Series(
        [
            meses_ativos(adm, deslig, ano)
            for adm, deslig in zip(ativos["Adm."], ativos["Deslig."], strict=True)
        ],
        index=ativos.index,
        dtype=object,
    )
    ativos = ativos[ativos["Meses Ativos"].astype(bool)]
    camara = aba.lower().startswith("câmara")
    complemento = aba.lower().startswith("complemento")
    ativos["is_camara"] = camara
    ativos["is_complemento"] = complemento

    familias = ativos[ativos["Titular_CPF"].notna()]
    posicao = familias.groupby("Titular_CPF", sort=False).cumcount().to_numpy()
    meses = familias["Meses Ativos"].map(len).to_numpy()
    eh_titular = (familias["Relação"] == "Titular").to_numpy()

    if camara:
        conta_no_total = posicao > 0
    elif complemento:
        conta_no_total = np.ones(len(familias), dtype=bool)
    else:
        conta_no_total = posicao < MEMBROS_NO_RATEIO
    total_meses = (
        pd.Series(np.where(conta_no_total, meses, 0), index=familias.index)
        .groupby(familias["Titular_CPF"], sort=False)
        .sum()
    )

    primeiros_titulares = familias[eh_titular].drop_duplicates("Titular_CPF")
    valor_por_mes: dict[str, float] = {}
    for chave, valor_anual in zip(
        primeiros_titulares["Titular_CPF"],
        primeiros_titulares.get(config.COLUNA_TOTAL_ANUAL, [None] * len(primeiros_titulares)),
        strict=True,
    ):
        anual = float(valor_anual) if pd.notna(valor_anual) else 0
        meses_validos = int(total_meses[chave])
        valor_por_mes[chave] = anual / meses_validos if meses_validos > 0 else 0

    # Famílias sem titular ficam de fora, como sempre ficaram.
    rateadas = familias["Titular_CPF"].isin(list(valor_por_mes)).to_numpy()
    familias = familias[rateadas]
    posicao, meses, eh_titular = posicao[rateadas], meses[rateadas], eh_titular[rateadas]
    por_mes = familias["Titular_CPF"].map(valor_por_mes).to_numpy(dtype=float)
    recebe = ~eh_titular if camara else (
        np.ones(len(familias), dtype=bool) if complemento else posicao < MEMBROS_NO_RATEIO
    )
    familias = familias.assign(Total=np.where(recebe, por_mes * meses, 0.0))

    # Mesma ordem do agrupamento original: famílias por CPF do titular.
    return familias.sort_values("Titular_CPF", kind="stable").reset_index(drop=True)


def _atribuir_titulares(ativos: pd.DataFrame) -> None:
    """Liga cada dependente ao titular da linha "T." mais recente acima dele.

    Dependentes cujo titular não tem CPF ficam sem família, e o titular deles
    também é ignorado no rateio por falta de CPF válido.
    """
    parentesco = ativos["Par."].astype(str).str.strip().str.upper()
    eh_titular = parentesco == TITULAR
    cpf_do_titular = ativos["CPF"].where(eh_titular).ffill()
    plano_do_titular = ativos["Tipo de Plano"].where(eh_titular).ffill()
    dependente = ~eh_titular & cpf_do_titular.notna() & (cpf_do_titular != "")

    ativos["Titular_CPF"] = None
    ativos["Relação"] = None
    ativos.loc[eh_titular, "Titular_CPF"] = ativos.loc[eh_titular, "CPF"]
    ativos.loc[eh_titular, "Relação"] = "Titular"
    ativos.loc[dependente, "Titular_CPF"] = cpf_do_titular[dependente]
    ativos.loc[dependente, "Relação"] = parentesco[dependente].map(
        lambda par: RELACOES.get(par, "Outros")
    )
    ativos.loc[dependente, "Tipo de Plano"] = plano_do_titular[dependente]
