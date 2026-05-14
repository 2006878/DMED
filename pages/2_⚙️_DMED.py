import streamlit as st
import sys
import os
from pathlib import Path
import base64
import pandas as pd
from datetime import datetime
import traceback

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from funcoes import *

# Carregando o ícone da aba
favicon = "icone.jpeg"

# Streamlit page configuration
st.set_page_config(page_title=f"ARQUIVO DMED - COSEMI", page_icon=favicon, initial_sidebar_state="expanded", layout="wide")

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
        /* Ajuste do Expander */
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

    st.markdown("<h3 style='font-size: 24px;'>Insira as informações abaixo para processar e criar o arquivo:</h3>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        cpf_input = st.text_input(
            "Digite o CPF do Responsável aqui (apenas números):",
            max_chars=11,
            help="Digite apenas os 11 números do CPF, sem pontos ou traços"
        )

        if cpf_input:
            cpf_digits = ''.join(filter(str.isdigit, cpf_input))
            if len(cpf_digits) != 11:
                st.error("CPF deve conter exatamente 11 dígitos e sem pontos ou traços.")
            else:
                cpf_responsavel = cpf_digits
        else:
            cpf_responsavel = ""

        nome_respostavel = st.text_input("Digite o nome do Responsável aqui.")
        st.selectbox("Selecione como deseja processar o arquivo:", ["Titulares e Dependentes", "somente Titulares"], key="processamento")
        st.write(f"Com a seleção atual o arquivo terá os dados informados incluindo ", st.session_state.processamento)

    with col2:
        ddd_input = st.text_input(
        "Digite o DDD do telefone do Responsável aqui (apenas números):",
        max_chars=2,
        help="Digite apenas os 2 números, sem pontos ou traços"
        )

        telefone_input = st.text_input(
            "Digite o telefone do Responsável aqui (apenas números):",
            max_chars=9,
            help="Digite apenas os números do telefone, sem pontos ou traços"
        )

    # =========================================================================
    # LÓGICA DE PROCESSAMENTO E EMISSÃO DE ARQUIVOS
    # =========================================================================
    if cpf_responsavel != "" and nome_respostavel != "" and ddd_input != "" and telefone_input != "" and st.button("📥 Processar e criar arquivo DMED"):
        
        # 1. Limpar arquivos locais antigos para garantir o download de dados frescos
        arquivos_temp = ['mensalidade_file.csv', 'despesas_file.csv', 'descontos_file.csv']
        for f in arquivos_temp:
            if os.path.exists(os.path.join(os.getcwd(), f)):
                os.remove(os.path.join(os.getcwd(), f))

        with st.spinner("Analisando planilhas, validando regras e gerando arquivo... (Isso pode levar alguns instantes)"):
            try:
                dmed_content = None
                lista_erros = []

                if st.session_state.processamento == "Titulares e Dependentes":
                    # A função main agora retorna o conteúdo E a lista de erros
                    dmed_content, lista_erros = create_dmed_content(cpf_responsavel, nome_respostavel, ddd_input, telefone_input)
                
                # elif st.session_state.processamento == "somente Titulares":
                #     dmed_content, lista_erros = create_dmed_content_titular(cpf_responsavel, nome_respostavel, ddd_input, telefone_input)
                
                else:
                    st.error("Opção de processamento inválida.")

                # =============================================================
                # VERIFICAÇÃO DE ERROS E GERAÇÃO DE BOTÕES (ATUALIZADO)
                # =============================================================
                tem_erro_fatal = any("🛑" in erro or "❌" in erro for erro in lista_erros)

                # Cenário 1: Gerou o DMED, mas tem erros
                if tem_erro_fatal and dmed_content:
                    st.warning("⚠️ **ATENÇÃO:** O arquivo DMED foi gerado conforme solicitado, mas **existem dados obrigatórios em branco** nas planilhas originais!")
                    st.info("Recomendamos baixar o Relatório de Erros e fazer a correção antes de enviar à Receita Federal.")
                    
                    # Formatar o texto do log para download
                    txt_erros = "========================================================\n"
                    txt_erros += f"RELATORIO DE INCONSISTENCIAS - COSEMI DMED\n"
                    txt_erros += f"Gerado em: {datetime.now().strftime('%d/%m/%Y as %H:%M:%S')}\n"
                    txt_erros += "========================================================\n\n"
                    txt_erros += "Por favor, corrija as linhas listadas abaixo nas planilhas originais:\n\n"
                    txt_erros += "\n".join(lista_erros)

                    # Colocar os botões lado a lado para o cliente
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        st.download_button(
                            label="📥 BAIXAR RELATÓRIO DE ERROS (.txt)",
                            data=txt_erros.encode('utf-8'),
                            file_name=f"Erros_Planilhas_{datetime.now().strftime('%Y%m%d')}.txt",
                            mime="text/plain",
                            type="primary" # Destaca o botão em vermelho/primário no Streamlit
                        )
                    with col_btn2:
                        st.download_button(
                            label="📥 BAIXAR DMED (COM ERROS) (.DEC)",
                            data=dmed_content.encode('utf-8'),
                            file_name=f"DMED_{datetime.now().strftime('%Y%m%d')}.DEC",
                            mime="text/plain"
                        )
                
                # Cenário 2: Sucesso Total (Pode ter avisos amarelos, mas nada fatal)
                elif dmed_content and not tem_erro_fatal:
                    st.success("✅ Arquivo DMED gerado e validado com sucesso!")
                    
                    # Se houver apenas avisos (bolinha amarela), mostramos sutilmente
                    if lista_erros:
                        with st.expander("⚠️ Avisos do Processamento (Não Impeditivos)"):
                            for aviso in lista_erros:
                                st.write(aviso)

                    st.download_button(
                        label="📥 BAIXAR ARQUIVO DMED (.DEC)",
                        data=dmed_content.encode('utf-8'),
                        file_name=f"DMED_{datetime.now().strftime('%Y%m%d')}.DEC",
                        mime="text/plain",
                        type="primary"
                    )
                
                # Cenário 3: Falha Crítica (Não conseguiu gerar a string do DMED)
                else:
                    st.error("Falha Crítica. O sistema não conseguiu montar o arquivo DMED.")
                    if lista_erros:
                        for erro in lista_erros:
                            st.write(erro)

            except Exception as e:
                st.error(f"Ocorreu um erro crítico no sistema: {str(e)}")
                traceback.print_exc()

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
                Tairone Amaral
            </a>
        </div>
    """, unsafe_allow_html=True)