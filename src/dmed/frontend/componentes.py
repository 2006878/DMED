"""Elementos de tela compartilhados pelas páginas."""

from __future__ import annotations

import base64
import html as html_padrao
from pathlib import Path

import streamlit as st

FRONTEND = Path(__file__).resolve().parent
ASSETS = FRONTEND / "assets"
FAVICON = str(ASSETS / "favicon.jpeg")
MANUAL = FRONTEND / "conteudo" / "manual_de_regras.md"

PAGINA_INICIO = "src/dmed/frontend/paginas/informe_irpf.py"
PAGINA_DMED = "src/dmed/frontend/paginas/arquivo_dmed.py"


class Chaves:
    """Chaves do st.session_state usadas pelas páginas."""

    CPF_CONSULTA = "cpf_input"
    SENHA = "password"
    SENHA_CORRETA = "password_correct"


CSS_OCULTAR_NAVEGACAO = """
    <style>
    /* Oculta todos os elementos de navegação */
    section[data-testid="stSidebar"] ul {
        display: none !important;
    }
    </style>
"""

CSS_OCULTAR_CABECALHO = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""

CSS_CARTOES = """
    /* Estilização dos containers de informações */
    .info-container {
        background-color: #D9E3DA; /* Verde claro */
        padding: 10px;
        margin-bottom: 5px;
        border-radius: 5px;
    }
    .info-container h4 {
        color: #005822; /* Verde escuro */
        margin: 0;
    }
    .info-container p {
        font-size: 18px;
        margin: 5px 0;
    }
"""

CSS_BOTAO_DOWNLOAD = """
    /* Centralizar botão de download */
    [data-testid="stDownloadButton"] {
        display: block;
        margin: 0 auto;
        max-width: 300px;
    }
"""

RODAPE = """
    <hr style='border:1px solid #e3e3e3;margin-top:40px'>
    <div style='text-align: center;'>
        Desenvolvido por
        <a href='https://www.linkedin.com/in/tairone-amaral/' target='_blank'>
            Tairone Amaral
        </a>
    </div>
"""


def html(conteudo: str) -> None:
    st.markdown(conteudo, unsafe_allow_html=True)


def configurar_pagina(titulo: str) -> None:
    st.set_page_config(
        page_title=titulo,
        page_icon=FAVICON,
        initial_sidebar_state="expanded",
        layout="wide",
    )


def menu_lateral(*, na_pagina_inicial: bool) -> None:
    """Menu próprio no lugar da navegação padrão, que fica oculta."""
    with st.sidebar:
        st.title("Menu COSEMI")
        if st.button("🏠 Home", disabled=na_pagina_inicial):
            st.switch_page(PAGINA_INICIO)
        if st.button("⚙️ DMED", disabled=not na_pagina_inicial):
            st.switch_page(PAGINA_DMED)


def exibir_logo() -> None:
    imagem = base64.b64encode((ASSETS / "logo.png").read_bytes()).decode()
    html(
        f"""
    <div style="display: flex; justify-content: center; margin: 1em 0;">
        <img src="data:image/png;base64,{imagem}" style="max-width: 300px; width: 100%; height: auto;">
    </div>
"""
    )


def cartao(titulo: object | None, texto: str) -> None:
    """Cartão verde com título opcional; o título é escapado (vem das planilhas).

    Sem linhas em branco: no Markdown elas encerrariam o bloco HTML.
    """
    linhas = ["<div class='info-container'>"]
    if titulo is not None:
        linhas.append(f"    <h4>{escapar(titulo)}</h4>")
    linhas += [f"    <p>{texto}</p>", "</div>"]
    html("\n".join(linhas))


def escapar(texto: object) -> str:
    return html_padrao.escape(str(texto), quote=False)
