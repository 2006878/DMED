import pandas as pd
from datetime import datetime
import os
from fpdf import FPDF

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
        df_filtrado['CPF_Sort'] = df_filtrado['Titular_CPF'].apply(format_cpf)
        df_filtrado = df_filtrado.sort_values(['CPF_Sort', 'Relação'], ascending=[True, False])

        # Remove temporary sorting column
        df_filtrado = df_filtrado.drop('CPF_Sort', axis=1)

        if pd.notna(titular_cpf):
            titular = grupo[grupo["Relação"] == "Titular"].iloc[0]
            valor_titular = float(str(titular["Total"]).replace("R$", "").replace(".", "").replace(",", ".").strip() or 0)
            
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
    mensalidades_file = os.path.join(os.getcwd(), 'mensalidades_file.csv')
    excel_file = os.path.join(os.getcwd(), 'MENSALIDADES.xlsx')

    if not os.path.exists(mensalidades_file) or os.path.getsize(mensalidades_file) == 0:
        df_mensalidades = pd.DataFrame()
        monthly_columns = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 
                           'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
        excel = pd.ExcelFile(excel_file)
        print("Reading Excel sheets:", excel.sheet_names)
        
        for sheet_name in excel.sheet_names:
            print(f"\nProcessing sheet: {sheet_name}")
            # Read all columns from Excel
            df = pd.read_excel(excel_file, sheet_name=sheet_name, engine="openpyxl")
            print(f"Found columns: {df.columns.tolist()}")
            
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
            
            # Converter colunas mensais para numérico
            for month in monthly_columns:
                if month in df.columns:
                    df[month] = pd.to_numeric(df[month].replace('[\\$,]', '', regex=True), errors='coerce')

            # Filtrar dados
            ano_anterior = pd.Timestamp.now().year - 1
            ano_atual = pd.Timestamp.now().year
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
            
            # Create a month name to number mapping
            month_mapping = {
                'janeiro': 1,
                'fevereiro': 2, 
                'março': 3,
                'abril': 4,
                'maio': 5,
                'junho': 6,
                'julho': 7,
                'agosto': 8,
                'setembro': 9,
                'outubro': 10,
                'novembro': 11,
                'dezembro': 12
            }

            # Dividir valores entre os dependentes
                        
            # Processar valores mensais
            for cpf_titular, grupo in df_filtrado.groupby("Titular_CPF"):
                if pd.notna(cpf_titular):
                    titular = grupo[grupo["Relação"] == "Titular"].iloc[0]
                    is_camara = titular['is_camara']
                    is_complemento = titular['is_complemento']
                    
                    # Para cada mês, calcular quantos dependentes estão ativos
                    for month in monthly_columns:
                        month_num = month_mapping[month]
                        
                        # Contar dependentes ativos no mês atual
                        dependentes_ativos = sum(1 for _, member in grupo.iterrows() 
                                            if month_num in member["Meses Ativos"])
                        
                        if dependentes_ativos > 0:
                            # Pegar o valor total do mês do titular
                            valor_total_mes = float(titular[month]) if pd.notna(titular[month]) else 0
                            # Regra específica para camara:
                            if is_camara:
                                if dependentes_ativos > 1:
                                    valor_por_dependente = valor_total_mes / (dependentes_ativos - 1)
                                else:
                                    valor_por_dependente = valor_total_mes
                            else:
                                valor_por_dependente = valor_total_mes / dependentes_ativos

                            # Distribuir o valor entre os dependentes ativos
                            for idx, (i, member) in enumerate(grupo.iterrows()):
                                if month_num in member["Meses Ativos"]:
                                    # Aplicar valor dividido antes das regras de limite
                                    current_value = valor_por_dependente
                                    # Aplicar regras de limite após a divisão
                                    if is_camara and member["Relação"] == "Titular":
                                        if member["Relação"] == "Titular":
                                            df_filtrado.at[i, month] = 0
                                        else:
                                            df_filtrado.at[i, month] = current_value
                                    elif is_complemento:
                                        df_filtrado.at[i, month] = current_value 
                                    else:
                                        if idx < 4:
                                            current_value = valor_total_mes / 4
                                            df_filtrado.at[i, month] = current_value
                                        else:
                                            df_filtrado.at[i, month] = 0

            # Concatenar com os dados existentes:
            df_mensalidades = pd.concat([df_mensalidades, df_filtrado], ignore_index=True)

        # Calcular total para 2024
        existing_months = [col for col in monthly_columns if col in df_mensalidades.columns]
        if existing_months:
            df_mensalidades['Total'] = df_mensalidades[existing_months].sum(axis=1)         
        else:
            print("Nenhuma coluna de meses encontrada no DataFrame.")
        
        # Salvar dados processados
        df_mensalidades.to_csv(mensalidades_file, index=False)
        print(f"Arquivo '{mensalidades_file}' criado com sucesso!")
        return df_mensalidades
    else:
        return pd.read_csv(mensalidades_file)
    
