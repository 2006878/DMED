"""Caminhos, constantes da declaração e acesso à configuração do Google Drive."""

from __future__ import annotations

import os
from datetime import datetime
from enum import StrEnum
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]

# Fonte pagadora, como aparece no PDF e no arquivo DMED.
CNPJ = "16651002000180"
CNPJ_FORMATADO = "16.651.002/0001-80"
RAZAO_SOCIAL_DMED = (
    "COOPERATIVA DE ECONOMIA E CREDITO MUTUO DOS SERVIDORES MUNICIPAIS DE ITABIRA "
    "LTDA SICOOB COSEMI"
)
RAZAO_SOCIAL_PDF = (
    "Cosemi - Cooperativa de Economia E Credito Mutuo dos",
    "Servidores Municipais de Itabira Ltda",
)
REGISTRO_ANS = "419761"

# A planilha de mensalidades mantém este nome de coluna para o total anual.
COLUNA_TOTAL_ANUAL = "Total 2024"
ARQUIVO_MENSALIDADES = "MENSALIDADES.xlsx"
ARQUIVO_DESCONTOS = "DESCONTOS.xlsx"

TIMEOUT_DOWNLOAD = (10, 120)  # segundos para conectar e para receber


class Planilha(StrEnum):
    """Planilhas baixadas do Google Drive (o valor é a chave em secrets.toml)."""

    MENSALIDADES = "mensalidades"
    DESCONTOS = "descontos"


class ConfiguracaoAusente(RuntimeError):
    """Falta uma configuração obrigatória em secrets.toml ou no ambiente."""


def ano_calendario() -> int:
    return pd.Timestamp.now().year - 1


def ano_entrega() -> int:
    return pd.Timestamp.now().year


def pasta_dados() -> Path:
    # Os testes apontam DMED_PASTA_DADOS para uma pasta temporária.
    return Path(os.environ.get("DMED_PASTA_DADOS", RAIZ / "data"))


def pasta_mensalidades() -> Path:
    return pasta_dados() / "mensalidades"


def pasta_despesas() -> Path:
    return pasta_dados() / "despesas"


def pasta_descontos() -> Path:
    return pasta_dados() / "descontos"


def pasta_cache() -> Path:
    return pasta_dados() / "cache"


def destino_planilha(planilha: Planilha) -> Path:
    if planilha is Planilha.MENSALIDADES:
        return pasta_mensalidades() / ARQUIVO_MENSALIDADES
    return pasta_descontos() / ARQUIVO_DESCONTOS


def variavel_drive(planilha: Planilha) -> str:
    return f"DMED_DRIVE_{planilha.name}"


def url_drive(planilha: Planilha) -> str:
    """URL de download do arquivo no Google Drive.

    O ID vem da variável DMED_DRIVE_<PLANILHA>, que o main.py preenche a partir
    da seção [drive] do secrets.toml.
    """
    id_arquivo = os.environ.get(variavel_drive(planilha))
    if not id_arquivo:
        raise ConfiguracaoAusente(
            f"ID do Google Drive para '{planilha.value}' não configurado "
            "(seção [drive] do secrets.toml)."
        )
    return f"https://drive.google.com/uc?id={id_arquivo}"


def agora() -> datetime:
    """Data e hora do servidor, usadas no PDF e no relatório de erros."""
    return datetime.now()  # noqa: DTZ005 - mantém o horário que o app sempre usou
