import streamlit as st
from funcoes import *
import base64
import pandas as pd
from datetime import datetime

# Carreguando o ícone da aba
favicon = "icone.jpeg"

# Streamlit page configuration
st.set_page_config(page_title=f"DMED {ano_anterior}- COSEMI", page_icon=favicon, layout="wide")

# Display logo
with open('logo.png', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode()

st.markdown(f"""
    <div style="display: flex; justify-content: center; margin: 1em 0;">
        <img src="data:image/png;base64,{image_data}" style="max-width: 300px; width: 100%; height: auto;">
    </div>
""", unsafe_allow_html=True)

st.title(f"DOWNLOAD DMED {ano_anterior} IRPF - COSEMI")

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

mensalidades = len(pd.read_csv('mensalidades_file.csv'))
descontos = len(pd.read_csv('descontos_file.csv'))
despesas = len(pd.read_csv('despesas_file.csv'))
quantidade_de_registros = mensalidades + despesas + descontos  

st.markdown("<h3 style='font-size: 24px;'>Baixe o arquivo de importação DMED:</h3>", unsafe_allow_html=True)
@st.cache_data
def content():
    start = datetime.now()
    try:
        content = create_dmed_content()
    except Exception as e:
        st.error(f"Ocorreu um erro ao gerar o arquivo DMED: {str(e)}")
        return
    end = datetime.now()
    st.success(f"Arquivo DMED gerado com sucesso! Tempo de execução: {end - start}")
    return content

with st.spinner(f"Processando {quantidade_de_registros} registros e criando arquivo DMED..."):
    dmed_content = content()
    
# Replace the download button section with
st.download_button(
    label="📥 Download DMED",
    data=dmed_content.encode('utf-8'),
    file_name=f"DMED_{datetime.now().strftime('%Y%m%d')}.DEC",
    mime="text/plain"
)

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