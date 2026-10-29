"""Ponto de entrada do Streamlit: registra as páginas e executa a escolhida."""

import logging
import os
import sys
from pathlib import Path

import streamlit as st

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

RAIZ = Path(__file__).resolve().parent
SRC = str(RAIZ / "src")
# Torna o pacote dmed importável sem instalá-lo. O Streamlit reexecuta este
# arquivo a cada interação, então só insere uma vez.
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from dmed.frontend.componentes import FAVICON, aplicar_identidade_visual  # noqa: E402

PAGINAS = RAIZ / "src" / "dmed" / "frontend" / "paginas"


def exportar_ids_do_drive() -> None:
    """Passa a seção [drive] do secrets.toml para o ambiente, onde o backend a lê."""
    try:
        ids = dict(st.secrets.get("drive", {}))
    except FileNotFoundError:  # nenhum secrets.toml configurado
        return
    for planilha, id_arquivo in ids.items():
        os.environ.setdefault(f"DMED_DRIVE_{planilha.upper()}", str(id_arquivo))


exportar_ids_do_drive()
st.set_page_config(page_title="COSEMI", page_icon=str(FAVICON), layout="centered")
aplicar_identidade_visual()
st.navigation(
    [
        st.Page(
            PAGINAS / "informe_irpf.py",
            title="Informe IRPF",
            icon=":material/receipt_long:",
            default=True,
        ),
        st.Page(
            PAGINAS / "arquivo_dmed.py",
            title="Arquivo DMED",
            icon=":material/description:",
            url_path="DMED",
        ),
    ],
    position="top",
).run()
