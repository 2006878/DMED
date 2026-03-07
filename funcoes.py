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
    if isinstance(cpf, (int, float)):
        if float(cpf).is_integer():
            cpf_str = str(int(float(cpf)))
        else:
            cpf_str = str(cpf).strip()
    else:
        cpf_str = str(cpf).strip()
        if re.fullmatch(r"\d+\.0", cpf_str):
            cpf_str = cpf_str[:-2]

    cpf_str = re.sub(r"\D", "", cpf_str)
    if not cpf_str:
        return ''
    return cpf_str.zfill(11)
    
def format_valor(valor_str):
    try:
        # Remove currency symbol and standardize decimal separator
        valor = str(valor_str).replace("R$", "").strip()
        # Handle different decimal formats
        if "," in valor:
            valor = valor.replace(".", "").replace(",", ".")
        # Convert to float and round to 2 decimal places
        valor_float = round(float(valor), 2)
        if valor_float == 0  or pd.isna(valor_float):
            valor_float = 0.01
        # Convert to cents without decimal point
        valor_cents = int(valor_float * 100)
        return f"{valor_cents:09d}"
    except:
        return ""

def parse_valor_monetario(valor):
    if pd.isna(valor):
        return 0.0
    valor_str = str(valor).replace("R$", "").strip()
    if not valor_str:
        return 0.0

    # Quando há vírgula, assume formato brasileiro (milhar com ponto e decimal com vírgula).
    if "," in valor_str:
        valor_str = valor_str.replace(".", "").replace(",", ".")
    else:
        # Sem vírgula, mantém ponto como separador decimal e remove lixo textual.
        valor_str = re.sub(r"[^0-9.\-]", "", valor_str)

    try:
        return round(float(valor_str), 2)
    except (ValueError, TypeError):
        return 0.0

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

@st.cache_data
def load_data(file_path):
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        print(f"Erro ao ler o arquivo {file_path}: {e}")
        return pd.DataFrame()

# Agrupar e processar dados de uma vez
def process_group_titular(grupo, titular_cpf):
    results = []
    
    # Processar titular
    titular = grupo.iloc[0]
    if not titular.empty:
        titular = titular.iloc[0]
        nome_titular = normalize_name(titular)
        
        # Calcular o valor total do grupo familiar (titular + dependentes)
        # valor_mensalidade_total = pd.to_numeric(grupo["Total"]).sum().round(2)
        # valor_mensalidade_total = pd.to_numeric(grupo["Valor"]).sum().round(2)
        # Converter e somar diretamente
        valor_mensalidade_total = grupo["Valor"].apply(lambda x: 
            float(str(x).replace("R$", "").replace(".", "").replace(",", ".").strip()) 
            if pd.notna(x) else 0.0
        ).sum().round(2)

        # Somar todas as despesas do grupo familiar
        valor_despesas_total = busca_dados_descontos(titular_cpf)
                
        # Atribuir todo o valor ao titular
        valor_titular = valor_mensalidade_total + valor_despesas_total
        
        if valor_titular <= 0:
            valor_titular = 0.01
            
        results.append(f"TOP|{format_cpf(titular_cpf)}|{nome_titular}|{format_valor(valor_titular)}|")

        # if titular_cpf == '02650137630':
        #     print(valor_titular)
    # Não adicionar dependentes ao arquivo DMED, já que todos os valores foram atribuídos ao titular
    
    return results

