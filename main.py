import streamlit as st
import io
from funcoes import *

# Streamlit page configuration
st.set_page_config(page_title=f"IRPF {ano_anterior}- COSEMI", layout="wide")
st.title(f"INFORME PLANO DE SAÚDE {ano_anterior} IRPF - COSEMI")

# Hide unnecessary UI elements
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)
    
# Add custom CSS to adjust only the CPF input width
st.markdown("""
    <style>
    /* Target specifically the CPF input */
    [data-testid="stTextInput"] {
        max-width: 300px;
        margin: 0 auto;
    }
    /* Center title */
    h1 {
        text-align: center;
    }
    
    /* Center headers */
    h3 {
        text-align: center;
    }
            
    /* Center download button */
    [data-testid="stDownloadButton"] {
        display: block;
        margin: 0 auto;
        max-width: 300px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h3 style='font-size: 24px;'>Digite o CPF do titular a ser consultado:</h3>", unsafe_allow_html=True)
cpf_alvo = format_cpf(st.text_input("", key="cpf_input"))

if cpf_alvo:
    df_filtrado = busca_dados_mensalidades(cpf_alvo)
    df_despesas = busca_dados_despesas(cpf_alvo)
    # Check if DataFrame has rows before accessing first element
    if not df_despesas.empty:
        nome = df_despesas["Nome"].iloc[0]
    else:
        nome = ""  # Or any default value you want to use

    descontos = busca_dados_descontos(nome)
 
    # Gerar PDF
    if not df_filtrado.empty or not df_despesas.empty:
        pdf_data = generate_pdf(df_filtrado, df_despesas, descontos, cpf_alvo)
        st.download_button(
            label="📥 Download PDF",
            data=pdf_data,
            file_name=f"relatorio_dmed_{cpf_alvo}.pdf",
            mime="application/pdf")
        
    # Create two columns
    col1, col2, col3 = st.columns(3)
    
    # Left column - Mensalidades
    with col1:
        st.markdown("### 📊 Mensalidade Plano de Saúde")
        if not df_filtrado.empty:
            for _, row in df_filtrado.iterrows():
                st.markdown(f"""
                    <div style='background-color: #f0f2f6; padding: 10px; margin-bottom: 5px;'>
                        <h4 style='color: #1f77b4; margin: 0;'>{row.iloc[0]}</h4>
                        <p style='font-size: 18px; margin: 5px 0;'>Valor: <strong>{row.iloc[1]}</strong></p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Não existem registros de mensalidades para o CPF informado.")
    
    # Right column - Despesas
    with col2:
        st.markdown("### 💉 Procedimentos co-participativos")
        if not df_despesas.empty:
            for _, row in df_despesas.iterrows():
                st.markdown(f"""
                    <div style='background-color: #e6f3ff; padding: 10px; margin-bottom: 5px;'>
                        <h4 style='color: #2196f3; margin: 0;'>{row.iloc[0]}</h4>
                        <p style='font-size: 18px; margin: 5px 0;'>Valor: <strong>{row.iloc[1]}</strong></p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Não existem registros de despesas para o CPF informado.")

    with col3:
        st.markdown("### 💰 Descontos em folha ")
        # st.write(f"Total de descontos 2024:{descontos}")
        if descontos:
            st.markdown(f"""
                <div style='background-color: #e6f3ff; padding: 10px; margin-bottom: 5px;'>
                    <h4 style='color: #2196f3; margin: 0;'>{nome}</h4>
                    <p style='font-size: 18px; margin: 5px 0;'>Valor: <strong>{descontos}</strong></p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Não existem registros de descontos para o CPF informado.")

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