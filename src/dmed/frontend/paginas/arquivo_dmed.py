"""Página protegida por senha: gera o arquivo DMED, mostra as pendências das
planilhas e atualiza as planilhas a partir do Google Drive."""

from __future__ import annotations

import hmac
import logging

import pandas as pd
import streamlit as st

from dmed.backend import config, fontes
from dmed.backend.arquivo_dmed import gerar_arquivo_dmed
from dmed.backend.config import Planilha
from dmed.backend.descontos import processar_descontos
from dmed.backend.despesas import processar_despesas
from dmed.backend.mensalidades import processar_mensalidades
from dmed.backend.ocorrencias import Severidade
from dmed.frontend.componentes import (
    Chaves,
    Etapas,
    botao_download,
    cartao,
    heroi,
    plural,
    rodape,
    secao,
)
from dmed.frontend.resultado_dmed import ResultadoDmed
from dmed.frontend.validacao import validar_responsavel

logger = logging.getLogger(__name__)

GRAVIDADE = {
    Severidade.CRITICO: "Crítico",
    Severidade.ERRO: "Erro",
    Severidade.AVISO: "Aviso",
    Severidade.ALERTA: "Alerta",
}
AJUDA_TECNICA = "Tente de novo; se continuar, avise o responsável técnico."


# Acesso -------------------------------------------------------------------


def _senha_configurada() -> str | None:
    try:
        return str(st.secrets["password"])
    except (KeyError, FileNotFoundError):
        return None


def _conferir_senha() -> None:
    correta = _senha_configurada()
    digitada = str(st.session_state.get(Chaves.SENHA, ""))
    st.session_state[Chaves.SENHA_CORRETA] = (
        correta is not None and hmac.compare_digest(digitada.encode(), correta.encode())
    )
    if st.session_state[Chaves.SENHA_CORRETA]:
        del st.session_state[Chaves.SENHA]  # não guarda a senha na sessão


def _sair() -> None:
    st.session_state.pop(Chaves.SENHA_CORRETA, None)
    st.session_state.pop(Chaves.RESULTADO_DMED, None)


def formulario_de_acesso() -> None:
    st.caption("Área restrita à equipe administrativa.")
    with st.form("acesso", border=False):
        st.text_input("Senha", type="password", key=Chaves.SENHA)
        st.form_submit_button("Entrar", type="primary", on_click=_conferir_senha)
    if Chaves.SENHA_CORRETA in st.session_state:
        if _senha_configurada() is None:
            st.error(
                "A senha desta página ainda não foi configurada. Peça ao "
                "responsável técnico para cadastrá-la nos secrets do app.",
                icon=":material/lock:",
            )
        else:
            st.error("Senha incorreta. Tente de novo.", icon=":material/lock:")


def _botao_sair() -> None:
    st.button("Sair", icon=":material/logout:", on_click=_sair)


# Geração do arquivo ---------------------------------------------------------


def formulario_do_responsavel() -> None:
    with st.form("responsavel", border=False):
        secao(
            "Responsável pelo preenchimento",
            "Dados que vão no registro do responsável (RESPO) dentro do arquivo.",
        )
        cpf, nome = st.columns([1, 2])
        cpf.text_input(
            "CPF", key="dmed_cpf", placeholder="000.000.000-00", max_chars=14
        )
        nome.text_input("Nome completo", key="dmed_nome")
        ddd, telefone = st.columns([1, 2])
        ddd.text_input("DDD", key="dmed_ddd", placeholder="31", max_chars=2)
        telefone.text_input(
            "Telefone", key="dmed_telefone", placeholder="99999-9999", max_chars=10
        )
        enviado = st.form_submit_button(
            "Gerar arquivo DMED", type="primary", icon=":material/description:"
        )
    if not enviado:
        return

    responsavel, problemas = validar_responsavel(
        st.session_state.dmed_cpf,
        st.session_state.dmed_nome,
        st.session_state.dmed_ddd,
        st.session_state.dmed_telefone,
    )
    if responsavel is None:
        st.error(
            "Confira os campos antes de gerar o arquivo:\n\n"
            + "\n".join(f"- {problema}" for problema in problemas),
            icon=":material/edit_note:",
        )
        return

    with st.status("Gerando o arquivo DMED...", expanded=True) as status:
        etapas = Etapas(["Processar as planilhas e montar o arquivo"])
        etapas.mostrar(0)
        try:
            conteudo, ocorrencias = gerar_arquivo_dmed(responsavel)
        except Exception as falha:
            # Falha inesperada: mostra a mensagem em vez de derrubar a página.
            logger.exception("Falha ao gerar o arquivo DMED")
            resultado = ResultadoDmed(None, falha=str(falha))
            etapas.mostrar(1, falhas={0})
            status.update(label="Não foi possível gerar o arquivo", state="error")
        else:
            resultado = ResultadoDmed(conteudo, ocorrencias)
            etapas.mostrar(1)
            status.update(
                label="Processamento concluído", state="complete", expanded=False
            )
    st.session_state[Chaves.RESULTADO_DMED] = resultado


