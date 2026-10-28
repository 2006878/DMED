"""Infraestrutura comum dos testes: relógio congelado, rede bloqueada e um
ambiente de execução com planilhas fictícias montadas a partir de
tests/fixtures/."""

import contextlib
import datetime as dt
import re
import shutil
import zlib
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest
import requests
import time_machine

RAIZ = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
ESPERADO = FIXTURES / "esperado"

# Onde o app espera as planilhas, relativo à pasta de execução.
PASTA_MENSALIDADES = Path("data/mensalidades")
PASTA_DESPESAS = Path("data/despesas")
PASTA_DESCONTOS = Path("data/descontos")

# O ano-calendário vem do relógio; congelar mantém as saídas estáveis entre anos.
AGORA = dt.datetime(2026, 3, 15, 12, 0, tzinfo=dt.timezone(dt.timedelta(hours=-3)))
_viagem = time_machine.travel(AGORA, tick=True)


def pytest_configure(config: pytest.Config) -> None:
    _viagem.start()


def pytest_unconfigure(config: pytest.Config) -> None:
    _viagem.stop()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--atualizar-esperado",
        action="store_true",
        help="Regrava as saídas esperadas em tests/fixtures/esperado/.",
    )


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch: pytest.MonkeyPatch) -> None:
    def bloqueia(*args: object, **kwargs: object) -> None:
        raise RuntimeError("acesso à rede bloqueado nos testes")

    monkeypatch.setattr(requests.Session, "request", bloqueia)


def monta_xlsx(origem: Path, destino: Path) -> None:
    """Gera uma planilha com uma aba por CSV de `origem` (`<ordem>-<aba>.csv`)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(destino, engine="openpyxl") as planilha:
        for csv in sorted(origem.glob("*.csv")):
            df = pd.read_csv(csv, encoding="utf-8")
            for coluna in ("Adm.", "Deslig."):
                if coluna in df.columns:
                    df[coluna] = pd.to_datetime(df[coluna])
            df.to_excel(planilha, sheet_name=csv.stem.split("-", 1)[1], index=False)


def monta_pasta(origem: Path, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for item in sorted(origem.iterdir()):
        if item.is_dir():
            monta_xlsx(item, destino / f"{item.name}.xlsx")
        else:
            shutil.copy(item, destino / item.name)


@pytest.fixture
def ambiente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pasta de execução com as planilhas fictícias."""
    monta_xlsx(
        FIXTURES / "mensalidades", tmp_path / PASTA_MENSALIDADES / "MENSALIDADES.xlsx"
    )
    monta_pasta(FIXTURES / "despesas", tmp_path / PASTA_DESPESAS)
    monta_pasta(FIXTURES / "descontos", tmp_path / PASTA_DESCONTOS)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def esperado(request: pytest.FixtureRequest) -> Callable[[str, str], None]:
    """Compara um texto com tests/fixtures/esperado/<nome> (ou o regrava)."""
    atualizar = request.config.getoption("--atualizar-esperado")

    def comparar(nome: str, obtido: str) -> None:
        arquivo = ESPERADO / nome
        if atualizar:
            arquivo.parent.mkdir(parents=True, exist_ok=True)
            arquivo.write_text(obtido, encoding="utf-8", newline="\n")
        assert obtido == arquivo.read_text(encoding="utf-8")

    return comparar


def csv_texto(df: pd.DataFrame) -> str:
    return df.to_csv(index=False, lineterminator="\n")


def normaliza_pdf(pdf: bytes) -> str:
    """Descomprime o conteúdo do PDF e troca datas e offsets por marcadores."""

    def descomprime(m: re.Match[bytes]) -> bytes:
        dados = m.group(1)
        with contextlib.suppress(zlib.error):
            dados = zlib.decompress(dados)
        return (
            b"stream\n"
            + re.sub(rb"\d{2}/\d{2}/\d{4}", b"<DATA>", dados)
            + b"\nendstream"
        )

    pdf = re.sub(rb"stream\r?\n(.*?)\r?\nendstream", descomprime, pdf, flags=re.S)
    pdf = re.sub(rb"/CreationDate \(D:\d+\)", b"/CreationDate (D:X)", pdf)
    pdf = re.sub(rb"/Length \d+", b"/Length X", pdf)
    pdf = re.sub(rb"\d{10} \d{5} [nf]", b"X", pdf)
    pdf = re.sub(rb"startxref\s+\d+", b"startxref X", pdf)
    return pdf.decode("latin-1")
