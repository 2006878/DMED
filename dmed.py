import streamlit as st
import io
from funcoes import *

# Streamlit page configuration
st.set_page_config(page_title=f"IRPF {ano_anterior}- COSEMI", layout="wide")
st.title(f"INFORME PLANO DE SAÚDE {ano_anterior} IRPF - COSEMI")

# Hide unnecessary UI elements
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)
    
# Add custom CSS to center content and style spinner
st.markdown("""
    <style>
    /* Center all content */
    .stApp {
        align-items: center;
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
    }
    
    /* Make spinner larger */
    .stSpinner > div {
        width: 100px !important;
        height: 100px !important;
        border-width: 6px !important;
    }
    
    /* Center title */
    h1 {
        text-align: center;
    }
    
    /* Center dataframe */
    [data-testid="stDataFrame"] {
        margin: 0 auto;
    }
    
    /* Center download button */
    [data-testid="stDownloadButton"] {
        display: block;
        margin: 2rem auto;
        max-width: 300px;
    }
    </style>
""", unsafe_allow_html=True)


st.markdown("<h3 style='font-size: 24px;'>Baixe o arquivo de importação DMED:</h3>", unsafe_allow_html=True)
import streamlit as st
from funcoes import *

# First load and cache the data
@st.cache_data
def load_data():
    return processa_mensalidades()

# Load the data
df = load_data()

if not df.empty:
    # Format Total column correctly
    df['Total'] = df['Total'].round(2).apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # Define columns to display
    colunas_desejadas = ['Nome', 'Empresa', 'Tipo de Plano', 'CPF', 'Titular_CPF', 'Relação', 'Total']
    
    # Show the dataframe
    st.dataframe(df[colunas_desejadas])
    
    with st.spinner("Criando arquivo..."):
        dmed_content = create_dmed_content(df)
        
        st.download_button(
            label="📥 Download DMED",
            data=dmed_content.encode('utf-8'),
            file_name=f"DMED_{datetime.now().strftime('%Y%m%d')}.DEC",
            mime="text/plain"
        )

        
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