"""Elementos de tela compartilhados pelas páginas.

O visual de cada um está em estilo.css, ligado pelas chaves dos containers
(st.container(key=...) gera a classe st-key-<chave>).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from html import escape
from pathlib import Path
from typing import Literal

import pandas as pd
import streamlit as st
import streamlit.components.v1 as componentes
from streamlit.delta_generator import DeltaGenerator

FRONTEND = Path(__file__).resolve().parent
ASSETS = FRONTEND / "assets"
LOGO = ASSETS / "logo.png"
FAVICON = ASSETS / "favicon.jpeg"
ESTILO = FRONTEND / "estilo.css"
ALTERNADOR = FRONTEND / "alternador_de_tema.html"

ICONE_DOWNLOAD = ":material/download:"

# Onde o Streamlit guarda o tema escolhido pela pessoa ("Light", "Dark" ou
# "System"), por endereço de página. O sufixo é a versão do formato no
# Streamlit 1.66; se ele mudar, o interruptor de tema para de ter efeito.
CHAVE_DO_TEMA = "stActiveTheme-{caminho}-v2"
PAGINAS_DO_APP = ("/", "/DMED")

RODAPE = (
    "<div class='rodape'>Desenvolvido por "
    "<a href='https://www.linkedin.com/in/tairone-amaral/' target='_blank'>"
    "Tairone Amaral</a> e "
    "<a href='https://www.linkedin.com/in/heitor-sabino09/' target='_blank'>"
    "Heitor Sabino</a></div>"
)


class Chaves:
    """Chaves do st.session_state usadas pelas páginas."""

    CPF_CONSULTA = "cpf_input"
    SENHA = "password"
    SENHA_CORRETA = "password_correct"
    RESULTADO_DMED = "resultado_dmed"


def aplicar_identidade_visual() -> None:
    """Logo, CSS de estilo.css e o botão de tema; chamado uma vez pelo
    main.py, antes de qualquer página."""
    st.logo(str(LOGO), size="large")
    st.html(f"<style>{ESTILO.read_text(encoding='utf-8')}</style>")
    alternador_de_tema()


def tema_escuro() -> bool:
    return st.context.theme.type == "dark"


def alternador_de_tema() -> None:
    """Interruptor no canto do cabeçalho que alterna entre o tema claro e o
    escuro, por clique, arraste ou teclado (alternador_de_tema.html)."""
    escuro = tema_escuro()
    chaves = [CHAVE_DO_TEMA.format(caminho=caminho) for caminho in PAGINAS_DO_APP]
    pagina = (
        ALTERNADOR.read_text(encoding="utf-8")
        .replace("__ESTILO__", ESTILO.read_text(encoding="utf-8"))
        .replace("__ESCURO__", "true" if escuro else "false")
        .replace("__CHAVES__", json.dumps(chaves))
    )
    with st.container(key="tema"):
        componentes.html(pagina, width=100, height=56)
        if escuro:
            # Marca usada pelo CSS para trocar as variáveis de cor.
            st.html("<span class='tema-escuro'></span>")


@contextmanager
def heroi(
    titulo: str, subtitulo: str, *, acao: Callable[[], None] | None = None
) -> Iterator[None]:
    """Faixa com o gradiente da marca, título e o card principal de vidro.

    O que for escrito dentro do `with` vai para o card de vidro. `acao`
    desenha um botão ao lado do título (o Sair da página DMED).
    """
    with st.container(key="heroi"):
        if acao is None:
            st.title(titulo, anchor=False)
        else:
            esquerda, direita = st.columns([4, 1], vertical_alignment="center")
            with esquerda:
                st.title(titulo, anchor=False)
            with direita:
                acao()
        st.html(f"<p class='heroi-subtitulo'>{escape(subtitulo)}</p>")
        with st.container(key="vidro"):
            yield


def cartao(chave: str) -> DeltaGenerator:
    """Card branco com borda e sombra suaves."""
    return st.container(key=f"cartao_{chave}")


def secao(titulo: str, ajuda: str | None = None) -> None:
    st.subheader(titulo, anchor=False, help=ajuda)


def rodape() -> None:
    st.html(RODAPE)


def tabela_de_valores(nomes: pd.Series[str], valores: list[str]) -> None:
    """Beneficiários e valores já formatados em reais.

    Tabela estática: cabe na tela do celular e não tem barra de ferramentas,
    que não faz sentido em listas curtas.
    """
    st.table(
        pd.DataFrame({"Beneficiário": nomes.to_list(), "Valor": valores}),
        hide_index=True,
        border="horizontal",
    )


def botao_download(
    rotulo: str,
    dados: bytes,
    nome_arquivo: str,
    mime: str,
    *,
    tipo: Literal["primary", "secondary"] = "primary",
) -> None:
    """Download que não recarrega a página: o que está na tela continua lá."""
    st.download_button(
        rotulo,
        data=dados,
        file_name=nome_arquivo,
        mime=mime,
        type=tipo,
        icon=ICONE_DOWNLOAD,
        on_click="ignore",
        width="stretch",
    )


class Etapas:
    """Andamento de um processamento: cada etapa aparece como pendente, em
    andamento (com animação), concluída ou com falha, e a barra mostra o total."""

    def __init__(self, rotulos: list[str]) -> None:
        self.rotulos = rotulos
        self._lista = st.empty()
        self._barra = st.empty()

    def mostrar(self, atual: int, falhas: set[int] | None = None) -> None:
        """Etapas antes de `atual` concluídas; `atual` = len(rotulos) encerra."""
        falhas = falhas or set()
        itens = []
        for indice, rotulo in enumerate(self.rotulos):
            if indice in falhas:
                classe = "falhou"
            elif indice < atual:
                classe = "feita"
            elif indice == atual:
                classe = "atual"
            else:
                classe = ""
            itens.append(f"<li class='{classe}'>{escape(rotulo)}</li>")
        self._lista.html(f"<ol class='etapas'>{''.join(itens)}</ol>")

        total = len(self.rotulos)
        concluidas = min(atual, total)
        if concluidas < total:
            texto = f"Etapa {concluidas + 1} de {total}"
        else:
            texto = "Concluído com falhas" if falhas else "Concluído"
        self._barra.progress(concluidas / total, text=texto)


def plural(quantidade: int, singular: str, plural: str) -> str:
    return f"{quantidade} {singular if quantidade == 1 else plural}"
