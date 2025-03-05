import streamlit as st
import pandas as pd
import json
import io
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
    if pd.isna(cpf):
        # return '24871771016' # Retorna um CPF fictício se o CPF for NaN
        return ''
    return str(cpf).replace('.','').replace('-','').strip().replace(' ', '').zfill(11)

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
        "DMED|2025|2024|N|||",
        "RESPO|49904329672|NOME DO RESPONSAVEL|31|995216547||||",
        "DECPJ|05699886000127|NOME EMPRESA|2|419761||49904329672|N||S|",
        "OPPAS|"
    ]
    
    # First sort by titular CPF
    for titular_cpf, grupo in sorted(df_filtrado.groupby("Titular_CPF")):

        # Create a sorting key with properly formatted CPFs
        df_filtrado['CPF_Sort'] = df_filtrado['Titular_CPF'].apply(lambda x: str(x).strip().replace(' ', '').zfill(11))

        # Sort by the formatted CPF key
        df_filtrado = df_filtrado.sort_values('CPF_Sort', ascending=True)

        # Drop the temporary sorting column
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
        return 12 if admission.year < 2024 else 13 - admission.month
    if termination.year == 2024 and admission.year == 2024:
        return (termination.month - admission.month)
    if termination.year == 2024 and admission.year < 2024:
        return termination.month

uploaded_file = st.file_uploader("Escolha um arquivo Excel", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl", skiprows=2, sheet_name="Mensalidade")
        
        # Filter data
        ano_anterior = pd.Timestamp.now().year - 1
        ano_atual = pd.Timestamp.now().year
        df["Deslig."] = pd.to_datetime(df["Deslig."], errors="coerce")
        df_filtrado = df[(df["Deslig."].dt.year == ano_anterior) | 
                        (df["Deslig."].dt.year == ano_atual) | 
                        (df["Deslig."].isna())].copy()
        
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
        st.write("### Dados Processados")
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