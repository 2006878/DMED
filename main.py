import streamlit as st
from funcoes import *
import base64

# Carreguando o ícone da aba
favicon = "icone.jpeg"

# Configuração da página
st.set_page_config(page_title=f"IRPF {ano_anterior} - COSEMI", page_icon=favicon, layout="wide")

# Ocultar elementos desnecessários da interface
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Estilos personalizados
st.markdown("""
    <style>
    /* Ajuste da largura do input CPF */
    [data-testid="stTextInput"] {
        max-width: 300px;
        margin: 0 auto;
    }
    /* Centralizar títulos */
    h1, h3 {
        text-align: center;
    }
    /* Centralizar botão de download */
    [data-testid="stDownloadButton"] {
        display: block;
        margin: 0 auto;
        max-width: 300px;
    }
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
    </style>
""", unsafe_allow_html=True)

# Adicionar logo com estilo responsivo
st.markdown("""
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
""", unsafe_allow_html=True)

# Display logo
with open('logo.png', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode()

st.markdown(f"""
    <div style="display: flex; justify-content: center; margin: 1em 0;">
        <img src="data:image/png;base64,{image_data}" style="max-width: 300px; width: 100%; height: auto;">
    </div>
""", unsafe_allow_html=True)

st.title(f"INFORME PLANO DE SAÚDE {ano_anterior} IRPF - COSEMI")

st.markdown("<h3 style='font-size: 24px;'>Digite o CPF do titular a ser consultado:</h3>", unsafe_allow_html=True)
cpf_alvo = format_cpf(st.text_input("Digite o CPF do Titular aqui.", label_visibility="collapsed", key="cpf_input"))

if cpf_alvo:
    with st.spinner("Buscando dados de mensalidades..."):
        df_filtrado = busca_dados_mensalidades(cpf_alvo)
        nome = df_filtrado["Nome"].iloc[0] if isinstance(df_filtrado, pd.DataFrame) and not df_filtrado.empty else ""
    with st.spinner("Buscando dados de descontos..."):
        descontos = busca_dados_descontos(cpf_alvo)
    with st.spinner("Buscando dados de despesas..."):
        df_despesas = busca_dados_despesas(cpf_alvo, nome)
    
    descontos = f"R$ {descontos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    if isinstance(df_filtrado, pd.DataFrame) and not df_filtrado.empty or not df_despesas.empty:
        pdf_data = generate_pdf(df_filtrado, df_despesas, descontos, cpf_alvo)
        st.download_button(
            label="📥 Download PDF",
            data=pdf_data,
            file_name=f"relatorio_dmed_{cpf_alvo}.pdf",
            mime="application/pdf"
        )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📊 Mensalidade Plano de Saúde")
        if not df_filtrado.empty:
            for _, row in df_filtrado.iterrows():
                valor = row["Valor"]  # Acessa a coluna 'Valor' diretamente
                # Remover "R$" e ajustar o formato numérico
                valor = str(valor).replace("R$", "").replace(".", "", valor.count(".") - 1).replace(",", ".").strip()
                try:
                    # Converter para float e formatar corretamente
                    valor_float = float(valor)
                    valor_formatado = f"{valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                except ValueError:
                    valor_formatado = "Valor inválido"
                st.markdown(f"""
                    <div class='info-container'>
                        <h4>{row['Nome']}</h4>
                        <p>Valor: <strong>R$ {valor_formatado}</strong></p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Não existem registros de mensalidades para o CPF informado.")
    
    with col2:
        st.markdown("### 💉 Procedimentos co-participativos")
        if not df_despesas.empty:
            df_despesas['exact_match'] = df_despesas['Nome'].str.upper() == nome.upper()
            df_despesas = df_despesas.sort_values('exact_match', ascending=False).drop('exact_match', axis=1)
            for _, row in df_despesas.iterrows():
                st.markdown(f"""
                    <div class='info-container'>
                        <h4>{row.iloc[0]}</h4>
                        <p>Valor: <strong>{row.iloc[1]}</strong></p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Não existem registros de despesas para o CPF informado.")

    with col3:

        st.markdown("### 💰 Descontos ")
        if descontos and descontos != "R$ 0,00":
            st.markdown(f"""
                <div class='info-container'>
                    <p>Total de descontos: <strong>{descontos}</strong></p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Não existem registros de descontos para o CPF informado.")

# Botão discreto para processar os dados no canto superior direito
st.markdown("""
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
""", unsafe_allow_html=True)

with st.expander("⚙️ Opções avançadas"):
    if st.button("Reprocessar dados"):
        bar=st.progress(0)
        with st.spinner("Processando mensalidades..."):
            processa_mensalidades()
            bar.progress(40)
        with st.spinner("Processando descontos..."):
            processa_descontos()
            bar.progress(80)
        with st.spinner("Processando despesas..."):
            processa_despesas()
            bar.progress(100)
        st.success("Reprocessamento concluído!")

st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("""
    <hr style='border:1px solid #e3e3e3;margin-top:40px'>
    <div style='text-align: center;'>
        Desenvolvido por 
        <a href='https://www.linkedin.com/in/tairone-amaral/' target='_blank'>
            Tairone Leandro do Amaral
        </a>
    </div>
""", unsafe_allow_html=True)
