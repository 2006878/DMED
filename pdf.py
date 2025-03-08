from fpdf import FPDF
import pandas as pd
from datetime import datetime

cpf_titular = input("Por favor, digite o CPF do titular: ")

df = pd.read_excel("mensalidades/IRF.xlsx", engine="openpyxl", skiprows=2, sheet_name="Mensalidade")

def gerar_pdf(df):
    if df.empty:
        print(f"Nenhuma família encontrada para o CPF {cpf_titular}")
        return
        
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(200, 10, "Relatório do Plano de Saúde", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    
    for i, row in df.iterrows():
        current_date = datetime.now().strftime("%d/%m/%Y")
        current_time = datetime.now().strftime("%H:%M")
        
        pdf.cell(200, 10, f"Data: {current_date}", ln=True)
        pdf.cell(200, 10, f"Hora: {current_time}", ln=True)
        pdf.ln(5)

        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(200, 10, "1 - DADOS CADASTRAIS", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, f"Nome: {row['Nome']}", ln=True)
        pdf.cell(200, 10, f"Matrícula: {row['Mat.']}", ln=True)
        pdf.cell(200, 10, f"CPF: {row['CPF']}", ln=True)
        pdf.cell(200, 10, f"Número do Usuário: {row['Nº usu.']}", ln=True)
        pdf.cell(200, 10, f"Parentesco: {row['Par.']}", ln=True)
        pdf.cell(200, 10, f"Data de Admissão: {row['Adm.']}", ln=True)
        pdf.ln(5)

        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(200, 10, "2 - MENSALIDADES 2024", ln=True)
        pdf.set_font("Arial", size=12)
        
        for month in range(1, 13):
            date_col = pd.Timestamp(f"2024-{month:02d}-01 00:00:00")
            if date_col in row.index:
                value = row[date_col]
                month_name = date_col.strftime("%B")
                pdf.cell(200, 10, f"{month_name}: R$ {value:.2f}", ln=True)
        
        pdf.ln(5)
        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(200, 10, "Total", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, f"Total 2024: R$ {row['Total 2024']:.2f}", ln=True)
        pdf.ln(10)

        nome_arquivo = f"relatorio_plano_saude_{row['CPF']}_{i+1}.pdf"
        
    pdf.output(nome_arquivo)

gerar_pdf(df)
