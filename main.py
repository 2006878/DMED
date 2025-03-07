import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
import os
from datetime import datetime

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

def format_cpf(cpf):
    if pd.isna(cpf) or str(cpf).strip() == '' or str(cpf).strip() == '0':
        return ''
    return str(cpf).strip().replace(' ', '').replace('.', '').replace('-', '').zfill(11)

def format_valor(valor_str):
    try:
        if pd.isna(valor_str):
            return ""
        valor = valor_str.replace("R$", "").replace(".", "").replace(",", ".").strip()
        return f"{int(float(valor)*100):09d}"
    except:
        return ""

def normalize_name(name):
    import unicodedata
    # Convert to uppercase and normalize
    normalized = unicodedata.normalize('NFKD', str(name).upper())
    # Remove accents
    normalized = u"".join([c for c in normalized if not unicodedata.combining(c)])
    # Replace Ç with C
    normalized = normalized.replace('Ç', 'C')
    # Remove any remaining special characters
    normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
    return normalized

def create_dmed_content(df_filtrado):
    content = [
        "DMED|{ano_atual}|{ano_anterior}|N|||",
        "RESPO|49904329672|NOME DO RESPONSAVEL|31|995216547||||",
        "DECPJ|05699886000127|NOME EMPRESA|2|419761||49904329672|N||S|",
        "OPPAS|"
    ]
    
    # First sort by titular CPF
    for titular_cpf, grupo in sorted(df_filtrado.groupby("Titular_CPF")):

        # Create sorting key and sort the dataframe
        df_filtrado['CPF_Sort'] = df_filtrado['Titular_CPF'].apply(format_cpf)
        df_filtrado = df_filtrado.sort_values(['CPF_Sort', 'Relação'], ascending=[True, False])

        # Remove temporary sorting column
        df_filtrado = df_filtrado.drop('CPF_Sort', axis=1)

        if pd.notna(titular_cpf):
            titular = grupo[grupo["Relação"] == "Titular"].iloc[0]
            valor_titular = float(titular["Total"].replace("R$", "").replace(".", "").replace(",", ".").strip() or 0)
            
            if valor_titular > 0:
                nome_titular = normalize_name(titular['Nome'])
                valor_titular_fmt = format_valor(titular["Total"])
                
                content.append(f"TOP|{format_cpf(titular_cpf)}|{nome_titular}|{valor_titular_fmt}|")
                
                # Get dependents and ensure CPF is properly formatted for sorting
                dependentes = grupo[grupo["Relação"] != "Titular"].copy()
                dependentes['CPF'] = dependentes['CPF'].apply(format_cpf)
                
                # Sort dependents by formatted CPF and birth date
                dependentes_sorted = dependentes.sort_values(['CPF'])
                
                for _, dep in dependentes_sorted.iterrows():
                    valor_dep = format_valor(dep["Total"])
                    codigo_dep = get_dependent_code(dep["Relação"])
                    nome_dep = normalize_name(dep['Nome'])
                    data_nasc = "" # Default if birth date is missing
                    
                    content.append(f"DTOP|{format_cpf(dep['CPF'])}|{data_nasc}|{nome_dep}|{codigo_dep}|{valor_dep}|")
    
    content.append("FIMDmed|")
    return "\n".join(content)

def get_dependent_code(relacao):
    codes = {
        "Cônjuge": "03",
        "Filho(a)": "04",
        "Enteado(a)": "06",
        "Pais": "08",
        "Agregado(a)/outros": "10"
    }
    return codes.get(relacao, "10")

def format_date(date):
    if pd.isna(date):
        return ''
    return pd.to_datetime(date).strftime('%Y%m%d')

def calculate_active_months(admission, termination=None):
    if pd.isna(admission):
        return 0
    if pd.isna(termination):
        return 12 if admission.year < ano_anterior else 13 - admission.month
    if termination.year == ano_anterior and admission.year == ano_anterior:
        return (termination.month - admission.month)
    if termination.year == ano_anterior and admission.year < ano_anterior:
        return termination.month
    if termination.year > ano_anterior and admission.year == ano_anterior:
        return (12 - admission.month)
    if termination.year > ano_anterior and admission.year < ano_anterior:
        return 12
    
# uploaded_file = st.file_uploader("Escolha um arquivo Excel", type=["xlsx"])
mensalidade_file = "mensalidades/IRF.xlsx"

# Caminho da pasta de dados
data_folder = os.path.join(os.getcwd(), 'despesas')

# Arquivo base
despesas_file = os.path.join(os.getcwd(), 'despesas_file.csv')

# Verificar se o arquivo existe e não está vazio
if not os.path.exists(despesas_file) or os.path.getsize(despesas_file) == 0:
    print(f"O arquivo '{despesas_file}' está vazio ou não existe. Inicializando DataFrame vazio.")
else: 
    # Remover o arquivo se ele existir
    os.remove(despesas_file)
    print(f"Arquivo '{despesas_file}' removido com sucesso.")

# Initialize empty DataFrame
df_despesas = pd.DataFrame()
print("DataFrame df_despesas inicializado.")