def exibir_resultado(resultado: ResultadoDmed) -> None:
    with cartao("resultado"):
        _resumo(resultado)
    if resultado.ocorrencias:
        with cartao("pendencias"):
            _pendencias(resultado)


def _resumo(resultado: ResultadoDmed) -> None:
    secao("Resultado")
    st.caption(f"Gerado em {resultado.gerado_em:%d/%m/%Y às %H:%M}")

    if resultado.falha:
        st.error(
            f"Ocorreu um erro inesperado ao gerar o arquivo. {AJUDA_TECNICA}",
            icon=":material/error:",
        )
        with st.expander("Detalhes técnicos"):
            st.code(resultado.falha, language=None)
        return

    bloqueantes = resultado.bloqueantes
    avisos = len(resultado.ocorrencias) - len(bloqueantes)
    if resultado.conteudo is None:
        st.error(
            "O arquivo não foi montado: a planilha de mensalidades não pôde ser "
            "processada. Corrija as pendências abaixo e gere de novo.",
            icon=":material/error:",
        )
    elif bloqueantes:
        st.warning(
            "Arquivo gerado com "
            f"{plural(len(bloqueantes), 'pendência', 'pendências')} que impedem "
            "o envio. Corrija as planilhas e gere de novo antes de enviar à "
            "Receita Federal.",
            icon=":material/warning:",
        )
    else:
        complemento = (
            f" Há {plural(avisos, 'aviso', 'avisos')} que não impedem o envio."
            if avisos
            else ""
        )
        st.success(
            f"Arquivo pronto para envio à Receita Federal.{complemento}",
            icon=":material/check_circle:",
        )

    if resultado.conteudo is not None:
        # Grade 2x2: quatro colunas cortariam os rótulos na largura da página.
        titulares, dependentes = st.columns(2)
        impedem, outros = st.columns(2)
        titulares.metric("Titulares", resultado.contar("TOP"))
        dependentes.metric("Dependentes", resultado.contar("DTOP"))
        impedem.metric(
            "Pendências", len(bloqueantes), help="Impedem o envio à Receita Federal."
        )
        outros.metric("Avisos", avisos)

    dia = f"{resultado.gerado_em:%Y%m%d}"
    arquivo, relatorio = st.columns(2)
    if resultado.conteudo is not None:
        with arquivo:
            botao_download(
                "Baixar DMED com pendências" if bloqueantes else "Baixar arquivo DMED",
                resultado.conteudo.encode("utf-8"),
                f"DMED_{dia}.DEC",
                "text/plain",
                tipo="secondary" if bloqueantes else "primary",
            )
    if resultado.ocorrencias:
        with relatorio:
            botao_download(
                "Baixar relatório de pendências",
                resultado.relatorio_de_erros().encode("utf-8"),
                f"Erros_Planilhas_{dia}.txt",
                "text/plain",
                tipo="primary"
                if bloqueantes or resultado.conteudo is None
                else "secondary",
            )

    st.button(
        "Limpar resultado",
        icon=":material/restart_alt:",
        on_click=lambda: st.session_state.pop(Chaves.RESULTADO_DMED, None),
    )


