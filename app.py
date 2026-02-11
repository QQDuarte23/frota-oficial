import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURAÇÃO GERAL E VISUAL ---
st.set_page_config(page_title="Qerqueijo Frota", page_icon="🚛", layout="wide")

# Lista fixa das tuas 24 viaturas
LISTA_VIATURAS = [
    "06-QO-19", "59-RT-87", "19-TF-05", "28-UO-50", "17-UM-19", "83-ZL-79", 
    "83-ZL-83", "AD-66-VN", "AD-71-VN", "AL-36-FF", "AL-30-FF", "AT-79-QU", 
    "AT-87-QU", "BE-64-TJ", "BE-16-TL", "BE-35-TJ", "BL-33-LG", "BL-68-LF", 
    "BR-83-SQ", "BU-45-NF", "BX-53-AB", "BO-08-DB", "AU-56-NT", "74-LU-19"
]

# CSS "Tanque de Guerra": Limpo, sem rodapés, menu a funcionar
st.markdown("""
    <style>
    /* Esconde barra de ferramentas direita e rodapé */
    [data-testid="stToolbar"] {visibility: hidden !important;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    
    /* Cabeçalho transparente para o menu funcionar */
    header[data-testid="stHeader"] {background: transparent !important;}
    
    /* Estilo Azul Qerqueijo */
    h1, h2, h3 { color: #002060; }
    .stButton>button { background-color: #002060; color: white; border: none; width: 100%; }
    .stButton>button:hover { background-color: #001540; color: white; }
    
    /* Ajuste para o Logo */
    div.stImage > img { display: block; margin-left: auto; margin-right: auto; }
    </style>
    """, unsafe_allow_html=True)

NOME_FOLHA_GOOGLE = "dados_frota"

# --- 2. LIGAÇÃO AO GOOGLE SHEETS ---
def conectar_gsheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "service_account" in st.secrets:
            creds_dict = st.secrets["service_account"]
            if "gcp_json" in creds_dict:
                creds_json = json.loads(creds_dict["gcp_json"])
            else:
                creds_json = creds_dict
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
            client = gspread.authorize(creds)
            return client.open(NOME_FOLHA_GOOGLE)
    except: return None

# --- 3. FUNÇÕES DE DADOS ---

# Carregar Faturas (Aba 1 do Excel)
def carregar_faturas():
    wb = conectar_gsheets()
    if wb:
        try:
            df = pd.DataFrame(wb.sheet1.get_all_records())
            if df.empty: return pd.DataFrame(columns=["Data_Fatura", "Matricula", "Categoria", "Valor", "KM_Atuais", "Num_Fatura", "Descricao"])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

# Carregar Validades (Aba 'Validades' do Excel)
def carregar_validades():
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            df_ex = pd.DataFrame(sheet.get_all_records())
            
            # Garante que as 24 matrículas aparecem, mesmo que o Excel esteja vazio
            df_base = pd.DataFrame({"Matricula": LISTA_VIATURAS})
            
            if not df_ex.empty:
                # Junta o que está no Excel com a lista fixa
                df_final = pd.merge(df_base, df_ex, on="Matricula", how="left").fillna("")
            else:
                # Se vazio, cria colunas em branco
                for c in ["Data_Seguro", "Data_Inspecao", "Data_IUC", "Observacoes"]:
                    df_base[c] = ""
                df_final = df_base
            return df_final
        except: return pd.DataFrame() # Retorna vazio se der erro
    return pd.DataFrame()

# Gravar Nova Fatura
def guardar_fatura(dados):
    wb = conectar_gsheets()
    if wb:
        try:
            wb.sheet1.append_row(dados)
            return True
        except: return False
    return False

# Atualizar TODA a tabela de Validades (Para quando editas na tabela)
def salvar_tabela_validades(df_novo):
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            sheet.clear() # Limpa tudo
            # Escreve de novo (Cabeçalhos + Dados)
            dados_lista = [df_novo.columns.values.tolist()] + df_novo.astype(str).values.tolist()
            sheet.update(dados_lista)
            return True
        except: return False
    return False

# Função Inteligente do Logo (Procura em todo o
