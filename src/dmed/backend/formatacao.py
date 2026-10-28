"""Conversões de CPF, nomes e valores monetários entre planilhas, tela e DMED."""

from __future__ import annotations

import re
import unicodedata

import pandas as pd


def formatar_cpf(cpf: object) -> str:
    """CPF com 11 dígitos, aceitando número, texto com máscara ou '123.0'."""
    if pd.isna(cpf) or str(cpf).strip() == "" or str(cpf).strip() == "0":  # type: ignore[call-overload]
        return ""
    if isinstance(cpf, int | float):
        cpf_str = str(int(float(cpf))) if float(cpf).is_integer() else str(cpf).strip()
    else:
        cpf_str = str(cpf).strip()
        if re.fullmatch(r"\d+\.0", cpf_str):
            cpf_str = cpf_str[:-2]

    cpf_str = re.sub(r"\D", "", cpf_str)
    if not cpf_str:
        return ""
    return cpf_str.zfill(11)


def formatar_valor_dmed(valor: object) -> str:
    """Valor em centavos com 9 dígitos, como o arquivo DMED exige.

    Os centavos são truncados (int), não arredondados, e zero vira R$ 0,01:
    é o comportamento que o arquivo enviado à Receita sempre teve.
    """
    try:
        texto = str(valor).replace("R$", "").strip()
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        valor_float = round(float(texto), 2)
        if valor_float == 0 or pd.isna(valor_float):
            valor_float = 0.01
        return f"{int(valor_float * 100):09d}"
    except (ValueError, OverflowError):
        return ""


def ler_valor_monetario(valor: object) -> float:
    """Lê 'R$ 1.234,56', '1234.56' ou um número; o que não for valor vira 0.0."""
    if pd.isna(valor):  # type: ignore[call-overload]
        return 0.0
    texto = str(valor).replace("R$", "").strip()
    if not texto:
        return 0.0

    # Com vírgula, o formato é brasileiro (milhar com ponto, decimal com vírgula).
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = re.sub(r"[^0-9.\-]", "", texto)

    try:
        return round(float(texto), 2)
    except ValueError:
        return 0.0


def normalizar_nome(nome: object) -> str:
    """Maiúsculas, sem acentos e só com letras, dígitos e espaços."""
    normalizado = unicodedata.normalize("NFKD", str(nome).upper())
    normalizado = "".join(c for c in normalizado if not unicodedata.combining(c))
    normalizado = normalizado.replace("Ç", "C")
    return "".join(c for c in normalizado if c.isalnum() or c.isspace())


def formatar_numero(valor: float) -> str:
    """1234.5 -> '1.234,50'."""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_moeda(valor: float) -> str:
    """1234.5 -> 'R$ 1.234,50'."""
    return f"R$ {formatar_numero(valor)}"
