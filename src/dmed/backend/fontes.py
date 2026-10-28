"""Acesso a arquivos e ao Google Drive: planilhas de entrada e caches em CSV."""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests

from dmed.backend import config
from dmed.backend.config import Planilha

logger = logging.getLogger(__name__)

# O Streamlit atende cada sessão numa thread do mesmo processo: a trava impede
# que dois processamentos gravem os caches ao mesmo tempo.
TRAVA = threading.RLock()

EXTENSOES_EXCEL = (".xlsx", ".xlsm", ".xls")


class CacheIndisponivel(RuntimeError):
    """O CSV processado não existe ou não pôde ser lido."""


def baixar_planilha(planilha: Planilha) -> None:
    """Baixa a planilha do Drive e só substitui a local se o download der certo."""
    destino = config.destino_planilha(planilha)
    resposta = requests.get(config.url_drive(planilha), timeout=config.TIMEOUT_DOWNLOAD)
    resposta.raise_for_status()
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".baixando")
    temporario.write_bytes(resposta.content)
    temporario.replace(destino)
    logger.info("Planilha %s atualizada a partir do Google Drive.", destino.name)


def baixar_planilhas_do_drive() -> tuple[bool, str]:
    """Atualiza as planilhas de descontos e de mensalidades a partir do Drive."""
    with TRAVA:
        try:
            for planilha in (Planilha.DESCONTOS, Planilha.MENSALIDADES):
                baixar_planilha(planilha)
        except (requests.RequestException, OSError, config.ConfiguracaoAusente) as erro:
            logger.warning("Falha ao baixar as planilhas do Google Drive: %s", erro)
            return False, f"❌ Erro ao atualizar os arquivos físicos: {erro}"
    return True, "Planilhas de Descontos e Mensalidades baixadas e atualizadas!"


def arquivos_da_pasta(pasta: Path) -> list[Path]:
    """Arquivos da pasta em ordem alfabética, igual no Windows e no Linux."""
    return sorted(
        (item for item in pasta.iterdir() if item.is_file()),
        key=lambda item: item.name.casefold(),
    )


def abas_da_planilha(arquivo: Path) -> Iterator[tuple[str, pd.DataFrame]]:
    with pd.ExcelFile(arquivo, engine="openpyxl") as excel:
        for aba in excel.sheet_names:
            yield str(aba), pd.read_excel(excel, sheet_name=aba, engine="openpyxl")


def caminho_cache(nome: str) -> Path:
    return config.pasta_cache() / f"{nome}.csv"


def gravar_cache(df: pd.DataFrame, nome: str) -> Path:
    """Grava o CSV por cópia temporária e troca atômica: leitores nunca veem metade."""
    destino = caminho_cache(nome)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".gravando")
    df.to_csv(temporario, index=False)
    temporario.replace(destino)
    return destino


def cache_existe(nome: str) -> bool:
    caminho = caminho_cache(nome)
    return caminho.exists() and caminho.stat().st_size > 0


def assinatura(caminho: Path) -> tuple[str, int, int] | None:
    """Identifica a versão do arquivo; muda sempre que ele é regravado."""
    try:
        estado = caminho.stat()
    except FileNotFoundError:
        return None
    return str(caminho), estado.st_mtime_ns, estado.st_size


def ler_cache(nome: str, *, como_texto: bool) -> pd.DataFrame:
    """Lê o CSV processado. Devolve uma cópia: quem chama pode alterá-la."""
    versao = assinatura(caminho_cache(nome))
    if versao is None:
        raise CacheIndisponivel(nome)
    return _ler_csv(versao, como_texto).copy()


@lru_cache(maxsize=8)
def _ler_csv(versao: tuple[str, int, int], como_texto: bool) -> pd.DataFrame:
    caminho = Path(versao[0])
    try:
        if como_texto:
            return pd.read_csv(caminho, dtype=str)
        return pd.read_csv(caminho)
    except (OSError, ValueError) as erro:
        raise CacheIndisponivel(caminho.name) from erro
