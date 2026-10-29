"""Página inicial: consulta pelo CPF do titular e informe de IRPF em PDF."""

from __future__ import annotations

import streamlit as st

from dmed.backend import config
from dmed.backend.consulta import Consulta, MensalidadesIndisponiveis
from dmed.backend.formatacao import formatar_moeda, ler_valor_monetario
from dmed.backend.informe_pdf import (
    gerar_informe_pdf,
    total_de_mensalidades,
    valor_para_exibicao,
)
from dmed.frontend.componentes import (
    Chaves,
    botao_download,
    cartao,
    heroi,
    rodape,
    secao,
    tabela_de_valores,
)
from dmed.frontend.validacao import CpfConsultado, cpf_com_mascara, ler_cpf_da_consulta

SEM_DESCONTOS = "R$ 0,00"

ano = config.ano_calendario()


def formulario_de_consulta() -> CpfConsultado | None:
    """Campo do CPF e botão Consultar; devolve o último CPF enviado, já lido."""
    with (
        st.form("consulta", border=False),
        # Campo do tamanho de um CPF e o botão até o fim do card; quebra no celular.
        st.container(horizontal=True, vertical_alignment="bottom", gap="medium"),
    ):
        st.text_input(
            "CPF do titular",
            key=Chaves.CPF_CONSULTA,
            placeholder="000.000.000-00",
            max_chars=14,
            help="Com ou sem pontos e traço.",
            width=300,
        )
        st.form_submit_button("Consultar", type="primary", width="stretch")

    digitado = str(st.session_state.get(Chaves.CPF_CONSULTA, ""))
    if not digitado:
        return None
    leitura = ler_cpf_da_consulta(digitado)
    if leitura.erro:
        st.error(leitura.erro, icon=":material/error:")
    elif leitura.aviso:
        st.warning(leitura.aviso, icon=":material/warning:")
    return leitura


def exibir_consulta(cpf: str) -> None:
    try:
        with st.spinner("Consultando..."):
            consulta = Consulta.carregar()
            familia = consulta.mensalidades(cpf)
            nome = familia["Nome"].iloc[0] if not familia.empty else ""
            total_descontos = formatar_moeda(
                ler_valor_monetario(consulta.descontos(cpf))
            )
            despesas = consulta.despesas(cpf, nome)
    except MensalidadesIndisponiveis:
        st.error(
            "Dados de mensalidades indisponíveis. Peça a quem administra o app "
            "para atualizar as planilhas na página **Arquivo DMED**.",
            icon=":material/error:",
        )
        return

    # CPF sem nenhum registro: só o aviso, sem resumo nem PDF.
    if (
        familia.empty
        and total_descontos == SEM_DESCONTOS
        and not consulta.tem_despesas(cpf)
    ):
        st.warning(
            f"Nenhum registro em {ano} para o CPF {cpf_com_mascara(cpf)}. "
            "Confira o número digitado.",
            icon=":material/search_off:",
        )
        return

    with cartao("titular"):
        identificacao, acao = st.columns([3, 2], vertical_alignment="center")
        with identificacao:
            st.subheader(nome or "Titular sem mensalidades no ano", anchor=False)
            st.caption(f"CPF {cpf_com_mascara(cpf)} · ano-calendário {ano}")
        with acao:
            if not familia.empty or not despesas.empty:
                botao_download(
                    "Baixar informe em PDF",
                    gerar_informe_pdf(familia, despesas, total_descontos, cpf),
                    f"informe_plano_saude_{ano}_{cpf}.pdf",
                    "application/pdf",
                )
        mensalidades, gastos = st.columns(2)
        mensalidades.metric("Total de mensalidades", total_de_mensalidades(familia))
        gastos.metric(
            "Total de despesas",
            total_descontos,
            help="Coparticipação descontada no ano, como no quadro de totais do informe.",
        )

    with cartao("mensalidades"):
        secao("Mensalidades do plano")
        if familia.empty:
            st.caption(f"Nenhuma mensalidade em {ano}.")
        else:
            tabela_de_valores(
                familia["Nome"],
                [f"R$ {valor_para_exibicao(valor)}" for valor in familia["Valor"]],
            )

    with cartao("despesas"):
        secao("Despesas de coparticipação")
        if despesas.empty:
            st.caption(f"Nenhuma despesa de coparticipação em {ano}.")
        else:
            # As despesas do titular aparecem primeiro.
            ordem = despesas["Nome"].str.upper() == nome.upper()
            ordenadas = despesas.assign(ordem=ordem).sort_values(
                "ordem", ascending=False
            )
            tabela_de_valores(ordenadas.iloc[:, 0], ordenadas.iloc[:, 1].to_list())


with heroi("Informe de plano de saúde", f"Ano-calendário {ano} · Imposto de Renda"):
    leitura = formulario_de_consulta()
if leitura is not None and leitura.cpf:
    exibir_consulta(leitura.cpf)

rodape()