try:
    start = datetime.now()
    # Iterate through files in data folder 
    for filename in os.listdir(data_folder):
        file_path = os.path.join(data_folder, filename)
        if os.path.isfile(file_path) and filename.endswith('.csv'):
            # Add sep parameter to handle correct field separation
            # Read CSV with specific column names and positions
            df = pd.read_csv(file_path, encoding='latin1', sep=';')
            df_despesas = pd.concat([df_despesas, df], ignore_index=True)
    # Convert columns to numeric
    df_despesas["VALOR_DO_SERVICO"] = pd.to_numeric(df_despesas["VALOR_DO_SERVICO"], errors="coerce").fillna(0).round(2)
    
    # Group by BENEFICIARIO and get the first occurrence of other columns while summing VALOR_DO_SERVICO
    df_despesas = df_despesas.groupby("BENEFICIARIO").agg({
        'CPF_DO_RESPONSAVEL': 'first',
        'VALOR_DO_SERVICO': 'sum'
    }).reset_index()

    print("Registros únicos por BENEFICIARIO com soma total calculada.")

    # Display processed data
    st.write("### Despesas Processadas")
    # Sort records by CPF_DO_RESPONSAVEL in ascending order
    df_despesas = df_despesas.sort_values('CPF_DO_RESPONSAVEL', ascending=True)
    st.dataframe(df_despesas)

    # Save the updated base file
    df_despesas.to_csv(despesas_file, index=False)
    print(f"Arquivo '{despesas_file}' atualizado com sucesso em {datetime.now() - start} segundos")
except Exception as e:
    print(f"Erro ao processar arquivo: {e}")
    

if mensalidade_file is not None and df_despesas is not None:
    try:
        df_mensalidades = pd.read_excel(mensalidade_file, engine="openpyxl", skiprows=2, sheet_name="Mensalidade")
        print("DataFrame df_mensalidades inicializado.")

        # Filter data
        ano_anterior = pd.Timestamp.now().year - 1
        ano_atual = pd.Timestamp.now().year
        df_mensalidades["Deslig."] = pd.to_datetime(df_mensalidades["Deslig."], errors="coerce")
        df_filtrado = df_mensalidades[(df_mensalidades["Deslig."].dt.year == ano_anterior) | 
                        (df_mensalidades["Deslig."].dt.year == ano_atual) | 
                        (df_mensalidades["Deslig."].isna())].copy()
        
        # Data transformations
        df_filtrado["Mat."] = df_filtrado["Mat."].astype(str)
        df_filtrado["Total 2024"] = pd.to_numeric(df_filtrado["Total 2024"], errors="coerce").fillna(0).round(2)
        df_filtrado["Titular_CPF"] = None
        df_filtrado["Relação"] = None
        df_filtrado["Total"] = 0.0

        # Relationship mapping
        relacao_mapeamento = {
            "T.": "Titular",
            "esp.": "Cônjuge", "esp": "Cônjuge", "es": "Cônjuge",
            "fil.": "Filho(a)", "fil": "Filho(a)", "Filh.": "Filho(a)",
            "Comp.": "Agregado(a)/outros",
            "mãe": "Mãe", "Pai": "Pai"
        }

        # Process relationships
        cpf_titular_atual = None
        for idx, row in df_filtrado.iterrows():
            par = row["Par."]
            if par == "T.":
                cpf_titular_atual = row["CPF"]
                df_filtrado.at[idx, "Titular_CPF"] = cpf_titular_atual
                df_filtrado.at[idx, "Relação"] = "Titular"
            elif cpf_titular_atual:
                df_filtrado.at[idx, "Titular_CPF"] = cpf_titular_atual
                df_filtrado.at[idx, "Relação"] = relacao_mapeamento.get(par, "Outros")

        # Calculate active months and weights
        df_filtrado["Meses Ativos"] = df_filtrado.apply(
            lambda row: calculate_active_months(row["Adm."], row["Deslig."]), axis=1
        )

        # Process family groups
        for cpf_titular, grupo in df_filtrado.groupby("Titular_CPF"):
            if pd.notna(cpf_titular):
                total_titular = grupo[grupo["Relação"] == "Titular"]["Total 2024"].sum()
                meses_totais = grupo["Meses Ativos"].sum()
                df_filtrado.loc[grupo.index, "Peso"] = grupo["Meses Ativos"] / meses_totais
                df_filtrado.loc[grupo.index, "Total"] = df_filtrado.loc[grupo.index, "Peso"] * total_titular

        # Format currency
        df_filtrado["Total"] = df_filtrado["Total"].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

        # Display processed data
        st.write("### Mensalidades Processados")
        colunas_exibicao = ["Nome", "CPF", "Mat.", "Titular_CPF", "Relação", "Total"]
        df_filtrado = df_filtrado.sort_values(by=["Titular_CPF", "Relação"], ascending=[True, False])
        st.dataframe(df_filtrado[colunas_exibicao])

        # Create download buttons
        output = io.BytesIO()
        df_filtrado[colunas_exibicao].to_excel(output, index=False, engine='openpyxl')
        output.seek(0)

        dmed_content = create_dmed_content(df_filtrado)

        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                label="📂 Download XLSX",
                data=output,
                file_name="dados_filtrados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            if st.button("Mostrar Dados JSON"):
                st.write("### Estrutura JSON dos Grupos Familiares")
                st.json(json.dumps(df_filtrado.to_dict(), ensure_ascii=False))

        with col3:
            st.download_button(
                label="Download DMED",
                data=dmed_content.encode('utf-8'),
                file_name=f"DMED_{datetime.now().strftime('%Y%m%d')}.DEC",
                mime="text/plain"
            )

        # Display statistics
        st.write("### Informações gerais dos dados")
        st.write(f"Quantidade de registros filtrados: {df_filtrado.shape[0]}")
        st.write(f"Quantidade de registros do arquivo original: {df.shape[0]}")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        print(f"Erro ao processar o arquivo: {e}")

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