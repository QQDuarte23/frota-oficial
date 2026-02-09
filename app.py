import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Qerqueijo Frota", page_icon="🚛", layout="wide")

# CSS
st.markdown("""
    <style>
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #F0F2F6; }
    h1, h2, h3 { color: #002060; }
    .stButton>button { background-color: #002060; color: white; border: none; }
    .stButton>button:hover { background-color: #001540; color: white; }
    div.stImage > img { display: block; margin-left: auto; margin-right: auto; }
    </style>
    """, unsafe_allow_html=True)

NOME_FOLHA_GOOGLE = "dados_frota"

# --- LIGAÇÃO GOOGLE SHEETS (VERSÃO RESISTENTE A ERROS 🛡️) ---
def conectar_gsheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "service_account" in st.secrets:
            creds_dict = st.secrets["service_account"]
            
            # --- O TRUQUE ESTÁ AQUI ---
            if "gcp_json" in creds_dict:
                raw_json = creds_dict["gcp_json"]
                # strict=False diz ao Python: "Ignora o lixo invisível e lê na mesma!"
                creds_json = json.loads(raw_json, strict=False)
            else:
                creds_json = creds_dict
            # --------------------------

        else:
            st.error("❌ Erro: Não encontrei a chave 'service_account' nos Segredos!")
            return None
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        return client.open(NOME_FOLHA_GOOGLE).sheet1
    except Exception as e:
        st.error(f"❌ Erro de Ligação (Chave): {e}")
        return None

def carregar_dados():
    sheet = conectar_gsheets()
    if sheet:
        try:
            df = pd.DataFrame(sheet.get_all_records())
            if df.empty: return pd.DataFrame(columns=["Data_Registo", "Data_Fatura", "Matricula", "Categoria", "Valor", "KM_Atuais", "Num_Fatura", "Descricao"])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def guardar_registo(dados):
    sheet = conectar_gsheets()
    if sheet:
        try:
            sheet.append_row(dados)
            return True
        except Exception as e:
            st.error(f"❌ O Google recusou: {e}")
            return False
    return False

# --- FUNÇÃO LOGO ---
def mostrar_logo():
    try:
        st.image("logo.png", use_container_width=True)
    except:
        try:
            st.image(".streamlit/logo.png", use_container_width=True)
        except:
            st.header("QERQUEIJO 🧀")

# --- INTERFACE ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        st.write(""); st.write("")
        mostrar_logo()
        st.info("Gestão de Frota Cloud")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            if senha == "queijo123": st.session_state['logado'] = True
            else: st.error("Senha
