import streamlit as st
import pandas as pd

# Configurações da página Streamlit
st.set_page_config(page_title="Dados DMED", layout="wide")

st.title("Tratamento de dados de saúde - DMED")

# Widget de upload de arquivo   
# uploaded_file = st.file_uploader("Escolha um arquivo Excel", type=["xlsx"])

# Definir o arquivo para upload
uploaded_file = "./anexos/IRF.xlsx"

if uploaded_file is not None:
    try:
        # Definir as colunas desejadas
        # colunas_desejadas = ["Nome", "Mat.", "CPF", "Par.", "Total 2024"]

        # Ler o arquivo ignorando as duas primeiras linhas
        df = pd.read_excel(uploaded_file, engine="openpyxl", skiprows=2, sheet_name="Mensalidade")

        df["Deslig."] = pd.to_datetime(df["Deslig."], errors="coerce")

        # Filtrar apenas as linhas onde "Deslig." é o ano anterior ao atual ou está vazio (NaT)
        ano_anterior = pd.Timestamp.now().year - 1
        df_filtrado = df[(df["Deslig."].dt.year == ano_anterior) | (df["Deslig."].isna())]

        # Converter a coluna "Total 2024" para numérico (caso tenha valores não numéricos)
        df_filtrado.loc[:, "Total 2024"] = pd.to_numeric(df_filtrado["Total 2024"], errors="coerce")
        
        # Preencher valores nulos com 0
        df_filtrado.fillna({"Total 2024": 0}, inplace=True)
        
        # Agrupar os valores de Total 2024 por Nome
        df_agrupado = df_filtrado[df_filtrado["Par."] == "T."].groupby(["Nome", "CPF"], as_index=False)["Total 2024"].sum()

        # Criar um dicionário para fácil acesso ao Total 2024 corrigido dos titulares
        totais_por_cpf = {row["CPF"]: row["Total 2024"] for _, row in df_agrupado.iterrows()}

        # Lista que armazenará os grupos familiares
        lista_grupos_familiares = {}

        # Variável para armazenar o CPF do titular mais recente
        cpf_titular_atual = None  

        def processar_linha(row):
            global cpf_titular_atual  # Mantém o titular atual enquanto percorremos as linhas

            if row["Par."] == "T.":  # Novo titular encontrado
                cpf_titular_atual = row["CPF"]  # Atualiza o titular atual
                lista_grupos_familiares[cpf_titular_atual] = {
                    "Titular": {
                        "Nome": row["Nome"],
                        "CPF": row["CPF"],
                        "Total 2024": row["Total 2024"],
                        "Relação": "Titular"
                    },
                    "Dependentes": []
                }

            elif row["Par."] in ["esp.", "fil.", "Comp.", "es", "esp", "fil", "Filh.", "mãe", "Pai"]:  # Dependentes
                if cpf_titular_atual is not None:  # Garante que temos um titular antes de adicionar dependentes
                    if row["Par."] in ["esp.", "esp", "es"]:
                        relacao = "Cônjuge"
                    elif row["Par."] in ["fil.", "fil", "Filh."]:
                        relacao = "Filho(a)"
                    elif row["Par."] in ["Comp."]:
                        relacao = "Agregado(a)/outros"
                    elif row["Par."] in ["mãe", "Pai"]:
                        relacao = "Mãe"
                    else:
                        relacao = "Outros"

                    dependente = {
                        "Nome": row["Nome"],
                        "CPF": row["CPF"],
                        "Total 2024": row["Total 2024"],
                        "Relação": relacao
                    }
                    lista_grupos_familiares[cpf_titular_atual]["Dependentes"].append(dependente)

        # Aplicar a função a cada linha do DataFrame original
        df_filtrado.apply(processar_linha, axis=1)

        # Agora, ajustar o Total 2024 para cada membro com base no tamanho do grupo
        for cpf_titular, grupo in lista_grupos_familiares.items():
            total_titular = grupo["Titular"]["Total 2024"]
            num_membros = 1 + len(grupo["Dependentes"])  # Titular + dependentes

            if num_membros > 0:
                valor_por_pessoa = total_titular / num_membros
                # Formatar como moeda Real Brasileiro (R$)
                valor_por_pessoa = f"R${valor_por_pessoa:.2f}"
                valor_por_pessoa = valor_por_pessoa.replace(".", ",")  # Substituir ponto por vírgula

                # Atualizar o valor para todos os membros
                grupo["Titular"]["Total 2024"] = valor_por_pessoa
                for dependente in grupo["Dependentes"]:
                    dependente["Total 2024"] = valor_por_pessoa
        
        st.write("### Grupos Familiares")
        # st.write(lista_grupos_familiares)
        st.write(df_filtrado)

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