def processa_despesas():
    # Caminho da pasta de dados
    data_folder = os.path.join(os.getcwd(), 'despesas_nova')
    # Arquivo base
    despesas_file = os.path.join(os.getcwd(), 'despesas_file.csv')
    
    # Verificar se o arquivo existe e não está vazio
    if not os.path.exists(despesas_file) or os.path.getsize(despesas_file) == 0:

        # Initialize empty DataFrame
        df_despesas = pd.DataFrame()
        print("DataFrame df_despesas inicializado.")

        start = datetime.now()
        # Iterate through files in data folder 
        for filename in os.listdir(data_folder):
            file_path = os.path.join(data_folder, filename)
            if os.path.isfile(file_path) and filename.endswith('.csv'):
                # Read only specified columns
                df = pd.read_csv(file_path, encoding='latin1', sep=';', 
                    usecols=['CPF_DO_RESPONSAVEL', 'BENEFICIARIO', 'VALOR_DO_SERVICO'])
                df_despesas = pd.concat([df_despesas, df], ignore_index=True)
        # Convert columns to numeric
        df_despesas["VALOR_DO_SERVICO"] = pd.to_numeric(df_despesas["VALOR_DO_SERVICO"], errors="coerce").fillna(0).round(2)
        
        # Group by BENEFICIARIO and get the first occurrence of other columns while summing VALOR_DO_SERVICO
        df_despesas = df_despesas.groupby("BENEFICIARIO").agg({
            'CPF_DO_RESPONSAVEL': 'first',
            'VALOR_DO_SERVICO': 'sum'
        }).reset_index()

        print("Registros únicos por BENEFICIARIO com soma total calculada.")
        df_despesas['CPF_DO_RESPONSAVEL'] = df_despesas['CPF_DO_RESPONSAVEL'].apply(format_cpf)
        
        # Save the updated base file
        df_despesas.to_csv(despesas_file, index=False)
        print(f"Arquivo '{despesas_file}' criado com sucesso em {datetime.now() - start} segundos")
        return df_despesas
    else: 
        df_despesas = pd.read_csv(despesas_file)
        print(f"Arquivo '{despesas_file}' foi lido com sucesso.")
        return df_despesas

def processa_descontos():
    descontos_file = os.path.join(os.getcwd(), 'descontos_file.csv')
    excel_file = os.path.join(os.getcwd(), 'DESCONTOS.xlsx')
    
    if not os.path.exists(descontos_file) or os.path.getsize(descontos_file) == 0:
        df_descontos = pd.DataFrame()
        
        # Read all sheets from single Excel file
        excel = pd.ExcelFile(excel_file)
        for sheet_name in excel.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, engine="openpyxl",
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


        print("Registros únicos por Nome com soma total calculada.")
        
        # Save the updated base file
        df_descontos.to_csv(descontos_file, index=False)
        print(f"Arquivo '{descontos_file}' criado com sucesso")
        return df_descontos
    else: 
        df_descontos = pd.read_csv(descontos_file)
        print(f"Arquivo '{descontos_file}' foi lido com sucesso.")
        return df_descontos
    
def busca_dados_descontos(cpf_alvo):
    df_filtrado = busca_dados_mensalidades(cpf_alvo)
    df_descontos = processa_descontos()
    total_descontos = 0

    if not df_descontos.empty:
        if not df_filtrado.empty:
            for _, row in df_filtrado.iterrows():
                nome = str(row['Nome']).strip()
                if nome:
                    df_descontos['Nome'] = df_descontos['Nome'].astype(str).str.strip()
                    # Convert nome to string explicitly before using in contains()
                    pattern = str(nome)
                    matches = df_descontos[df_descontos['Nome'].str.contains(pattern, case=False, na=False, regex=False)]
                    if not matches.empty:
                        total_descontos += matches["Total de Descontos"].iloc[0]

    return total_descontos

