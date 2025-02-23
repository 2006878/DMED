import streamlit as st
import pandas as pd
import json
import dotenv
import io
import smtplib
import email.message
import os


# Carregar variáveis de ambiente e colocar os valores nas devidas variáveis
dotenv.load_dotenv()
senha_email = os.getenv("SENHA_EMAIL")
email_origem = os.getenv("EMAIL_ORIGEM")
email_destino = os.getenv("EMAIL_DESTINO")

# Configurações da página Streamlit
# st.set_page_config(page_title="Dados DMED", layout="wide")
st.set_page_config(page_title="Dados DMED")

st.title("Tratamento de dados - DMED")

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

# Widget de upload de arquivo   
uploaded_file = st.file_uploader("Escolha um arquivo Excel", type=["xlsx"])

# Definir o arquivo para upload
# uploaded_file = "./anexos/IRF.xlsx"

if uploaded_file is not None:
    try:
        # Ler o arquivo ignorando as duas primeiras linhas
        df = pd.read_excel(uploaded_file, engine="openpyxl", skiprows=2, sheet_name="Mensalidade")

        # Filtrar apenas as colunas desejadas
        ano_anterior = pd.Timestamp.now().year - 1
        ano_atual = pd.Timestamp.now().year
        df["Deslig."] = pd.to_datetime(df["Deslig."], errors="coerce")
        df_filtrado = df[(df["Deslig."].dt.year == ano_anterior) | (df["Deslig."].dt.year == ano_atual) | (df["Deslig."].isna())].copy()        

        # Converter "mat." para string
        df_filtrado["Mat."] = df_filtrado["Mat."].astype(str)
        
        # Converter "Total 2024" para numérico, substituindo NaN por 0
        df_filtrado["Total 2024"] = pd.to_numeric(df_filtrado["Total 2024"], errors="coerce").fillna(0).round(2)

        # Criar colunas adicionais
        df_filtrado["Titular_CPF"] = None  # CPF do titular vinculado ao dependente
        df_filtrado["Relação"] = None  # Tipo de relação com o titular
        df_filtrado["Total"] = 0.0  # Valor ajustado

        cpf_titular_atual = None  # Variável para armazenar o CPF do titular atual

        # Dicionário de relacionamento
        relacao_mapeamento = {
            "T.": "Titular",
            "esp.": "Cônjuge", "esp": "Cônjuge", "es": "Cônjuge",
            "fil.": "Filho(a)", "fil": "Filho(a)", "Filh.": "Filho(a)",
            "Comp.": "Agregado(a)/outros",
            "mãe": "Mãe", "Pai": "Pai"
        }

        # Definir titular e dependentes
        for idx, row in df_filtrado.iterrows():
            par = row["Par."]
            if par == "T.":  # Se for titular
                cpf_titular_atual = row["CPF"]
                df_filtrado.at[idx, "Titular_CPF"] = cpf_titular_atual
                df_filtrado.at[idx, "Relação"] = "Titular"
            elif cpf_titular_atual:  # Se for dependente
                df_filtrado.at[idx, "Titular_CPF"] = cpf_titular_atual
                df_filtrado.at[idx, "Relação"] = relacao_mapeamento.get(par, "Outros")

        # Função para calcular os meses ativos, considerando o desligamento, se houver
        def calcular_meses_ativos(admissao, desligamento=None):
            if pd.isna(admissao):
                return 0  # Se não houver data de admissão, não há meses
            if pd.isna(desligamento):  # Se não houver desligamento, calcular até dezembro de 2024
                return 12 if admissao.year < 2024 else 13 - admissao.month
            # Se houver desligamento, calcular até a data de desligamento
            if desligamento.year == 2024 and admissao.year == 2024:
                return (desligamento.month - admissao.month)
            if desligamento.year == 2024 and admissao.year < 2024:
                return desligamento.month

        # Aplicar a função para calcular os meses de trabalho considerando o desligamento
        df_filtrado["Meses Ativos"] = df_filtrado.apply(
            lambda row: calcular_meses_ativos(row["Adm."], row["Deslig."]), axis=1
        )

        # Ajuste do cálculo dos meses e dos pesos
        for cpf_titular, grupo in df_filtrado.groupby("Titular_CPF"):
            if pd.notna(cpf_titular):  # Garantir que há um titular válido
                # Recuperar o total 2024 do titular
                total_titular = grupo[grupo["Relação"] == "Titular"]["Total 2024"].sum()

                dependentes = grupo[grupo["Relação"] != "Titular"].copy()


                # Calcular os meses totais do grupo (titular + dependentes)
                # meses_totais = grupo["Meses Ativos"] + dependentes["Meses Ativos"].sum()
                meses_totais = grupo["Meses Ativos"].sum()
                
                dependentes["Peso"] = dependentes["Meses Ativos"] / meses_totais

                # Se houver dependentes, calculamos a quantidade de meses deles considerando o desligamento
                if not dependentes.empty:

                    # Calcular os pesos para o grupo (titular e dependentes)
                    grupo["Peso"] = grupo["Meses Ativos"] / meses_totais
                    dependentes.loc[:, "Peso"] = dependentes["Meses Ativos"] / meses_totais

                    # Atribuir os pesos aos dependentes
                    df_filtrado.loc[dependentes.index, "Peso"] = dependentes["Peso"]

                # Atribuir o peso do titular ao grupo
                df_filtrado.loc[grupo.index, "Peso"] = grupo["Meses Ativos"] / meses_totais    

                # Agora, distribuímos proporcionalmente o valor total do titular entre os membros
                df_filtrado.loc[grupo.index, "Total"] = df_filtrado.loc[grupo.index, "Peso"] * total_titular
                df_filtrado.loc[dependentes.index, "Total"] = df_filtrado.loc[dependentes.index, "Peso"] * total_titular

        # Certifique-se de que "Total" está em formato numérico
        df_filtrado["Total"] = pd.to_numeric(df_filtrado["Total"], errors="coerce").fillna(0)

        # Formatar como moeda brasileira (R$)
        df_filtrado["Total"] = df_filtrado["Total"].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

        # Dicionário para armazenar os grupos familiares
        grupos_familiares = {}

        # Iterar sobre o DataFrame e estruturar os dados
        for _, row in df_filtrado.iterrows():
            cpf_titular = row["Titular_CPF"]
            
            # Se o titular ainda não foi registrado, adiciona
            if cpf_titular not in grupos_familiares:
                grupos_familiares[cpf_titular] = {
                    "Nome": row["Nome"],
                    "CPF": row["CPF"],
                    "Matricula": row["Mat."],
                    "Total": row["Total"],
                    "Dependentes": []
                }
            
            # Se não for titular, adiciona como dependente
            if row["Relação"] != "Titular":
                grupos_familiares[cpf_titular]["Dependentes"].append({
                    "Nome": row["Nome"],
                    "CPF": row["CPF"],
                    "Matricula": row["Mat."],
                    "Relação": row["Relação"],
                    "Total": row["Total"]
                })

        def enviar_emails():
            # Contador para testes de email
            contador = 0

            for cpf_titular, grupo in grupos_familiares.items():
                try:
                    if contador < 1:
                        corpo_email = f"""
                        <h1>Olá, {grupo['Nome']}!</h1>
                        <p>Segue abaixo a relação dos dependentes vinculados ao seu CPF:</p>
                        <p>Titular: {grupo['Nome']} - CPF: {grupo['CPF']} - Total: {grupo['Total']}</p>
                        """
                        for dependente in grupo["Dependentes"]:
                            corpo_email += f"""
                            <p>Dependente: {dependente['Nome']} - Relação: {dependente['Relação']} - CPF: {dependente['CPF']} - Total: {dependente['Total']}</p>
                            """
                        corpo_email += """
                        <p>Atenciosamente,</p>
                        <p>Equipe de Saúde</p>
                        """

                        msg = email.message.Message()
                        msg["Subject"] = "Relação de Despesas de Saúde"
                        msg["From"] = email_origem
                        msg["To"] = email_destino
                        password = senha_email
                        msg.add_header("Content-Type", "text/html; charset=utf-8")
                        msg.set_payload(corpo_email.encode("utf-8"), "utf-8")

                        envia = smtplib.SMTP("smtp.gmail.com", 587)
                        envia.starttls()
                        envia.login(msg["From"], password)
                        envia.sendmail(msg["From"], msg["To"], msg.as_string())

                        contador += 1
                        st.success("E-mail enviado com sucesso!")
                        print("E-mail enviado com sucesso!")

                except Exception as e:
                    st.error(f"Erro ao eniar o e-mail: {e}")
                    print(f"Erro ao eniar o e-mail: {e}")
    

        # Converter para JSON
        json_resultado = json.dumps(grupos_familiares, ensure_ascii=False, indent=4)

        # Se precisar salvar como arquivo:
        # with open("grupos_familiares.json", "w", encoding="utf-8") as f:
        #     f.write(json_resultado)        
        
        st.write("### Dados Processados")
        # st.write(lista_grupos_familiares)
        # Colunas a serem exibidas
        colunas_exibicao = ["Nome", "CPF", "Mat.", "Titular_CPF", "Relação", "Total"]
        # Ordenar primeiro pela coluna "Titular_CPF" e depois pela coluna "Relação" (para colocar o titular antes dos dependentes)
        df_filtrado = df_filtrado.sort_values(by=["Titular_CPF", "Relação"], ascending=[True, False])
        st.dataframe(df_filtrado[colunas_exibicao])
        
        # Supondo que seu DataFrame seja df_filtrado
        # Crie um arquivo Excel em memória (sem incluir o índice)
        output = io.BytesIO()
        df_filtrado[colunas_exibicao].to_excel(output, index=False, engine='openpyxl')  # Não inclui o índice
        output.seek(0)  # Voltar ao início do arquivo para leitura

        # Criar colunas para os botões
        col1, col2 = st.columns(2)

        # Botão de download na primeira coluna
        with col1:
            st.download_button(
                label="📂 Download XLSX",
                data=output,
                file_name="dados_filtrados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Baixar o arquivo processado"
            )

            # Botão de envio de e-mail na segunda coluna
            with col2:
                # st.markdown(
                #     """
                #     <style>
                #     .stButton>button {
                #         background-color: white ;
                #         color: black;
                #         font-weight: bold;
                #         border-radius: 8px;
                #         padding: 10px 20px;
                #     }
                #     </style>
                #     """,
                #     unsafe_allow_html=True
                # )
                
                if st.button("📧 Enviar e-mail"):
                    enviar_emails()

        # Exibir JSON no Streamlit
        # st.write("### Estrutura JSON dos Grupos Familiares")
        # st.json(json_resultado)

        # Exibir informações gerais sobre os dados
        st.write("### Informações gerais dos dados")
        st.write(f"Quantidade de registros filtrados: {df_filtrado.shape[0]}")
        st.write(f"Quantidade de registros do arquivo original: {df.shape[0]}")
        
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        print(f"Erro ao processar o arquivo: {e}")

# Rodapé com link para o LinkedIn
st.markdown(
    """
    <hr style='border:1px solid #e3e3e3;margin-top:40px'>
    <div style='text-align: center;'>
        Desenvolvido por 
        <a href='https://www.linkedin.com/in/tairone-amaral/' target='_blank'>
            Tairone Leandro do Amaral
        </a>
    </div>
    """,
    unsafe_allow_html=True
)