def create_dmed_content_titular(responsavel_cpf, responsavel_nome, ddd_responsavel, telefone_responsavel):
    start = datetime.now()
    
    mensalidades_file = os.path.join(os.getcwd(), 'mensalidade_file.csv')
    if not os.path.exists(mensalidades_file) or os.path.getsize(mensalidades_file) == 0:
        processa_mensalidades()
    try:
        df_filtrado = pd.read_csv(mensalidades_file, dtype=str)
    except Exception as e:
        print(f"Erro ao ler o arquivo de mensalidades: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro
        
    # df_despesas_raw = load_data(os.path.join(os.getcwd(), 'despesas_file.csv'))
    # if df_despesas_raw.empty:
    #     return ""

    print("Criando arquivo DMed...")
    
    # Pré-processar dados
    df_filtrado['Total'] = pd.to_numeric(df_filtrado['Total'], errors='coerce').fillna(0).round(2)
    df_filtrado['Titular_CPF'] = df_filtrado['Titular_CPF'].apply(format_cpf)
    
    # Cabeçalho do DMED
    content = [
        f"DMED|{ano_atual}|{ano_anterior}|N|||",
        f"RESPO|{responsavel_cpf}|{responsavel_nome}|{ddd_responsavel}|{telefone_responsavel}||||",
        f"DECPJ|16651002000180|COOPERATIVA DE ECONOMIA E CREDITO MUTUO DOS SERVIDORES MUNICIPAIS DE ITABIRA LTDA SICOOB COSEMI|2|419761||{responsavel_cpf}|N||S|",
        "OPPAS|"
    ]
        
    # Agrupar dados por Titular_CPF para processar cada grupo familiar
    df_grouped = df_filtrado.groupby(['Titular_CPF']).agg({
        'Nome': 'first',  # Pegar o nome do primeiro registro (que deve ser o titular)
        'Relação': 'first',
        'CPF': 'first'
    }).reset_index()
    # print(df_grouped['Titular_CPF'].unique())
    # Processar cada grupo de titular
    for titular_cpf in df_grouped['Titular_CPF'].unique():
        if pd.notna(titular_cpf):
            # Obter todos os registros do grupo familiar
            # grupo = df_filtrado[df_filtrado['Titular_CPF'] == titular_cpf]
            grupo = busca_dados_mensalidades(titular_cpf)
            # grupo  = df_filtrado[df_filtrado['Titular_CPF'] == titular_cpf]
            if grupo.empty:
                print(f"Grupo vazio para titular CPF: {titular_cpf}")
                continue
            else:
                # Processar o grupo e adicionar resultados ao content
                results = process_group_titular(grupo, titular_cpf)
                content.extend(results)
    
    content.append("FIMDmed|")
    end = datetime.now()
    print(f"Tempo total de execução: {end - start}")
    return "\n".join(content)

# Agrupar e processar dados de uma vez
def process_group(grupo, titular_cpf, despesas_dict):
    results = []
    
    # Processar titular
    titular = grupo[grupo["Relação"] == "Titular"]
    if not titular.empty:
        titular = titular.iloc[0]
        nome_titular = normalize_name(titular['Nome'])
        
        # Buscar valor de despesa do dicionário pré-calculado
        valor_despesas = despesas_dict.get(titular_cpf, {}).get(nome_titular, 0)
        valor_titular = pd.to_numeric(titular["Total"]).round(2) + valor_despesas
        
        if valor_titular <= 0:
            valor_titular = 0.01
            
        results.append(f"TOP|{format_cpf(titular_cpf)}|{nome_titular}|{format_valor(valor_titular)}|")
    
    # Processar dependentes
    dependentes = grupo[grupo["Relação"] != "Titular"].copy()
    if not dependentes.empty:
        dependentes['CPF'] = dependentes['CPF'].apply(format_cpf)
        dependentes_sorted = dependentes.sort_values(['CPF'])
        
        for _, dep in dependentes_sorted.iterrows():
            nome_dep = normalize_name(dep['Nome'])
            valor_mensalidade = pd.to_numeric(dep["Total"])
            valor_despesas = despesas_dict.get(titular_cpf, {}).get(nome_dep, 0)
            
            valor_total = valor_mensalidade + valor_despesas
            if valor_total <= 0:
                valor_total = 0.01
                
            results.append(f"DTOP|{format_cpf(dep['CPF'])}||{nome_dep}|{get_dependent_code(dep['Relação'])}|{format_valor(str(valor_total))}|")
    
    return results

def create_dmed_content(responsavel_cpf, responsavel_nome, ddd_responsavel, telefone_responsavel):
    start = datetime.now()
    
    mensalidades_file = os.path.join(os.getcwd(), 'mensalidade_file.csv')
    if not os.path.exists(mensalidades_file) or os.path.getsize(mensalidades_file) == 0:
        processa_mensalidades()
    try:
        df_filtrado = pd.read_csv(mensalidades_file, dtype=str)
    except Exception as e:
        print(f"Erro ao ler o arquivo de mensalidades: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro
        
    df_despesas_raw = load_data(os.path.join(os.getcwd(), 'despesas_file.csv'))
    if df_despesas_raw.empty:
        return ""

    print("Criando arquivo DMed...")
    
    # Pré-processar dados
    df_filtrado['Total'] = pd.to_numeric(df_filtrado['Total'], errors='coerce').fillna(0).round(2)
    df_filtrado['Titular_CPF'] = df_filtrado['Titular_CPF'].apply(format_cpf)
    
    # Cabeçalho do DMED
    content = [
        f"DMED|{ano_atual}|{ano_anterior}|N|||",
        f"RESPO|{responsavel_cpf}|{responsavel_nome}|{ddd_responsavel}|{telefone_responsavel}||||",
        f"DECPJ|16651002000180|COOPERATIVA DE ECONOMIA E CREDITO MUTUO DOS SERVIDORES MUNICIPAIS DE ITABIRA LTDA SICOOB COSEMI|2|419761||{responsavel_cpf}|N||S|",
        "OPPAS|"
    ]
    
    # Pré-calcular despesas para todos os titulares
    despesas_dict = {}
    for cpf in df_filtrado['Titular_CPF'].unique():
        if pd.notna(cpf):
            titular_nome = df_filtrado[df_filtrado['Titular_CPF'] == cpf]['Nome'].iloc[0]
            df_desp = busca_dados_despesas(cpf, titular_nome)
            
            # Criar dicionário para lookup rápido
            despesas_dict[cpf] = {}
            for _, row in df_desp.iterrows():
                nome_norm = normalize_name(row['Nome'])
                valor_str = str(row['Valor']).replace("R$", "").replace(".", "").replace(",", ".").strip()
                despesas_dict[cpf][nome_norm] = float(valor_str or 0)
    
    # Agrupar dados por Nome para evitar duplicatas
    df_grouped = df_filtrado.groupby(['Titular_CPF', 'Nome']).agg({
        'Total': 'sum',
        'Relação': 'first',
        'CPF': 'first'
    }).reset_index()
    
    # Processar cada grupo de titular
    for titular_cpf, grupo in df_grouped.groupby('Titular_CPF'):
        if pd.notna(titular_cpf):
            # Processar o grupo e adicionar resultados ao content
            results = process_group(grupo, titular_cpf, despesas_dict)
            content.extend(results)
    
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
                    titulares = grupo[grupo["Relação"] == "Titular"]

                    if titulares.empty:
                        print(f"Grupo sem titular ignorado: {cpf_titular}")
                        continue

                    titular = titulares.iloc[0]
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
    import unicodedata

    print("Processando despesas...")

    def normaliza_coluna(col):
        base = unicodedata.normalize("NFKD", str(col))
        base = "".join(c for c in base if not unicodedata.combining(c))
        base = re.sub(r"\s+", " ", base).strip().upper()
        return base

    def padroniza_df(df):
        if df is None or df.empty:
            return pd.DataFrame(columns=["Nome", "CPF", "Valor a Pagar"])

        col_map = {c: normaliza_coluna(c) for c in df.columns}
        nome_col = next((orig for orig, norm in col_map.items() if norm in {"NOME", "BENEFICIARIO"}), None)
        cpf_col = next((orig for orig, norm in col_map.items() if norm in {"CPF", "CPF DO RESPONSAVEL", "CPF_DO_RESPONSAVEL"}), None)
        valor_col = next((
            orig for orig, norm in col_map.items()
            if norm in {"VALOR A PAGAR", "VALOR_DO_SERVICO", "VALOR DO SERVICO", "VALOR"}
        ), None)

        if not nome_col or not valor_col:
            return pd.DataFrame(columns=["Nome", "CPF", "Valor a Pagar"])

        if not cpf_col:
            df["CPF_AUSENTE"] = ""
            cpf_col = "CPF_AUSENTE"

        out = df[[nome_col, cpf_col, valor_col]].copy()
        out.columns = ["Nome", "CPF", "Valor a Pagar"]
        return out

    try:
        data_folder = os.path.join(os.getcwd(), "despesas_nova")
        if not os.path.isdir(data_folder):
            print("Pasta despesas_nova não encontrada.")
            return None

        frames = []
        for filename in os.listdir(data_folder):
            file_path = os.path.join(data_folder, filename)
            if not os.path.isfile(file_path):
                continue

            lower = filename.lower()
            if lower.endswith((".xlsx", ".xlsm", ".xls")):
                excel = pd.ExcelFile(file_path, engine="openpyxl")
                for sheet_name in excel.sheet_names:
                    df_sheet = pd.read_excel(excel, sheet_name=sheet_name, engine="openpyxl")
                    frames.append(padroniza_df(df_sheet))
            elif lower.endswith(".csv"):
                df_csv = None
                for encoding in ("latin1", "utf-8"):
                    for sep in (";", ",", None):
                        try:
                            kwargs = {"encoding": encoding}
                            if sep is None:
                                kwargs.update({"sep": None, "engine": "python"})
                            else:
                                kwargs["sep"] = sep
                            df_csv = pd.read_csv(file_path, **kwargs)
                            break
                        except Exception:
                            continue
                    if df_csv is not None:
                        break
                frames.append(padroniza_df(df_csv))

        if not frames:
            print("Nenhum arquivo de despesas válido encontrado.")
            return None

        df_despesas = pd.concat(frames, ignore_index=True)
        df_despesas["Nome"] = df_despesas["Nome"].fillna("").astype(str).str.strip().str.upper()
        df_despesas["CPF"] = df_despesas["CPF"].apply(format_cpf)
        df_despesas["Valor a Pagar"] = df_despesas["Valor a Pagar"].apply(parse_valor_monetario)
        nome_valido = df_despesas["Nome"].str.contains(r"[A-Z0-9]", regex=True, na=False)
        df_despesas = df_despesas[
            (df_despesas["CPF"] != "") | ((df_despesas["Nome"] != "") & nome_valido)
        ]
        df_despesas = df_despesas[~((df_despesas["CPF"] == "") & (df_despesas["Valor a Pagar"] <= 0))]

        if df_despesas.empty:
            print("Nenhum registro de despesas após limpeza.")
            return None

        df_despesas["Chave_Agrupamento"] = df_despesas.apply(
            lambda row: row["CPF"] if row["CPF"] else row["Nome"],
            axis=1
        )
        df_despesas = df_despesas.groupby("Chave_Agrupamento", as_index=False).agg({
            "Nome": "first",
            "CPF": "first",
            "Valor a Pagar": "sum"
        })
        df_despesas["Valor a Pagar"] = df_despesas["Valor a Pagar"].round(2)
        df_despesas = df_despesas.drop(columns=["Chave_Agrupamento"])
        df_despesas["CPF"] = df_despesas["CPF"].fillna("").astype(str)

        # Mapear CPF do responsável para o Titular_CPF das mensalidades.
        cpf_para_titular = {}
        nome_para_titular = {}
        mensalidades_file = os.path.join(os.getcwd(), "mensalidade_file.csv")
        if not os.path.exists(mensalidades_file) or os.path.getsize(mensalidades_file) == 0:
            processa_mensalidades()
        try:
            df_mens = pd.read_csv(mensalidades_file, dtype=str)
            if not df_mens.empty and "Titular_CPF" in df_mens.columns:
                df_mens["Titular_CPF"] = df_mens["Titular_CPF"].apply(format_cpf)
                if "CPF" in df_mens.columns:
                    df_mens["CPF"] = df_mens["CPF"].apply(format_cpf)
                else:
                    df_mens["CPF"] = ""
                if "Nome" in df_mens.columns:
                    df_mens["Nome"] = df_mens["Nome"].fillna("").astype(str).str.strip().str.upper()
                else:
                    df_mens["Nome"] = ""

                for _, row in df_mens.iterrows():
                    titular = row["Titular_CPF"]
                    if not titular:
                        continue
                    cpf_benef = row["CPF"]
                    nome_benef = row["Nome"]
                    if cpf_benef and cpf_benef not in cpf_para_titular:
                        cpf_para_titular[cpf_benef] = titular
                    if nome_benef and nome_benef not in nome_para_titular:
                        nome_para_titular[nome_benef] = titular
        except Exception as e:
            print(f"Erro ao mapear Titular_CPF das mensalidades: {e}")

        df_despesas["CPF_DO_RESPONSAVEL"] = df_despesas.apply(
            lambda row: (
                cpf_para_titular.get(row["CPF"])
                or nome_para_titular.get(row["Nome"])
                or row["CPF"]
            ),
            axis=1
        )
        df_despesas["CPF_DO_RESPONSAVEL"] = df_despesas["CPF_DO_RESPONSAVEL"].apply(format_cpf)

        # Mantém compatibilidade com o restante do fluxo atual.
        df_despesas["BENEFICIARIO"] = df_despesas["Nome"]
        df_despesas["VALOR_DO_SERVICO"] = df_despesas["Valor a Pagar"]

        despesas_file = "despesas_file.csv"
        df_despesas.to_csv(despesas_file, index=False)
        print("Arquivo de despesas atualizado com sucesso!")
        return despesas_file

    except Exception as e:
        print(f"Error processing expenses: {e}")
        return None

def processa_descontos():
    df_descontos = pd.DataFrame()

    try:
        print("Processando descontos...")
        data_folder = os.path.join(os.getcwd(), "descontos")

        if os.path.isdir(data_folder):
            for filename in os.listdir(data_folder):
                file_path = os.path.join(data_folder, filename)
                if not (os.path.isfile(file_path) and filename.lower().endswith(".xlsx")):
                    continue

                excel = pd.ExcelFile(file_path, engine="openpyxl")
                for sheet_name in excel.sheet_names:
                    df = pd.read_excel(excel, sheet_name=sheet_name, engine="openpyxl")
                    if df.empty:
                        continue

                    df.columns = [str(col).strip() for col in df.columns]
                    if "Nome" not in df.columns or "Total de Descontos" not in df.columns:
                        continue
                    if "CPF" not in df.columns:
                        df["CPF"] = ""

                    df = df[["Nome", "CPF", "Total de Descontos"]]
                    df_descontos = pd.concat([df_descontos, df], ignore_index=True)
        else:
            url_excel_file = "https://drive.google.com/uc?id=132cv-9fgKpgHUkJZbl3hz0G5nkJFot22"
            response = requests.get(url_excel_file)
            response.raise_for_status()
            excel = pd.ExcelFile(BytesIO(response.content), engine="openpyxl")
            for sheet_name in excel.sheet_names:
                df = pd.read_excel(excel, sheet_name=sheet_name, engine="openpyxl")
                if df.empty:
                    continue

                df.columns = [str(col).strip() for col in df.columns]
                if "Nome" not in df.columns or "Total de Descontos" not in df.columns:
                    continue
                if "CPF" not in df.columns:
                    df["CPF"] = ""

                df = df[["Nome", "CPF", "Total de Descontos"]]
                df_descontos = pd.concat([df_descontos, df], ignore_index=True)

        if df_descontos.empty:
            print("Nenhum desconto encontrado para processar.")
            return None

        df_descontos["Nome"] = df_descontos["Nome"].fillna("").astype(str).str.strip().str.upper()
        df_descontos["CPF"] = df_descontos["CPF"].apply(format_cpf)
        df_descontos["Total de Descontos"] = df_descontos["Total de Descontos"].apply(parse_valor_monetario)
        df_descontos = df_descontos[(df_descontos["CPF"] != "") | (df_descontos["Nome"] != "")]

        df_descontos["Chave_Agrupamento"] = df_descontos.apply(
            lambda row: row["CPF"] if row["CPF"] else row["Nome"],
            axis=1
        )
        df_descontos = df_descontos.groupby("Chave_Agrupamento", as_index=False).agg({
            "Nome": "first",
            "CPF": "first",
            "Total de Descontos": "sum"
        })
        df_descontos["Total de Descontos"] = df_descontos["Total de Descontos"].round(2)
        df_descontos = df_descontos.drop(columns=["Chave_Agrupamento"])

        descontos_file = "descontos_file.csv"
        df_descontos.to_csv(descontos_file, index=False)
        print("Arquivo de descontos atualizado com sucesso!")
        return descontos_file
    except Exception as e:
        print(f"Erro ao processar o arquivo de descontos: {e}")
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
        return 0.0

    total_descontos = 0.0
    if df_descontos.empty:
        return total_descontos

    if "Total de Descontos" not in df_descontos.columns and "Valor a Pagar" in df_descontos.columns:
        df_descontos["Total de Descontos"] = df_descontos["Valor a Pagar"]
    if "Total de Descontos" not in df_descontos.columns:
        return total_descontos
    if "Nome" not in df_descontos.columns:
        return total_descontos

    if "CPF" in df_descontos.columns:
        df_descontos["CPF"] = df_descontos["CPF"].apply(format_cpf)
    df_descontos["Nome"] = df_descontos["Nome"].astype(str).str.strip().str.upper()
    df_descontos["Total de Descontos"] = df_descontos["Total de Descontos"].apply(parse_valor_monetario)

    cpf_alvo_formatado = format_cpf(cpf_alvo)
    if cpf_alvo_formatado and "CPF" in df_descontos.columns:
        matches_cpf = df_descontos[df_descontos["CPF"] == cpf_alvo_formatado]
        print(matches_cpf)
        if not matches_cpf.empty:
            return float(matches_cpf["Total de Descontos"].sum())

    if isinstance(df_filtrado, pd.DataFrame) and not df_filtrado.empty:
        nome = str(df_filtrado["Nome"].iloc[0]).strip().upper()
        if nome:
            matches_nome = df_descontos[df_descontos["Nome"] == nome]
            if not matches_nome.empty:
                total_descontos += float(matches_nome["Total de Descontos"].sum())

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
        df_filtrado = pd.read_csv(mensalidades_file, dtype=str)
    except Exception as e:
        print(f"Erro ao ler o arquivo de mensalidades: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro
    
    if df_filtrado.empty:
        st.error("Erro ao processar mensalidades — verifique o arquivo do Google Drive")
        st.stop()

    # Verificar se df_filtrado é um DataFrame válido
    if isinstance(df_filtrado, pd.DataFrame) and not df_filtrado.empty:
        df_filtrado["Titular_CPF"] = df_filtrado["Titular_CPF"].apply(format_cpf)
        df_filtrado = df_filtrado[df_filtrado["Titular_CPF"] == cpf_alvo]
         # Converter colunas numéricas para float ANTES de qualquer cálculo
        colunas_numericas = ['Total', 'Total 2024', 'Valor']
        for col in colunas_numericas:
            if col in df_filtrado.columns:
                df_filtrado[col] = pd.to_numeric(
                    df_filtrado[col].astype(str).str.replace(',', '.'),
                    errors='coerce'
                ).fillna(0)

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
    try:
        descontos = float(busca_dados_descontos(cpf_alvo))
        print(f"Descontos encontrados para CPF {cpf_alvo}: {descontos}")
    except Exception as e:
        print(f"Erro ao calcular descontos: {e}")
        descontos = 0
    
    if not df_despesas.empty:
        df_despesas["CPF_DO_RESPONSAVEL"] = df_despesas["CPF_DO_RESPONSAVEL"].apply(format_cpf)
        df_despesas = df_despesas[df_despesas["CPF_DO_RESPONSAVEL"] == cpf_alvo]
        print(f"Despesas encontradas para CPF {cpf_alvo}: {df_despesas}")
        total_despesas = df_despesas["VALOR_DO_SERVICO"].sum()
        #print(f"Total de despesas: {total_despesas}")
            
        if not df_despesas.empty:
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
                    df_despesas = pd.DataFrame({"BENEFICIARIO": [nome], "VALOR_DO_SERVICO": [descontos]})
                
                elif len(df_despesas) == 1:
                    df_despesas.at[df_despesas.index[0], "VALOR_DO_SERVICO"] = descontos

            # Identificar registros com valores negativos
            negativos_mask = df_despesas["VALOR_DO_SERVICO"] < 0
            negativos_total = df_despesas.loc[negativos_mask, "VALOR_DO_SERVICO"].sum()
            
            if negativos_total < 0:
                # Encontrar o primeiro índice com um valor positivo
                primeiro_positivo_idx = df_despesas[df_despesas["VALOR_DO_SERVICO"] > 0].index.min()
                
                if pd.notna(primeiro_positivo_idx):  # Se existir pelo menos um registro positivo
                    df_despesas.at[primeiro_positivo_idx, "VALOR_DO_SERVICO"] += negativos_total
            
                # Zeramos os valores negativos para não gerar inconsistências
                df_despesas.loc[negativos_mask, "VALOR_DO_SERVICO"] = 0
        
        else:
            df_despesas = pd.DataFrame({"BENEFICIARIO": [nome], "VALOR_DO_SERVICO": [descontos]})

    if df_despesas.empty:
        df_despesas = pd.DataFrame({"BENEFICIARIO": [nome], "VALOR_DO_SERVICO": [descontos]})        
    
    if df_despesas.empty and descontos == 0:
        return pd.DataFrame(columns=['Nome', 'Valor'])
           
    df_despesas["VALOR_DO_SERVICO"] = df_despesas["VALOR_DO_SERVICO"].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    df_despesas = df_despesas[['BENEFICIARIO', 'VALOR_DO_SERVICO']].rename(
        columns={'BENEFICIARIO': 'Nome', 'VALOR_DO_SERVICO': 'Valor'}
    )
     
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
    pdf.cell(0, 8, 'ANO - CALENDÁRIO DE 2025', ln=True, align='C')
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
    descontos_info.append(f"Total de Despesas: {descontos}")
    descontos_info.append(f"Total de Mensalidades: R$ {total_mensalidades:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    
    draw_section('5 - TOTAIS', descontos_info)

    pdf.cell(0, 6, f'Documento criado em: {datetime.now().strftime("%d/%m/%Y")}', ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')