def _pendencias(resultado: ResultadoDmed) -> None:
    secao(
        "Pendências nas planilhas",
        "Primeiro as que impedem o envio. A descrição indica a planilha e a linha.",
    )
    tabela = pd.DataFrame(
        {
            "Gravidade": [GRAVIDADE[o.severidade] for o in resultado.ocorrencias],
            "Impede o envio": [
                "Sim" if o.severidade.bloqueante else "Não"
                for o in resultado.ocorrencias
            ],
            "Descrição": [o.texto for o in resultado.ocorrencias],
        }
    ).sort_values("Impede o envio", ascending=False, kind="stable")
    st.dataframe(
        tabela,
        hide_index=True,
        width="stretch",
        column_config={
            "Gravidade": st.column_config.TextColumn(width="small"),
            "Impede o envio": st.column_config.TextColumn(width="small"),
            "Descrição": st.column_config.TextColumn(width="large"),
        },
    )


# Atualização das planilhas --------------------------------------------------


def _quando(planilha: Planilha) -> str:
    instante = fontes.modificado_em(config.destino_planilha(planilha))
    return f"{instante:%d/%m/%Y às %H:%M}" if instante else "ainda não baixada"


def atualizar_planilhas() -> None:
    secao(
        "Atualizar planilhas",
        "Baixa mensalidades e descontos do Google Drive e refaz o processamento. "
        "Use depois de alterar as planilhas no Drive; leva cerca de um minuto.",
    )
    st.caption(
        f"Última atualização · mensalidades: {_quando(Planilha.MENSALIDADES)} · "
        f"descontos: {_quando(Planilha.DESCONTOS)}"
    )
    if not st.button("Atualizar planilhas", icon=":material/sync:"):
        return

    processamentos = (
        ("mensalidades", processar_mensalidades),
        ("descontos", processar_descontos),
        ("despesas", processar_despesas),
    )
    with st.status("Atualizando as planilhas...", expanded=True) as status:
        etapas = Etapas(
            ["Baixar as planilhas do Google Drive"]
            + [f"Processar {rotulo}" for rotulo, _ in processamentos]
        )
        etapas.mostrar(0)
        baixou, mensagem = fontes.baixar_planilhas_do_drive()
        indices_com_falha = set() if baixou else {0}
        falhas = []
        for indice, (rotulo, processar) in enumerate(processamentos, start=1):
            etapas.mostrar(indice, indices_com_falha)
            caminho, _ = processar()
            if caminho is None:
                falhas.append(rotulo)
                indices_com_falha.add(indice)
        etapas.mostrar(len(etapas.rotulos), indices_com_falha)

        if baixou and not falhas:
            status.update(label="Planilhas atualizadas", state="complete")
            st.toast("Planilhas atualizadas.", icon=":material/check_circle:")
            return
        status.update(
            label="A atualização não foi concluída", state="error", expanded=True
        )

    if not baixou:
        st.error(
            "Não foi possível baixar as planilhas do Google Drive; o app segue "
            "com as da última atualização. Confira a internet e a configuração "
            f"do Drive. {AJUDA_TECNICA}",
            icon=":material/cloud_off:",
        )
        with st.expander("Detalhes técnicos"):
            st.code(mensagem.removeprefix("❌ "), language=None)
    if falhas:
        st.error(
            f"Não foi possível processar: {', '.join(falhas)}. Gere o arquivo "
            "DMED para ver as pendências da planilha.",
            icon=":material/error:",
        )


# Página -----------------------------------------------------------------------

autenticado = bool(st.session_state.get(Chaves.SENHA_CORRETA))
with heroi(
    "Arquivo DMED",
    f"Ano-calendário {config.ano_calendario()} · Receita Federal",
    acao=_botao_sair if autenticado else None,
):
    if autenticado:
        formulario_do_responsavel()
    else:
        formulario_de_acesso()

if autenticado:
    resultado = st.session_state.get(Chaves.RESULTADO_DMED)
    if isinstance(resultado, ResultadoDmed):
        exibir_resultado(resultado)
    with cartao("atualizar"):
        atualizar_planilhas()

rodape()
