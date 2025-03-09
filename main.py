import streamlit as st
import io
from funcoes import *

# Streamlit page configuration
st.set_page_config(page_title="Dados DMED")
st.title("Tratamento de dados - DMED")

# Hide unnecessary UI elements
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)
    
st.markdown("<h3 style='font-size: 24px;'>Digite o CPF do titular a ser consultado:</h3>", unsafe_allow_html=True)
cpf_alvo = format_cpf(st.text_input("", key="cpf_input"))

if cpf_alvo:
    df_filtrado = busca_dados_mensalidades(cpf_alvo)
    if not df_filtrado.empty:
        st.write("### Mensalidades:")
        st.dataframe(df_filtrado)
    else:
        st.write("Nenhum dado de mensalidade encontrado para o CPF fornecido.")

    df_despesas = busca_dados_despesas(cpf_alvo)
    if not df_despesas.empty:
        st.write("### Despesas:")   
        st.dataframe(df_despesas)
    else:
        st.write("Nenhum dado de mensalidade encontrado para o CPF fornecido.")

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