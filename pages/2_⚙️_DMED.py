import streamlit as st
from funcoes import *
import base64
import pandas as pd
from datetime import datetime

# Carreguando o ícone da aba
favicon = "icone.jpeg"

# Streamlit page configuration
st.set_page_config(page_title=f"ARQUIVO DMED - COSEMI", page_icon=favicon, initial_sidebar_state="collapsed", layout="wide")

# Display logo
with open('logo.png', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode()

st.markdown(f"""
    <div style="display: flex; justify-content: center; margin: 1em 0;">
        <img src="data:image/png;base64,{image_data}" style="max-width: 300px; width: 100%; height: auto;">
    </div>
""", unsafe_allow_html=True)


# Ocultar completamente o menu lateral original
st.markdown("""
    <style>
    /* Oculta todos os elementos de navegação */
    section[data-testid="stSidebar"] ul {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# Criar seu próprio menu lateral
with st.sidebar:
    st.title("Menu COSEMI")
    
    # Botão para voltar à página inicial
    if st.button("🏠 Home"):
        st.switch_page("main.py")
    
    # Botão para a página atual (DMED)
    st.button("⚙️ DMED", disabled=True)

# Configuração de autenticação
def check_password():
    """Retorna `True` se o usuário tiver a senha correta."""
    def password_entered():
        """Verifica se a senha inserida pelo usuário está correta."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Não armazene a senha
        else:
            st.session_state["password_correct"] = False

    # Primeiro executa esta verificação
    if "password_correct" not in st.session_state:
        # Primeiro acesso, mostre o formulário de entrada
        st.text_input(
            "Senha", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Senha incorreta, mostre o formulário de entrada
        st.text_input(
            "Senha", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Senha incorreta")
        return False
    else:
        # Senha correta, acesso permitido
        return True

# Início da aplicação
if check_password():

    st.title(f"DOWNLOAD ARQUIVO DMED - COSEMI")

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
        /* Centralizar títulos */
        h1, h2, h3 {
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

    # Add custom CSS for centered expander content
    st.markdown("""
        <style>
        .streamlit-expanderContent {
            display: flex;
            justify-content: center;
            align-items: center;
            text-align: center;
        }
        .streamlit-expanderContent div {
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h3 style='font-size: 24px;'>Baixe o arquivo de importação DMED:</h3>", unsafe_allow_html=True)

    if st.button("📥 Processar e criar arquivo DMED"):
        bar = st.progress(0)
        with st.spinner("Processando mensalidades..."):
            processa_mensalidades()
            bar.progress(25)
        with st.spinner("Processando despesas..."):
            processa_despesas()
            bar.progress(50)
        with st.spinner("Processando descontos..."):
            processa_descontos()
        bar.progress(75)
        with st.spinner("Criando arquivo DMED..."):
            try:
                dmed_content = create_dmed_content()
                bar.progress(100)
                st.success("Arquivo DMED gerado com sucesso!")
                if dmed_content:
                    st.download_button(
                        label="📥 Download DMED",
                        data=dmed_content.encode('utf-8'),
                        file_name=f"DMED_{datetime.now().strftime('%Y%m%d')}.DEC",
                        mime="text/plain"
                    )
                else:
                    st.error("Erro ao processar os dados.")
            except Exception as e:
                st.error(f"Ocorreu um erro ao processar os dados: {str(e)}")

    with st.expander("Manual de regras", expanded=False):
        with open('manual.md', 'r', encoding='utf-8') as file:
            manual_content = file.read()
        st.markdown(manual_content)

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