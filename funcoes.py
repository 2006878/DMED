import pandas as pd
from datetime import datetime
import os
from fpdf import FPDF
import re
import requests
from io import BytesIO
import streamlit as st

ano_anterior = pd.Timestamp.now().year - 1
ano_atual = pd.Timestamp.now().year

def format_cpf(cpf):
    if pd.isna(cpf) or str(cpf).strip() == '' or str(cpf).strip() == '0':
        return ''
    return str(cpf).strip().replace(' ', '').replace('.', '').replace('-', '').zfill(11)

def format_valor(valor_str):
    try:
        if pd.isna(valor_str):
            return ""
        # Remove currency symbol and standardize decimal separator
        valor = str(valor_str).replace("R$", "").strip()
        # Handle different decimal formats
        if "," in valor:
            valor = valor.replace(".", "").replace(",", ".")
        # Convert to float and round to 2 decimal places
        valor_float = round(float(valor), 2)
        # Convert to cents without decimal point
        valor_cents = int(valor_float * 100)
        return f"{valor_cents:09d}"
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

def create_dmed_content():
    start = datetime.now()
    processa_mensalidades()
    mensalidades_file = os.path.join(os.getcwd(), 'mensalidade_file.csv')
    try:
        df_filtrado = pd.read_csv(mensalidades_file)
    except Exception as e:
        print(f"Erro ao ler o arquivo de mensalidades: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro
    
    processa_descontos()

    processa_despesas()
    despesas_file = os.path.join(os.getcwd(), 'despesas_file.csv')
    try:
        df_despesas = pd.read_csv(despesas_file)
    except Exception as e:
        print(f"Erro ao ler o arquivo de despesas: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro

    print("Iniciando criação do DMed...")
    # Format Total column correctly
    # Certifique-se de que a coluna 'Total' contém apenas valores numéricos
    df_filtrado['Total'] = pd.to_numeric(df_filtrado['Total'], errors='coerce').fillna(0)
    # Arredonde os valores e aplique a formatação
    df_filtrado['Total'] = df_filtrado['Total'].round(2).apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    df_filtrado['Titular_CPF'] = df_filtrado['Titular_CPF'].apply(format_cpf)

    cpf_respostavel = "59374705672"
    nome_respostavel = "Paulo Alexandre da Silva"
    cnpj_empresa = "16651002000180"
    nome_empresa = "COOPERATIVA DE ECONOMIA E CREDITO MUTUO DOS SERVIDORES MUNICIPAIS DE ITABIRA LTDA SICOOB COSEMI"

    content = [
        f"DMED|{ano_atual}|{ano_anterior}|N|||",
        f"RESPO|{cpf_respostavel}|{nome_respostavel}||||||",
        f"DECPJ|{cnpj_empresa}|{nome_empresa}|2|419761||{cpf_respostavel}|N||S|",
        "OPPAS|"
    ]
    
    # First sort by titular CPF
    for titular_cpf, grupo in sorted(df_filtrado.groupby("Titular_CPF")):

        # Create sorting key and sort the dataframe
        df_filtrado['CPF_Sort'] = df_filtrado['Titular_CPF']
        df_filtrado = df_filtrado.sort_values(['CPF_Sort', 'Relação'], ascending=[True, False])

        # Remove temporary sorting column
        df_filtrado = df_filtrado.drop('CPF_Sort', axis=1)

        if pd.notna(titular_cpf):
            titular = grupo[grupo["Relação"] == "Titular"].iloc[0]
            nome_titular = normalize_name(titular['Nome'])
    
            # Get all family expenses at once
            df_despesas = busca_dados_despesas(titular_cpf, titular['Nome'])
            
            # Get titular value from both sources
            valor_mensalidade = pd.to_numeric(str(titular["Total"]).replace("R$", "").replace(".", "").replace(",", ".").strip(), errors='coerce')

            valor_despesas = float(str(df_despesas[df_despesas['Nome'] == nome_titular]['Valor'].iloc[0]).replace("R$", "").replace(".", "").replace(",", ".").strip() or 0) if not df_despesas.empty and nome_titular in df_despesas['Nome'].values else 0
            
            valor_titular = valor_mensalidade + valor_despesas
            
            valor_titular_fmt = format_valor(valor_titular)
            
            content.append(f"TOP|{format_cpf(titular_cpf)}|{nome_titular}|{valor_titular_fmt}|")
            
            # Get dependents and ensure CPF is properly formatted for sorting
            # print(grupo)
            dependentes = grupo[grupo["Relação"] != "Titular"].copy()
            # print(len(dependentes))
            dependentes['CPF'] = dependentes['CPF'].apply(format_cpf)
            
            # Sort dependents by formatted CPF and birth date
            dependentes_sorted = dependentes.sort_values(['CPF'])
            
            # For dependents, reuse the same df_despesas
            for _, dep in dependentes_sorted.iterrows():
                nome_dep = normalize_name(dep['Nome'])
                valor_mensalidade = pd.to_numeric(str(dep["Total"]).replace("R$", "").replace(".", "").replace(",", ".").strip(), errors='coerce')
                valor_despesas = float(str(df_despesas[df_despesas['Nome'] == nome_dep]['Valor'].iloc[0]).replace("R$", "").replace(".", "").replace(",", ".").strip() or 0) if not df_despesas.empty and nome_dep in df_despesas['Nome'].values else 0
                
                valor_total = valor_mensalidade + valor_despesas
                valor_dep = format_valor(str(valor_total))
                codigo_dep = get_dependent_code(dep["Relação"])
                data_nasc = ""
                
                content.append(f"DTOP|{format_cpf(dep['CPF'])}|{data_nasc}|{nome_dep}|{codigo_dep}|{valor_dep}|")
    
    content.append("FIMDmed|")
    end = datetime.now()
    print(f"Tempo total de execução: {end - start}")
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
    if pd.isna(admission) or admission.year > ano_anterior:
        return []
    if pd.isna(termination):
        return [month for month in range(1, 13)] if admission.year < ano_anterior else [month for month in range(int(admission.month), 13)]
    
    if termination.year == ano_anterior and admission.year == ano_anterior:
        return [month for month in range(int(admission.month), int(termination.month) + 1)]
    
    if termination.year == ano_anterior and admission.year < ano_anterior:
        return [month for month in range(1, int(termination.month) + 1)]
    
    if termination.year > ano_anterior and admission.year == ano_anterior:
        return [month for month in range(int(admission.month), 13)]
    
    if termination.year > ano_anterior and admission.year < ano_anterior:
        return [month for month in range(1, 13)]  # Returns [1,2,3,4,5,6,7,8,9,10,11,12]
    
    return []
    
def processa_mensalidades():
    url_excel_file = "https://drive.google.com/uc?id=1NEqJ7VaM_dICfTPpSSVIkwwfSLCaOTcE"
    df_mensalidades = pd.DataFrame()
    
    try:
        response = requests.get(url_excel_file)
        response.raise_for_status()  # Verificar se o download foi bem-sucedido
        excel = pd.ExcelFile(BytesIO(response.content), engine="openpyxl")
        
        print("Processando mensalidades...")
        for sheet_name in excel.sheet_names:
            #print(f"\nProcessing sheet: {sheet_name}")
            # Read all columns from Excel
            df = pd.read_excel(excel, sheet_name=sheet_name, engine="openpyxl")
            #print(f"Found columns: {df.columns.tolist()}")
            
            # Add default plan type if column doesn't exist
            if 'Tipo de Plano' not in df.columns:
                if sheet_name.lower().startswith('apartamento'):
                    df['Tipo de Plano'] = 'Apartamento'
                else:
                    df['Tipo de Plano'] = 'Enfermaria'
            
            # Standardize plan types
            df['Tipo de Plano'] = df['Tipo de Plano'].apply(
                lambda x: 'Apartamento' if str(x).strip().upper() == 'APARTAMENTO' 
                else 'Enfermaria'
            )

            # Verificar se as colunas necessárias existem
            required_columns = ['Par.', 'CPF', 'Adm.', 'Deslig.']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise KeyError(f"Colunas ausentes na planilha {sheet_name}: {missing_columns}")
            
            # Filtrar dados
            ano_anterior = pd.Timestamp.now().year - 1
            df["Deslig."] = pd.to_datetime(df["Deslig."], errors="coerce")
            df["Adm."] = pd.to_datetime(df["Adm."], errors="coerce")
            df_filtrado = df[
                (df["Deslig."].dt.year >= ano_anterior) | 
                (pd.isna(df["Deslig."]))
            ].copy()

            # Transformações de dados
            df_filtrado["CPF"] = df_filtrado["CPF"].apply(format_cpf)
            df_filtrado["Titular_CPF"] = None
            df_filtrado["Relação"] = None
            df_filtrado["Total"] = 0.0

            # Mapeamento de relações
            relacao_mapeamento = {
                "T.": "Titular", "T": "Titular",
                "esp.": "Cônjuge", "esp": "Cônjuge", "es": "Cônjuge", "Conj.": "Cônjuge", "conj": "Cônjuge",
                "fil.": "Filho(a)", "fil": "Filho(a)", "Filh.": "Filho(a)",
                "ent.": "Enteado(a)", "ent": "Enteado(a)", "Ent.": "Enteado(a)",
                "Comp.": "Agregado(a)/outros", "comp.": "Agregado(a)/outros",
                "mãe": "Pais", "mae": "Pais", "Pai": "Pais"
            }

            # Processar relações
            cpf_titular_atual = None
            plano_tipo_atual = None
            for idx, row in df_filtrado.iterrows():
                par = row["Par."]
                if par == "T.":
                    cpf_titular_atual = format_cpf(row["CPF"]) if pd.notna(row["CPF"]) else row["Nome"]
                    df_filtrado.at[idx, "Titular_CPF"] = cpf_titular_atual
                    df_filtrado.at[idx, "Relação"] = "Titular"
                    plano_tipo_atual = row["Tipo de Plano"]  # Store titular's plan type
                elif cpf_titular_atual:
                    df_filtrado.at[idx, "Titular_CPF"] = cpf_titular_atual
                    df_filtrado.at[idx, "Relação"] = relacao_mapeamento.get(par, "Outros")
                    df_filtrado.at[idx, "Tipo de Plano"] = plano_tipo_atual  # Apply titular's plan type to dependent
            
            # Calcular meses ativos e pesos
            df_filtrado["Meses Ativos"] = df_filtrado.apply(
                lambda row: calculate_active_months(row["Adm."], row["Deslig."]), axis=1
            )

            # Filtrar linhas com meses ativos diferente de vazio
            df_filtrado = df_filtrado[df_filtrado["Meses Ativos"].astype(bool)]

            # Adicionar colunas padrão
            
            df_filtrado["Tipo de Plano"] = df_filtrado.get("Tipo de Plano", "Enfermaria")
            df_filtrado['is_camara'] = sheet_name.lower().startswith('câmara')
            df_filtrado['is_complemento'] = sheet_name.lower().startswith('complemento')
            
            # Dividir valores entre os dependentes
            # Inside the group processing section of processa_mensalidades()
            # Dentro do loop que processa os grupos:
            for cpf_titular, grupo in df_filtrado.groupby("Titular_CPF"):
                if pd.notna(cpf_titular):
                    titular = grupo[grupo["Relação"] == "Titular"].iloc[0]
                    is_camara = titular['is_camara']

                    # Get total value from "Total 2024" column
                    valor_total_anual = float(titular["Total 2024"]) if pd.notna(titular["Total 2024"]) else 0

                    if is_camara:
                        # Calculate active months only for first 4 members
                        total_meses_validos = sum(
                            len(member["Meses Ativos"])
                            for idx, (_, member) in enumerate(grupo.iterrows())
                            if idx > 0
                        )
                    else:
                        # Calculate active months only for first 4 members
                        total_meses_validos = sum(
                            len(member["Meses Ativos"])
                            for idx, (_, member) in enumerate(grupo.iterrows())
                            if idx < 4
                        )

                    # Calculate value per active month for valid members
                    valor_por_mes = valor_total_anual / total_meses_validos if total_meses_validos > 0 else 0

                    # Redefinir os índices do grupo para evitar problemas de indexação
                    grupo = grupo.reset_index(drop=True)

                    # Distribute value based on active months for each member
                    for idx, member in grupo.iterrows():
                        if is_camara:
                            if member["Relação"] == "Titular":
                                grupo.at[idx, "Total"] = 0
                            else:
                                meses_ativos_membro = len(member["Meses Ativos"])
                                valor_membro = valor_por_mes * meses_ativos_membro
                                grupo.at[idx, "Total"] = valor_membro
                        else:
                            if idx < 4:  # First 4 members
                                meses_ativos_membro = len(member["Meses Ativos"])
                                valor_membro = valor_por_mes * meses_ativos_membro
                                grupo.at[idx, "Total"] = valor_membro
                            else:  # Beyond 4 members
                                grupo.at[idx, "Total"] = 0

                    # Adicionar os registros ao DataFrame df_mensalidades
                    df_mensalidades = pd.concat([df_mensalidades, grupo], ignore_index=True)
        
        mensalidades_file = 'mensalidade_file.csv'
        # Salvar dados processados
        df_mensalidades.to_csv(mensalidades_file, index=False)
        print(f"Arquivo de mensalidades atualizado com sucesso!")
        return mensalidades_file
    except Exception as e:
        print(f"Erro ao baixar ou processar o arquivo do Google Drive: {e}")
        return None
    
def processa_despesas():
    print("Processando despesas...")
    # try:
    #     # Direct download URLs for each CSV file
    #     csv_urls = [
    #         "https://drive.google.com/uc?id=1Z5pfvRtS8yqXVf8u867BDmgN4BiHhPKs",
    #         "https://drive.google.com/uc?id=1sHdItzuc6srIbM11a255DSy_xIJGEpsy",
    #         "https://drive.google.com/uc?id=1d3oN54IUvfJKoakIC4X2AypDWSkDrBrR",
    #         "https://drive.google.com/uc?id=1B-4TwpLRHMlxVjQco21BIaFPepvd1Le1",
    #         "https://drive.google.com/uc?id=1Pq_o57GAohLgpcqBe8A4iHeNIUgS5pwh",
    #         "https://drive.google.com/uc?id=1YQWTcyZT7Z7nlC3xVluA7K7liKNlxIYK",
    #         "https://drive.google.com/uc?id=1MCgApVa45epiFX5mvUEAJFmXEahe3bxW",
    #         "https://drive.google.com/uc?id=1ujLQQL12rZ6giicEL25EK2t60n8zuRnY",
    #         "https://drive.google.com/uc?id=1gI8JE9KMP2hII2J4I8CzEAANImiVy9_e",
    #         "https://drive.google.com/uc?id=1Yz2MLHBi1MLrDglu18s18vGmUqaPZuBe",
    #         "https://drive.google.com/uc?id=1yXn_HleVD0lZ_1kA2exTQUK8OrrsEuKJ",
    #         "https://drive.google.com/uc?id=1m-kEXJl2hjfxkYahHRiWYxbDerieKULx",
    #         "https://drive.google.com/uc?id=1IhJoaM-rzk5PxAllmiOixCJy43I5JywP",
    #         "https://drive.google.com/uc?id=14KQMu3DGf487Lac_KQgb6G8t6pMe1XXu",
    #         "https://drive.google.com/uc?id=1W-PfFd9QEbs5qO9Z0teq2th2hn35_0Tq",
    #         "https://drive.google.com/uc?id=1j0GLvhXqNgmYWOQi8kHCnFbGHd7lS4Q7",
    #         "https://drive.google.com/uc?id=10nmuCaNHdXCALwTMKlCqBwtVnEwgjET0",
    #         "https://drive.google.com/uc?id=1QME2XU1NNhYcDZhkU03ExOXAJSKHw4du",
    #         "https://drive.google.com/uc?id=1u_TEEOdEPBGBqWWMcjmYGYgh0UBZ07-c",
    #         "https://drive.google.com/uc?id=16xlx0fiEW3cxLI42pxjoTFw7FAdGy_hP",
    #         "https://drive.google.com/uc?id=17TzbF1SLlwD7a6Kn2xATO32a2XMwnGKp",
    #         "https://drive.google.com/uc?id=1w-CDOzq5h6Q0VI8Leu14XIX_ZhsKVaah",
    #         "https://drive.google.com/uc?id=1MKUWXU1IZyHKvTpuHH3eZZE-AgX6Nysv",
    #         "https://drive.google.com/uc?id=1qlAGVHPVdPTre4pj3dlXO88Xxa5VGNXE",
    #         "https://drive.google.com/uc?id=1AD_AXTQoBBYMszNrZhUidjVuasQ8IQy9",
    #         "https://drive.google.com/uc?id=1JnXLFUbZCAAJgaBF4EIA6sFhqbCpRtOd",
    #         "https://drive.google.com/uc?id=1OVg4IMe-j0P8eKRPujsyv9RV8PTfKAMh",
    #         "https://drive.google.com/uc?id=1eP5HfqthGyfKlbWxcEFyLrSmsfWRO7Hx",
    #         "https://drive.google.com/uc?id=1tlLfCci_Yo0ty0QR1u1KLedH19xBBJNK",
    #         "https://drive.google.com/uc?id=1Fdn8ePUM1CVk7dHuw9VGjA-DZR57bMWq",
    #         "https://drive.google.com/uc?id=1bOIsE182VieY5Xt-Dmlt96m72oaMNT92",
    #         "https://drive.google.com/uc?id=1yEDq1VNrPTJLp00ogKdLvfCKTIZRU1I3",
    #         "https://drive.google.com/uc?id=1nhF-NvJIB61pUjI1XdCIrD1LS7wT68Dq",
    #         "https://drive.google.com/uc?id=1qQ1JYJmMh7zhNqfXThWC1SpdxP7EoZdD",
    #         "https://drive.google.com/uc?id=1_WV2At8dOh4hCW9sdo6Y_JnYtyukOiDh",
    #         "https://drive.google.com/uc?id=1k6QX0qDeT4VSTXLTuNQxd6PSj7AkQtS1",
    #     ]
        
    #     df_despesas = pd.DataFrame()

    #     for url in csv_urls:
    #         response = requests.get(url)
    #         response.raise_for_status()
            
    #         df = pd.read_csv(BytesIO(response.content), encoding='latin1', sep=';',
    #                        usecols=['CPF_DO_RESPONSAVEL', 'BENEFICIARIO', 'VALOR_DO_SERVICO'])
    #         df_despesas = pd.concat([df_despesas, df], ignore_index=True)
    
    try:
        # Caminho da pasta de dados
        data_folder = os.path.join(os.getcwd(), 'despesas_nova')
        
        # Initialize empty DataFrame
        df_despesas = pd.DataFrame()
        #print("DataFrame df_despesas inicializado.")

        # Iterate through files in data folder 
        for filename in os.listdir(data_folder):
            file_path = os.path.join(data_folder, filename)
            if os.path.isfile(file_path) and filename.endswith('.csv'):
                # Read only specified columns
                df = pd.read_csv(file_path, encoding='latin1', sep=';', 
                    usecols=['CPF_DO_RESPONSAVEL', 'BENEFICIARIO', 'VALOR_DO_SERVICO'])
                df_despesas = pd.concat([df_despesas, df], ignore_index=True)
            
        df_despesas["VALOR_DO_SERVICO"] = pd.to_numeric(df_despesas["VALOR_DO_SERVICO"], errors="coerce").fillna(0).round(2)
        df_despesas = df_despesas.groupby("BENEFICIARIO").agg({
            'CPF_DO_RESPONSAVEL': 'first',
            'VALOR_DO_SERVICO': 'sum'
        }).reset_index()
        df_despesas['CPF_DO_RESPONSAVEL'] = df_despesas['CPF_DO_RESPONSAVEL'].apply(format_cpf)
        
        despesas_file = 'despesas_file.csv'
        df_despesas.to_csv(despesas_file, index=False)
        print(f"Arquivo de despesas atualizado com sucesso!")
        return despesas_file
    
    except Exception as e:
        print(f"Error processing expenses: {e}")
        return None

def processa_descontos():
    url_excel_file = "https://drive.google.com/uc?id=132cv-9fgKpgHUkJZbl3hz0G5nkJFot22"
    df_descontos = pd.DataFrame()

    try:
        response = requests.get(url_excel_file)
        response.raise_for_status()  # Verificar se o download foi bem-sucedido
        excel = pd.ExcelFile(BytesIO(response.content), engine="openpyxl")
        
        print("Processando descontos...")

        # Read all sheets from single Excel file
        excel = pd.ExcelFile(excel)
        for sheet_name in excel.sheet_names:
            df = pd.read_excel(excel, sheet_name=sheet_name, engine="openpyxl",
                             usecols=["Nome", "Total de Descontos"])
            df_descontos = pd.concat([df_descontos, df], ignore_index=True)
        
        # Convert column to numeric
        df_descontos["Total de Descontos"] = pd.to_numeric(df_descontos["Total de Descontos"], 
                                                        errors="coerce").fillna(0).round(2)
        
        # Clean the Nome column by stripping whitespace and standardizing case
        df_descontos['Nome'] = df_descontos['Nome'].str.strip().str.upper()

        # Group by Nome after cleaning and sum Total de Descontos
        df_descontos = df_descontos.groupby('Nome', as_index=False).agg({
            'Total de Descontos': 'sum'
        }).reset_index(drop=True)

        descontos_file = 'descontos_file.csv'
        # Save the updated base file
        df_descontos.to_csv(descontos_file, index=False)
        print(f"Arquivo de descontos atualizado com sucesso!")
        return descontos_file
    except Exception as e:  
        print(f"Erro ao baixar ou processar o arquivo do Google Drive: {e}")
        return None

@st.cache_data    
def busca_descontos_drive():
    print("Buscando descontos no drive...")
    url_descontos = "https://drive.google.com/uc?id=1UR7B8kd1B_-Y-bVf1eNaMThDThQ56ui8"
    try:
        df_descontos = pd.read_csv(url_descontos, delimiter=',', encoding='utf-8')
        print("Descontos baixado com sucesso.")
        return df_descontos
    except Exception as e:
        print(f"Erro ao ler o arquivo de desontos do Drive: {e}")
        return pd.DataFrame()
    
def busca_dados_descontos(cpf_alvo):
    df_filtrado = busca_dados_mensalidades(cpf_alvo)
    descontos_file = os.path.join(os.getcwd(), 'descontos_file.csv')
    if not os.path.exists(descontos_file) or os.path.getsize(descontos_file) == 0:
        processa_descontos()
    try:
        df_descontos = pd.read_csv(descontos_file)
    except Exception as e:
        print(f"Erro ao ler o arquivo de descontos: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro

    total_descontos = 0
    if not df_descontos.empty:
        if isinstance(df_filtrado, pd.DataFrame) and not df_filtrado.empty:
            nome = str(df_filtrado["Nome"].iloc[0]).strip()
            if nome:
                df_descontos['Nome'] = df_descontos['Nome'].astype(str).str.strip()
                # Convert nome to string explicitly before using in contains()
                pattern = str(nome)
                matches = df_descontos[df_descontos['Nome'].str.contains(pattern, case=False, na=False, regex=False)]
                if not matches.empty:
                    total_descontos += float(matches["Total de Descontos"].iloc[0])

    return total_descontos

@st.cache_data
def busca_mensalidades_drive():
    print("Buscando mensalidades no drive...")
    url_mensalidades = "https://drive.google.com/uc?id=1t4h1Y2OmvZiYTrmHkBRBmVAP3GC4KYdM"
    try:
        df_mensalidades = pd.read_csv(url_mensalidades, delimiter=',', encoding='utf-8')
        print("Mensalidades baixadas com sucesso.")
        return df_mensalidades
    except Exception as e:
        print(f"Erro ao ler o arquivo de mensalidades do Drive: {e}")
        return pd.DataFrame()
    
def busca_dados_mensalidades(cpf_alvo):
    mensalidades_file = os.path.join(os.getcwd(), 'mensalidade_file.csv')
    if not os.path.exists(mensalidades_file) or os.path.getsize(mensalidades_file) == 0:
        processa_mensalidades()
    try:
        df_filtrado = pd.read_csv(mensalidades_file)
    except Exception as e:
        print(f"Erro ao ler o arquivo de mensalidades: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro
    
    # Verificar se df_filtrado é um DataFrame válido
    if isinstance(df_filtrado, pd.DataFrame) and not df_filtrado.empty:
        df_filtrado["Titular_CPF"] = df_filtrado["Titular_CPF"].apply(format_cpf)
        df_filtrado = df_filtrado[df_filtrado["Titular_CPF"] == cpf_alvo]

        # Criando a coluna auxiliar para priorizar o Titular
        df_filtrado["Ordem"] = (df_filtrado["Relação"] != "Titular").astype(int)

        # Aplicando groupby mantendo "Ordem"
        df_filtrado = df_filtrado.groupby(["Nome", "Ordem"], as_index=False).agg({
            "Total": "sum"
        })

        # Convertendo "Total" para número
        df_filtrado["Total"] = pd.to_numeric(df_filtrado["Total"], errors='coerce').round(2)

        # Ordenação final: Titular primeiro
        df_filtrado = df_filtrado.sort_values(by=["Ordem", "Total"], ascending=[True, False]).drop(columns=["Ordem"])

        # Ajuste do Total 2024, se necessário
        if "Total 2024" in df_filtrado.columns:
            total_esperado = float(df_filtrado[df_filtrado["Ordem"] == 0]["Total 2024"].iloc[0])
            soma_atual = df_filtrado["Total"].sum()
            
            if abs(soma_atual - total_esperado) >= 0.01:  # Tolerância para comparação de float
                diferenca = total_esperado - soma_atual
                
                # Ajustando o primeiro registro com Total > 0
                mask = df_filtrado["Total"] > 0
                if mask.any():
                    idx = df_filtrado[mask].index[0]
                    df_filtrado.at[idx, "Total"] += diferenca
        
        df_filtrado = df_filtrado[['Nome', 'Total']].rename(columns={'Nome': 'Nome', 'Total': 'Valor'})

        df_filtrado["Valor"] = df_filtrado["Valor"].apply(format_currency)
    
    return df_filtrado

@st.cache_data
def busca_despesas_drive():
    print("Buscando despesas no drive...")
    url_despesas = "https://drive.google.com/uc?id=1jBGtNAQEVI6lVslyEJkPfXZpesm39193"
    try:
        df_despesas = pd.read_csv(url_despesas, delimiter=',', encoding='utf-8')
        print("Despesas baixadas com sucesso.")
        return df_despesas
    except Exception as e:
        print(f"Erro ao ler o arquivo de despesas do Drive: {e}")
        return pd.DataFrame()
    
def busca_dados_despesas(cpf_alvo, nome):
    despesas_file = os.path.join(os.getcwd(), 'despesas_file.csv')
    if not os.path.exists(despesas_file) or os.path.getsize(despesas_file) == 0:
        processa_despesas()
    try:
        df_despesas = pd.read_csv(despesas_file)
    except Exception as e:
        print(f"Erro ao ler o arquivo de despesas: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro
    
    if not df_despesas.empty:
        df_despesas["CPF_DO_RESPONSAVEL"] = df_despesas["CPF_DO_RESPONSAVEL"].apply(format_cpf)
        df_despesas = df_despesas[df_despesas["CPF_DO_RESPONSAVEL"] == cpf_alvo]
        total_despesas = df_despesas["VALOR_DO_SERVICO"].sum()
        #print(f"Total de despesas: {total_despesas}")
        
        descontos = float(busca_dados_descontos(cpf_alvo))
        #print(f"Descontos: {descontos}")
        diferenca = descontos - total_despesas
        #print(f"Diferença: {diferenca}")

        # Normalizar os nomes no DataFrame
        df_despesas["BENEFICIARIO"] = df_despesas["BENEFICIARIO"].str.strip().str.upper()

        # Normalizar o nome fornecido
        nome_normalizado = nome.strip().upper()

        # Aplicar a máscara para encontrar o nome
        pattern = re.escape(nome_normalizado)  # Escapar caracteres especiais no nome
        mask = df_despesas["BENEFICIARIO"] == nome_normalizado
        #print(f"Nome fornecido: {nome_normalizado}")
        #print(f"Nomes no DataFrame: {df_despesas['BENEFICIARIO'].unique()}")
        #print(f"Máscara gerada: {mask}")

        # Verificar se há correspondências
        if mask.any():
            # Create a sorting column (True values will come first)
            df_despesas['sort_order'] = mask
            
            # Sort by the new column and drop it
            df_despesas = df_despesas.sort_values('sort_order', ascending=False).drop('sort_order', axis=1)
        
        remaining_mask = ~mask
        remaining_count = remaining_mask.sum()
        total_remaining_mask = df_despesas.loc[remaining_mask, "VALOR_DO_SERVICO"].sum()
        #print(f"Total do valor dos dependentes: {total_remaining_mask}")
        #print(f"Quantidade de dependentes: {remaining_count}")

        if descontos > 0 and mask is True:
            df_despesas.loc[mask, "VALOR_DO_SERVICO"] += diferenca
            
        elif diferenca != 0:  # Only process if there's a difference to distribute
            if remaining_count > 0 and total_remaining_mask >= abs(diferenca) or remaining_count > 0 and total_remaining_mask < abs(diferenca) and diferenca > 0:
                value_per_record = abs(diferenca) / remaining_count
                
                # Initialize insufficient_mask before the conditional blocks
                insufficient_mask = pd.Series(False, index=df_despesas.index)
                # Handle records with insufficient values
                if diferenca < 0:
                    insufficient_mask = remaining_mask & (df_despesas["VALOR_DO_SERVICO"] < value_per_record)

                if insufficient_mask.any():
                    insufficient_values = df_despesas.loc[insufficient_mask, "VALOR_DO_SERVICO"]
                    df_despesas.loc[insufficient_mask, "VALOR_DO_SERVICO"] = 0
                    diferenca += insufficient_values.sum()
                    
                    # Update remaining records
                    remaining_mask = remaining_mask & ~insufficient_mask
                    remaining_count = remaining_mask.sum()
                    
                    # Recalculate value_per_record only if there are remaining records
                    if remaining_count > 0:
                        value_per_record = abs(diferenca) / remaining_count
                        
                # Process remaining records with sufficient values
                if remaining_count > 0:
                    if diferenca < 0:
                        df_despesas.loc[remaining_mask, "VALOR_DO_SERVICO"] -= value_per_record
                    else:
                        df_despesas.loc[remaining_mask, "VALOR_DO_SERVICO"] += value_per_record
            
            if remaining_count > 0 and total_remaining_mask < abs(diferenca) and diferenca < 0:
                df_despesas.loc[remaining_mask, "VALOR_DO_SERVICO"] = 0
                # df_despesas.loc[mask, "VALOR_DO_SERVICO"] == descontos
                df_despesas.at[df_despesas.index[0], "VALOR_DO_SERVICO"] = descontos

            elif df_despesas.empty:
                df_despesas = pd.DataFrame(columns=['BENEFICIARIO', 'VALOR_DO_SERVICO'])
                df_despesas["VALOR_DO_SERVICO"] = descontos
                df_despesas["BENEFICIARIO"] = nome
            elif len(df_despesas) == 1:
                df_despesas.at[df_despesas.index[0], "VALOR_DO_SERVICO"] = descontos
        
        df_despesas["VALOR_DO_SERVICO"] = df_despesas["VALOR_DO_SERVICO"].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        df_despesas = df_despesas[['BENEFICIARIO', 'VALOR_DO_SERVICO']].rename(
            columns={'BENEFICIARIO': 'Nome', 'VALOR_DO_SERVICO': 'Valor'}
        )
        
        if df_despesas.empty and descontos == 0:
            return pd.DataFrame(columns=['Nome', 'Valor'])
            
    return df_despesas

def format_currency(value):
    try:
        value = float(value)  # Converte para número caso seja string
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except ValueError:
        return "Valores de desconto não encontrados."

def generate_pdf(df_mensalidades, df_despesas, descontos, cpf):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)  # Quebra de página automática
    pdf.add_page()
    
    # Função para formatar títulos de seções
    def draw_section(title, content_lines):
        """ Cria uma seção com um título sublinhado e uma borda ao redor do conteúdo. """
        pdf.set_font('Arial', 'B', 12)
        start_y = pdf.get_y()
        
        # Criando o título sublinhado
        pdf.cell(0, 8, title, ln=True, align='L')
        pdf.set_draw_color(0, 0, 0)  # Cor preta para a linha
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Linha abaixo do título
        pdf.ln(4)  # Espaço após a linha
        
        # Adicionando o conteúdo dentro do retângulo
        pdf.set_font('Arial', '', 12)
        for line in content_lines:
            pdf.cell(0, 6, line, ln=True)
        
        end_y = pdf.get_y()
        pdf.rect(10, start_y, 190, end_y - start_y + 2)  # Borda ao redor do conteúdo
        pdf.ln(6)  # Espaçamento extra

    # Cabeçalho
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'INFORME PLANO DE SAÚDE', ln=True, align='C')
    pdf.ln(3)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 8, 'ANO - CALENDÁRIO DE 2024', ln=True, align='C')
    pdf.cell(0, 8, 'IMPOSTO DE RENDA - PESSOA FÍSICA', ln=True, align='C')
    pdf.ln(10)

    # 1. DADOS CADASTRAIS
    titular = df_mensalidades.iloc[0]['Nome'] if isinstance(df_mensalidades, pd.DataFrame) and not df_mensalidades.empty else "N/A"
    draw_section('1 - DADOS CADASTRAIS', [f"Titular: {titular} - CPF: {cpf}"])

    # 2. IDENTIFICAÇÃO DA FONTE PAGADORA
    fonte_pagadora = [
        "Nome empresarial: Cosemi - Cooperativa de Economia E Credito Mutuo dos",
        "Servidores Municipais de Itabira Ltda",
        "CNPJ: 16.651.002/0001-80"
    ]
    draw_section('2 - IDENTIFICAÇÃO DA FONTE PAGADORA', fonte_pagadora)

    # 3. INFORMAÇÕES PLANO DE SAÚDE
    info_plano = ["Mensalidade Plano de Saúde:"]
    if isinstance(df_mensalidades, pd.DataFrame) and not df_mensalidades.empty:
        for _, row in df_mensalidades.iterrows():
            nome = row['Nome'] if 'Nome' in row else "N/A"
            valor = row['Valor'] if 'Valor' in row else "R$ 0,00"
            info_plano.append(f"Nome: {nome} - Valor: {valor}")
    draw_section('3 - INFORMAÇÕES PLANO DE SAÚDE', info_plano)

    # 4. INFORMAÇÕES DESPESAS
    despesas_info = []
    for _, row in df_despesas.iterrows():
        nome = row['Nome'] if 'Nome' in row else "N/A"
        valor = row['Valor'] if 'Valor' in row else "R$ 0,00"
        despesas_info.append(f"Nome: {nome} - Valor: {valor}")
    draw_section('4 - INFORMAÇÕES DESPESAS', despesas_info)

    # 5. TOTAIS
    descontos_info = []
    # Removendo caracteres inesperados e convertendo corretamente
    df_mensalidades['Valor'] = df_mensalidades['Valor'].astype(str).str.strip()  # Remove espaços extras
    df_mensalidades['Valor'] = df_mensalidades['Valor'].str.replace(r'[^\d,]', '', regex=True)  # Remove tudo que não for número ou vírgula
    df_mensalidades['Valor'] = df_mensalidades['Valor'].str.replace(',', '.', regex=True)  # Substitui vírgula por ponto para conversão
    
    # Removendo valores vazios antes da conversão
    df_mensalidades = df_mensalidades[df_mensalidades['Valor'] != '']
    
    # Convertendo para float
    df_mensalidades['Valor'] = df_mensalidades['Valor'].astype(float)
    
    # Calculando total
    total_mensalidades = df_mensalidades['Valor'].sum()
    
    # Exibir resultado formatado
    descontos_info = []
    descontos_info.append(f"Total de Descontos: {descontos}")
    descontos_info.append(f"Total de Mensalidades: R$ {total_mensalidades:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    
    draw_section('5 - TOTAIS', descontos_info)

    pdf.cell(0, 6, f'Documento criado em: {datetime.now().strftime("%d/%m/%Y")}', ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')
