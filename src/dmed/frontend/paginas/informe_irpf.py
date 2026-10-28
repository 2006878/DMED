"""Página inicial: consulta pelo CPF do titular e informe de IRPF em PDF."""

from __future__ import annotations

import streamlit as st

from dmed.backend import config, fontes
from dmed.backend.consulta import Consulta, MensalidadesIndisponiveis
from dmed.backend.descontos import processar_descontos
from dmed.backend.despesas import processar_despesas
from dmed.backend.formatacao import formatar_cpf, formatar_moeda, ler_valor_monetario
from dmed.backend.informe_pdf import gerar_informe_pdf, valor_para_exibicao
from dmed.backend.mensalidades import processar_mensalidades
from dmed.frontend.componentes import (
    CSS_BOTAO_DOWNLOAD,
    CSS_CARTOES,
    CSS_OCULTAR_CABECALHO,
    CSS_OCULTAR_NAVEGACAO,
    RODAPE,
    Chaves,
    cartao,
    configurar_pagina,
    exibir_logo,
    html,
    menu_lateral,
)

SEM_DESCONTOS = "R$ 0,00"

ano = config.ano_calendario()
configurar_pagina(f"IRPF {ano} - COSEMI")
html(CSS_OCULTAR_NAVEGACAO)
menu_lateral(na_pagina_inicial=True)
html(CSS_OCULTAR_CABECALHO)
html(
    f"""
    <style>
    /* Ajuste da largura do input CPF */
    [data-testid="stTextInput"] {{
        max-width: 300px;
        margin: 0 auto;
    }}
    /* Centralizar títulos */
    h1, h3 {{
        text-align: center;
    }}
    {CSS_BOTAO_DOWNLOAD}
    {CSS_CARTOES}
    </style>
"""
)
html(
    """
    <style>
    .container {
        display: flex;
        justify-content: center;
        max-width: 800px;
        margin: 0 auto;
        padding: 10px;
    }
    img {
        max-width: 100%;
        height: auto;
    }
    </style>
"""
)
exibir_logo()

st.title(f"INFORME PLANO DE SAÚDE {ano} IRPF - COSEMI")
html("<h3 style='font-size: 24px;'>Digite o CPF do titular a ser consultado:</h3>")
cpf = formatar_cpf(
    st.text_input(
        "Digite o CPF do Titular aqui.",
        label_visibility="collapsed",
        key=Chaves.CPF_CONSULTA,
    )
)

if cpf:
    try:
        with st.spinner("Buscando dados de mensalidades..."):
            consulta = Consulta.carregar()
            familia = consulta.mensalidades(cpf)
            nome = familia["Nome"].iloc[0] if not familia.empty else ""
        with st.spinner("Buscando dados de descontos..."):
            total_descontos = formatar_moeda(ler_valor_monetario(consulta.descontos(cpf)))
        with st.spinner("Buscando dados de despesas..."):
            despesas = consulta.despesas(cpf, nome)
    except MensalidadesIndisponiveis as falha:
        st.error(str(falha))
        st.stop()

    # CPF sem nenhum registro: só os avisos, sem cartões nem PDF.
    sem_registros = (
        familia.empty and total_descontos == SEM_DESCONTOS and not consulta.tem_despesas(cpf)
    )

    if not sem_registros and (not familia.empty or not despesas.empty):
        st.download_button(
            label="📥 Download PDF",
            data=gerar_informe_pdf(familia, despesas, total_descontos, cpf),
            file_name=f"relatorio_dmed_{cpf}.pdf",
            mime="application/pdf",
        )

    coluna_mensalidades, coluna_despesas, coluna_descontos = st.columns(3)

    with coluna_mensalidades:
        st.markdown("### 📊 Mensalidade Plano de Saúde")
        if not familia.empty:
            for membro, valor in zip(familia["Nome"], familia["Valor"], strict=True):
                cartao(membro, f"Valor: <strong>R$ {valor_para_exibicao(valor)}</strong>")
        else:
            st.info("Não existem registros de mensalidades para o CPF informado.")

    with coluna_despesas:
        st.markdown("### 💉 Procedimentos co-participativos")
        if not sem_registros and not despesas.empty:
            # As despesas do titular aparecem primeiro.
            ordem = despesas["Nome"].str.upper() == nome.upper()
            for _, linha in despesas.assign(ordem=ordem).sort_values(
                "ordem", ascending=False
            ).iterrows():
                cartao(linha.iloc[0], f"Valor: <strong>{linha.iloc[1]}</strong>")
        else:
            st.info("Não existem registros de despesas para o CPF informado.")

    with coluna_descontos:
        st.markdown("### 💰 Descontos ")
        if total_descontos and total_descontos != SEM_DESCONTOS:
            cartao(None, f"Total de descontos: <strong>{total_descontos}</strong>")
        else:
            st.info("Não existem registros de descontos para o CPF informado.")

# Botão discreto para reprocessar os dados, no canto superior direito.
html(
    """
    <style>
    .expander-container {
        position: fixed;
        top: 10px;
        right: 10px;
        width: auto; /* Ajusta a largura automaticamente ao conteúdo */
        z-index: 1000;
    }
    .streamlit-expander {
        width: auto !important; /* Ajusta a largura do expander */
        display: inline-block; /* Garante que o expander ocupe apenas o espaço necessário */
    }
    </style>
    <div class="expander-container">
"""
)

with st.expander("⚙️ Opções avançadas"):
    if st.button("🔄 Reprocessar dados"):
        barra = st.progress(0)
        with st.spinner("Baixando bases atualizadas do Google Drive..."):
            sucesso, mensagem = fontes.baixar_planilhas_do_drive()
            if not sucesso:
                st.error(mensagem)
            barra.progress(25)
        with st.spinner("Processando regras de mensalidades..."):
            processar_mensalidades()
            barra.progress(50)
        with st.spinner("Validando base de descontos..."):
            processar_descontos()
            barra.progress(75)
        with st.spinner("Processando despesas..."):
            processar_despesas()
            barra.progress(100)
        st.success("Bases atualizadas e reprocessamento concluído com sucesso!")

html("</div>")
html(RODAPE)
