import streamlit as st
import base64

# Configuração da página
st.set_page_config(page_title="Manual do Sistema")

# Carreguando o ícone da aba
favicon = "icone.jpeg"

# Display logo
with open('logo.png', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode()

st.markdown(f"""
    <div style="display: flex; justify-content: center; margin: 1em 0;">
        <img src="data:image/png;base64,{image_data}" style="max-width: 300px; width: 100%; height: auto;">
    </div>
""", unsafe_allow_html=True)

# Título da página
st.title("📘 Manual do Sistema")

# Ocultar elementos desnecessários da interface
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

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

# Função para carregar o conteúdo do arquivo Markdown
def carregar_manual(filepath):
    with open(filepath, "r", encoding="utf-8") as file:
        return file.read()

# Carregar o conteúdo do arquivo manual.md
manual_content = carregar_manual("manual.md")

# Exibir o conteúdo do manual em formato Markdown
st.markdown(manual_content)