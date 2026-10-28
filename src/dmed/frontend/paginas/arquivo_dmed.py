"""Página protegida por senha que gera o arquivo DMED e o relatório de erros."""

from __future__ import annotations

import hmac
import logging

import streamlit as st

from dmed.backend import config
from dmed.backend.arquivo_dmed import Responsavel, gerar_arquivo_dmed
from dmed.backend.ocorrencias import Ocorrencia
from dmed.frontend.componentes import (
    CSS_BOTAO_DOWNLOAD,
    CSS_CARTOES,
    CSS_OCULTAR_CABECALHO,
    CSS_OCULTAR_NAVEGACAO,
    MANUAL,
    RODAPE,
    Chaves,
    configurar_pagina,
    exibir_logo,
    html,
    menu_lateral,
)

logger = logging.getLogger(__name__)

DIGITOS_CPF = 11

configurar_pagina("ARQUIVO DMED - COSEMI")
exibir_logo()
html(CSS_OCULTAR_NAVEGACAO)
menu_lateral(na_pagina_inicial=False)


def _senha_configurada() -> str | None:
    try:
        return str(st.secrets["password"])
    except (KeyError, FileNotFoundError):
        return None


def _conferir_senha() -> None:
    correta = _senha_configurada()
    digitada = str(st.session_state[Chaves.SENHA])
    st.session_state[Chaves.SENHA_CORRETA] = (
        correta is not None and hmac.compare_digest(digitada.encode(), correta.encode())
    )
    if st.session_state[Chaves.SENHA_CORRETA]:
        del st.session_state[Chaves.SENHA]  # não guarda a senha na sessão


def senha_confirmada() -> bool:
    if st.session_state.get(Chaves.SENHA_CORRETA):
        return True
    st.text_input("Senha", type="password", on_change=_conferir_senha, key=Chaves.SENHA)
    if Chaves.SENHA_CORRETA in st.session_state:
        if _senha_configurada() is None:
            st.error("A senha desta página não está configurada (secrets.toml).")
        else:
            st.error("😕 Senha incorreta")
    return False


def relatorio_de_erros(ocorrencias: list[Ocorrencia]) -> str:
    separador = "========================================================\n"
    return (
        separador
        + "RELATORIO DE INCONSISTENCIAS - COSEMI DMED\n"
        + f"Gerado em: {config.agora():%d/%m/%Y as %H:%M:%S}\n"
        + separador
        + "\n"
        + "Por favor, corrija as linhas listadas abaixo nas planilhas originais:\n\n"
        + "\n".join(str(o) for o in ocorrencias)
    )


def exibir_resultado(conteudo: str | None, ocorrencias: list[Ocorrencia]) -> None:
    impede_envio = any(o.severidade.bloqueante for o in ocorrencias)
    hoje = f"{config.agora():%Y%m%d}"

    if conteudo and impede_envio:
        st.warning(
            "⚠️ **ATENÇÃO:** O arquivo DMED foi gerado conforme solicitado, mas "
            "**existem dados obrigatórios em branco** nas planilhas originais!"
        )
        st.info(
            "Recomendamos baixar o Relatório de Erros e fazer a correção antes de "
            "enviar à Receita Federal."
        )
        coluna_erros, coluna_dmed = st.columns(2)
        with coluna_erros:
            st.download_button(
                label="📥 BAIXAR RELATÓRIO DE ERROS (.txt)",
                data=relatorio_de_erros(ocorrencias).encode("utf-8"),
                file_name=f"Erros_Planilhas_{hoje}.txt",
                mime="text/plain",
                type="primary",
            )
        with coluna_dmed:
            st.download_button(
                label="📥 BAIXAR DMED (COM ERROS) (.DEC)",
                data=conteudo.encode("utf-8"),
                file_name=f"DMED_{hoje}.DEC",
                mime="text/plain",
            )
    elif conteudo:
        st.success("✅ Arquivo DMED gerado e validado com sucesso!")
        if ocorrencias:
            with st.expander("⚠️ Avisos do Processamento (Não Impeditivos)"):
                for ocorrencia in ocorrencias:
                    st.write(str(ocorrencia))
        st.download_button(
            label="📥 BAIXAR ARQUIVO DMED (.DEC)",
            data=conteudo.encode("utf-8"),
            file_name=f"DMED_{hoje}.DEC",
            mime="text/plain",
            type="primary",
        )
    else:
        st.error("Falha Crítica. O sistema não conseguiu montar o arquivo DMED.")
        for ocorrencia in ocorrencias:
            st.write(str(ocorrencia))


if senha_confirmada():
    st.title("DOWNLOAD ARQUIVO DMED - COSEMI")
    html(CSS_OCULTAR_CABECALHO)
    html(
        f"""
        <style>
        /* Centralizar títulos */
        h1, h2, h3 {{
            text-align: center;
        }}
        {CSS_BOTAO_DOWNLOAD}
        {CSS_CARTOES}
        /* Ajuste do Expander */
        .streamlit-expanderContent {{
            display: flex;
            justify-content: center;
            align-items: center;
            text-align: center;
        }}
        .streamlit-expanderContent div {{
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
        }}
        </style>
    """
    )
    html(
        "<h3 style='font-size: 24px;'>Insira as informações abaixo para processar e "
        "criar o arquivo:</h3>"
    )

    coluna_esquerda, coluna_direita = st.columns(2)
    with coluna_esquerda:
        cpf_digitado = st.text_input(
            "Digite o CPF do Responsável aqui (apenas números):",
            max_chars=DIGITOS_CPF,
            help="Digite apenas os 11 números do CPF, sem pontos ou traços",
        )
        cpf_responsavel = "".join(filter(str.isdigit, cpf_digitado))
        if cpf_digitado and len(cpf_responsavel) != DIGITOS_CPF:
            st.error("CPF deve conter exatamente 11 dígitos e sem pontos ou traços.")
            cpf_responsavel = ""
        nome_responsavel = st.text_input("Digite o nome do Responsável aqui.")

    with coluna_direita:
        ddd = st.text_input(
            "Digite o DDD do telefone do Responsável aqui (apenas números):",
            max_chars=2,
            help="Digite apenas os 2 números, sem pontos ou traços",
        )
        telefone = st.text_input(
            "Digite o telefone do Responsável aqui (apenas números):",
            max_chars=9,
            help="Digite apenas os números do telefone, sem pontos ou traços",
        )

    preenchido = all((cpf_responsavel, nome_responsavel, ddd, telefone))
    if preenchido and st.button("📥 Processar e criar arquivo DMED"):
        with st.spinner(
            "Analisando planilhas, validando regras e gerando arquivo... "
            "(Isso pode levar alguns instantes)"
        ):
            try:
                conteudo, ocorrencias = gerar_arquivo_dmed(
                    Responsavel(cpf_responsavel, nome_responsavel, ddd, telefone)
                )
            except Exception as falha:
                # Falha inesperada: mostra a mensagem em vez de derrubar a página.
                logger.exception("Falha ao gerar o arquivo DMED")
                st.error(f"Ocorreu um erro crítico no sistema: {falha}")
            else:
                exibir_resultado(conteudo, ocorrencias)

    with st.expander("Manual de regras", expanded=False):
        st.markdown(MANUAL.read_text(encoding="utf-8"))

    html(RODAPE)
