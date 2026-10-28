"""Ponto de entrada do Streamlit: registra as páginas e executa a escolhida."""

import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent
SRC = str(RAIZ / "src")
# Torna o pacote dmed importável sem instalá-lo. O Streamlit reexecuta este
# arquivo a cada interação, então só insere uma vez.
if SRC not in sys.path:
    sys.path.insert(0, SRC)

PAGINAS = RAIZ / "src" / "dmed" / "frontend" / "paginas"

st.navigation(
    [
        st.Page(PAGINAS / "informe_irpf.py", default=True),
        st.Page(PAGINAS / "arquivo_dmed.py", url_path="DMED"),
    ],
    position="hidden",
).run()