def busca_dados_mensalidades(cpf_alvo):
    """
    Busca os dados das mensalidades do titular e seus dependentes com base no CPF do titular.
    Retorna um DataFrame com os nomes e valores das mensalidades.
    """
    df_filtrado = processa_mensalidades()
    
    if not df_filtrado.empty:
        # Formatar o CPF do titular e dos dependentes
        df_filtrado["Titular_CPF"] = df_filtrado["Titular_CPF"].apply(format_cpf)
        
        # Filtrar pelo CPF do titular (incluindo dependentes)
        df_filtrado = df_filtrado[df_filtrado["Titular_CPF"] == cpf_alvo]
        
        # Selecionar apenas as colunas necessárias
        df_filtrado = df_filtrado[['Nome', 'Total']].rename(columns={'Nome': 'Nome', 'Total': 'Valor'})
        
        # Formatar o valor como moeda
        df_filtrado["Valor"] = df_filtrado["Valor"].apply(format_currency)
    
    return df_filtrado

def busca_dados_despesas(cpf_alvo, nome):
    df_despesas = processa_despesas()
    if not df_despesas.empty:
        df_despesas["CPF_DO_RESPONSAVEL"] = df_despesas["CPF_DO_RESPONSAVEL"].apply(format_cpf)
        df_despesas = df_despesas[df_despesas["CPF_DO_RESPONSAVEL"] == cpf_alvo]
        total_despesas = df_despesas["VALOR_DO_SERVICO"].sum()
        print(f"Total de despesas: {total_despesas}")
        
        descontos = float(busca_dados_descontos(cpf_alvo))
        print(f"Descontos: {descontos}")
        diferenca = descontos - total_despesas
        print(f"Diferença: {diferenca}")

        mask = df_despesas["BENEFICIARIO"].str.contains(nome, case=False, na=False)
        remaining_mask = ~df_despesas["BENEFICIARIO"].str.contains(nome, case=False, na=False)
        remaining_count = remaining_mask.sum()
        total_remaining_mask = df_despesas.loc[remaining_mask, "VALOR_DO_SERVICO"].sum()
        print(f"Total do valor dos dependentes: {total_remaining_mask}")
        print(f"Quantidade de dependentes: {remaining_count}")

        
        if descontos > 0 and not mask.empty:    
            if diferenca > 0 or remaining_count == 0 or total_remaining_mask < diferenca:
                if total_remaining_mask < diferenca:
                    diferenca = diferenca - total_remaining_mask
                df_despesas.loc[mask, "VALOR_DO_SERVICO"] += diferenca
                    
            elif diferenca < 0 and remaining_count > 0 or mask.empty and remaining_count > 0:
                value_per_record = abs(diferenca) / remaining_count
                
                # First handle records with insufficient values
                insufficient_mask = remaining_mask & (df_despesas["VALOR_DO_SERVICO"] < value_per_record)
                if insufficient_mask.any():
                    insufficient_values = df_despesas.loc[insufficient_mask, "VALOR_DO_SERVICO"]
                    df_despesas.loc[insufficient_mask, "VALOR_DO_SERVICO"] = 0
                    diferenca += insufficient_values.sum()
                    
                    # Update remaining records
                    remaining_mask = remaining_mask & ~insufficient_mask
                    remaining_count = remaining_mask.sum()
                    
                    if remaining_count > 0:
                        value_per_record = abs(diferenca) / remaining_count
                
                # Process remaining records with sufficient values
                if remaining_count > 0:
                    df_despesas.loc[remaining_mask, "VALOR_DO_SERVICO"] -= value_per_record
        
        # Create new row for titular if not exists
        titular_mask = df_despesas["BENEFICIARIO"].str.contains(nome, case=False, na=False)
        if not titular_mask.any() and not df_despesas.empty:
            new_row = pd.DataFrame({
                'CPF_DO_RESPONSAVEL': [cpf_alvo],
                'BENEFICIARIO': [nome],
                'VALOR_DO_SERVICO': [diferenca]
            })
            df_despesas = pd.concat([df_despesas, new_row], ignore_index=True)
        else:
            df_despesas.loc[titular_mask, "VALOR_DO_SERVICO"] += diferenca

        df_despesas["VALOR_DO_SERVICO"] = df_despesas["VALOR_DO_SERVICO"].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        df_despesas = df_despesas[['BENEFICIARIO', 'VALOR_DO_SERVICO']].rename(
            columns={'BENEFICIARIO': 'Nome', 'VALOR_DO_SERVICO': 'Valor'}
        )
        
        if df_despesas.empty:
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
    titular = df_mensalidades.iloc[0]['Nome'] if not df_mensalidades.empty else "N/A"
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
    if not df_mensalidades.empty:
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

    # 5. DESCONTOS
    descontos_info = [f"Total de Descontos: {descontos}"]
    draw_section('5 - DESCONTOS', descontos_info)

    pdf.cell(0, 6, f'Documento criado em: {datetime.now().strftime("%d/%m/%Y")}', ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')
