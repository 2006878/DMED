"""Informe de plano de saúde para o IRPF, em PDF."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, cast

import pandas as pd
from fpdf import FPDF

from dmed.backend import config
from dmed.backend.formatacao import formatar_moeda, formatar_numero


def valor_para_soma(valor_moeda: object) -> str:
    """'R$ 1.234,56' -> '1234.56': só dígitos e a vírgula decimal, que vira ponto.

    É a conversão usada no total do informe e nos valores exibidos na tela.
    Como descarta tudo que não é dígito ou vírgula, o sinal de negativo some.
    """
    return re.sub(r"[^\d,]", "", str(valor_moeda).strip()).replace(",", ".")


def valor_para_exibicao(valor_moeda: object) -> str:
    """Valor de mensalidade como aparece na tela inicial ('1.234,56')."""
    convertido = valor_para_soma(valor_moeda)
    texto = (
        convertido.replace("R$", "")
        .replace(".", "", convertido.count(".") - 1)
        .replace(",", ".")
        .strip()
    )
    try:
        return formatar_numero(float(texto))
    except ValueError:
        return "Valor inválido"


def gerar_informe_pdf(
    mensalidades: pd.DataFrame, despesas: pd.DataFrame, descontos: str, cpf: str
) -> bytes:
    """Gera o informe a partir das tabelas da consulta, sem alterá-las."""
    pdf: Any = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def secao(titulo: str, linhas: list[str]) -> None:
        """Título sublinhado e borda ao redor do conteúdo."""
        pdf.set_font("Arial", "B", 12)
        inicio_y = pdf.get_y()
        pdf.cell(0, 8, titulo, ln=True, align="L")
        pdf.set_draw_color(0, 0, 0)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Arial", "", 12)
        for linha in linhas:
            pdf.cell(0, 6, linha, ln=True)
        fim_y = pdf.get_y()
        pdf.rect(10, inicio_y, 190, fim_y - inicio_y + 2)
        pdf.ln(6)

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "INFORME PLANO DE SAÚDE", ln=True, align="C")
    pdf.ln(3)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, f"ANO - CALENDÁRIO DE {config.ano_calendario()}", ln=True, align="C")
    pdf.cell(0, 8, "IMPOSTO DE RENDA - PESSOA FÍSICA", ln=True, align="C")
    pdf.ln(10)

    titular = mensalidades.iloc[0]["Nome"] if not mensalidades.empty else "N/A"
    secao("1 - DADOS CADASTRAIS", [f"Titular: {titular} - CPF: {cpf}"])
    secao(
        "2 - IDENTIFICAÇÃO DA FONTE PAGADORA",
        [
            f"Nome empresarial: {config.RAZAO_SOCIAL_PDF[0]}",
            config.RAZAO_SOCIAL_PDF[1],
            f"CNPJ: {config.CNPJ_FORMATADO}",
        ],
    )
    secao(
        "3 - INFORMAÇÕES PLANO DE SAÚDE",
        ["Mensalidade Plano de Saúde:", *_linhas_nome_valor(mensalidades)],
    )
    secao("4 - INFORMAÇÕES DESPESAS", _linhas_nome_valor(despesas))

    valores = mensalidades["Valor"].map(valor_para_soma)
    total_mensalidades = valores[valores != ""].astype(float).sum()
    secao(
        "5 - TOTAIS",
        [
            f"Total de Despesas: {descontos}",
            f"Total de Mensalidades: {formatar_moeda(total_mensalidades)}",
        ],
    )

    pdf.cell(0, 6, f"Documento criado em: {datetime.now():%d/%m/%Y}", ln=True, align="C")
    return cast(str, pdf.output(dest="S")).encode("latin-1")


def _linhas_nome_valor(tabela: pd.DataFrame) -> list[str]:
    linhas = []
    for _, linha in tabela.iterrows():
        nome = linha["Nome"] if "Nome" in linha else "N/A"
        valor = linha["Valor"] if "Valor" in linha else "R$ 0,00"
        linhas.append(f"Nome: {nome} - Valor: {valor}")
    return linhas
